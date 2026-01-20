import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Load results
df = pd.read_csv('/tmp/consistency_results.csv')

# Calculate statistics
stats = df.groupby('nodes').agg({
    'lpst_time': ['mean', 'std'],
    'burst_time': ['mean', 'std']
}).reset_index()

stats.columns = ['nodes', 'lpst_mean', 'lpst_std', 'burst_mean', 'burst_std']

print("=" * 60)
print("ANÁLISIS DE CONSISTENCIA DE RESULTADOS")
print("=" * 60)
print(f"\n{'Nodos':<12} {'Método':<10} {'Media (ms)':<12} {'Std Dev':<10} {'CV %':<10}")
print("-" * 60)

for _, row in stats.iterrows():
    nodes = int(row['nodes'])
    lpst_cv = (row['lpst_std'] / row['lpst_mean']) * 100
    burst_cv = (row['burst_std'] / row['burst_mean']) * 100
    
    print(f"{nodes:<12} {'LPST':<10} {row['lpst_mean']:>10.2f}   {row['lpst_std']:>8.2f}   {lpst_cv:>7.2f}")
    print(f"{'':<12} {'Burst':<10} {row['burst_mean']:>10.2f}   {row['burst_std']:>8.2f}   {burst_cv:>7.2f}")
    print("-" * 60)

# Create visualization
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# Plot 1: Mean times with error bars
nodes_list = stats['nodes'].values
x = np.arange(len(nodes_list))
width = 0.35

axes[0].bar(x - width/2, stats['lpst_mean'], width, yerr=stats['lpst_std'], 
            label='Single Thread', capsize=5, alpha=0.8, color='blue')
axes[0].bar(x + width/2, stats['burst_mean'], width, yerr=stats['burst_std'],
            label='Burst (16 Workers)', capsize=5, alpha=0.8, color='red')

axes[0].set_xlabel('Número de Nodos')
axes[0].set_ylabel('Tiempo de Ejecución (ms)')
axes[0].set_title('Consistencia de Resultados (Media ± Desviación Estándar)')
axes[0].set_xticks(x)
axes[0].set_xticklabels([f"{int(n/1e6)}M" for n in nodes_list])
axes[0].legend()
axes[0].grid(axis='y', alpha=0.3)

# Plot 2: Coefficient of variation (CV%)
lpst_cv = (stats['lpst_std'] / stats['lpst_mean']) * 100
burst_cv = (stats['burst_std'] / stats['burst_mean']) * 100

axes[1].bar(x - width/2, lpst_cv, width, label='Single Thread', alpha=0.8, color='blue')
axes[1].bar(x + width/2, burst_cv, width, label='Burst (16 Workers)', alpha=0.8, color='red')

axes[1].set_xlabel('Número de Nodos')
axes[1].set_ylabel('Coeficiente de Variación (%)')
axes[1].set_title('Variabilidad Relativa (CV = σ/μ × 100)')
axes[1].set_xticks(x)
axes[1].set_xticklabels([f"{int(n/1e6)}M" for n in nodes_list])
axes[1].legend()
axes[1].grid(axis='y', alpha=0.3)
axes[1].axhline(y=5, color='green', linestyle='--', alpha=0.5, label='5% threshold')

plt.tight_layout()
plt.savefig('consistency_analysis.png', dpi=150)
print("\n✓ Gráfico de consistencia guardado en 'consistency_analysis.png'")

# Individual runs plot
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

for nodes in df['nodes'].unique():
    subset = df[df['nodes'] == nodes]
    label = f"{int(nodes/1e6)}M nodos"
    axes[0].plot(subset['run'], subset['lpst_time'], marker='o', label=label)
    axes[1].plot(subset['run'], subset['burst_time'], marker='s', label=label)

axes[0].set_xlabel('Run #')
axes[0].set_ylabel('Tiempo de Ejecución (ms)')
axes[0].set_title('Single Thread - Consistencia por Ejecución')
axes[0].legend()
axes[0].grid(True, alpha=0.3)

axes[1].set_xlabel('Run #')
axes[1].set_ylabel('Tiempo de Ejecución (ms)')
axes[1].set_title('Burst (16 Workers) - Consistencia por Ejecución')
axes[1].legend()
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('consistency_runs.png', dpi=150)
print("✓ Gráfico de ejecuciones individuales guardado en 'consistency_runs.png'")
