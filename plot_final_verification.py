import matplotlib.pyplot as plt
import numpy as np

# Datos consolidados de las pruebas de consistencia
nodes = [1000000, 3000000, 4000000, 5000000, 10000000]
lpst_times = [1213.67, 4047.69, 6199.37, 7333.69, 16835.90]
burst_times = [2236.00, 4035.00, 4668.00, 5359.00, 10139.00]

plt.figure(figsize=(10, 6))
plt.plot(nodes, lpst_times, marker='o', linestyle='-', label='Single Threaded (LPST)', color='blue', linewidth=2)
plt.plot(nodes, burst_times, marker='s', linestyle='--', label='Burst (16 Workers)', color='red', linewidth=2)

# Punto de convergencia detectado en la segunda prueba (3M)
plt.scatter([3000000], [4035.00], color='green', s=100, zorder=5, label='Crossover Point')
plt.annotate('Punto de Convergencia\n(~3M nodos)', 
             xy=(3000000, 4035.00), 
             xytext=(3500000, 2000),
             arrowprops=dict(facecolor='black', shrink=0.05, width=1, headwidth=8))

plt.xscale('log')
plt.yscale('log')
plt.xlabel('Número de Nodos (escala log)')
plt.ylabel('Tiempo de Ejecución (ms, escala log)')
plt.title('Consistencia de Rendimiento: LPST vs Burst (16 Particiones)')
plt.legend()
plt.grid(True, which="both", ls="-", alpha=0.3)

# Añadir etiquetas de speedup
for i, txt in enumerate(nodes):
    speedup = lpst_times[i] / burst_times[i]
    plt.text(nodes[i], burst_times[i] * 0.8, f"{speedup:.2f}x", ha='center', fontsize=9, color='darkred')

plt.tight_layout()
plt.savefig('performance_verification_final.png')
print("Gráfico 'performance_verification_final.png' generado con los datos de consistencia.")
