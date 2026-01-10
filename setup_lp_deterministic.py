#!/usr/bin/env python3
"""
Setup deterministic test data for Label Propagation in MinIO
Creates two disjoint cliques of 6 nodes each with specific expected outcomes.
Nodes 0-5: Clique A (Seed Node 0 -> Label 100)
Nodes 6-11: Clique B (Seed Node 6 -> Label 200)

Workers: 4
Total Nodes: 12
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
key_prefix = "graphs/deterministic-graph"

# Create bucket if it doesn't exist
if not client.bucket_exists(bucket_name):
    client.make_bucket(bucket_name)

# Define Graph
# Community A: 0, 1, 2, 3, 4, 5
clique_a = [0, 1, 2, 3, 4, 5]
# Community B: 6, 7, 8, 9, 10, 11
clique_b = [6, 7, 8, 9, 10, 11]

edges = []

# Helper to add full mesh edges
def add_clique_edges(nodes):
    for src in nodes:
        for dst in nodes:
            if src == dst: continue
            edge_str = f"{src}\t{dst}"
            # Add seed labels
            if src == 0: # Seed for A
                edge_str += "\t100"
            elif src == 6: # Seed for B
                edge_str += "\t200"
            
            edges.append(edge_str)

add_clique_edges(clique_a)
add_clique_edges(clique_b)

# Partition edges into 4 partitions
# Partition strategy: based on source node modulo 4
num_partitions = 4
partitions = [[] for _ in range(num_partitions)]

for edge in edges:
    src_node = int(edge.split('\t')[0])
    partition_id = src_node % num_partitions
    partitions[partition_id].append(edge)

# Upload each partition as a separate object
total_edges = 0
for i in range(num_partitions):
    partition_data = "\n".join(partitions[i]).encode('utf-8')
    data_stream = io.BytesIO(partition_data)
    object_key = f"{key_prefix}/part-{str(i).zfill(5)}"
    
    client.put_object(
        bucket_name,
        object_key,
        data_stream,
        len(partition_data),
        content_type="text/plain"
    )
    
    print(f"✅ Uploaded partition {i} to {bucket_name}/{object_key} ({len(partitions[i])} edges)")
    total_edges += len(partitions[i])

print(f"\nSummary:")
print(f"   Total Nodes: 12")
print(f"   Total Edges: {total_edges}")
print(f"   Partitions: {num_partitions}")
print(f"   Expected: Nodes 0-5 -> Label 100, Nodes 6-11 -> Label 200")
