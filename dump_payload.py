
import json
import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'labelpropagation'))
from labelpropagation_utils import generate_payload

params = generate_payload(
    endpoint="http://minio-service.default:9000",
    partitions=1,
    num_nodes=2000,
    bucket="test-bucket",
    key="graphs/large-2000",
    convergence_threshold=0,
    max_iterations=5,
    granularity=1
)
print(json.dumps(params[0]))
