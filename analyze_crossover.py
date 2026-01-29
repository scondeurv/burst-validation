#!/usr/bin/env python3
"""
Crossover Analysis - Pinpoint where Burst becomes faster than Standalone
"""
import pandas as pd
import numpy as np
from scipy import interpolate
import matplotlib.pyplot as plt

# Read data
df = pd.read_csv('incremental_results.csv')

# Filter to crossover region (9M-11M)
crossover_region = df[(df['nodes'] >= 9000000) & (df['nodes'] <= 11000000)].copy()
crossover_region['nodes_M'] = crossover_region['nodes'] / 1_000_000

# Sort by nodes
crossover_region = crossover_region.sort_values('nodes')

print("=" * 70)
print("CROSSOVER REGION ANALYSIS (9M - 11M nodes)")
print("=" * 70)
print()

# Display data
print(crossover_region[['nodes_M', 'standalone_ms', 'burst_ms', 'speedup']].to_string(index=False))
print()

# Find crossover point (speedup = 1.0)
# Use interpolation for sub-sampling precision
speedup_values = crossover_region['speedup'].values
nodes_values = crossover_region['nodes_M'].values

# Interpolate to find where speedup crosses 1.0
if speedup_values.min() < 1.0 < speedup_values.max():
    # Linear interpolation
    f = interpolate.interp1d(nodes_values, speedup_values, kind='linear')
    
    # Search for crossover point
    test_range = np.linspace(nodes_values.min(), nodes_values.max(), 1000)
    speedups_interp = f(test_range)
    
    # Find where speedup crosses 1.0
    crossover_idx = np.argmin(np.abs(speedups_interp - 1.0))
    crossover_point = test_range[crossover_idx]
    
    print(f"🎯 ESTIMATED CROSSOVER POINT: {crossover_point:.2f}M nodes")
    print(f"   (Speedup = {speedups_interp[crossover_idx]:.4f})")
    print()
    
    # Find exact measurements surrounding the crossover
    below_1x = crossover_region[crossover_region['speedup'] < 1.0]
    above_1x = crossover_region[crossover_region['speedup'] > 1.0]
    
    if not below_1x.empty and not above_1x.empty:
        last_below = below_1x.iloc[-1]
        first_above = above_1x.iloc[0]
        
        print("📊 Bracketing Measurements:")
        print(f"   Last point where Standalone wins: {last_below['nodes_M']:.1f}M (speedup {last_below['speedup']:.3f}x)")
        print(f"   First point where Burst wins:     {first_above['nodes_M']:.1f}M (speedup {first_above['speedup']:.3f}x)")
        print()
        print(f"   Crossover occurs between {last_below['nodes_M']:.1f}M and {first_above['nodes_M']:.1f}M nodes")
        print()

# Calculate statistics
print("=" * 70)
print("PERFORMANCE STATISTICS")
print("=" * 70)
print()
print(f"Minimum Speedup:  {speedup_values.min():.3f}x at {nodes_values[speedup_values.argmin()]:.1f}M nodes")
print(f"Maximum Speedup:  {speedup_values.max():.3f}x at {nodes_values[speedup_values.argmax()]:.1f}M nodes")
print(f"Mean Speedup:     {speedup_values.mean():.3f}x")
print(f"Std Dev:          {speedup_values.std():.3f}")
print()

# Generate visualization
plt.figure(figsize=(12, 8))

# Plot speedup curve
plt.subplot(2, 1, 1)
plt.plot(nodes_values, speedup_values, 'o-', linewidth=2, markersize=8, label='Measured Speedup')
plt.axhline(y=1.0, color='r', linestyle='--', linewidth=2, label='Speedup = 1.0 (Crossover)')
plt.xlabel('Graph Size (Million Nodes)', fontsize=12)
plt.ylabel('Speedup (Burst vs Standalone)', fontsize=12)
plt.title('Crossover Point Analysis: Where Burst Becomes Faster', fontsize=14, fontweight='bold')
plt.grid(True, alpha=0.3)
plt.legend(fontsize=10)

# Highlight crossover region
if speedup_values.min() < 1.0 < speedup_values.max():
    plt.axvspan(last_below['nodes_M'], first_above['nodes_M'], alpha=0.2, color='green', 
                label=f'Crossover Region ({last_below["nodes_M"]:.1f}M - {first_above["nodes_M"]:.1f}M)')
    plt.axvline(x=crossover_point, color='orange', linestyle=':', linewidth=2, 
                label=f'Estimated Crossover: {crossover_point:.2f}M')

# Plot execution times
plt.subplot(2, 1, 2)
plt.plot(nodes_values, crossover_region['standalone_ms'] / 1000, 'o-', 
         linewidth=2, markersize=6, label='Standalone (Rust)', color='blue')
plt.plot(nodes_values, crossover_region['burst_ms'] / 1000, 's-', 
         linewidth=2, markersize=6, label='Burst (Distributed)', color='red')
plt.xlabel('Graph Size (Million Nodes)', fontsize=12)
plt.ylabel('Execution Time (seconds)', fontsize=12)
plt.title('Execution Times: Standalone vs Burst', fontsize=14, fontweight='bold')
plt.grid(True, alpha=0.3)
plt.legend(fontsize=10)

# Highlight where burst becomes faster
if speedup_values.min() < 1.0 < speedup_values.max():
    plt.axvspan(last_below['nodes_M'], first_above['nodes_M'], alpha=0.2, color='green')

plt.tight_layout()
plt.savefig('crossover_analysis.png', dpi=300, bbox_inches='tight')
print(f"✅ Visualization saved: crossover_analysis.png")
print()

# Additional insights
print("=" * 70)
print("KEY INSIGHTS")
print("=" * 70)
print()
print("1. Burst overhead dominates for small graphs (<10M nodes)")
print("2. Crossover occurs around 10M nodes due to:")
print("   - Communication overhead amortization")
print("   - Parallel computation benefits")
print("   - Graph processing complexity scaling")
print("3. Beyond crossover, speedup continues to improve with scale")
print()
