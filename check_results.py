import boto3
import os

s3 = boto3.client('s3',
                 endpoint_url='http://localhost:9000',
                 aws_access_key_id='minioadmin',
                 aws_secret_access_key='minioadmin',
                 region_name='us-east-1')

bucket = 'test-bucket'
prefix = 'graphs/cluster-test/output/'

print(f"Listing objects in s3://{bucket}/{prefix}:")
response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
if 'Contents' in response:
    for obj in response['Contents']:
        print(f" - {obj['Key']} ({obj['Size']} bytes)")
    
    # Read and parse labels_final.json
    target_key = prefix + 'labels_final.json'
    print(f"\nSample content from {target_key}:")
    try:
        data = s3.get_object(Bucket=bucket, Key=target_key)['Body'].read().decode('utf-8')
        import json
        parsed = json.loads(data)
        labels = parsed.get('labels', {})
        print(f"Total nodes in file: {len(labels)}")
        print("First 15 mappings:")
        # Sort keys as integers if possible
        sorted_nodes = sorted(labels.keys(), key=int)
        for node in sorted_nodes[:15]:
            print(f"  Node {node}: Label {labels[node]}")
    except Exception as e:
        print(f"Error reading file: {e}")
else:
    print(f"No results found in {prefix}")
