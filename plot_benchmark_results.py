#!/usr/bin/env python3
"""
Plot Label Propagation Benchmark Results
"""
import matplotlib.pyplot as plt
import numpy as np

# Benchmark data
nodes = [1, 5, 8, 10, 12.5, 15, 20, 25]  # Million nodes
times = [5.7, 11.2, 16.4, 20.3, 25.6, 27.5, 33.7, 39.8]  # seconds
edges = [10, 50, 80, 100, 125, 150, 200, 250]  # Million edges
memory = [2048, 2048, 2048, 2048, 2048, 4096, 4096, 4096]  # MB

# Create figure with subplots
fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('Label Propagation Scaling Benchmarks (OpenWhisk Burst)', 
             fontsize=16, fontweight='bold')

# 1. Execution Time vs Nodes
ax1.plot(nodes, times, 'o-', linewidth=2, markersize=8, color='#2E86AB', label='Actual')
# Linear fit
coeffs = np.polyfit(nodes, times, 1)
linear_fit = np.poly1d(coeffs)
ax1.plot(nodes, linear_fit(nodes), '--', color='#A23B72', linewidth=2, 
         label=f'Linear fit: {coeffs[0]:.2f}x + {coeffs[1]:.2f}')
ax1.set_xlabel('Nodes (Millions)', fontsize=12)
ax1.set_ylabel('Execution Time (seconds)', fontsize=12)
ax1.set_title('Scaling: Execution Time vs Graph Size', fontsize=13, fontweight='bold')
ax1.grid(True, alpha=0.3)
ax1.legend()
# Add data labels
for i, (x, y) in enumerate(zip(nodes, times)):
    ax1.annotate(f'{y}s', (x, y), textcoords="offset points", 
                xytext=(0,5), ha='center', fontsize=9)

# 2. Throughput
throughput_nodes = [n/t for n, t in zip(nodes, times)]  # M nodes/sec
throughput_edges = [e/t for e, t in zip(edges, times)]  # M edges/sec

ax2_twin = ax2.twinx()
line1 = ax2.plot(nodes, throughput_nodes, 's-', linewidth=2, markersize=8, 
                 color='#F18F01', label='Nodes/sec')
line2 = ax2_twin.plot(nodes, throughput_edges, '^-', linewidth=2, markersize=8, 
                      color='#C73E1D', label='Edges/sec')
ax2.set_xlabel('Graph Size (Million Nodes)', fontsize=12)
ax2.set_ylabel('Throughput (M nodes/sec)', fontsize=12, color='#F18F01')
ax2_twin.set_ylabel('Throughput (M edges/sec)', fontsize=12, color='#C73E1D')
ax2.set_title('Processing Throughput', fontsize=13, fontweight='bold')
ax2.grid(True, alpha=0.3)
ax2.tick_params(axis='y', labelcolor='#F18F01')
ax2_twin.tick_params(axis='y', labelcolor='#C73E1D')
# Combine legends
lines = line1 + line2
labels = [l.get_label() for l in lines]
ax2.legend(lines, labels, loc='upper right')

# 3. Scaling Efficiency (vs 1M baseline)
baseline_time = times[0]
baseline_nodes = nodes[0]
ideal_times = [baseline_time * (n/baseline_nodes) for n in nodes]
actual_times = times

ax3.plot(nodes, ideal_times, 'o--', linewidth=2, markersize=8, 
         color='#6A994E', label='Ideal Linear Scaling', alpha=0.7)
ax3.plot(nodes, actual_times, 's-', linewidth=2, markersize=8, 
         color='#2E86AB', label='Actual Performance')
ax3.set_xlabel('Nodes (Millions)', fontsize=12)
ax3.set_ylabel('Execution Time (seconds)', fontsize=12)
ax3.set_title('Actual vs Ideal Linear Scaling', fontsize=13, fontweight='bold')
ax3.grid(True, alpha=0.3)
ax3.legend()

# Calculate efficiency
efficiency = [(ideal/actual)*100 for ideal, actual in zip(ideal_times, actual_times)]
for i, (x, eff) in enumerate(zip(nodes, efficiency)):
    ax3.annotate(f'{eff:.0f}%', (x, actual_times[i]), 
                textcoords="offset points", xytext=(0,-15), 
                ha='center', fontsize=8, color='red')

# 4. Memory Configuration & Performance
colors = ['#2E86AB' if m == 2048 else '#E63946' for m in memory]
bars = ax4.bar(range(len(nodes)), times, color=colors, alpha=0.7, edgecolor='black')
ax4.set_xticks(range(len(nodes)))
ax4.set_xticklabels([f'{n}M' for n in nodes], rotation=45)
ax4.set_xlabel('Graph Size', fontsize=12)
ax4.set_ylabel('Execution Time (seconds)', fontsize=12)
ax4.set_title('Performance by Memory Configuration', fontsize=13, fontweight='bold')
ax4.grid(True, alpha=0.3, axis='y')

# Add legend for memory
from matplotlib.patches import Patch
legend_elements = [Patch(facecolor='#2E86AB', label='2048MB'),
                   Patch(facecolor='#E63946', label='4096MB')]
ax4.legend(handles=legend_elements, loc='upper left')

# Add time labels on bars
for i, (bar, t) in enumerate(zip(bars, times)):
    height = bar.get_height()
    ax4.text(bar.get_x() + bar.get_width()/2., height,
            f'{t}s', ha='center', va='bottom', fontsize=9)

plt.tight_layout()
plt.savefig('lp_benchmark_results.png', dpi=300, bbox_inches='tight')
print("✓ Gráfica guardada en: lp_benchmark_results.png")

# Print summary statistics
print("\n=== Summary Statistics ===")
print(f"Data points: {len(nodes)}")
print(f"Node range: {min(nodes)}M - {max(nodes)}M")
print(f"Time range: {min(times)}s - {max(times)}s")
print(f"Average throughput: {np.mean(throughput_nodes):.2f} M nodes/sec")
print(f"Average throughput: {np.mean(throughput_edges):.2f} M edges/sec")
print(f"Linear fit slope: {coeffs[0]:.3f} sec/M nodes")
print(f"Linear fit R²: {np.corrcoef(nodes, times)[0,1]**2:.4f}")
print(f"Average scaling efficiency: {np.mean(efficiency):.1f}%")

plt.show()
