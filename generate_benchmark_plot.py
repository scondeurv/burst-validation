import matplotlib.pyplot as plt
import pandas as pd

# Load data from the results file
data = []
results_file = "/tmp/benchmark_results.txt"

with open(results_file, "r") as f:
    for line in f:
        parts = line.split()
        if len(parts) == 3:
            data.append({
                "Nodes": int(parts[0]),
                "SingleThread": float(parts[1]),
                "Burst": float(parts[2])
            })

df = pd.DataFrame(data)

# Create the plot
plt.figure(figsize=(10, 6))
plt.plot(df["Nodes"], df["SingleThread"], marker='o', label='Single Thread (LPST)')
plt.plot(df["Nodes"], df["Burst"], marker='s', label='Burst (OpenWhisk Distributed)')

plt.xscale('log')
plt.yscale('log')
plt.xlabel('Number of Nodes (Log Scale)')
plt.ylabel('Time (ms) (Log Scale)')
plt.title('Performance Comparison: Single Thread vs Burst')
plt.legend()
plt.grid(True, which="both", ls="-", alpha=0.5)

# Save the plot
output_path = "/home/sergio/src/tfm/burst-validation/performance_comparison.png"
plt.savefig(output_path)
print(f"Plot saved to {output_path}")
