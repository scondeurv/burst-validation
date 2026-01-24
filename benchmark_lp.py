#!/usr/bin/env python3
import subprocess
import json
import time
import os
import sys
import argparse

# Add parent directory for utils
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from labelpropagation.labelpropagation_utils import generate_payload
from ow_client.openwhisk_executor import OpenwhiskExecutor
from ow_client.time_helper import get_millis

def run_lpst(num_nodes, max_iter, local_graph):
    lpst_bin = "./labelpropagation/lpst/target/release/label-propagation"
    print("\n--- Running LPST (Single-Threaded Rust) ---")
    if not os.path.exists(lpst_bin):
        print("Error: lpst binary not found. Please compile it first with 'cargo build --release'")
        return None

    cmd = [lpst_bin, local_graph, str(num_nodes), str(max_iter)]
    start = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    end = time.time()
    
    if result.returncode != 0:
        print(f"Error running lpst: {result.stderr}")
        return None
    
    data = json.loads(result.stdout)
    data['total_real_time_ms'] = (end - start) * 1000
    print(f"LPST Finished in {data['total_real_time_ms']:.2f} ms")
    return data

def run_ow_lp(num_nodes, max_iter, partitions, memory, granularity):
    print("\n--- Running OW-LP (Distributed Burst) ---")
    
    ow_host = "localhost"
    ow_port = 31001
    lp_endpoint = "http://minio-service.default:9000"
    bucket = "test-bucket"
    key = f"graphs/large-{num_nodes}"
    backend = "redis-list"

    # Use parameters from run_labelpropagation.sh
    cmd = [
        sys.executable, "labelpropagation/labelpropagation.py",
        "--ow-host", ow_host,
        "--ow-port", str(ow_port),
        "--lp-endpoint", lp_endpoint,
        "--partitions", str(partitions),
        "--num-nodes", str(num_nodes),
        "--bucket", bucket,
        "--key", key,
        "--granularity", str(granularity),
        "--backend", backend,
        "--chunk-size", "1024",
        "--max-iterations", str(max_iter),
        "--convergence-threshold", "0",
        "--runtime-memory", str(memory)
    ]
    
    print(f"Executing: {' '.join(cmd)}")
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    subprocess.run(cmd, env=env)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--nodes", type=int, default=100000)
    parser.add_argument("--partitions", type=int, default=24)
    parser.add_argument("--granularity", type=int, default=1)
    parser.add_argument("--iter", type=int, default=10)
    parser.add_argument("--memory", type=int, default=512)
    parser.add_argument("--skip-validation", action="store_true", 
                       help="Skip correctness validation")
    args = parser.parse_args()

    num_nodes = args.nodes
    partitions = args.partitions
    granularity = args.granularity
    max_iter = args.iter
    memory = args.memory
    local_graph = f"large_{num_nodes}.txt"

    lpst_res = run_lpst(num_nodes, max_iter, local_graph)
    run_ow_lp(num_nodes, max_iter, partitions, memory, granularity)

    if not os.path.exists("labelpropagation-burst.json"):
        print("Benchmarking failed. labelpropagation-burst.json not found.")
        return

    with open("labelpropagation-burst.json", "r") as f:
        burst_data = json.load(f)

    # Calculate distributed time from worker timestamps
    min_start = float('inf')
    max_end = 0

    for worker in burst_data:
        ts_map = {t['key']: int(t['value']) for t in worker.get('timestamps', [])}
        if 'worker_start' in ts_map and 'worker_end' in ts_map:
            min_start = min(min_start, ts_map['worker_start'])
            max_end = max(max_end, ts_map['worker_end'])

    if min_start == float('inf') or max_end == 0:
        print("Warning: Could not find valid worker timestamps in labelpropagation-burst.json")
        burst_time_ms = 0
    else:
        burst_time_ms = max_end - min_start
        print(f"BURST Distributed Time: {burst_time_ms:.2f} ms")

    # Performance comparison
    if lpst_res:
        print("\n========================================")
        print("      PERFORMANCE COMPARISON")
        print("========================================")
        print(f"LPST Time:  {lpst_res['total_real_time_ms']:.2f} ms")
        print(f"Burst Time: {burst_time_ms:.2f} ms")
        if burst_time_ms > 0:
            speedup = lpst_res['total_real_time_ms'] / burst_time_ms
            format_char = "x"
        else:
            speedup = 0
            format_char = " (Error)"
        print(f"Speedup:    {speedup:.2f}{format_char}")
        print("========================================\n")
    
    # Run validation if not skipped
    if not args.skip_validation:
        print("\n========================================")
        print("   RUNNING CORRECTNESS VALIDATION")
        print("========================================")
        
        validation_cmd = [
            sys.executable, "labelpropagation/validate_results.py",
            "--num-communities", "4",
            "--nodes-per-community", "100",
            "--num-workers", str(partitions),
            "--output", "validation_report.html"
        ]
        
        result = subprocess.run(validation_cmd)
        
        if result.returncode != 0:
            print("\n✗ Validation FAILED - see validation_report.html for details")
            sys.exit(1)
        else:
            print("\n✓ Validation PASSED")
    else:
        print("\n[Validation skipped]")

if __name__ == "__main__":
    main()

