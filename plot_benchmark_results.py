#!/usr/bin/env python3
"""
Plot Label Propagation Benchmark Results: Burst vs Standalone
"""
import matplotlib.pyplot as plt
import numpy as np

# Updated Benchmark data (from latest complete crossover study)
nodes = [0.5, 2, 5, 8, 10]  # Million nodes
edges = [5, 20, 50, 80, 100]  # Million edges
times_burst = [13.89, 15.99, 20.08, 26.77, 26.86]  # seconds
times_standalone = [1.76, 7.66, 18.50, 31.31, 38.29]  # seconds

# Create figure with subplots
fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('Label Propagation Performance: Crossover Point Analysis\nOpenWhisk Burst (4 workers) vs Standalone Rust', 
             fontsize=16, fontweight='bold')

# 1. Execution Time Comparison
ax1.plot(nodes, times_burst, 'o-', linewidth=2, markersize=8, color='#2E86AB', label='Burst (Distributed 4-workers)')
ax1.plot(nodes, times_standalone, 's-', linewidth=2, markersize=8, color='#A23B72', label='Standalone (Sequential Rust)')
ax1.set_xlabel('Nodes (Millions)', fontsize=12)
ax1.set_ylabel('Execution Time (seconds)', fontsize=12)
ax1.set_title('Execution Time Comparison', fontsize=13, fontweight='bold')
ax1.grid(True, alpha=0.3)
ax1.legend()

# 2. Speedup
speedup = [s/b for s, b in zip(times_standalone, times_burst)]
ax2.plot(nodes, speedup, 'D-', linewidth=2, markersize=8, color='#F18F01')
ax2.axhline(y=1, color='red', linestyle='--', alpha=0.7, linewidth=2, label='Crossover (1.0x)')
ax2.axvline(x=6, color='green', linestyle=':', alpha=0.5, linewidth=2, label='Estimated Crossover (~6M)')
ax2.set_xlabel('Nodes (Millions)', fontsize=12)
ax2.set_ylabel('Speedup (Standalone / Burst)', fontsize=12)
ax2.set_title('Relative Speedup (Crossover at ~6M nodes)', fontsize=13, fontweight='bold')
ax2.grid(True, alpha=0.3)
ax2.set_ylim(0, max(speedup) * 1.2)
ax2.legend()

# Add speedup labels
for i, (x, s) in enumerate(zip(nodes, speedup)):
    ax2.annotate(f'{s:.2f}x', (x, s), textcoords="offset points", 
                xytext=(0,10), ha='center', fontsize=10, fontweight='bold')

# 3. Throughput (Million edges/sec)
throughput_burst = [e/t for e, t in zip(edges, times_burst)]
throughput_standalone = [e/t for e, t in zip(edges, times_standalone)]
ax3.plot(nodes, throughput_burst, 'o-', linewidth=2, markersize=8, color='#2E86AB', label='Burst')
ax3.plot(nodes, throughput_standalone, 's-', linewidth=2, markersize=8, color='#A23B72', label='Standalone')
ax3.set_xlabel('Nodes (Millions)', fontsize=12)
ax3.set_ylabel('M edges / second', fontsize=12)
ax3.set_title('Edge Processing Throughput', fontsize=13, fontweight='bold')
ax3.grid(True, alpha=0.3)
ax3.legend()

# 4. Scaling Factor (Efficiency)
standalone_scaling = [times_standalone[i]/times_standalone[0] for i in range(len(nodes))]
burst_scaling = [times_burst[i]/times_burst[0] for i in range(len(nodes))]
size_scaling = [nodes[i]/nodes[0] for i in range(len(nodes))]

ax4.plot(nodes, size_scaling, '--', color='gray', label='Ideal (Linear)', alpha=0.5, linewidth=2)
ax4.plot(nodes, standalone_scaling, 's-', color='#A23B72', label='Standalone Growth', linewidth=2, markersize=8)
ax4.plot(nodes, burst_scaling, 'o-', color='#2E86AB', label='Burst Growth', linewidth=2, markersize=8)
ax4.set_xlabel('Nodes (Millions)', fontsize=12)
ax4.set_ylabel('Relative Growth Factor', fontsize=12)
ax4.set_title('Scaling Factor vs Baseline (0.5M)', fontsize=13, fontweight='bold')
ax4.grid(True, alpha=0.3)
ax4.legend()

plt.tight_layout()
plt.savefig('lp_benchmark_comparison.png', dpi=300, bbox_inches='tight')
print("✓ Gráfica guardada en: lp_benchmark_comparison.png")

# Print summary statistics
print("\n=== Benchmark Summary ===")
print(f"{'Nodes (M)':<12} | {'Standalone (s)':<15} | {'Burst (s)':<12} | {'Speedup':<8}")
print('-' * 55)
for i in range(len(nodes)):
    print(f"{nodes[i]:<12} | {times_standalone[i]:<15} | {times_burst[i]:<12} | {speedup[i]:.2f}x")

plt.tight_layout()
plt.show()
