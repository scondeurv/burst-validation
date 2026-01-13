import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

# Data gathered from the benchmarks (updated with 10M nodes)
data = {
    'Nodes': [10000, 100000, 500000, 1000000, 5000000, 10000000],
    'LPST (ms)': [7.51, 57.01, 364.17, 735.30, 4417.99, 9417.10],
    'Burst (ms)': [17.00, 79.00, 413.00, 898.00, 5139.00, 10876.00],
}

df = pd.DataFrame(data)
df['Speedup'] = df['LPST (ms)'] / df['Burst (ms)']

fig, ax1 = plt.subplots(figsize=(12, 7))

# Plot times
ax1.set_xlabel('Number of Nodes', fontsize=12)
ax1.set_ylabel('Execution Time (ms)', fontsize=12)
ax1.plot(df['Nodes'], df['LPST (ms)'], marker='o', label='LPST (Single Thread)', color='tab:blue', linewidth=2.5, markersize=8)
ax1.plot(df['Nodes'], df['Burst (ms)'], marker='s', label='Burst (Distributed)', color='tab:orange', linewidth=2.5, markersize=8)
ax1.tick_params(axis='y')
ax1.set_xscale('log')
ax1.set_yscale('log')
ax1.grid(True, which="both", ls="-", alpha=0.3)

# Secondary axis for speedup
ax2 = ax1.twinx()
ax2.set_ylabel('Speedup (LPST / Burst)', fontsize=12, color='tab:green')
ax2.plot(df['Nodes'], df['Speedup'], marker='^', label='Speedup', color='tab:green', linestyle='--', linewidth=2.5, markersize=8)
ax2.axhline(y=1.0, color='r', linestyle=':', linewidth=2, alpha=0.7, label='Crossover (1.0x)')
ax2.set_ylim(0, 1.4)
ax2.tick_params(axis='y', labelcolor='tab:green')

# Legend
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=11)

plt.title('Label Propagation Performance: LPST vs Burst (10k to 10M nodes)', fontsize=13, fontweight='bold')

# Add annotation for key finding
textstr = f'Peak speedup: 0.88x at 500k nodes\nNo crossover achieved'
props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
ax1.text(0.98, 0.05, textstr, transform=ax1.transAxes, fontsize=10,
         verticalalignment='bottom', horizontalalignment='right', bbox=props)

plt.tight_layout()
plt.savefig('performance_scaling_10m.png', dpi=100)
print("Graph saved as performance_scaling_10m.png")
print("\nSummary:")
print(df.to_string(index=False))
