#!/usr/bin/env python3
"""
Script to run single-machine (non-distributed) label propagation
using the same dataset as the distributed version for fair comparison.
"""

import json
import time
import subprocess
import tempfile
import os
import sys

# Import boto3 - assume it's available in the environment
import boto3

print("📥 Cargando datos del grafo desde MinIO (mismo dataset que versión distribuida)...")
start_load = time.time()

# Load the same graph data used by distributed version from MinIO
s3_client = boto3.client(
    's3',
    endpoint_url='http://localhost:9000',
    aws_access_key_id='minioadmin',
    aws_secret_access_key='minioadmin'
)

# Load all 4 partitions
all_edges = []
all_labels = {}

for partition in range(4):
    key = f"graphs/test-graph/part-{partition:05d}"
    response = s3_client.get_object(Bucket='test-bucket', Key=key)
    content = response['Body'].read().decode('utf-8')
    
    # Parse TSV format: each line is "node1\tnode2" or "node1\tnode2\tlabel"
    for line in content.strip().split('\n'):
        parts = line.split('\t')
        if len(parts) >= 2:
            node1, node2 = int(parts[0]), int(parts[1])
            all_edges.append([node1, node2])
            
            # Check if there's a label (3rd column)
            if len(parts) >= 3:
                label = int(parts[2])
                all_labels[node1] = label

load_time = time.time() - start_load
print(f"✅ Datos cargados desde MinIO: {len(all_edges)} aristas, {len(all_labels)} nodos etiquetados")
print(f"   Tiempo de carga: {load_time:.3f}s")

# Create a temporary Rust program to run label propagation
# Convert edges to tuples format
edges_rust = ", ".join([f"({e[0]}, {e[1]})" for e in all_edges])

rust_code = f"""
use std::collections::{{HashMap, HashSet}};
use std::time::Instant;

fn main() {{
    let start_time = Instant::now();
    
    // Load edges
    let edges: Vec<(usize, usize)> = vec![{edges_rust}];
    
    // Load initial labels
    let mut labeled_nodes: HashMap<usize, usize> = HashMap::new();
    {chr(10).join(f'    labeled_nodes.insert({k}, {v});' for k, v in all_labels.items())}
    
    // Build adjacency list
    let mut adjacency: HashMap<usize, Vec<usize>> = HashMap::new();
    let mut all_nodes = HashSet::new();
    
    for (from, to) in &edges {{
        all_nodes.insert(*from);
        all_nodes.insert(*to);
        adjacency.entry(*from).or_insert_with(Vec::new).push(*to);
        adjacency.entry(*to).or_insert_with(Vec::new).push(*from);
    }}
    
    // Initialize labels (use node ID as label if not provided)
    let mut labels: HashMap<usize, usize> = HashMap::new();
    for &node in &all_nodes {{
        labels.insert(node, *labeled_nodes.get(&node).unwrap_or(&node));
    }}
    
    // Keep track of initially labeled nodes (clamping)
    let initially_labeled: HashSet<usize> = labeled_nodes.keys().copied().collect();
    
    println!("Graph: {{}} nodes, {{}} edges", all_nodes.len(), edges.len());
    println!("Initially labeled: {{}} nodes", initially_labeled.len());
    
    let data_load_time = start_time.elapsed();
    
    // Run label propagation
    let max_iterations = 10;
    let convergence_threshold = 0.0;
    
    let mut iteration = 0;
    let mut converged = false;
    
    let algo_start = Instant::now();
    
    while iteration < max_iterations && !converged {{
        let iter_start = Instant::now();
        
        let mut new_labels = labels.clone();
        let mut changed_count = 0;
        
        for &node in &all_nodes {{
            // Skip initially labeled nodes (clamping)
            if initially_labeled.contains(&node) {{
                continue;
            }}
            
            if let Some(neighbors) = adjacency.get(&node) {{
                if neighbors.is_empty() {{
                    continue;
                }}
                
                // Count label frequencies from neighbors
                let mut label_counts: HashMap<usize, usize> = HashMap::new();
                for &neighbor in neighbors {{
                    if let Some(&label) = labels.get(&neighbor) {{
                        *label_counts.entry(label).or_insert(0) += 1;
                    }}
                }}
                
                // Find the most common label (with deterministic tie-breaking)
                if let Some((&new_label, _)) = label_counts.iter()
                    .max_by(|a, b| a.1.cmp(b.1).then(b.0.cmp(a.0))) {{
                    
                    if labels.get(&node) != Some(&new_label) {{
                        new_labels.insert(node, new_label);
                        changed_count += 1;
                    }}
                }}
            }}
        }}
        
        labels = new_labels;
        
        let iter_time = iter_start.elapsed();
        println!("Iteration {{}}: {{}} changes ({{:.3}}ms)", iteration, changed_count, iter_time.as_secs_f64() * 1000.0);
        
        let change_ratio = changed_count as f64 / all_nodes.len() as f64;
        if change_ratio <= convergence_threshold {{
            converged = true;
        }}
        
        iteration += 1;
    }}
    
    let algo_time = algo_start.elapsed();
    
    println!("\\nConverged: {{}}", converged);
    println!("Total iterations: {{}}", iteration);
    println!("\\nTiming breakdown:");
    println!("  Data structures setup: {{:.3}}ms", data_load_time.as_secs_f64() * 1000.0);
    println!("  Algorithm execution: {{:.3}}ms", algo_time.as_secs_f64() * 1000.0);
    println!("  Total time: {{:.3}}ms", start_time.elapsed().as_secs_f64() * 1000.0);
}}
"""

print("\n🔨 Compilando y ejecutando versión no distribuida...")

# Create temporary directory
with tempfile.TemporaryDirectory() as tmpdir:
    # Write Rust source
    src_dir = os.path.join(tmpdir, 'src')
    os.makedirs(src_dir)
    
    with open(os.path.join(src_dir, 'main.rs'), 'w') as f:
        f.write(rust_code)
    
    # Create Cargo.toml
    cargo_toml = """[package]
name = "lp_single"
version = "0.1.0"
edition = "2021"

[dependencies]
"""
    
    with open(os.path.join(tmpdir, 'Cargo.toml'), 'w') as f:
        f.write(cargo_toml)
    
    # Compile and run
    compile_start = time.time()
    compile_result = subprocess.run(
        ['cargo', 'build', '--release'],
        cwd=tmpdir,
        capture_output=True,
        text=True
    )
    compile_time = time.time() - compile_start
    
    if compile_result.returncode != 0:
        print("❌ Error de compilación:")
        print(compile_result.stderr)
        exit(1)
    
    print(f"✅ Compilación exitosa ({compile_time:.1f}s)")
    print("\n" + "="*60)
    print("📊 EJECUCIÓN - VERSIÓN NO DISTRIBUIDA")
    print("="*60 + "\n")
    
    # Run the program
    run_start = time.time()
    run_result = subprocess.run(
        [os.path.join(tmpdir, 'target', 'release', 'lp_single')],
        capture_output=True,
        text=True
    )
    run_time = time.time() - run_start
    
    if run_result.returncode != 0:
        print("❌ Error de ejecución:")
        print(run_result.stderr)
        exit(1)
    
    print(run_result.stdout)
    print(f"\nTiempo total de ejecución: {run_time:.3f}s")

print("\n" + "="*60)
print("📊 COMPARACIÓN CON VERSIÓN DISTRIBUIDA")
print("="*60)

# Load distributed results
with open('labelpropagation-burst.json') as f:
    distributed_results = json.load(f)

w = distributed_results[0]
timestamps = {t['key']: int(t['value']) for t in w['timestamps']}

worker_start = timestamps['worker_start']
worker_end = timestamps['worker_end']
get_input_time = timestamps['get_input_end'] - timestamps['get_input']
algo_time_dist = worker_end - timestamps['iter_0_start']

print(f"\n🔀 Versión Distribuida (4 workers):")
print(f"   - Carga de datos (S3/MinIO): {get_input_time} ms")
print(f"   - Ejecución algoritmo: {algo_time_dist} ms")
print(f"   - Total worker: {worker_end - worker_start} ms")

print(f"\n💻 Versión Single-Machine:")
print(f"   - Carga de datos (S3/MinIO): {load_time * 1000:.1f} ms")
print(f"   - Setup estructuras: ver output arriba")
print(f"   - Ejecución algoritmo: ver output arriba")

print("\n📊 Análisis:")
print(f"   La versión distribuida incluye overhead de comunicación")
print(f"   entre workers (broadcast/reduce via Redis), mientras que")
print(f"   la versión single ejecuta todo en memoria local.")
print(f"\n   Ambas versiones cargan desde MinIO para comparación justa.")
