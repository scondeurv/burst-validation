from minio import Minio
import os

client = Minio("localhost:9000", access_key="minioadmin", secret_key="minioadmin", secure=False)
if not client.bucket_exists("test-bucket"):
    client.make_bucket("test-bucket")
    
client.fput_object("test-bucket", "graphs/large-2000", "large_2000.txt")
print("Uploaded large_2000.txt to test-bucket/graphs/large-2000")
