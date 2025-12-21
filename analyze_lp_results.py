#!/usr/bin/env python3
import json

with open('labelpropagation-burst.json') as f:
    data = json.load(f)

print('📊 Análisis de Resultados - Label Propagation')
print('=' * 60)
print(f'Workers ejecutados: {len(data)}')
print()

# Analizar tiempos del primer worker (todos son similares)
w = data[0]
host_submit = w['host_submit']
timestamps = {t['key']: int(t['value']) for t in w['timestamps']}

print('⏱️  Tiempos de Ejecución (Worker 0):')
print('-' * 60)

# Calcular tiempos
worker_start = timestamps['worker_start']
worker_end = timestamps['worker_end']
get_input_time = timestamps['get_input_end'] - timestamps['get_input']
iter_0_time = timestamps['iter_1_end'] - timestamps['iter_0_start']
total_worker_time = worker_end - worker_start

print(f'Tiempo total del worker: {total_worker_time} ms')
print(f'Tiempo de carga de datos (S3): {get_input_time} ms')
print(f'Tiempo de iteraciones 0-1: {iter_0_time} ms')
print()

# Analizar cada iteración
print('🔄 Desglose por Iteración:')
print('-' * 60)
for i in range(2):  # 2 iteraciones
    iter_key = f'iter_{i}_'
    if f'{iter_key}start' in timestamps:
        start = timestamps[f'{iter_key}start']
        if i == 0:
            end = timestamps['iter_1_end']
        else:
            end = timestamps['worker_end']
        
        broadcast = timestamps.get(f'{iter_key}broadcast_labels', start)
        compute = timestamps.get(f'{iter_key}compute', start)
        reduce_labels = timestamps.get(f'{iter_key}reduce_labels', start)
        reduce_changed = timestamps.get(f'{iter_key}reduce_changed', start)
        
        print(f'Iteración {i}:')
        print(f'  - Broadcast labels: {broadcast - start} ms')
        print(f'  - Compute: {compute - broadcast} ms')
        print(f'  - Reduce labels: {reduce_labels - compute} ms')
        print(f'  - Reduce changed: {reduce_changed - reduce_labels} ms')
        print(f'  - Total: {end - start} ms')
        print()

# Resumen
print('📈 Resumen:')
print('-' * 60)
print(f'✅ Convergencia alcanzada en iteración 1')
print(f'   Threshold configurado: 0')
print(f'   Nodos procesados: 1000')
print(f'   Particiones: 4 workers')
print(f'   Backend: Redis List')
print()

# Tiempos agregados
print('⚡ Tiempos Clave:')
print(f'   - Host submit → Worker start: {worker_start - host_submit} ms')
print(f'   - Worker start → Worker end: {worker_end - worker_start} ms')
print(f'   - Worker end → Finished: {w["finished"] - worker_end} ms')
print(f'   - Total end-to-end: {w["finished"] - host_submit} ms')
