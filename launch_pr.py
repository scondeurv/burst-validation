#!/usr/bin/env python3
"""
Simplified PageRank launcher for OpenWhisk Burst.
"""

import sys
sys.path.insert(0, '/home/sergio/src/tfm/burst-validation')

from ow_client.openwhisk_executor import OpenwhiskExecutor
from ow_client.time_helper import get_millis
from pagerank.pagerank_utils import generate_payload
import json

# Hardcoded configuration for simplicity
TIMEOUT = 300000  # 5 minutes
NUM_WORKERS = 4
NUM_NODES = 5  # Based on test dataset
PR_ENDPOINT = "http://minio-service.default:9000"
BACKEND = "redis-list"
REDIS_URL = "redis://dragonfly.default:6379"
BUCKET = "test-bucket"
KEY = "graphs/pagerank"
CUSTOM_IMAGE = "burstcomputing/runtime-rust-burst:latest"

print("🚀 Lanzando PageRank en OpenWhisk Burst")
print("=" * 60)
print(f"Workers: {NUM_WORKERS}")
print(f"Nodos: {NUM_NODES}")
print(f"Endpoint: {PR_ENDPOINT}")
print(f"Backend: {BACKEND}")
print(f"Bucket: {BUCKET}")
print(f"Key: {KEY}")
print()

# Generate payload
params = generate_payload(
    endpoint=PR_ENDPOINT,
    partitions=NUM_WORKERS,
    num_nodes=NUM_NODES,
    bucket=BUCKET,
    key=KEY
)

print(f"📋 Payload generado para {len(params)} workers")

# Create executor
executor = OpenwhiskExecutor("localhost", 31001, debug=False)

print("\n⏳ Ejecutando PageRank...")
host_submit = get_millis()

try:
    dt = executor.burst(
        "pagerank",
        params,
        file="./pagerank/pagerank.zip",
        memory=4096,
        custom_image=CUSTOM_IMAGE,
        debug_mode=False,
        burst_size=NUM_WORKERS,
        join=True,
        backend=BACKEND,
        chunk_size=1048576,
        is_zip=True,
        timeout=TIMEOUT
    )
    
    finished = get_millis()
    
    print(f"✅ Ejecución completada en {(finished - host_submit) / 1000:.2f}s")
    
    # Process results
    flattened_results = [item for sublist in dt.get_results() for item in sublist]
    flattened_results.sort(key=lambda x: x['key'])
    
    results = [{
        "fn_id": i["key"],
        "host_submit": host_submit,
        "timestamps": i["timestamps"],
        "finished": finished
    } for i in flattened_results]
    
    # Save results
    with open("pagerank-burst.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📊 Resultados guardados en pagerank-burst.json")
    print(f"   Workers completados: {len(results)}")
    
    # Show timing summary
    if results:
        w = results[0]
        timestamps = {t['key']: int(t['value']) for t in w['timestamps']}
        if 'worker_start' in timestamps and 'worker_end' in timestamps:
            worker_time = timestamps['worker_end'] - timestamps['worker_start']
            print(f"   Tiempo de worker: {worker_time} ms")
    
except Exception as e:
    print(f"\n❌ Error durante la ejecución: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
