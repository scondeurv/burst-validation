import subprocess
import json
import csv
import sys
import os

# Configuration
NODES_START = 9_700_000   # Critical region: 9.7M
NODES_STEP = 100_000      # 0.1M increments for precision
NODES_END = 10_000_000    # End at 10M (re-validate anomaly)
PARTITIONS = 4
ITERATIONS = 10
MEMORY = 4096  # Increased for larger graphs
S3_ENDPOINT_HOST = "http://localhost:9000"
S3_ENDPOINT_WORKERS = "http://minio-service.default.svc.cluster.local:9000"
BUCKET = "test-bucket"
OUTPUT_CSV = "incremental_results.csv"

def run_cmd(cmd):
    print(f"Executing: {' '.join(cmd)}")
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stdout}")
        return None
    # print(result.stdout) # Reduced verbosity for long runs
    # Find summary lines
    for line in result.stdout.split('\n'):
        if any(x in line for x in ["LPST Time:", "Burst Time:", "Speedup:", "Nodes:"]):
            print(line)
    return result.stdout

def main():
    # Prepare CSV (append if exists)
    file_exists = os.path.isfile(OUTPUT_CSV)
    with open(OUTPUT_CSV, mode='a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["nodes", "standalone_ms", "burst_ms", "speedup"])

    for n in range(NODES_START, NODES_END + NODES_STEP, NODES_STEP):
        print(f"\n>>> BENCHMARKING {n/1_000_000:.1f}M NODES <<<")
        
        # 1. Setup data (from host using venv)
        setup_cmd = [
            ".venv/bin/python", "setup_large_lp_data.py",
            "--nodes", str(n),
            "--partitions", str(PARTITIONS),
            "--bucket", BUCKET,
            "--endpoint", S3_ENDPOINT_HOST
        ]
        run_cmd(setup_cmd)

        # 2. Run benchmark (both modes using venv)
        bench_cmd = [
            ".venv/bin/python", "benchmark_lp.py",
            "--nodes", str(n),
            "--partitions", str(PARTITIONS),
            "--iter", str(ITERATIONS),
            "--memory", str(MEMORY),
            "--s3-endpoint", S3_ENDPOINT_WORKERS
        ]
        
        output = run_cmd(bench_cmd)
        if not output:
            continue

        # Parse results from benchmark_lp.py output
        # Expecting lines like: "LPST Time: 18831" or "Burst Time: 27556"
        standalone_ms = 0
        burst_ms = 0
        
        for line in output.split('\n'):
            # The script outputs "LPST Time: XXX" or "Standalone Time: XXX" depending on version
            if "LPST Time:" in line or "Standalone Time:" in line:
                try:
                    standalone_ms = float(line.split(':')[1].strip().split(' ')[0])
                except: pass
            if "Burst Time:" in line:
                try:
                    burst_ms = float(line.split(':')[1].strip().split(' ')[0])
                except: pass
        
        if standalone_ms > 0 and burst_ms > 0:
            speedup = standalone_ms / burst_ms
            with open(OUTPUT_CSV, mode='a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([n, standalone_ms, burst_ms, speedup])
            print(f"Result for {n} nodes saved: Speedup {speedup:.2f}x")

if __name__ == "__main__":
    main()
