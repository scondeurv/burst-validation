#!/usr/bin/env python3
"""
Upload PageRank test dataset to MinIO for OpenWhisk execution.
"""

import boto3
import os

# MinIO configuration
s3_client = boto3.client(
    's3',
    endpoint_url='http://localhost:9000',
    aws_access_key_id='minioadmin',
    aws_secret_access_key='minioadmin'
)

bucket_name = 'test-bucket'
local_dataset_path = 'pagerank/test-dataset/edges'
s3_prefix = 'graphs/pagerank'

print(f"📤 Uploading PageRank dataset to MinIO...")

# Upload all partition files
partition_files = sorted([f for f in os.listdir(local_dataset_path) if f.startswith('part-')])

for partition_file in partition_files:
    local_file = os.path.join(local_dataset_path, partition_file)
    s3_key = f"{s3_prefix}/{partition_file}"
    
    with open(local_file, 'rb') as f:
        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=f
        )
    
    print(f"  ✓ Uploaded {partition_file} to s3://{bucket_name}/{s3_key}")

print(f"\n✅ Dataset uploaded successfully!")
print(f"   Bucket: {bucket_name}")
print(f"   Prefix: {s3_prefix}")
print(f"   Files: {len(partition_files)}")
