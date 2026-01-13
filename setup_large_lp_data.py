#!/usr/bin/env python3
import os
import random
import boto3
import argparse
import io

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--nodes", type=int, default=100000)
    parser.add_argument("--partitions", type=int, default=16)
    args = parser.parse_args()

    num_nodes = args.nodes
    num_partitions = args.partitions
    bucket_name = "test-bucket"
    key_prefix = f"graphs/large-{num_nodes}"
    local_file = f"large_{num_nodes}.txt"

    # S3 connection (MinIO)
    s3 = boto3.client(
        's3',
        endpoint_url='http://localhost:9000',
        aws_access_key_id='minioadmin',
        aws_secret_access_key='minioadmin',
        region_name='us-east-1'
    )

    # Ensure bucket exists
    try:
        s3.create_bucket(Bucket=bucket_name)
    except:
        pass

    print(f"Generating graph with {num_nodes} nodes and {num_partitions} partitions...")

    nodes_per_part_approx = num_nodes // num_partitions
    all_edges_count = 0

    partition_buffers = [io.StringIO() for _ in range(num_partitions)]

    with open(local_file, "w") as f_local:
        for p in range(num_partitions):
            start_node = p * nodes_per_part_approx
            end_node = (p + 1) * nodes_per_part_approx if p < num_partitions - 1 else num_nodes
            
            community_nodes = list(range(start_node, end_node))
            
            for i in range(len(community_nodes)):
                src = community_nodes[i]
                label = p if i % 10 == 0 else None
                num_targets = min(6, len(community_nodes))
                targets = random.sample(community_nodes, num_targets)
                for dst in targets:
                    if src != dst:
                        if label is not None:
                            edge = f"{src}\t{dst}\t{label}"
                        else:
                            edge = f"{src}\t{dst}"
                        
                        f_local.write(edge + "\n")
                        part_idx = src % num_partitions
                        partition_buffers[part_idx].write(edge + "\n")
                        all_edges_count += 1
            
            # Bridge edge
            next_p = (p + 1) % num_partitions
            src_bridge = p * nodes_per_part_approx + random.randint(0, nodes_per_part_approx - 1)
            dst_bridge = next_p * nodes_per_part_approx + random.randint(0, nodes_per_part_approx - 1)
            edge_bridge = f"{src_bridge}\t{dst_bridge}"
            f_local.write(edge_bridge + "\n")
            partition_buffers[src_bridge % num_partitions].write(edge_bridge + "\n")
            all_edges_count += 1

    print(f"Local graph saved to {local_file} ({all_edges_count} edges).")
    
    # Also upload the full graph
    with open(local_file, "rb") as f:
        s3.put_object(Bucket=bucket_name, Key=key_prefix + ".full", Body=f)
    print(f"Uploaded full graph to {key_prefix}.full")

    print(f"Uploading {num_partitions} optimized partitions...")
    
    for i in range(num_partitions):
        part_content = partition_buffers[i].getvalue()
        part_data = part_content.encode('utf-8')
        part_key = f"{key_prefix}/part-{i}"
        s3.put_object(Bucket=bucket_name, Key=part_key, Body=part_data)
        print(f"Uploaded {part_key} ({len(part_data)} bytes)")
            
    # Verify
    resp = s3.list_objects_v2(Bucket=bucket_name, Prefix=key_prefix)
    print(f"Verification: Found {[o['Key'] for o in resp.get('Contents', [])]} in S3.")

if __name__ == "__main__":
    main()
