use std::{
    cmp::Ordering,
    time::{SystemTime, UNIX_EPOCH},
};
use ahash::AHashMap as HashMap;

use aws_config::Region;
use aws_credential_types::Credentials;
use aws_sdk_s3::Client as S3Client;
use burst_communication_middleware::{Middleware, MiddlewareActorHandle};
use bytes::Bytes;
use futures::future::join_all;
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
    labels: Option<Vec<u32>>,
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
#[derive(Debug, Clone, PartialEq)]
pub struct LabelsMessage(pub Vec<u32>);

impl From<Bytes> for LabelsMessage {
    fn from(bytes: Bytes) -> Self {
        let vecu32 = bytes
            .chunks_exact(4)
            .map(|chunk| {
                let arr: [u8; 4] = chunk.try_into().unwrap();
                u32::from_le_bytes(arr)
            })
            .collect();
        LabelsMessage(vecu32)
    }
}

impl From<LabelsMessage> for Bytes {
    fn from(val: LabelsMessage) -> Self {
        let mut bytes = Vec::with_capacity(val.0.len() * 4);
        for num in val.0 {
            bytes.extend_from_slice(&num.to_le_bytes());
        }
        Bytes::from(bytes)
    }
}

/// Count message for convergence (single u64)
#[derive(Debug, Clone)]
struct CountMessage(pub u64);

struct CSRGraph {
    owned_nodes: Vec<u32>,
    offsets: Vec<u32>,
    flat_edges: Vec<u32>,
}

impl From<Bytes> for CountMessage {
    fn from(bytes: Bytes) -> Self {
        let mut arr = [0u8; 8];
        if bytes.len() >= 8 {
            arr.copy_from_slice(&bytes[..8]);
        }
        CountMessage(u64::from_le_bytes(arr))
    }
}

impl From<CountMessage> for Bytes {
    fn from(val: CountMessage) -> Self {
        Bytes::from(val.0.to_le_bytes().to_vec())
    }
}

/// Load adjacency for this worker partition.
async fn load_partition_flat(
    params: &Input,
    s3_client: &S3Client,
    worker_id: u32,
) -> (CSRGraph, Vec<(u32, u32)>) {
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
    let mut initial_labels = Vec::new();

    let mut all_found = true;
    for result in results {
        match result {
            Ok(output) => {
                if let Ok(data) = output.body.collect().await {
                    let bytes = data.to_vec();
                    if let Ok(body_str) = std::str::from_utf8(&bytes) {
                        for line in body_str.lines() {
                            if line.trim().is_empty() { continue; }
                            let mut it = line.split('\t');
                            let src = it.next().and_then(|s| s.parse::<u32>().ok());
                            let dst = it.next().and_then(|s| s.parse::<u32>().ok());
                            let label = it.next().and_then(|s| s.parse::<i64>().ok());
                            if let (Some(s), Some(d)) = (src, dst) {
                                edges.push((s, d));
                                if let Some(l) = label { if l >= 0 { initial_labels.push((s, l as u32)); } }
                            }
                        }
                    }
                } else { all_found = false; break; }
            }
            Err(_) => { all_found = false; break; }
        }
    }

    if !all_found || edges.is_empty() {
        println!("[Worker {}] Falling back to full graph: {}", worker_id, params.input_data.key);
        if let Ok(output) = s3_client.get_object().bucket(&params.input_data.bucket).key(&params.input_data.key).send().await {
            if let Ok(data) = output.body.collect().await {
                let bytes = data.to_vec();
                if let Ok(body_str) = std::str::from_utf8(&bytes) {
                    for line in body_str.lines() {
                        if line.trim().is_empty() { continue; }
                        let mut it = line.split('\t');
                        let src = it.next().and_then(|s| s.parse::<u32>().ok());
                        let dst = it.next().and_then(|s| s.parse::<u32>().ok());
                        let label = it.next().and_then(|s| s.parse::<i64>().ok());
                        if let (Some(s), Some(d)) = (src, dst) {
                            let target_worker = (s % params.partitions) / params.granularity;
                            if target_worker == worker_id {
                                edges.push((s, d));
                                if let Some(l) = label { if l >= 0 { initial_labels.push((s, l as u32)); } }
                            }
                        }
                    }
                }
            }
        }
    }

    edges.sort_unstable_by_key(|e| e.0);
    let mut owned_nodes = Vec::new();
    let mut offsets = vec![0u32; (params.num_nodes + 1) as usize];
    let mut flat_edges = Vec::with_capacity(edges.len());
    let mut current_offset = 0u32;
    let mut edge_idx = 0;
    for n in 0..params.num_nodes {
        offsets[n as usize] = current_offset;
        let mut found = false;
        while edge_idx < edges.len() && edges[edge_idx].0 == n {
            flat_edges.push(edges[edge_idx].1);
            edge_idx += 1;
            current_offset += 1;
            found = true;
        }
        if found { owned_nodes.push(n); }
    }
    offsets[params.num_nodes as usize] = current_offset;

    println!("[Worker {}] Final graph size: {} owned nodes, {} edges", worker_id, owned_nodes.len(), flat_edges.len());
    (CSRGraph { owned_nodes, offsets, flat_edges }, initial_labels)
}

fn should_continue(iter: u32, max_iter: Option<u32>, changed: u32, threshold: u32) -> bool {
    let under_threshold = changed <= threshold;
    let under_iter = match max_iter {
        Some(m) => iter < m,
        None => iter < MAX_ITER,
    };
    under_iter && !under_threshold
}

fn majority_label(counts: &mut HashMap<u32, usize>, current: u32) -> u32 {
    if counts.is_empty() {
        return current;
    }
    let mut best = current;
    let mut best_count = 0usize;
    for (label, count) in counts.iter() {
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
    counts.clear();
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
    let (graph, initial_labels_vec) = rt.block_on(load_partition_flat(&params, &s3_client, worker));
    timestamps.push(timestamp("get_input_end"));

    // Initialize labels
    let mut labels = vec![UNKNOWN; params.num_nodes as usize];
    let mut initial_labels = HashMap::default();
    for (node, label) in initial_labels_vec {
        if (node as usize) < labels.len() {
            labels[node as usize] = label;
            initial_labels.insert(node, label);
        }
    }

    // Check globally if any worker has seeds
    let local_has_seeds_val = if !initial_labels.is_empty() { 1 } else { 0 };
    let reduced_seeds_msg = middleware
        .reduce(LabelsMessage(vec![local_has_seeds_val]), |mut a, b| {
            if a.0[0] == 1 || b.0[0] == 1 { a.0[0] = 1; }
            a
        })
        .unwrap();

    let global_seeds_msg = if let Some(msg) = reduced_seeds_msg {
        middleware.broadcast(Some(msg), ROOT_WORKER).unwrap()
    } else {
        middleware.broadcast(None, ROOT_WORKER).unwrap()
    };
    let global_has_seeds = global_seeds_msg.0[0] == 1;
    
    // Unsupervised mode setup
    if !global_has_seeds && initial_labels.is_empty() {
        println!("[Worker {}] No initial labels found globally, using unsupervised mode", worker);
        for &idx in &graph.owned_nodes {
            labels[idx as usize] = idx;
        }
    }

    // Initial labels reduction
    let initial_msg = LabelsMessage(labels);
    let combined = middleware
        .reduce(initial_msg, |mut left, right| {
            for (a, b) in left.0.iter_mut().zip(right.0.iter()) {
                if *a == UNKNOWN { *a = *b; }
            }
            left
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
    let unsupervised_mode = !global_has_seeds;
    let mut counts_map = HashMap::default();

    while iter < max_iter {
        timestamps.push(timestamp(&format!("iter_{}_start", iter)));

        global_labels = if worker == ROOT_WORKER {
            middleware.broadcast(Some(LabelsMessage(global_labels.0)), ROOT_WORKER).unwrap()
        } else {
            middleware.broadcast(None, ROOT_WORKER).unwrap()
        };
        timestamps.push(timestamp(&format!("iter_{}_broadcast_labels", iter)));

        let mut local_updates = vec![UNKNOWN; params.num_nodes as usize];
        let mut local_changed: u32 = 0;

        for &node in &graph.owned_nodes {
            let idx = node as usize;
            let current_label = global_labels.0[idx];

            if !unsupervised_mode && initial_labels.contains_key(&node) {
                local_updates[idx] = current_label;
                continue;
            }

            let start = graph.offsets[idx];
            let end = graph.offsets[idx + 1];
            
            for i in start..end {
                let neighbor = graph.flat_edges[i as usize] as usize;
                let label = global_labels.0[neighbor];
                if label != UNKNOWN {
                    *counts_map.entry(label).or_insert(0) += 1;
                }
            }

            let new_label = majority_label(&mut counts_map, current_label);
            local_updates[idx] = new_label;
            if new_label != current_label {
                local_changed += 1;
            }
        }
        timestamps.push(timestamp(&format!("iter_{}_compute", iter)));

        let reduced_labels = middleware
            .reduce(LabelsMessage(local_updates), |mut left, right| {
                for (a, b) in left.0.iter_mut().zip(right.0.iter()) {
                    if *a == UNKNOWN { *a = *b; }
                }
                left
            })
            .unwrap();
        timestamps.push(timestamp(&format!("iter_{}_reduce_labels", iter)));

        let reduced_changed = middleware
            .reduce(LabelsMessage(vec![local_changed]), |mut a, b| {
                a.0[0] = a.0[0].saturating_add(b.0[0]);
                a
            })
            .unwrap();
        timestamps.push(timestamp(&format!("iter_{}_reduce_changed", iter)));

        let should_stop = if worker == ROOT_WORKER {
            if let Some(msg) = reduced_labels { global_labels = msg; }
            if let Some(count_msg) = reduced_changed {
                let total_changed = count_msg.0[0];
                println!("[Worker {worker}] iter {iter}: changed={total_changed}");
                !should_continue(iter, params.max_iterations, total_changed, threshold)
            } else { false }
        } else { false };

        let stop_signal = middleware.broadcast(
            if worker == ROOT_WORKER { Some(LabelsMessage(vec![if should_stop { 1 } else { 0 }])) } else { None },
            ROOT_WORKER
        ).unwrap();

        if stop_signal.0[0] == 1 { break; }
        iter += 1;
        timestamps.push(timestamp(&format!("iter_{}_end", iter)));
    }

    timestamps.push(timestamp("worker_end"));
    Output {
        bucket: params.input_data.bucket.clone(),
        key: format!("worker-{}", worker),
        timestamps,
        labels: None,
    }
}

pub fn main(args: Value, burst_middleware: Middleware<LabelsMessage>) -> Result<Value, Error> {
    let input: Input = serde_json::from_value(args)?;
    let handle = burst_middleware.get_actor_handle();
    let result = label_propagation(input, &handle);
    serde_json::to_value(result)
}