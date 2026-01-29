#!/bin/bash

# Benchmark Suite: 0.5M to 10M nodes
# Run with: bash run_benchmark_suite.sh

NODES_LIST="500000 1000000 2000000 3000000 4000000 5000000 6000000 7000000 8000000 9000000 10000000"
RESULTS_FILE="benchmark_results_$(date +%Y%m%d_%H%M%S).txt"

echo "=== Label Propagation Benchmark Suite ===" | tee $RESULTS_FILE
echo "Date: $(date)" | tee -a $RESULTS_FILE
echo "Partitions: 4" | tee -a $RESULTS_FILE
echo "Iterations: 10" | tee -a $RESULTS_FILE
echo "Memory: 4096MB" | tee -a $RESULTS_FILE
echo "" | tee -a $RESULTS_FILE

counter=1
total=$(echo $NODES_LIST | wc -w)

for nodes in $NODES_LIST; do
    echo "" | tee -a $RESULTS_FILE
    echo "==========================================" | tee -a $RESULTS_FILE
    echo "[$counter/$total] Benchmark: $(printf "%'d" $nodes) nodes" | tee -a $RESULTS_FILE
    echo "==========================================" | tee -a $RESULTS_FILE
    
    .venv/bin/python benchmark_lp.py \
        --nodes $nodes \
        --partitions 4 \
        --iter 10 \
        --memory 4096 \
        --s3-endpoint http://minio-service.default.svc.cluster.local:9000 \
        2>&1 | tee -a $RESULTS_FILE
    
    echo "" | tee -a $RESULTS_FILE
    counter=$((counter + 1))
done

echo "" | tee -a $RESULTS_FILE
echo "=== Benchmark Suite Complete ===" | tee -a $RESULTS_FILE
echo "Results saved to: $RESULTS_FILE"
