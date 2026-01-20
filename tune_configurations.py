#!/usr/bin/env python3
import subprocess
import json
import os
import sys

def run_test(nodes, partitions, granularity, chunk_size, memory, iterations=10):
    print(f"\n>>> TESTING: Nodes={nodes}, Partitions={partitions}, Granularity={granularity}, Chunk={chunk_size}, Memory={memory}")
    
    cmd = [
        "python3", "benchmark_lp.py",
        "--nodes", str(nodes),
        "--partitions", str(partitions),
        "--granularity", str(granularity),
        "--chunk-size", str(chunk_size),
        "--memory", str(memory),
        "--iter", str(iterations)
    ]
    
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    
    if result.returncode != 0:
        print(f"FAILED: {result.stderr}")
        return None
    
    output = result.stdout
    lpst_time = 0
    burst_time = 0
    
    for line in output.split('\n'):
        if "LPST Finished in" in line:
            lpst_time = float(line.split()[-2])
        if "BURST Distributed Time:" in line:
            burst_time = float(line.split()[-2])
            
    speedup = lpst_time / burst_time if burst_time > 0 else 0
    print(f"RESULT: LPST={lpst_time:.2f}ms, Burst={burst_time:.2f}ms, Speedup={speedup:.2f}x")
    
    return {
        "nodes": nodes,
        "partitions": partitions,
        "granularity": granularity,
        "chunk_size": chunk_size,
        "memory": memory,
        "lpst_ms": lpst_time,
        "burst_ms": burst_time,
        "speedup": speedup
    }

def main():
    configs = [
        # 100k Nodes
        {"nodes": 100000, "partitions": 16, "granularity": 1, "chunk_size": 1024, "memory": 512},
        {"nodes": 100000, "partitions": 4, "granularity": 1, "chunk_size": 256, "memory": 512},
        {"nodes": 100000, "partitions": 4, "granularity": 4, "chunk_size": 256, "memory": 512},
        
        # 1M Nodes
        {"nodes": 1000000, "partitions": 8, "granularity": 1, "chunk_size": 512, "memory": 1024},
        {"nodes": 1000000, "partitions": 16, "granularity": 1, "chunk_size": 1024, "memory": 1024},
        
        # 5M Nodes
        {"nodes": 5000000, "partitions": 16, "granularity": 1, "chunk_size": 1024, "memory": 2048},
        
        # 10M Nodes
        {"nodes": 10000000, "partitions": 16, "granularity": 1, "chunk_size": 1024, "memory": 1536},
        {"nodes": 10000000, "partitions": 21, "granularity": 1, "chunk_size": 1024, "memory": 1536}
    ]
    
    final_results = []
    
    for cfg in configs:
        # Reduce iterations for very large graphs
        iters = 10
        if cfg['nodes'] >= 5000000:
            iters = 3
        res = run_test(**cfg, iterations=iters)
        if res:
            final_results.append(res)
            
    with open("tuning_results.json", "w") as f:
        json.dump(final_results, f, indent=4)
    
    print("\n" + "="*50)
    print("BEST CONFIGURATIONS SUMMARY")
    print("="*50)
    
    # Sort by nodes and then speedup
    final_results.sort(key=lambda x: (x['nodes'], -x['speedup']))
    
    current_nodes = 0
    for r in final_results:
        if r['nodes'] != current_nodes:
            print(f"\nNodes: {r['nodes']}")
            current_nodes = r['nodes']
            print(f"  * BEST: P={r['partitions']}, G={r['granularity']}, C={r['chunk_size']}, M={r['memory']} -> {r['speedup']:.2f}x")
        else:
            print(f"    Alternative: P={r['partitions']}, G={r['granularity']}, C={r['chunk_size']}, M={r['memory']} -> {r['speedup']:.2f}x")

if __name__ == "__main__":
    main()
