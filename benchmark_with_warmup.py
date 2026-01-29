#!/usr/bin/env python3
"""
Incremental Benchmark with Container Warm-up
Reduces cold start variance by pre-warming OpenWhisk containers
"""
import subprocess
import json
import csv
import sys
import os
import time

# Configuration
NODES_START = 9_200_000
NODES_STEP = 400_000
NODES_END = 12_000_000
PARTITIONS = 4
ITERATIONS = 10
MEMORY = 4096
S3_ENDPOINT_HOST = "http://localhost:9000"
S3_ENDPOINT_WORKERS = "http://minio-service.default.svc.cluster.local:9000"
BUCKET = "test-bucket"
OUTPUT_CSV = "warmup_multiples_04m_results.csv"

def run_cmd(cmd):
    print(f"Executing: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout, result.stderr, result.returncode

def warmup_containers():
    """
    Warm up OpenWhisk containers by invoking with minimal workload
    """
    print("\n" + "="*70)
    print("WARMING UP CONTAINERS")
    print("="*70)
    
    # Use tiny graph for warm-up (100K nodes)
    warmup_nodes = 100000
    
    # Generate tiny graph
    print(f"Generating warm-up graph ({warmup_nodes} nodes)...")
    cmd = [
        ".venv/bin/python", "setup_large_lp_data.py",
        "--nodes", str(warmup_nodes),
        "--partitions", str(PARTITIONS),
        "--bucket", BUCKET,
        "--endpoint", S3_ENDPOINT_HOST
    ]
    stdout, stderr, rc = run_cmd(cmd)
    if rc != 0:
        print(f"ERROR generating warm-up data: {stderr}")
        return False
    
    # Run warm-up benchmark (both modes to warm all paths)
    print(f"Running warm-up benchmark...")
    cmd = [
        ".venv/bin/python", "benchmark_lp.py",
        "--nodes", str(warmup_nodes),
        "--partitions", str(PARTITIONS),
        "--iter", "2",  # Just 2 iterations for warm-up
        "--memory", str(MEMORY),
        "--s3-endpoint", S3_ENDPOINT_WORKERS
    ]
    stdout, stderr, rc = run_cmd(cmd)
    if rc != 0:
        print(f"WARNING: Warm-up benchmark failed: {stderr}")
        # Don't fail completely, warm-up is best-effort
    
    print("✓ Containers warmed up")
    print("Waiting 5 seconds for containers to stabilize...")
    time.sleep(5)
    return True

def run_benchmark(nodes):
    """Run benchmark for given node count"""
    # Generate data
    cmd = [
        ".venv/bin/python", "setup_large_lp_data.py",
        "--nodes", str(nodes),
        "--partitions", str(PARTITIONS),
        "--bucket", BUCKET,
        "--endpoint", S3_ENDPOINT_HOST
    ]
    stdout, stderr, rc = run_cmd(cmd)
    if rc != 0:
        print(f"ERROR generating data: {stderr}")
        return None
    
    # Run benchmark
    cmd = [
        ".venv/bin/python", "benchmark_lp.py",
        "--nodes", str(nodes),
        "--partitions", str(PARTITIONS),
        "--iter", str(ITERATIONS),
        "--memory", str(MEMORY),
        "--s3-endpoint", S3_ENDPOINT_WORKERS
    ]
    stdout, stderr, rc = run_cmd(cmd)
    if rc != 0:
        print(f"ERROR running benchmark: {stderr}")
        return None
    
    # Parse results
    lpst_time = None
    burst_time = None
    speedup = None
    
    for line in stdout.split('\n'):
        if 'LPST Time:' in line:
            lpst_time = float(line.split(':')[1].strip())
        elif 'Burst Time:' in line:
            burst_time = float(line.split(':')[1].strip())
        elif 'Speedup:' in line:
            speedup_str = line.split(':')[1].strip().replace('x', '')
            speedup = float(speedup_str)
    
    if lpst_time and burst_time and speedup:
        return {
            'nodes': nodes,
            'standalone_ms': lpst_time,
            'burst_ms': burst_time,
            'speedup': speedup
        }
    return None

def main():
    print("\n" + "="*70)
    print("INCREMENTAL BENCHMARK WITH WARM-UP")
    print(f"Range: {NODES_START/1e6:.1f}M - {NODES_END/1e6:.1f}M nodes")
    print(f"Step: {NODES_STEP/1e6:.1f}M")
    print("="*70 + "\n")
    
    # Phase 1: Warm-up
    if not warmup_containers():
        print("WARNING: Warm-up failed, proceeding anyway...")
    
    # Initialize CSV
    file_exists = os.path.exists(OUTPUT_CSV)
    with open(OUTPUT_CSV, 'a', newline='') as csvfile:
        fieldnames = ['nodes', 'standalone_ms', 'burst_ms', 'speedup']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
    
    # Phase 2: Run benchmarks
    nodes = NODES_START
    while nodes <= NODES_END:
        print("\n" + "="*70)
        print(f">>> BENCHMARKING {nodes/1e6:.1f}M NODES (WARM CONTAINERS) <<<")
        print("="*70)
        
        result = run_benchmark(nodes)
        
        if result:
            # Save to CSV
            with open(OUTPUT_CSV, 'a', newline='') as csvfile:
                fieldnames = ['nodes', 'standalone_ms', 'burst_ms', 'speedup']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writerow(result)
            
            print(f"LPST Time: {result['standalone_ms']}")
            print(f"Burst Time: {result['burst_ms']}")
            print(f"Speedup: {result['speedup']:.2f}x")
            print(f"Result for {nodes} nodes saved: Speedup {result['speedup']:.2f}x")
        else:
            print(f"FAILED to get results for {nodes} nodes")
        
        nodes += NODES_STEP
    
    print("\n" + "="*70)
    print("BENCHMARK COMPLETE")
    print(f"Results saved to: {OUTPUT_CSV}")
    print("="*70)

if __name__ == "__main__":
    main()
