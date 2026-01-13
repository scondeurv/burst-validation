use std::{
    time::{SystemTime, UNIX_EPOCH},
};
use ahash::{AHashMap, AHashSet};
use futures::future::join_all;

use aws_config::Region;
use aws_credential_types::Credentials;
use aws_sdk_s3::Client as S3Client;
use burst_communication_middleware::{Middleware, MiddlewareActorHandle};
use bytes::Bytes;
use serde_derive::{Deserialize, Serialize};
use serde_json::{Error, Value};
use tokio::io::AsyncBufReadExt;

const ROOT_WORKER: u32 = 0;
const MAX_ITER: u32 = 30;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
struct Input {
    input_data: S3InputParams,
    error: f64,
    iterations: Option<u32>,
    num_nodes: u32,
    partitions: u32,
    granularity: u32,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
struct S3InputParams {
    bucket: String,
    key: String,
    region: String,
    endpoint: Option<String>,
    aws_access_key_id: String,
    aws_secret_access_key: String,
    aws_session_token: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
struct Output {
    bucket: String,
    key: String,
    timestamps: Vec<Timestamp>,
    #[serde(skip_serializing_if = "Option::is_none")]
    page_ranks: Option<Vec<f64>>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
struct Timestamp {
    key: String,
    value: String,
}

fn timestamp(key: String) -> Timestamp {
    let current_system_time = SystemTime::now();
    let duration_since_epoch = current_system_time.duration_since(UNIX_EPOCH).unwrap();
    let milliseconds_timestamp = duration_since_epoch.as_millis();
    Timestamp {
        key,
        value: milliseconds_timestamp.to_string(),
    }
}

#[derive(Debug, Clone)]
pub struct PagerankMessage(Vec<f64>);

impl From<Bytes> for PagerankMessage {
    fn from(bytes: Bytes) -> Self {
        // println!("Cast from bytes, size is {:?}", bytes.len());

        let mut vecu8 = bytes.to_vec();
        let vecf64 = unsafe {
            let ratio = std::mem::size_of::<f64>() / std::mem::size_of::<u8>();
            let length = vecu8.len() / ratio;
            let capacity = vecu8.capacity() / ratio;
            let ptr = vecu8.as_mut_ptr() as *mut f64;

            // Don't run the destructor for vec32
            std::mem::forget(vecu8);

            // Construct new Vec
            Vec::from_raw_parts(ptr, length, capacity)
        };
        PagerankMessage(vecf64)
    }
}

impl From<PagerankMessage> for Bytes {
    fn from(mut val: PagerankMessage) -> Self {
        let vec8 = unsafe {
            let ratio = std::mem::size_of::<f64>() / std::mem::size_of::<u8>();
            let length = val.0.len() * ratio;
            let capacity = val.0.capacity() * ratio;
            let ptr = val.0.as_mut_ptr() as *mut u8;

            // Don't run the destructor for vec32
            std::mem::forget(val.0);

            // Construct new Vec
            Vec::from_raw_parts(ptr, length, capacity)
        };
        let b = Bytes::from(vec8);
        // println!("Cast to bytes, size is {:?}", b.len());
        b
    }
}

async fn load_partition_flat(
    params: &Input,
    s3_client: &S3Client,
    worker_id: u32,
) -> (Vec<u32>, Vec<u32>, Vec<u32>) {
    let start_part = worker_id * params.granularity;
    let end_part = (worker_id + 1) * params.granularity;
    
    let mut fetch_futures = Vec::new();

    for p in start_part..end_part {
        let part_key = format!("{}/part-{}", params.input_data.key, p);
        fetch_futures.push(async move {
            s3_client
                .get_object()
                .bucket(&params.input_data.bucket)
                .key(&part_key)
                .send()
                .await
        });
    }

    let results = join_all(fetch_futures).await;
    let mut edges = Vec::with_capacity(100_000 * params.granularity as usize);

    for result in results {
        if let Ok(output) = result {
            if let Ok(data) = output.body.collect().await {
                let bytes = data.to_vec();
                if let Ok(body_str) = std::str::from_utf8(&bytes) {
                    for line in body_str.lines() {
                        if line.trim().is_empty() { continue; }
                        let mut it = line.split('\t');
                        let src = it.next().and_then(|s| s.parse::<u32>().ok());
                        let dst = it.next().and_then(|s| s.parse::<u32>().ok());
                        if let (Some(s), Some(d)) = (src, dst) {
                            edges.push((s, d));
                        }
                    }
                }
            }
        }
    }

    if edges.is_empty() {
        return (Vec::new(), vec![0; (params.num_nodes + 1) as usize], Vec::new());
    }

    // Sort edges by source node to build CSR
    edges.sort_unstable_by_key(|e| e.0);

    let mut flat_edges = Vec::with_capacity(edges.len());
    let mut offsets = vec![0u32; (params.num_nodes + 1) as usize];
    let mut owned_nodes = Vec::new();
    
    if !edges.is_empty() {
        let mut current_node = edges[0].0;
        owned_nodes.push(current_node);
        let mut count = 0;
        let mut last_offset = 0;
        
        for (src, dst) in edges {
            if src != current_node {
                // Fill offsets for all nodes between current and src
                for i in (current_node as usize + 1)..=(src as usize) {
                    offsets[i] = last_offset + count;
                }
                last_offset += count;
                current_node = src;
                owned_nodes.push(src);
                count = 0;
            }
            flat_edges.push(dst);
            count += 1;
        }
        // Fill remaining offsets
        for i in (current_node as usize + 1)..=params.num_nodes as usize {
            offsets[i] = last_offset + count;
        }
    }

    (flat_edges, offsets, owned_nodes)
}

fn pagerank(params: Input, burst_middleware: &MiddlewareActorHandle<PagerankMessage>) -> Output {
    let mut timestamps = Vec::new();
    timestamps.push(timestamp("worker_start".to_string()));

    let worker = burst_middleware.info.worker_id;
    println!(
        "[Worker {}] Starting pagerank: {:?}",
        burst_middleware.info.worker_id, params
    );
    // create s3 client
    let credentials_provider = Credentials::new(
        params.input_data.aws_access_key_id.clone(),
        params.input_data.aws_secret_access_key.clone(),
        params.input_data.aws_session_token.clone(),
        None,
        "static",
    );

    let config = match params.input_data.endpoint.clone() {
        Some(endpoint) => {
            aws_sdk_s3::config::Builder::new()
                .endpoint_url(endpoint)
                .credentials_provider(credentials_provider)
                .region(Region::new(params.input_data.region.clone()))
                .force_path_style(true)
                .build()
        }
        None => aws_sdk_s3::config::Builder::new()
            .credentials_provider(credentials_provider)
            .region(Region::new(params.input_data.region.clone()))
            .build(),
    };
    let s3_client = S3Client::from_conf(config);

    let tokio_runtime = tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build()
        .unwrap();

    let init_pagerank = 1.0 / params.num_nodes as f64;
    let mut page_ranks = vec![init_pagerank; params.num_nodes as usize];
    let mut err = f64::MAX;
    let mut iter = 0;
    let mut sum = vec![0.0; params.num_nodes as usize];
    
    timestamps.push(timestamp("get_input".to_string()));
    let (flat_edges, offsets, owned_nodes) = tokio_runtime.block_on(load_partition_flat(&params, &s3_client, worker));
    timestamps.push(timestamp("get_input_end".to_string()));

    println!("[Worker {}] Owned nodes: {}, Edges: {}", worker, owned_nodes.len(), flat_edges.len());
    
    let mut inv_out_links = vec![0.0; params.num_nodes as usize];
    for &node in &owned_nodes {
        let count = offsets[node as usize + 1] - offsets[node as usize];
        if count > 0 {
            inv_out_links[node as usize] = 1.0 / count as f64;
        }
    }

    let iterations = params.iterations.unwrap_or(MAX_ITER);
    while iter < iterations {
        let iter_t0 = SystemTime::now();

        let pr_msg = if burst_middleware.info.worker_id == ROOT_WORKER {
            burst_middleware
                .broadcast(Some(PagerankMessage(page_ranks.clone())), ROOT_WORKER)
                .unwrap()
        } else {
            burst_middleware.broadcast(None, ROOT_WORKER).unwrap()
        };
        page_ranks = pr_msg.0;

        timestamps.push(timestamp(format!("iter_{}_broadcast_weights", iter)));

        // Core PageRank Loop
        for &node in &owned_nodes {
            let idx = node as usize;
            let weight = page_ranks[idx] * inv_out_links[idx];
            let start = offsets[idx] as usize;
            let end = offsets[idx + 1] as usize;
            
            for i in start..end {
                let target = flat_edges[i] as usize;
                if target < sum.len() {
                    sum[target] += weight;
                }
            }
        }

        timestamps.push(timestamp(format!("iter_{}_calc_sums", iter)));

        let sum_msg = burst_middleware
            .reduce(PagerankMessage(std::mem::take(&mut sum)), |mut vec1, vec2| {
                for (a, b) in vec1.0.iter_mut().zip(vec2.0.iter()) {
                    *a += b;
                }
                vec1
            })
            .unwrap();
        
        sum = vec![0.0; params.num_nodes as usize];
        
        timestamps.push(timestamp(format!("iter_{}_reduce", iter)));

        let new_norm = if let Some(x) = sum_msg {
            let new_page_ranks = x.0;
            err = new_page_ranks
                .iter()
                .zip(page_ranks.iter())
                .map(|(a, b)| (a - b).powi(2))
                .sum::<f64>()
                .sqrt();

            page_ranks = new_page_ranks;
            Some(PagerankMessage(vec![err]))
        } else {
            None
        };
        timestamps.push(timestamp(format!("iter_{}_calc_err", iter)));

        err = burst_middleware
            .broadcast(new_norm, ROOT_WORKER)
            .unwrap()
            .0
            .pop()
            .unwrap();
        
        timestamps.push(timestamp(format!("iter_{}_broadcast_err", iter)));

        let iter_t = SystemTime::now().duration_since(iter_t0).unwrap().as_secs_f32();
        println!(
            "[Worker {}] Iteration {} took {:.4} s, err={:.6}",
            worker, iter, iter_t, err
        );

        timestamps.push(timestamp(format!("iter_{}_end", iter)));
        iter += 1;
    }

    timestamps.push(timestamp("worker_end".to_string()));
    Output {
        bucket: params.input_data.bucket.clone(),
        key: params.input_data.key.clone(),
        timestamps,
        page_ranks: if worker == ROOT_WORKER {
            Some(page_ranks)
        } else {
            None
        },
    }
}

// ow_main would be the entry point of an actual open whisk burst worker
pub fn main(args: Value, burst_middleware: Middleware<PagerankMessage>) -> Result<Value, Error> {
    let input: Input = serde_json::from_value(args)?;
    let burst_middleware = burst_middleware.get_actor_handle();

    let result = pagerank(input, &burst_middleware);

    serde_json::to_value(result)
}

// main function acts as a wrapper of what the OW runtime would do, used for debugging
// #[tokio::main]
// async fn main() {
//     let file = File::open("sort_payload.json").unwrap();
//     let inputs: Vec<Input> = serde_json::from_reader(file).unwrap();

//     let burst_size = 4;
//     let mut group_ranges: HashMap<String, HashSet<u32>> = HashMap::new();
//     let range = (0..burst_size).collect::<HashSet<u32>>();
//     group_ranges.insert("0".to_string(), range);

//     let proxies = match BurstMiddleware::create_proxies::<TokioChannelImpl, RabbitMQMImpl, _, _>(
//         BurstOptions::new(
//             "terasort".to_string(),
//             burst_size,
//             group_ranges,
//             0.to_string(),
//         ),
//         TokioChannelOptions::new()
//             .broadcast_channel_size(256)
//             .build(),
//         RabbitMQOptions::new(inputs[0].rabbitmq_config.uri.clone())
//             .durable_queues(true)
//             .ack(true)
//             .build(),
//     )
//     .await
//     {
//         Ok(p) => p,
//         Err(e) => {
//             // error!("{:?}", e);
//             println!("{:?}", e);
//             panic!();
//         }
//     };

//     let mut threads = Vec::with_capacity(inputs.len());
//     for (proxy, input) in zip(proxies, inputs) {
//         let (idx, middleware) = proxy;
//         let thread = thread::spawn(move || {
//             println!("thread start: id={}", idx);
//             let result = ow_main(serde_json::to_value(input).unwrap(), middleware).unwrap();
//             println!("thread end: id={}", idx);
//             result
//         });
//         threads.push(thread);
//     }

//     for (i, t) in threads.into_iter().enumerate() {
//         let result = t.join().unwrap();
//         // write output to file, this would be the response of OW invokation
//         let file = File::create(format!("output_{}.json", i)).unwrap();
//         serde_json::to_writer(file, &result).unwrap();
//     }
// }
