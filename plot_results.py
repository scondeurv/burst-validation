import matplotlib.pyplot as plt
import pandas as pd

# Data gathered from the benchmarks
data = {
    'Nodes': [10000, 100000, 500000, 1000000, 5000000],
    'LPST (ms)': [25, 83.18, 367.63, 740, 4734.82],
    'Burst (ms)': [52, 153.0, 421.0, 880, 5265],
}

df = pd.DataFrame(data)
df['Speedup'] = df['LPST (ms)'] / df['Burst (ms)']

fig, ax1 = plt.subplots(figsize=(10, 6))

# Plot times
ax1.set_xlabel('Number of Nodes')
ax1.set_ylabel('Execution Time (ms)')
ax1.plot(df['Nodes'], df['LPST (ms)'], marker='o', label='LPST (Single Thread)', color='tab:blue')
ax1.plot(df['Nodes'], df['Burst (ms)'], marker='s', label='Burst (Distributed)', color='tab:orange')
ax1.tick_params(axis='y')
ax1.set_xscale('log')
ax1.set_yscale('log')
ax1.grid(True, which="both", ls="-", alpha=0.5)

# Secondary axis for speedup
ax2 = ax1.twinx()
ax2.set_ylabel('Speedup (LPST / Burst)')
ax2.plot(df['Nodes'], df['Speedup'], marker='^', label='Speedup', color='tab:green', linestyle='--')
ax2.axhline(y=1.0, color='r', linestyle=':', label='Crossover (1.0x)')
ax2.set_ylim(0, 1.2)

# Legend
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')

plt.title('Label Propagation Performance Scaling: LPST vs Burst')
plt.tight_layout()
plt.savefig('performance_scaling.png')
print("Graph saved as performance_scaling.png")
