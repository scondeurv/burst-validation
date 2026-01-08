import argparse
import pandas as pd
import json

from ow_client.parser import add_openwhisk_to_parser, add_burst_to_parser, try_or_except
from ow_client.time_helper import get_millis
from ow_client.openwhisk_executor import OpenwhiskExecutor
from labelpropagation_utils import generate_payload, add_labelpropagation_to_parser


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_openwhisk_to_parser(parser)
    add_labelpropagation_to_parser(parser)
    add_burst_to_parser(parser)
    args = try_or_except(parser)

    params = generate_payload(
        endpoint=args.lp_endpoint,
        partitions=args.partitions,
        num_nodes=args.num_nodes,
        bucket=args.bucket,
        key=args.key,
        convergence_threshold=args.convergence_threshold,
        max_iterations=args.max_iterations,
    )

    executor = OpenwhiskExecutor(args.ow_host, args.ow_port, args.debug)

    host_submit = get_millis()
    dt = executor.burst("labelpropagation",
                        params,
                        file="./labelpropagation.zip",
                        memory=args.runtime_memory if args.runtime_memory else 4096,
                        custom_image=args.custom_image,
                        debug_mode=args.debug,
                        burst_size=args.granularity,
                        join=args.join,
                        backend=args.backend,
                        chunk_size=args.chunk_size,
                        is_zip=True)
    finished = get_millis()

    flattened_results = [item for sublist in dt.get_results() for item in sublist]
    flattened_results.sort(key=lambda x: x['key'])

    results = []
    for i in flattened_results:
        res = {
            "fn_id": i["key"],
            "host_submit": host_submit,
            "timestamps": i["timestamps"],
            "finished": finished
        }
        if "labels" in i:
            res["labels"] = i["labels"]
        results.append(res)

    json.dump(results, open("labelpropagation-burst.json", "w"))
