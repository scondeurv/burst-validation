#!/usr/bin/env python3
"""
Analiza y compara los timestamps de Worker 0 entre 9.6M y 10M para entender
la diferencia en rendimiento.
"""

import re

def extract_worker_data(filename):
    """Extrae timestamps del log de benchmark."""
    with open(filename, 'r') as f:
        content = f.read()
    
    # Buscar líneas con timestamps
    timestamps = {}
    for line in content.split('\n'):
        # Buscar patrones como: {'key': 'worker_start', 'value': '1769706997240'}
        match = re.search(r"'key': '([^']+)', 'value': '(\d+)'", line)
        if match:
            key, value = match.groups()
            timestamps[key] = int(value)
    
    return timestamps

def analyze_iterations(ts, label):
    """Analiza timing de iteraciones."""
    print(f"\n{label}:")
    
    if not ts:
        print("  No timestamps found!")
        return None
    
    start = ts.get('worker_start', 0)
    print(f"  S3 input load: {ts.get('get_input_end', 0) - ts.get('get_input', 0)} ms")
    print(f"  Worker execution: {ts.get('worker_end', 0) - start} ms")
    print(f"  S3 output write: {ts.get('write_labels_end', 0) - ts.get('write_labels_start', 0)} ms")
    
    print("\n  Iteraciones (compute → reduce → broadcast):")
    iter_times = []
    for i in range(10):
        iter_start = ts.get(f'iter_{i}_start')
        compute = ts.get(f'iter_{i}_compute')
        reduce = ts.get(f'iter_{i}_reduce_labels')
        broadcast = ts.get(f'iter_{i}_broadcast_labels')
        
        if all([iter_start, compute, reduce, broadcast]):
            c_time = compute - iter_start
            r_time = reduce - compute
            b_time = broadcast - reduce
            total = broadcast - iter_start
            print(f"    Iter {i}: compute={c_time:3d}ms, reduce={r_time:3d}ms, broadcast={b_time:3d}ms → total={total:3d}ms")
            iter_times.append((c_time, r_time, b_time, total))
    
    if iter_times:
        avg_compute = sum(t[0] for t in iter_times) / len(iter_times)
        avg_reduce = sum(t[1] for t in iter_times) / len(iter_times)
        avg_broadcast = sum(t[2] for t in iter_times) / len(iter_times)
        avg_total = sum(t[3] for t in iter_times) / len(iter_times)
        print(f"\n  PROMEDIO: compute={avg_compute:.1f}ms, reduce={avg_reduce:.1f}ms, broadcast={avg_broadcast:.1f}ms → total={avg_total:.1f}ms")
        return {
            'worker_time': ts.get('worker_end', 0) - start,
            's3_write': ts.get('write_labels_end', 0) - ts.get('write_labels_start', 0),
            'avg_compute': avg_compute,
            'avg_reduce': avg_reduce,
            'avg_broadcast': avg_broadcast,
            'avg_iter': avg_total
        }
    
    return None

# Analizar ambos archivos
print("="*70)
print("COMPARACIÓN DETALLADA: 9.6M vs 10M")
print("="*70)

ts_96m = extract_worker_data('comparison_9.6M.log')
stats_96m = analyze_iterations(ts_96m, "9.6M")

ts_10m = extract_worker_data('comparison_10M.log')
stats_10m = analyze_iterations(ts_10m, "10M")

if stats_96m and stats_10m:
    print("\n" + "="*70)
    print("DIFERENCIAS CLAVE (10M - 9.6M)")
    print("="*70)
    print(f"Worker execution:  {stats_10m['worker_time']:5d}ms - {stats_96m['worker_time']:5d}ms = {stats_10m['worker_time'] - stats_96m['worker_time']:+6d}ms")
    print(f"S3 write time:     {stats_10m['s3_write']:5d}ms - {stats_96m['s3_write']:5d}ms = {stats_10m['s3_write'] - stats_96m['s3_write']:+6d}ms")
    print(f"Avg compute/iter:  {stats_10m['avg_compute']:5.1f}ms - {stats_96m['avg_compute']:5.1f}ms = {stats_10m['avg_compute'] - stats_96m['avg_compute']:+6.1f}ms")
    print(f"Avg reduce/iter:   {stats_10m['avg_reduce']:5.1f}ms - {stats_96m['avg_reduce']:5.1f}ms = {stats_10m['avg_reduce'] - stats_96m['avg_reduce']:+6.1f}ms")
    print(f"Avg broadcast/iter:{stats_10m['avg_broadcast']:5.1f}ms - {stats_96m['avg_broadcast']:5.1f}ms = {stats_10m['avg_broadcast'] - stats_96m['avg_broadcast']:+6.1f}ms")
    print(f"Avg total/iter:    {stats_10m['avg_iter']:5.1f}ms - {stats_96m['avg_iter']:5.1f}ms = {stats_10m['avg_iter'] - stats_96m['avg_iter']:+6.1f}ms")
    
    print("\n" + "="*70)
    print("ANÁLISIS")
    print("="*70)
    
    # Calcular overhead de comunicación
    comm_overhead_96m = stats_96m['avg_reduce'] + stats_96m['avg_broadcast']
    comm_overhead_10m = stats_10m['avg_reduce'] + stats_10m['avg_broadcast']
    
    print(f"Overhead comunicación por iteración:")
    print(f"  9.6M: {comm_overhead_96m:.1f}ms (reduce + broadcast)")
    print(f"  10M:  {comm_overhead_10m:.1f}ms (reduce + broadcast)")
    print(f"  Diferencia: {comm_overhead_10m - comm_overhead_96m:+.1f}ms")
    
    print(f"\nTiempo total en iteraciones (10 × avg):")
    print(f"  9.6M: {stats_96m['avg_iter'] * 10:.0f}ms")
    print(f"  10M:  {stats_10m['avg_iter'] * 10:.0f}ms")
    print(f"  Ahorro: {(stats_96m['avg_iter'] - stats_10m['avg_iter']) * 10:.0f}ms")
