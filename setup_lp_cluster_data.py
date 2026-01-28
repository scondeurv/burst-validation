#!/usr/bin/env python3
import argparse
import io
import os
import boto3
from botocore.client import Config

def generate_and_upload_graph(endpoint, access_key, secret_key, bucket, key_prefix, num_nodes, num_partitions, seed_ratio=0.1, density=20):
    # Use boto3 which is already in requirements.txt
    s3 = boto3.client(
        's3',
        endpoint_url=f"http://{endpoint}" if not endpoint.startswith("http") else endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(signature_version='s3v4'),
        region_name='us-east-1'
    )

    try:
        s3.create_bucket(Bucket=bucket)
        print(f"✅ Bucket creado: {bucket}")
    except s3.exceptions.BucketAlreadyOwnedByYou:
        print(f"ℹ️ Bucket {bucket} ya existe")
    except s3.exceptions.BucketAlreadyExists:
        print(f"ℹ️ Bucket {bucket} ya existe")

    print(f"Generating graph: {num_nodes} nodes, {num_partitions} partitions, density={density}...")
    
    # Pre-generar buffers para cada partición
    partitions = [io.StringIO() for _ in range(num_partitions)]
    
    for i in range(num_nodes):
        src = i
        # Connect to 'density' neighbors (like the standalone version)
        for offset in range(1, density + 1):
            dst = (i + offset) % num_nodes
            part_idx = src % num_partitions
            
            # Add label for seed nodes (10% of nodes)
            if i % int(1/seed_ratio) == 0 and offset == 1:
                label = (i // (num_nodes // 4)) * 100 
                line = f"{src}\t{dst}\t{label}"
            else:
                line = f"{src}\t{dst}"
            partitions[part_idx].write(line + "\n")

    # Subir particiones
    for i, buf in enumerate(partitions):
        data = buf.getvalue().encode('utf-8')
        object_name = f"{key_prefix}/part-{str(i).zfill(5)}"
        
        s3.put_object(
            Bucket=bucket,
            Key=object_name,
            Body=data,
            ContentType="text/plain"
        )
        print(f"✅ Subida partición {i} a {bucket}/{object_name} ({len(data)} bytes)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Configura datos para Label Propagation en MinIO")
    parser.add_argument("--endpoint", default="localhost:9000")
    parser.add_argument("--access-key", default="minioadmin")
    parser.add_argument("--secret-key", default="minioadmin")
    parser.add_argument("--bucket", default="test-bucket")
    parser.add_argument("--prefix", default="graphs/cluster-test")
    parser.add_argument("--nodes", type=int, default=10000)
    parser.add_argument("--partitions", type=int, default=32)
    parser.add_argument("--density", type=int, default=20, help="Number of neighbors each node connects to")
    
    args = parser.parse_args()
    
    generate_and_upload_graph(
        args.endpoint, args.access_key, args.secret_key, 
        args.bucket, args.prefix, args.nodes, args.partitions, density=args.density
    )
