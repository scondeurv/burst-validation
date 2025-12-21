use std::{
    cmp::Ordering,
    collections::HashMap,
    time::{SystemTime, UNIX_EPOCH},
};

use aws_config::Region;
use aws_credential_types::Credentials;
use aws_sdk_s3::Client as S3Client;
use burst_communication_middleware::{Middleware, MiddlewareActorHandle};
use bytes::Bytes;
use serde_derive::{Deserialize, Serialize};
use serde_json::{Error, Value};
use tokio::io::AsyncBufReadExt;

const ROOT_WORKER: u32 = 0;
const MAX_ITER: u32 = 50;
const UNKNOWN: u32 = u32::MAX;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
struct Input {
    input_data: S3InputParams,
    num_nodes: u32,
    max_iterations: Option<u32>,
    convergence_threshold: Option<u32>,
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
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
struct Timestamp {
    key: String,
    value: String,
}

fn timestamp(key: &str) -> Timestamp {
    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_millis();
    Timestamp {
        key: key.to_string(),
        value: now.to_string(),
    }
}

/// Full label vector message (one `u32` per node)
#[derive(Debug, Clone)]
pub struct LabelsMessage(pub Vec<u32>);

impl From<Bytes> for LabelsMessage {
    fn from(bytes: Bytes) -> Self {
        let mut vecu8 = bytes.to_vec();
        let vecu32 = unsafe {
            let ratio = std::mem::size_of::<u32>() / std::mem::size_of::<u8>();
            let length = vecu8.len() / ratio;
            let capacity = vecu8.capacity() / ratio;
            let ptr = vecu8.as_mut_ptr() as *mut u32;
            std::mem::forget(vecu8);
            Vec::from_raw_parts(ptr, length, capacity)
        };
        LabelsMessage(vecu32)
    }
}

impl From<LabelsMessage> for Bytes {
    fn from(mut val: LabelsMessage) -> Self {
        let vec8 = unsafe {
            let ratio = std::mem::size_of::<u32>() / std::mem::size_of::<u8>();
            let length = val.0.len() * ratio;
            let capacity = val.0.capacity() * ratio;
            let ptr = val.0.as_mut_ptr() as *mut u8;
            std::mem::forget(val.0);
            Vec::from_raw_parts(ptr, length, capacity)
        };
        Bytes::from(vec8)
    }
}

/// Count message for convergence (single u64)
#[derive(Debug, Clone)]
struct CountMessage(pub u64);

impl From<Bytes> for CountMessage {
    fn from(bytes: Bytes) -> Self {
        let mut arr = [0u8; 8];
        arr.copy_from_slice(&bytes[..8]);
        CountMessage(u64::from_le_bytes(arr))
    }
}

impl From<CountMessage> for Bytes {
    fn from(val: CountMessage) -> Self {
        Bytes::from(val.0.to_le_bytes().to_vec())
    }
}

/// Load adjacency for this worker partition.
/// Each line format: `src\tdst[\tlabel]` where `label` is optional initial label.
async fn load_partition(
    params: &Input,
    s3_client: &S3Client,
    worker_id: u32,
    burst_size: u32,
) -> (HashMap<u32, Vec<u32>>, HashMap<u32, u32>) {
    let reader = s3_client
        .get_object()
        .bucket(&params.input_data.bucket)
        .key(&params.input_data.key)
        .send()
        .await
        .unwrap()
        .body
        .into_async_read();

    let mut lines = reader.lines();
    let mut graph: HashMap<u32, Vec<u32>> = HashMap::new();
    let mut initial_labels: HashMap<u32, u32> = HashMap::new();

    while let Some(line) = lines.next_line().await.unwrap() {
        if line.trim().is_empty() {
            continue;
        }
        let parts: Vec<&str> = line.split('\t').collect();
        if parts.len() < 2 {
            continue;
        }
        let src: u32 = parts[0].parse().unwrap();
        if src % burst_size != worker_id {
            continue;
        }
        let dst: u32 = parts[1].parse().unwrap();
        graph.entry(src).or_default().push(dst);
        if parts.len() >= 3 {
            let label: i64 = parts[2].parse().unwrap_or(-1);
            if label >= 0 {
                initial_labels.insert(src, label as u32);
            }
        }
    }

    (graph, initial_labels)
}

fn should_continue(iter: u32, max_iter: Option<u32>, changed: u32, threshold: u32) -> bool {
    let under_threshold = changed <= threshold;
    let under_iter = match max_iter {
        Some(m) => iter < m,
        None => iter < MAX_ITER,
    };
    under_iter && !under_threshold
}

fn majority_label(counts: &HashMap<u32, usize>, current: u32) -> u32 {
    if counts.is_empty() {
        return current;
    }
    let mut best = current;
    let mut best_count = 0usize;
    for (label, count) in counts {
        if *label == UNKNOWN {
            continue;
        }
        match count.cmp(&best_count) {
            Ordering::Greater => {
                best = *label;
                best_count = *count;
            }
            Ordering::Equal => {
                if *label < best {
                    best = *label;
                }
            }
            Ordering::Less => {}
        }
    }
    best
}

fn label_propagation(
    params: Input,
    middleware: &MiddlewareActorHandle<LabelsMessage>,
) -> Output {
    let mut timestamps = vec![timestamp("worker_start")];

    let worker = middleware.info.worker_id;
    let burst_size = middleware.info.burst_size;
    println!(
        "[Worker {worker}] starting label propagation (burst_size={burst_size}, num_nodes={})",
        params.num_nodes
    );

    // S3 client
    let credentials_provider = Credentials::from_keys(
        params.input_data.aws_access_key_id.clone(),
        params.input_data.aws_secret_access_key.clone(),
        params.input_data.aws_session_token.clone(),
    );

    let config = match params.input_data.endpoint.clone() {
        Some(endpoint) => aws_sdk_s3::config::Builder::new()
            .endpoint_url(endpoint)
            .credentials_provider(credentials_provider)
            .region(Region::new(params.input_data.region.clone()))
            .force_path_style(true)
            .build(),
        None => aws_sdk_s3::config::Builder::new()
            .credentials_provider(credentials_provider)
            .region(Region::new(params.input_data.region.clone()))
            .build(),
    };
    let s3_client = S3Client::from_conf(config);
    let rt = tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build()
        .unwrap();

    // Load partition
    timestamps.push(timestamp("get_input"));
    let (graph, initial_labels) = rt.block_on(load_partition(&params, &s3_client, worker, burst_size));
    timestamps.push(timestamp("get_input_end"));

    let mut labels = vec![UNKNOWN; params.num_nodes as usize];
    for (node, label) in initial_labels.iter() {
        if (*node as usize) < labels.len() {
            labels[*node as usize] = *label;
        }
    }

    // Reduce initial labels to build a consistent global view, then broadcast
    let initial_msg = LabelsMessage(labels.clone());
    let combined = middleware
        .reduce(initial_msg, |left, right| {
            let merged = left
                .0
                .iter()
                .zip(right.0.iter())
                .map(|(a, b)| if *a != UNKNOWN { *a } else { *b })
                .collect();
            LabelsMessage(merged)
        })
        .unwrap();

    let mut global_labels = if let Some(msg) = combined {
        middleware.broadcast(Some(msg), ROOT_WORKER).unwrap()
    } else {
        middleware.broadcast(None, ROOT_WORKER).unwrap()
    };

    let max_iter = params.max_iterations.unwrap_or(MAX_ITER);
    let threshold = params.convergence_threshold.unwrap_or(0);
    let mut iter = 0;

    while iter < max_iter {
        timestamps.push(timestamp(&format!("iter_{}_start", iter)));

        // Broadcast current labels so every worker has a consistent view
        global_labels = if middleware.info.worker_id == ROOT_WORKER {
            middleware
                .broadcast(Some(LabelsMessage(global_labels.0.clone())), ROOT_WORKER)
                .unwrap()
        } else {
            middleware.broadcast(None, ROOT_WORKER).unwrap()
        };
        timestamps.push(timestamp(&format!("iter_{}_broadcast_labels", iter)));

        let mut local_updates = vec![UNKNOWN; labels.len()];
        let mut local_changed: u64 = 0;

        for (node, neighbors) in graph.iter() {
            let idx = *node as usize;
            let current_label = global_labels.0.get(idx).cloned().unwrap_or(UNKNOWN);

            // Clamp labeled nodes
            if initial_labels.contains_key(node) {
                local_updates[idx] = current_label;
                continue;
            }

            let mut counts: HashMap<u32, usize> = HashMap::new();
            for neighbor in neighbors {
                let n_idx = *neighbor as usize;
                if let Some(label) = global_labels.0.get(n_idx) {
                    *counts.entry(*label).or_insert(0) += 1;
                }
            }

            let new_label = majority_label(&counts, current_label);
            local_updates[idx] = new_label;
            if new_label != current_label {
                local_changed += 1;
            }
        }
        timestamps.push(timestamp(&format!("iter_{}_compute", iter)));

        let reduced_labels = middleware
            .reduce(LabelsMessage(local_updates), |left, right| {
                let merged = left
                    .0
                    .iter()
                    .zip(right.0.iter())
                    .map(|(a, b)| if *a != UNKNOWN { *a } else { *b })
                    .collect();
                LabelsMessage(merged)
            })
            .unwrap();
        timestamps.push(timestamp(&format!("iter_{}_reduce_labels", iter)));

        let reduced_changed = middleware
            .reduce(
                LabelsMessage(vec![local_changed as u32]),
                |a, b| LabelsMessage(vec![a.0[0].saturating_add(b.0[0])]),
            )
            .unwrap();
        timestamps.push(timestamp(&format!("iter_{}_reduce_changed", iter)));

        // Check convergence and broadcast result to all workers
        let should_stop = if middleware.info.worker_id == ROOT_WORKER {
            if let Some(msg) = reduced_labels {
                global_labels = msg;
            }
            if let Some(count_msg) = reduced_changed {
                let total_changed = count_msg.0[0];
                println!(
                    "[Worker {worker}] iteration {iter}: total_changed={total_changed} threshold={threshold}"
                );
                !should_continue(iter, params.max_iterations, total_changed, threshold)
            } else {
                false
            }
        } else {
            false
        };

        // Broadcast stop decision to all workers (0 = continue, 1 = stop)
        let stop_signal = middleware
            .broadcast(
                if middleware.info.worker_id == ROOT_WORKER {
                    Some(LabelsMessage(vec![if should_stop { 1 } else { 0 }]))
                } else {
                    None
                },
                ROOT_WORKER,
            )
            .unwrap();

        if stop_signal.0[0] == 1 {
            // Broadcast final labels before stopping
            if middleware.info.worker_id == ROOT_WORKER {
                middleware
                    .broadcast(Some(LabelsMessage(global_labels.0.clone())), ROOT_WORKER)
                    .ok();
            }
            break;
        }

        iter += 1;
        timestamps.push(timestamp(&format!("iter_{}_end", iter)));
    }

    timestamps.push(timestamp("worker_end"));
    Output {
        bucket: params.input_data.bucket.clone(),
        key: format!("worker-{}", worker),
        timestamps,
    }
}

pub fn main(args: Value, burst_middleware: Middleware<LabelsMessage>) -> Result<Value, Error> {
    let input: Input = serde_json::from_value(args)?;
    let handle = burst_middleware.get_actor_handle();
    let result = label_propagation(input, &handle);
    serde_json::to_value(result)
}
