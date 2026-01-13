#!/usr/bin/env python3
"""
Analyze different partition granularities and their impact on communication overhead
With 24 cores and 32GB RAM, determine optimal configurations
"""

import math

def analyze_configuration(nodes, partitions, memory_per_worker_mb):
    """Analyze a configuration"""
    
    # Estimation models
    work_per_partition = nodes / partitions
    
    # Communication complexity (simplified)
    # Each worker needs to sync labels with others
    sync_messages = partitions * (partitions - 1) / 2  # All-to-all in worst case
    
    # Memory model: nodes + overhead
    # Assuming ~200 bytes per node (label + adjacency info)
    data_size_per_node = 200  # bytes
    total_data = (nodes * data_size_per_node) / 1024 / 1024  # MB
    data_per_partition = total_data / partitions
    overhead_factor = 1.3  # Temporary buffers, serialization, etc
    
    required_memory = (data_per_partition * overhead_factor)
    
    print(f"\nPartitions: {partitions}, Memory: {memory_per_worker_mb}MB")
    print(f"  Work per partition: {work_per_partition:,.0f} nodes")
    print(f"  Est. data per partition: {data_per_partition:.1f}MB (with {overhead_factor}x overhead)")
    print(f"  Memory constraint: {'✓ OK' if required_memory <= memory_per_worker_mb else '✗ VIOLATED'}")
    print(f"  Sync messages (est.): {sync_messages:.0f}")
    
    # Granularity score: balance between too fine (overhead) and too coarse (imbalance)
    # Optimal is around 100k-500k nodes per partition for this problem
    granularity_score = 0
    if 100000 <= work_per_partition <= 500000:
        granularity_score = 10
    elif 50000 <= work_per_partition <= 1000000:
        granularity_score = 8
    elif 10000 <= work_per_partition <= 2000000:
        granularity_score = 5
    else:
        granularity_score = 2
    
    # Memory utilization score
    if memory_per_worker_mb >= required_memory * 1.5:  # Good headroom
        memory_score = 10
    elif memory_per_worker_mb >= required_memory:
        memory_score = 8
    else:
        memory_score = 0  # Invalid
    
    # Partition count efficiency score (divisors of 24)
    core_divisors = [1, 2, 3, 4, 6, 8, 12, 24]
    if partitions in core_divisors:
        partition_score = 10
    elif partitions % 2 == 0 and partitions <= 48:
        partition_score = 8
    else:
        partition_score = 5
    
    total_score = (granularity_score * 0.4) + (memory_score * 0.3) + (partition_score * 0.3)
    
    return {
        'partitions': partitions,
        'memory': memory_per_worker_mb,
        'work_per_partition': work_per_partition,
        'required_memory': required_memory,
        'granularity_score': granularity_score,
        'memory_score': memory_score,
        'partition_score': partition_score,
        'total_score': total_score,
        'memory_ok': required_memory <= memory_per_worker_mb
    }

def main():
    print("=" * 80)
    print("CONFIGURATION ANALYSIS FOR 24-CORE, 32GB SYSTEM")
    print("=" * 80)
    
    # Test sizes
    test_cases = [
        (100000, "100k nodes"),
        (500000, "500k nodes"),
        (1000000, "1M nodes"),
        (5000000, "5M nodes"),
    ]
    
    for nodes, label in test_cases:
        print("\n" + "=" * 80)
        print(f"{label}")
        print("=" * 80)
        
        # Test various partition counts
        partitions_to_test = [4, 6, 8, 12, 16, 24, 32, 48]
        memory_to_test = [512, 1024, 2048, 4096, 8192]
        
        configs = []
        for p in partitions_to_test:
            for m in memory_to_test:
                config = analyze_configuration(nodes, p, m)
                if config['memory_ok']:
                    configs.append(config)
        
        # Sort by total score
        configs.sort(key=lambda x: x['total_score'], reverse=True)
        
        print(f"\nTop 5 configurations for {label}:")
        print(f"{'Partitions':<12} {'Memory':<10} {'Score':<8} {'Granularity':<12} {'Memory':<10}")
        print("-" * 80)
        
        for config in configs[:5]:
            print(f"{config['partitions']:<12} {config['memory']:>4}MB     {config['total_score']:>6.1f}   {config['granularity_score']:>6.1f}        {config['partition_score']:>6.1f}")

if __name__ == "__main__":
    main()
