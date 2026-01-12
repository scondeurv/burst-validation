#!/usr/bin/env python3
"""
Setup complex deterministic test data for Label Propagation in MinIO
Creates a multi-community graph with different topologies:
- Community A (nodes 0-7): Dense clique with internal structure
- Community B (nodes 8-14): Star topology with central hub
- Community C (nodes 15-19): Chain/path topology
- Bridge edges connecting communities

Workers: 8
Total Nodes: 20
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
key_prefix = "graphs/deterministic-complex"

# Create bucket if it doesn't exist
if not client.bucket_exists(bucket_name):
    client.make_bucket(bucket_name)

edges = []

# ============================================================
# Community A: Dense clique (nodes 0-7)
# Seed: Node 0 -> Label 100
# ============================================================
clique_a = list(range(0, 8))
for src in clique_a:
    for dst in clique_a:
        if src != dst:
            edge_str = f"{src}\t{dst}"
            if src == 0:  # Seed for community A
                edge_str += "\t100"
            edges.append(edge_str)

# ============================================================
# Community B: Star topology (nodes 8-14)
# Hub: Node 8 (Seed -> Label 200)
# Leaves: 9, 10, 11, 12, 13, 14
# ============================================================
hub_b = 8
leaves_b = list(range(9, 15))
# Hub connects to all leaves
for leaf in leaves_b:
    edge_str = f"{hub_b}\t{leaf}"
    if hub_b == 8:
        edge_str += "\t200"
    edges.append(edge_str)
# Leaves connect back to hub
for leaf in leaves_b:
    edges.append(f"{leaf}\t{hub_b}")

# ============================================================
# Community C: Chain/Path topology (nodes 15-19)
# Seed: Node 15 -> Label 300
# Linear chain: 15 -> 16 -> 17 -> 18 -> 19
# Add bidirectional edges for connectivity
# ============================================================
chain_c = list(range(15, 20))
for i in range(len(chain_c) - 1):
    src = chain_c[i]
    dst = chain_c[i + 1]
    edge_str = f"{src}\t{dst}"
    if src == 15:
        edge_str += "\t300"
    edges.append(edge_str)
    # Bidirectional
    edges.append(f"{dst}\t{src}")

# ============================================================
# Bridge edges between communities (sparse connections)
# ============================================================
# Bridge A-B: Node 5 (end of clique A) -> Node 8 (hub of B)
edges.append("5\t8")
edges.append("8\t5")

# Bridge B-C: Node 14 (leaf of B) -> Node 15 (start of chain C)
edges.append("14\t15")
edges.append("15\t14")

# Bridge C-A: Node 19 (end of chain C) -> Node 2 (middle of clique A)
edges.append("19\t2")
edges.append("2\t19")

# ============================================================
# Internal community connections (strengthen clusters)
# ============================================================
# Extra edges within A for strength
edges.append("0\t3")
edges.append("3\t0")
edges.append("1\t5")
edges.append("5\t1")

# Extra edges within B leaves for local cohesion
edges.append("9\t10")
edges.append("10\t9")
edges.append("11\t12")
edges.append("12\t11")
edges.append("13\t14")
edges.append("14\t13")

# Partition edges based on source node modulo worker count
num_workers = 8
partitions = [[] for _ in range(num_workers)]

for edge in edges:
    src_node = int(edge.split('\t')[0])
    partition_id = src_node % num_workers
    partitions[partition_id].append(edge)

# Upload each partition
total_edges = 0
for i in range(num_workers):
    if partitions[i]:
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
        
        print(f"✅ Uploaded partition {i:2d} to {bucket_name}/{object_key} ({len(partitions[i]):3d} edges)")
        total_edges += len(partitions[i])
    else:
        print(f"⚠️  Partition {i:2d} is empty (no nodes assigned)")

print(f"\n{'='*60}")
print(f"Summary:")
print(f"{'='*60}")
print(f"Total Nodes:     20")
print(f"  - Community A (dense clique):  nodes 0-7")
print(f"  - Community B (star):          nodes 8-14")
print(f"  - Community C (chain):         nodes 15-19")
print(f"Total Edges:     {total_edges}")
print(f"Workers:         {num_workers}")
print(f"\nExpected Convergence:")
print(f"  - Nodes 0-7   -> Label 100 (from seed node 0)")
print(f"  - Nodes 8-14  -> Label 200 (from seed node 8)")
print(f"  - Nodes 15-19 -> Label 300 (from seed node 15)")
print(f"\nNote: Bridge edges create weak connections between communities.")
print(f"      Strong internal structure should preserve label boundaries.")
