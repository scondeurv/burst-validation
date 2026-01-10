#!/bin/bash

cd /home/sergio/src/tfm/burst-validation

# First, setup the graph data
echo "Setting up label propagation test data..."
python3 setup_lp_deterministic.py

# Then run the label propagation burst
PYTHONPATH=. uv run labelpropagation/labelpropagation.py \
  --ow-host localhost \
  --ow-port 31001 \
  --lp-endpoint http://192.168.49.1:9000 \
  --partitions 4 \
  --num-nodes 12 \
  --bucket test-bucket \
  --key graphs/deterministic-graph \
  --granularity 4 \
  --backend redis-list \
  --chunk-size 1024 \
  --max-iterations 10 \
  --convergence-threshold 0
