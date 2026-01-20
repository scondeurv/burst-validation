import matplotlib.pyplot as plt
import numpy as np

# Datos recopilados de las pruebas
nodes = [10000, 100000, 500000, 1000000, 2000000, 3000000, 4000000, 5000000, 10000000]
lpst_times = [9.02, 115.45, 602.12, 1213.14, 2835.63, 4148.25, 5831.24, 7439.58, 16861.41]
burst_times = [1530.00, 1642.00, 1856.00, 2256.00, 3212.00, 4326.00, 4977.00, 5904.00, 9784.00]

plt.figure(figsize=(10, 6))
plt.plot(nodes, lpst_times, marker='o', linestyle='-', label='Single Threaded (LPST)', color='blue')
plt.plot(nodes, burst_times, marker='s', linestyle='--', label='Burst (16 Workers)', color='red')

# Resaltar el punto de convergencia (aproximado 3.2M)
plt.axvline(x=3200000, color='gray', linestyle=':', alpha=0.7)
plt.text(3300000, 12000, 'Converge ~3.2M', color='black', fontweight='bold')

plt.xscale('log')
plt.yscale('log')
plt.xlabel('Número de Nodos (log)')
plt.ylabel('Tiempo de Ejecución (ms, log)')
plt.title('Performance: Single Threaded vs Burst Label Propagation')
plt.legend()
plt.grid(True, which="both", ls="-", alpha=0.5)

plt.tight_layout()
plt.savefig('performance_comparison_final.png')
print("Gráfico 'performance_comparison_final.png' generado exitosamente.")
