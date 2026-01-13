#!/usr/bin/env python3
"""
Grid search over key parameters to find optimal Burst configuration
Tests: number of partitions, memory per worker, and other variables
"""

import subprocess
import json
import time
import os
import sys
import argparse
from itertools import product

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_benchmark(nodes, partitions, memory, iterations=3):
    """Run a single benchmark with given parameters"""
    
    print(f"\n  Testing: {nodes} nodes, {partitions} partitions, {memory}MB memory")
    
    # Make sure data is generated
    if not os.path.exists(f"large_{nodes}.txt"):
        print(f"  Generating {nodes} node graph...")
        cmd = f"PYTHONPATH=. uv run setup_large_lp_data.py --nodes {nodes}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  Error generating data: {result.stderr}")
            return None
    
    # Repackage action
    subprocess.run("zip -j labelpropagation.zip labelpropagation/ow-lp/bin/exec > /dev/null 2>&1", shell=True)
    
    # Run benchmark
    cmd = f"PYTHONPATH=. uv run benchmark_lp.py --nodes {nodes} --partitions {partitions} --iter {iterations} --memory {memory}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"  Benchmark failed: {result.stderr[:200]}")
        return None
    
    # Extract timings
    output = result.stdout
    lpst_time = None
    burst_time = None
    
    for line in output.split('\n'):
        if 'LPST Time:' in line:
            lpst_time = float(line.split()[-2])
        elif 'Burst Time:' in line or 'BURST Distributed Time:' in line:
            burst_time = float(line.split()[-2])
    
    if lpst_time is None or burst_time is None:
        print(f"  Could not extract timings from output")
        return None
    
    speedup = lpst_time / burst_time if burst_time > 0 else 0
    
    return {
        'nodes': nodes,
        'partitions': partitions,
        'memory': memory,
        'lpst': lpst_time,
        'burst': burst_time,
        'speedup': speedup
    }

def main():
    parser = argparse.ArgumentParser(description='Grid search for optimal Burst parameters')
    parser.add_argument('--nodes', type=int, default=500000, help='Number of nodes to test')
    parser.add_argument('--partitions', type=int, nargs='+', default=[4, 6, 8, 12, 16, 24],
                       help='Partition counts to test (optimized for 24-core system)')
    parser.add_argument('--memory', type=int, nargs='+', default=[1024, 2048, 4096, 8192],
                       help='Memory per worker to test (in MB)')
    parser.add_argument('--iter', type=int, default=3, help='Iterations per benchmark')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("PARAMETER GRID SEARCH FOR BURST OPTIMIZATION")
    print("=" * 80)
    print(f"Problem size: {args.nodes} nodes")
    print(f"Partitions to test: {args.partitions}")
    print(f"Memory configs to test: {[f'{m}MB' for m in args.memory]}")
    print(f"Iterations per test: {args.iter}")
    print("=" * 80)
    
    results = []
    total_tests = len(args.partitions) * len(args.memory)
    current = 0
    
    for partitions in args.partitions:
        for memory in args.memory:
            current += 1
            print(f"\n[{current}/{total_tests}]", end='')
            
            result = run_benchmark(args.nodes, partitions, memory, args.iter)
            if result:
                results.append(result)
                print(f"  → Speedup: {result['speedup']:.2f}x (LPST: {result['lpst']:.0f}ms, Burst: {result['burst']:.0f}ms)")
            else:
                print(f"  → FAILED")
    
    # Print summary
    print("\n" + "=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)
    
    if not results:
        print("No successful benchmarks!")
        return
    
    # Sort by speedup (descending)
    results.sort(key=lambda x: x['speedup'], reverse=True)
    
    print(f"\n{'Rank':<5} {'Partitions':<12} {'Memory':<10} {'LPST (ms)':<12} {'Burst (ms)':<12} {'Speedup':<10}")
    print("-" * 80)
    
    for i, r in enumerate(results[:10], 1):
        speedup_str = f"{r['speedup']:.3f}x"
        print(f"{i:<5} {r['partitions']:<12} {r['memory']:>4}MB     {r['lpst']:>11.0f} {r['burst']:>12.0f} {speedup_str:>9}")
    
    best = results[0]
    print("\n" + "=" * 80)
    print("BEST CONFIGURATION")
    print("=" * 80)
    print(f"Partitions: {best['partitions']}")
    print(f"Memory:     {best['memory']} MB")
    print(f"Speedup:    {best['speedup']:.3f}x")
    print(f"LPST Time:  {best['lpst']:.0f} ms")
    print(f"Burst Time: {best['burst']:.0f} ms")
    
    # Save results to file
    with open('grid_search_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    print("\nResults saved to: grid_search_results.json")

if __name__ == "__main__":
    main()
