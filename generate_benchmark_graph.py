#!/usr/bin/env python3
import random
import os
import sys
import io
from minio import Minio

# Configuration
NUM_NODES = 500
COMMUNITIES = 4
EDGES_PER_NODE = 3
BRIDGE_PROB = 0.05
PARTITIONS = 4
BUCKET_NAME = "test-bucket"
KEY_PREFIX = "graphs/benchmark-graph"

# MinIO connection
client = Minio(
    "localhost:9000",
    access_key="minioadmin",
    secret_key="minioadmin",
    secure=False
)

def generate_graph():
    print(f"Generating graph with {NUM_NODES} nodes and {COMMUNITIES} communities...")
    nodes_per_comm = NUM_NODES // COMMUNITIES
    edges = []
    
    # Seeds
    seeds = {}
    for i in range(COMMUNITIES):
        seed_node = i * nodes_per_comm
        seeds[seed_node] = (i + 1) * 100

    for i in range(NUM_NODES):
        comm_id = i // nodes_per_comm
        
        # Internal edges
        for _ in range(EDGES_PER_NODE):
            dst = random.randint(comm_id * nodes_per_comm, min((comm_id + 1) * nodes_per_comm - 1, NUM_NODES - 1))
            if i != dst:
                edge_str = f"{i}\t{dst}"
                if i in seeds:
                    edge_str += f"\t{seeds[i]}"
                edges.append(edge_str)
        
        # Bridge edges
        if random.random() < BRIDGE_PROB:
            dst = random.randint(0, NUM_NODES - 1)
            if i // nodes_per_comm != dst // nodes_per_comm:
                edges.append(f"{i}\t{dst}")

    return edges, seeds

def save_local(edges, filename="benchmark_graph.txt"):
    with open(filename, "w") as f:
        f.write("\n".join(edges))
    print(f"Saved local graph to {filename}")

def upload_minio(edges):
    if not client.bucket_exists(BUCKET_NAME):
        client.make_bucket(BUCKET_NAME)

    # Partition edges by source node % PARTITIONS
    partitions_data = [[] for _ in range(PARTITIONS)]
    for edge in edges:
        src = int(edge.split('\t')[0])
        partitions_data[src % PARTITIONS].append(edge)

    for i in range(PARTITIONS):
        data = "\n".join(partitions_data[i]).encode('utf-8')
        client.put_object(
            BUCKET_NAME,
            f"{KEY_PREFIX}/part-{str(i).zfill(5)}",
            io.BytesIO(data),
            len(data),
            content_type="text/plain"
        )
    print(f"Uploaded {PARTITIONS} partitions to MinIO: {BUCKET_NAME}/{KEY_PREFIX}")

if __name__ == "__main__":
    edges, seeds = generate_graph()
    save_local(edges)
    upload_minio(edges)
    print(f"Graph generation complete. Total edges: {len(edges)}")
    print(f"Initial seeds: {seeds}")
