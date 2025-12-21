#!/usr/bin/env python3
"""Launch Label Propagation burst execution"""
import sys
import os
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from labelpropagation.labelpropagation_utils import generate_payload
from ow_client.openwhisk_executor import OpenwhiskExecutor
from ow_client.time_helper import get_millis

# Configuration
OW_HOST = "localhost"
OW_PORT = 31001
LP_ENDPOINT = "http://192.168.49.1:9000"
PARTITIONS = 4
NUM_NODES = 1000
BUCKET = "test-bucket"
KEY = "graphs/test-graph"
GRANULARITY = 4
BACKEND = "redis-list"
CHUNK_SIZE = 1024
MAX_ITERATIONS = 10
CONVERGENCE_THRESHOLD = 0
MEMORY = 4096
TIMEOUT = 300000  # 5 minutes in milliseconds
CUSTOM_IMAGE = "burstcomputing/runtime-rust-burst:latest"

print("=" * 60)
print("Label Propagation Burst Execution")
print("=" * 60)
print(f"OpenWhisk: {OW_HOST}:{OW_PORT}")
print(f"Partitions: {PARTITIONS}")
print(f"Nodes: {NUM_NODES}")
print(f"Backend: {BACKEND}")
print(f"Max iterations: {MAX_ITERATIONS}")
print("=" * 60)

# Generate payload
params = generate_payload(
    endpoint=LP_ENDPOINT,
    partitions=PARTITIONS,
    num_nodes=NUM_NODES,
    bucket=BUCKET,
    key=KEY,
    convergence_threshold=CONVERGENCE_THRESHOLD,
    max_iterations=MAX_ITERATIONS
)

print(f"\nGenerated {len(params)} worker payloads")

# Create executor
executor = OpenwhiskExecutor(OW_HOST, OW_PORT, debug=True)

# Execute burst
print("\nStarting burst execution...")
host_submit = get_millis()

try:
    dt = executor.burst(
        "labelpropagation",
        params,
        file="labelpropagation/labelpropagation.zip",
        memory=MEMORY,
        custom_image=CUSTOM_IMAGE,
        debug_mode=True,
        burst_size=GRANULARITY,
        join=False,
        backend=BACKEND,
        chunk_size=CHUNK_SIZE,
        is_zip=True,
        timeout=TIMEOUT
    )
    
    finished = get_millis()
    print(f"\nExecution finished!")
    print(f"Total time: {finished - host_submit} ms")
    
    # Process results
    results_data = dt.get_results()
    print(f"\nRaw results: {results_data}")
    
    # Handle different result formats
    if isinstance(results_data, list) and len(results_data) > 0:
        if isinstance(results_data[0], dict):
            # Results are already dictionaries
            flattened_results = results_data
        else:
            # Results might be nested lists
            flattened_results = [item for sublist in results_data for item in (sublist if isinstance(sublist, list) else [sublist])]
    else:
        flattened_results = []
    
    # Filter and process valid results
    valid_results = [r for r in flattened_results if isinstance(r, dict) and 'key' in r]
    
    if valid_results:
        valid_results.sort(key=lambda x: x['key'])
        
        results = [{
            "fn_id": i["key"],
            "host_submit": host_submit,
            "timestamps": i.get("timestamps", {}),
            "finished": finished
        } for i in valid_results]
    else:
        # If no valid results with 'key', create basic results
        results = [{
            "result": r,
            "host_submit": host_submit,
            "finished": finished
        } for r in flattened_results if r]
    
    # Save results
    output_file = "labelpropagation-burst.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to: {output_file}")
    print(f"Total workers: {len(results)}")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
