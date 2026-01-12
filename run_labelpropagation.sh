#!/bin/bash

# Then run the label propagation burst
PYTHONPATH=. uv run labelpropagation/labelpropagation.py \
  --ow-host localhost \
  --ow-port 31001 \
  --lp-endpoint http://minio-service.default:9000 \
  --partitions 8 \
  --num-nodes 20 \
  --bucket test-bucket \
  --key graphs/deterministic-complex\
  --granularity 8 \
  --backend redis-list \
  --chunk-size 1024 \
  --max-iterations 10 \
  --convergence-threshold 0
