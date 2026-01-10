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
        process_graph_line(&line, &mut graph, &mut initial_labels, worker_id, burst_size);
    }

    (graph, initial_labels)
}

fn process_graph_line(
    line: &str,
    graph: &mut HashMap<u32, Vec<u32>>,
    initial_labels: &mut HashMap<u32, u32>,
    worker_id: u32,
    burst_size: u32,
) {
    if line.trim().is_empty() {
        return;
    }
    let parts: Vec<&str> = line.split('\t').collect();
    if parts.len() < 2 {
        return;
    }
    
    // Use parse().ok() to allow cleaner failure handling
    if let (Ok(src), Ok(dst)) = (parts[0].parse::<u32>(), parts[1].parse::<u32>()) {
        if src % burst_size != worker_id {
            return;
        }
        graph.entry(src).or_default().push(dst);
        
        if parts.len() >= 3 {
             if let Ok(label) = parts[2].parse::<i64>() {
                if label >= 0 {
                    initial_labels.insert(src, label as u32);
                }
             }
        }
    }
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

    // Initialize labels: use provided labels or node ID as initial community
    let mut labels = vec![UNKNOWN; params.num_nodes as usize];
    for (node, label) in initial_labels.iter() {
        if (*node as usize) < labels.len() {
            labels[*node as usize] = *label;
        }
    }

    // Check globally if any worker has seeds
    // Use LabelsMessage to transport boolean flag (1=true, 0=false) because middleware is typed to LabelsMessage
    let local_has_seeds_val = if !initial_labels.is_empty() { 1 } else { 0 };
    let reduced_seeds_msg = middleware
        .reduce(LabelsMessage(vec![local_has_seeds_val]), |a, b| {
            LabelsMessage(vec![if a.0[0] == 1 || b.0[0] == 1 { 1 } else { 0 }])
        })
        .unwrap();

    let global_seeds_msg = if let Some(msg) = reduced_seeds_msg {
        middleware.broadcast(Some(msg), ROOT_WORKER).unwrap()
    } else {
        middleware.broadcast(None, ROOT_WORKER).unwrap()
    };
    
    let global_has_seeds = global_seeds_msg.0[0] == 1;
    
    // If no initial labels provided GLOBALLY, use unsupervised mode: each node starts with its own ID
    // If seeds exist anywhere, nodes without seeds remain UNKNOWN
    if !global_has_seeds && initial_labels.is_empty() {
        println!("[Worker {}] No initial labels found globally, using unsupervised mode (each node = own community)", worker);
        for idx in 0..params.num_nodes as usize {
            if (idx as u32) % burst_size == worker {
                labels[idx] = idx as u32;
            }
        }
    } else if global_has_seeds && initial_labels.is_empty() {
        println!("[Worker {}] Seeds exist globally. Local partition has no seeds -> Keeping as UNKNOWN.", worker);
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
    let unsupervised_mode = initial_labels.is_empty();

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

        let mut local_updates = vec![UNKNOWN; params.num_nodes as usize];
        let mut local_changed: u64 = 0;

        for idx in 0..params.num_nodes as usize {
            if (idx as u32) % burst_size != worker {
                continue;
            }

            let current_label = global_labels.0.get(idx).cloned().unwrap_or(UNKNOWN);

            // Clamp labeled nodes ONLY in supervised mode
            if !unsupervised_mode && initial_labels.contains_key(&(idx as u32)) {
                local_updates[idx] = current_label;
                continue;
            }

            if let Some(neighbors) = graph.get(&(idx as u32)) {
                let mut counts: HashMap<u32, usize> = HashMap::new();
                for neighbor in neighbors {
                    let n_idx = *neighbor as usize;
                    if let Some(label) = global_labels.0.get(n_idx) {
                        if *label != UNKNOWN {
                            *counts.entry(*label).or_insert(0) += 1;
                        }
                    }
                }

                let new_label = majority_label(&counts, current_label);
                local_updates[idx] = new_label;
                if new_label != current_label {
                    local_changed += 1;
                }
            } else {
                // Node owned by this worker but has no outgoing edges
                local_updates[idx] = current_label;
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
        labels: if worker == ROOT_WORKER {
            Some(global_labels.0)
        } else {
            None
        },
    }
}

pub fn main(args: Value, burst_middleware: Middleware<LabelsMessage>) -> Result<Value, Error> {
    let input: Input = serde_json::from_value(args)?;
    let handle = burst_middleware.get_actor_handle();
    let result = label_propagation(input, &handle);
    serde_json::to_value(result)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_labels_message_serialization() {
        let original = LabelsMessage(vec![1, 2, u32::MAX, 123456]);
        let bytes: Bytes = original.clone().into();
        let decoded: LabelsMessage = bytes.into();
        assert_eq!(original, decoded);
    }

    #[test]
    fn test_count_message_serialization() {
        let original = CountMessage(99999);
        let bytes: Bytes = original.clone().into();
        let decoded: CountMessage = bytes.into();
        assert_eq!(original.0, decoded.0);
    }

    #[test]
    fn test_majority_label() {
        // Clear winner
        let mut counts = HashMap::new();
        counts.insert(1, 10);
        counts.insert(2, 5);
        assert_eq!(majority_label(&counts, 99), 1);

        // Tie breaking (lowest label wins)
        let mut counts = HashMap::new();
        counts.insert(10, 5);
        counts.insert(20, 5);
        assert_eq!(majority_label(&counts, 99), 10);

        // Fallback to current
        let counts = HashMap::new();
        assert_eq!(majority_label(&counts, 55), 55);
    }

    #[test]
    fn test_should_continue() {
        // Under max_iter, changed > threshold -> Continue
        assert!(should_continue(0, Some(10), 5, 0));
        
        // Under max_iter, changed <= threshold -> Stop
        assert!(!should_continue(0, Some(10), 0, 0));

        // Over max_iter -> Stop
        assert!(!should_continue(10, Some(10), 5, 0));
    }

    #[test]
    fn test_process_graph_line() {
        let mut graph = HashMap::new();
        let mut initials = HashMap::new();
        let worker_id = 0;
        let burst_size = 2; // worker 0 handles even nodes, worker 1 handles odd nodes

        // Valid line for worker 0
        process_graph_line("0\t1", &mut graph, &mut initials, worker_id, burst_size);
        assert!(graph.contains_key(&0));
        assert_eq!(graph[&0], vec![1]);

        // Line for worker 1 (should be ignored)
        process_graph_line("1\t2", &mut graph, &mut initials, worker_id, burst_size);
        assert!(!graph.contains_key(&1));

        // Line with label
        process_graph_line("2\t3\t99", &mut graph, &mut initials, worker_id, burst_size);
        assert_eq!(initials[&2], 99);
    }
}