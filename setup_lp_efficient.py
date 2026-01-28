#!/usr/bin/env python3
import argparse
import os
import boto3
from botocore.client import Config
import tempfile

def generate_and_upload_graph(endpoint, access_key, secret_key, bucket, key_prefix, num_nodes, num_partitions, seed_ratio=0.1, density=20):
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
    except:
        pass

    print(f"Generating large graph: {num_nodes} nodes, {num_partitions} partitions, density={density}...")
    
    # Create temp files for partitions to stay memory-efficient
    temp_files = [tempfile.NamedTemporaryFile(mode='w', delete=False) for _ in range(num_partitions)]
    local_graph_file = f"large_{num_nodes}.txt"
    
    try:
        with open(local_graph_file, 'w') as f_local:
            for i in range(num_nodes):
                src = i
                for offset in range(1, density + 1):
                    dst = (i + offset) % num_nodes
                    part_idx = src % num_partitions
                    
                    if i % int(1/seed_ratio) == 0 and offset == 1:
                        label = (i // (num_nodes // 4)) * 100 
                        line = f"{src}\t{dst}\t{label}\n"
                    else:
                        line = f"{src}\t{dst}\n"
                    
                    f_local.write(line)
                    temp_files[part_idx].write(line)
                
                if i % 1000000 == 0:
                    print(f"  Processed {i} nodes...")

        # Close all temp files
        for f in temp_files:
            f.close()

        print(f"✅ Local graph written to {local_graph_file}")

        # Upload partitions
        for i, f in enumerate(temp_files):
            object_name = f"{key_prefix}/part-{str(i).zfill(5)}"
            print(f"Uploading partition {i} to {bucket}/{object_name}...")
            s3.upload_file(f.name, bucket, object_name)
            print(f"  ✅ Uploaded {object_name}")

    finally:
        # Cleanup temp files
        for f in temp_files:
            if os.path.exists(f.name):
                os.remove(f.name)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="High-efficiency graph generator for LP")
    parser.add_argument("--endpoint", default="localhost:9000")
    parser.add_argument("--access-key", default="minioadmin")
    parser.add_argument("--secret-key", default="minioadmin")
    parser.add_argument("--bucket", default="test-bucket")
    parser.add_argument("--prefix", default=None)
    parser.add_argument("--nodes", type=int, required=True)
    parser.add_argument("--partitions", type=int, default=4)
    parser.add_argument("--density", type=int, default=20)
    
    args = parser.parse_args()
    
    prefix = args.prefix if args.prefix else f"graphs/large-{args.nodes}"
    
    generate_and_upload_graph(
        args.endpoint, args.access_key, args.secret_key, 
        args.bucket, prefix, args.nodes, args.partitions, density=args.density
    )
