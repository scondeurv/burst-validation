#!/bin/bash

NODES=(10000 100000 500000 1000000 5000000)
MEMORY=2048

# Create a temporary file to collect results
RESULTS_FILE="/tmp/benchmark_results.txt"
> "$RESULTS_FILE"

# Ensure we start fresh
rm -f labelpropagation-burst.json

for nodes in "${NODES[@]}"; do
    echo "=========================================="
    echo "Running benchmark for $nodes nodes"
    echo "=========================================="
    
    # Generate data with consistent partitions (16)
    PYTHONPATH=. uv run setup_large_lp_data.py --nodes "$nodes" --partitions 16
    
    # Repackage action
    zip -j labelpropagation.zip labelpropagation/ow-lp/bin/exec > /dev/null 2>&1
    
    # Run benchmark and capture output. Use 16 partitions to match setup.
    output=$(PYTHONPATH=. uv run benchmark_lp.py --nodes "$nodes" --partitions 16 --iter 5 --memory "$MEMORY" 2>&1)
    
    # Extract timing values
    lpst_time=$(echo "$output" | grep "LPST Time:" | awk '{print $3}')
    burst_time=$(echo "$output" | grep "Burst Time:" | awk '{print $3}')
    
    # If burst_time is 0 or empty, benchmark failed
    if [[ -z "$burst_time" || "$burst_time" == "0.00" ]]; then
        echo "ERROR: Benchmark failed for $nodes nodes"
        continue
    fi
    
    echo "$nodes $lpst_time $burst_time" >> "$RESULTS_FILE"
    
    # Clean up JSON to avoid cross-run contamination
    rm -f labelpropagation-burst.json
    echo ""
done

echo "All benchmarks completed!"
echo "Results:"
cat "$RESULTS_FILE"
