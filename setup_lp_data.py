#!/usr/bin/env python3
"""
Setup test data for Label Propagation in MinIO
Creates a simple graph with 1000 nodes partitioned into 4 files
"""
from minio import Minio
import io

# MinIO connection
client = Minio(
    "localhost:9000",
    access_key="minioadmin",
    secret_key="minioadmin",
    secure=False
)

bucket_name = "test-bucket"
prefix = "graphs/test-graph"

# Create bucket if it doesn't exist
if not client.bucket_exists(bucket_name):
    client.make_bucket(bucket_name)
    print(f"✅ Created bucket: {bucket_name}")
else:
    print(f"ℹ️  Bucket {bucket_name} already exists")

# Generate a simple graph: each node connects to next node
# 1000 nodes, 4 partitions = 250 nodes per partition
num_nodes = 1000
num_partitions = 4
nodes_per_partition = num_nodes // num_partitions

for partition in range(num_partitions):
    edges = []
    start_node = partition * nodes_per_partition
    end_node = start_node + nodes_per_partition
    
    # Create edges: each node -> next node (with wraparound)
    # Add seed labels: one seed every N nodes within this partition
    seed_interval = 10  # Creates ~25 seeds per partition (10% of nodes have labels)
    for i, node in enumerate(range(start_node, end_node)):
        next_node = (node + 1) % num_nodes
        # Add initial label for seed nodes (evenly distributed in partition)
        if i % seed_interval == 0:
            edges.append(f"{node}\t{next_node}\t{partition}")
        else:
            edges.append(f"{node}\t{next_node}")
    
    # Upload partition
    data = "\n".join(edges).encode('utf-8')
    object_name = f"{prefix}/part-{str(partition).zfill(5)}"
    
    client.put_object(
        bucket_name,
        object_name,
        io.BytesIO(data),
        length=len(data),
        content_type="text/plain"
    )
    print(f"✅ Uploaded {object_name} ({len(edges)} edges)")

print(f"\n✨ Setup complete! Graph data ready in s3://{bucket_name}/{prefix}/")
