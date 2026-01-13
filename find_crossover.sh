#!/bin/bash

# Find the crossover point where distributed becomes faster than single-threaded
# Start with larger sizes to find the crossover more efficiently

SIZES=(10000000)  # Start with 10M
MEMORY=4096       # Use more memory for larger datasets

RESULTS_FILE="/tmp/crossover_results.txt"
> "$RESULTS_FILE"

for nodes in "${SIZES[@]}"; do
    echo "=========================================="
    echo "Testing $nodes nodes"
    echo "=========================================="
    
    # Generate data if not exists locally
    if [ ! -f "large_${nodes}.txt" ]; then
        echo "Generating graph with $nodes nodes..."
        PYTHONPATH=. uv run setup_large_lp_data.py --nodes "$nodes" 2>&1 | tail -5
    fi
    
    # Repackage action
    zip -j labelpropagation.zip labelpropagation/ow-lp/bin/exec > /dev/null 2>&1
    
    # Run benchmark
    output=$(PYTHONPATH=. uv run benchmark_lp.py --nodes "$nodes" --partitions 32 --iter 5 --memory "$MEMORY" 2>&1)
    
    # Extract timing values
    lpst_time=$(echo "$output" | grep "LPST Time:" | awk '{print $3}')
    burst_time=$(echo "$output" | grep "Burst Time:" | awk '{print $3}')
    
    if [ -z "$lpst_time" ] || [ -z "$burst_time" ]; then
        echo "Failed to extract timing for $nodes nodes"
        echo "$output" | grep -E "Time:|Error"
    else
        speedup=$(echo "scale=2; $lpst_time / $burst_time" | bc)
        echo "$nodes $lpst_time $burst_time $speedup" | tee -a "$RESULTS_FILE"
        
        # Check if we found crossover
        if (( $(echo "$speedup > 1.0" | bc -l) )); then
            echo "✓ CROSSOVER FOUND at $nodes nodes! Speedup: ${speedup}x"
        else
            echo "✗ Still below 1.0x (${speedup}x). Need larger datasets."
        fi
    fi
    
    echo ""
done

echo "Results summary:"
cat "$RESULTS_FILE"
