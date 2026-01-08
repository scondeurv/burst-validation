#!/usr/bin/env python3
from minio import Minio

client = Minio(
    "localhost:9000",
    access_key="minioadmin",
    secret_key="minioadmin",
    secure=False
)

# Get first file
obj = client.get_object("test-bucket", "graphs/test-graph/part-00000")
content = obj.read().decode('utf-8')

print("=== First 30 lines of part-00000 ===")
for i, line in enumerate(content.split('\n')[:30]):
    parts = line.split('\t')
    print(f"Line {i}: {len(parts)} columns - {line}")

print("\n=== Summary ===")
lines = content.strip().split('\n')
with_labels = sum(1 for line in lines if len(line.split('\t')) >= 3)
total = len(lines)
print(f"Total edges: {total}")
print(f"Edges with labels: {with_labels}")
print(f"Edges without labels: {total - with_labels}")
