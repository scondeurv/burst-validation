#!/usr/bin/env python3
import os
import random
from minio import Minio
import argparse
import io

# Config
NUM_NODES = 100000

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--nodes", type=int, default=100000)
    parser.add_argument("--partitions", type=int, default=24)
    args = parser.parse_args()

    num_nodes = args.nodes
    num_partitions = args.partitions
    bucket_name = "test-bucket"
    key_prefix = f"graphs/pagerank-{num_nodes}"
    local_file = f"pagerank_{num_nodes}.txt"

    # MinIO connection
    client = Minio(
        "localhost:9000",
        access_key="minioadmin",
        secret_key="minioadmin",
        secure=False
    )

    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)

    print(f"Generating graph with {num_nodes} nodes and {num_partitions} partitions...")

    # Nodes per partition
    partitions = [[] for _ in range(num_partitions)]
    all_edges = []
    
    nodes_per_part_approx = num_nodes // num_partitions

    for p in range(num_partitions):
        start_node = p * nodes_per_part_approx
        end_node = (p + 1) * nodes_per_part_approx if p < num_partitions - 1 else num_nodes
        
        community_nodes = list(range(start_node, end_node))
        
        # Internal edges (dense-ish)
        for i in range(len(community_nodes)):
            src = community_nodes[i]
            label = src # Every node starts with its own label
            # Each node connects to ~5 other nodes in its community
            targets = random.sample(community_nodes, min(6, len(community_nodes)))
            for dst in targets:
                if src != dst:
                    edge = f"{src}\t{dst}\t{label}"
                    
                    # Use MOD partitioning to match OW-LP worker logic
                    target_part = src % num_partitions
                    partitions[target_part].append(edge)
                    all_edges.append(edge)

    # Bridge edges between communities to make it connected
    for p in range(num_partitions):
        next_p = (p + 1) % num_partitions
        src = p * nodes_per_part_approx + random.randint(0, nodes_per_part_approx - 1)
        dst = next_p * nodes_per_part_approx + random.randint(0, nodes_per_part_approx - 1)
        edge = f"{src}\t{dst}"
        
        # Use MOD partitioning here too
        target_part = src % num_partitions
        partitions[target_part].append(edge)
        all_edges.append(edge)

    # 1. Upload full graph to MinIO (for backward compatibility if needed)
    content = "\n".join(all_edges) + "\n"
    data = content.encode('utf-8')
    client.put_object(bucket_name, key_prefix, io.BytesIO(data), len(data))
    print(f"Uploaded full graph to {key_prefix}")

    # 2. Upload INDIVIDUAL partitions for optimized loading
    print(f"Uploading {num_partitions} optimized partitions...")
    for i in range(num_partitions):
        part_content = "\n".join(partitions[i]) + "\n"
        part_data = part_content.encode('utf-8')
        part_key = f"{key_prefix}/part-{i}"
        client.put_object(bucket_name, part_key, io.BytesIO(part_data), len(part_data))

    # Save local file for LPST
    with open(local_file, "w") as f:
        f.write("\n".join(all_edges) + "\n")

    print(f"Saved local graph to {local_file}")
    print(f"Graph setup complete with {num_partitions} individual partitions.")

if __name__ == "__main__":
    main()
