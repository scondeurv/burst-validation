import matplotlib.pyplot as plt
import numpy as np

# Data
nodes_m = np.array([1, 5, 15, 25])
nodes = nodes_m * 1_000_000
times_standalone_s = np.array([3.61, 21.6, 63.8, 108.4])
times_burst_s = np.array([5.04, 14.1, 33.3, 50.8])
speedups = times_standalone_s / times_burst_s

# Figure 1: Comparison + Speedup (Crossover)
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
fig.suptitle('Label Propagation Performance Analysis (4 Partitions)', fontsize=16, fontweight='bold')

# Plot 1: Times
ax1.plot(nodes_m, times_standalone_s, 'o-', linewidth=2.5, markersize=10, color='#A23B72', label='Standalone (Sequential Rust)')
ax1.plot(nodes_m, times_burst_s, 's-', linewidth=2.5, markersize=10, color='#2E86AB', label='Burst (Distributed OpenWhisk)')
ax1.set_xlabel('Graph Size (Million Nodes)', fontsize=12)
ax1.set_ylabel('Execution Time (seconds)', fontsize=12)
ax1.set_title('Execution Time Comparison', fontsize=14)
ax1.grid(True, alpha=0.3)
ax1.legend()

# Interpolate crossover (linear between first two points)
# x1=1, y_s1=3.61, y_b1=5.04
# x2=5, y_s2=21.6, y_b2=14.1
# Standalone: y = 4.4975 * x - 0.8875
# Burst: y = 2.265 * x + 2.775
# 4.4975x - 0.8875 = 2.265x + 2.775
# 2.2325x = 3.6625 => x = 1.64
crossover_x = 1.64
ax1.axvline(x=crossover_x, color='red', linestyle='--', alpha=0.6)
ax1.annotate(f'Crossover point\n~{crossover_x:.2f}M nodes', xy=(crossover_x, 8), xytext=(crossover_x+2, 30),
             arrowprops=dict(facecolor='black', shrink=0.05, width=1, headwidth=5))

# Plot 2: Speedup
ax2.plot(nodes_m, speedups, 'D-', linewidth=2.5, markersize=10, color='#F18F01')
ax2.axhline(y=1.0, color='red', linestyle='--', linewidth=2, label='Break-even')
ax2.fill_between(nodes_m, 1.0, speedups, where=(speedups > 1.0), alpha=0.2, color='green', label='Burst Advantage')
ax2.fill_between(nodes_m, speedups, 1.0, where=(speedups < 1.0), alpha=0.2, color='red', label='Standalone Advantage')
ax2.set_xlabel('Graph Size (Million Nodes)', fontsize=12)
ax2.set_ylabel('Speedup Factor', fontsize=12)
ax2.set_title('Speedup Analysis', fontsize=14)
ax2.grid(True, alpha=0.3)
ax2.legend()

# Add labels to speedup points
for x, y in zip(nodes_m, speedups):
    ax2.annotate(f'{y:.2f}x', (x, y), textcoords="offset points", xytext=(0,12), ha='center', fontweight='bold')

plt.tight_layout(rect=[0, 0, 1, 0.95])
plt.savefig('lp_performance_dashboard.png', dpi=300)
print("✅ Dashboard guardado en: lp_performance_dashboard.png")

# Figure 2: Throughput
plt.figure(figsize=(10, 6))
edges = nodes_m * 10 # Ring graph
throughput_s = edges / times_standalone_s
throughput_b = edges / times_burst_s

plt.plot(nodes_m, throughput_s, 'o-', label='Standalone (Sequential)', color='#A23B72')
plt.plot(nodes_m, throughput_b, 's-', label='Burst (Distributed)', color='#2E86AB')
plt.xlabel('Nodes (Millions)')
plt.ylabel('Throughput (Million edges/sec)')
plt.title('Processing Throughput Scaling')
plt.grid(True, alpha=0.3)
plt.legend()
plt.savefig('lp_throughput_scaling.png', dpi=300)
print("✅ Gráfica de throughput guardada en: lp_throughput_scaling.png")
