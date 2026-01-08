#!/bin/bash

cd /home/sergio/src/tfm/burst-validation

PYTHONPATH=. uv run labelpropagation/labelpropagation.py \
  --ow-host localhost \
  --ow-port 31001 \
  --lp-endpoint http://192.168.49.1:9000 \
  --partitions 4 \
  --num-nodes 1000 \
  --bucket test-bucket \
  --key graphs/test-graph \
  --granularity 4 \
  --backend redis-list \
  --chunk-size 1024 \
  --max-iterations 10 \
  --convergence-threshold 0
