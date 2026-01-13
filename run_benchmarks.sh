#!/bin/bash

NODES=(10000 100000 500000 1000000 5000000)
MEMORY=2048

# Create a temporary file to collect results
RESULTS_FILE="/tmp/benchmark_results.txt"
> "$RESULTS_FILE"

for nodes in "${NODES[@]}"; do
    echo "=========================================="
    echo "Running benchmark for $nodes nodes"
    echo "=========================================="
    
    # Generate data
    PYTHONPATH=. uv run setup_large_lp_data.py --nodes "$nodes"
    
    # Repackage action
    zip -j labelpropagation.zip labelpropagation/ow-lp/bin/exec > /dev/null 2>&1
    
    # Run benchmark and capture output
    output=$(PYTHONPATH=. uv run benchmark_lp.py --nodes "$nodes" --partitions 32 --iter 5 --memory "$MEMORY" 2>&1)
    
    # Extract timing values
    lpst_time=$(echo "$output" | grep "LPST Time:" | awk '{print $3}')
    burst_time=$(echo "$output" | grep "Burst Time:" | awk '{print $3}')
    
    echo "$nodes $lpst_time $burst_time" >> "$RESULTS_FILE"
    
    echo ""
done

echo "All benchmarks completed!"
echo "Results:"
cat "$RESULTS_FILE"
