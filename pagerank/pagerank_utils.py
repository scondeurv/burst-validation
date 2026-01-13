import argparse
import json
import boto3
import os
from pprint import pprint

DEFAULT_ERROR = 0.00005
DEFAULT_OUTPUT = "pagerank_payload.json"

AWS_S3_REGION = "us-east-1"
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", "minioadmin")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "minioadmin")

def generate_payload(endpoint, partitions, num_nodes, bucket, key, granularity=1, error=DEFAULT_ERROR, max_iterations=None):
    payload_list = []
    num_requests = partitions // granularity
    
    for i in range(num_requests):
        payload_list.append(
            {
                "group_id": i,
                "partitions": partitions,
                "granularity": granularity,
                "num_nodes": num_nodes,
                "error": error,
                **({"iterations": max_iterations} if max_iterations is not None else {}),
                "input_data": {
                    "bucket": bucket,
                    "key": key, # Base key, workers will append /part-N
                    "endpoint": endpoint,
                    "region": AWS_S3_REGION,
                    "aws_access_key_id": AWS_ACCESS_KEY_ID,
                    "aws_secret_access_key": AWS_SECRET_ACCESS_KEY,
                },
            }
        )

    return payload_list

def add_pagerank_to_parser(parser):
    parser.add_argument("--pr-endpoint", type=str, required=True,
                        help="Endpoint of the S3 service in which the pagerank file is stored")
    parser.add_argument("--partitions", type=int, required=True, help="Number of partitions")
    parser.add_argument("--num-nodes", type=int, required=True, help="Number of nodes in the dataset graph")
    parser.add_argument("--bucket", type=str, required=True, help="Pagerank bucket name")
    parser.add_argument("--key", type=str, required=True, help="Pagerank object key")
    parser.add_argument("--max-iterations", type=int, default=None, help="Maximum iterations")
