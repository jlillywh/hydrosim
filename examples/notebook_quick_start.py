"""
# HydroSim Notebook Quick Start

This notebook-friendly example demonstrates the complete HydroSim workflow
with clear explanations and visualizations optimized for Jupyter environments.

## Overview

This example shows how to:
1. Set up a simple water network
2. Run a simulation
3. Analyze and visualize results
4. Export data for further analysis

## Prerequisites

```python
# Install required packages if not already installed
# !pip install hydrosim pandas matplotlib
```
"""

# Cell 1: Imports and Setup
import hydrosim as hs
import pandas as pd
import numpy as np
import os
from datetime import datetime

# Create output directory
os.makedirs('notebook_output', exist_ok=True)

print("✅ HydroSim imported successfully!")
print(f"📦 Version: {hs.__version__ if hasattr(hs, '__version__') else 'unknown'}")

# Cell 2: Create Sample Data
"""
## Step 1: Create Sample Data

Let's generate some realistic sample data for our simulation.
"""

# Generate 30 days of sample climate data
dates = pd.date_range('2024-01-01', periods=30, freq='D')

# Create realistic climate patterns
day_of_year = np.arange(1, 31)
climate_data = pd.DataFrame({
    'date': dates,
    'precip': np.random.exponential(2.5, 30),  # Precipitation (mm/day)
    't_max': 15 + 8 * np.sin(day_of_year * 2 * np.pi / 365) + np.random.normal(0, 2, 30),
    't_min': 5 + 6 * np.sin(day_of_year * 2 * np.pi / 365) + np.random.normal(0, 1.5, 30),
    'solar': 15 + 4 * np.sin(day_of_year * 2 * np.pi / 365) + np.random.normal(0, 1, 30)
})

# Generate sample inflow data (correlated with precipitation)
base_inflow = 800 + 300 * np.sin(day_of_year * 2 * np.pi / 365)
precip_effect = climate_data['precip'] * 50  # 50 m³/day per mm of precip
inflow_data = pd.DataFrame({
    'date': dates,
    'inflow': base_inflow + precip_effect + np.random.normal(0, 100, 30)
})

# Save data files
climate_data.to_csv('notebook_output/climate_data.csv', index=False)
inflow_data.to_csv('notebook_output/inflow_data.csv', index=False)

print("📊 Sample data created:")
print("  • Climate data: 30 days of weather")
print("  • Inflow data: Catchment runoff")
print("\n📈 Climate data preview:")
display(climate_data.head())

# Cell 3: Create Network Configuration
"""
## Step 2: Define Water Network

We'll create a simple but realistic water system with:
- A catchment (source of water)
- A reservoir (storage)
- A city (water demand)
"""

network_config = '''
model_name: "Notebook Tutorial Network"
author: "HydroSim Notebook Tutorial"

climate:
  source_type: timeseries
  filepath: notebook_output/climate_data.csv
  site:
    latitude: 45.0    # Mid-latitude location
    elevation: 1000.0 # 1000m elevation

nodes:
  # Water source from catchment
  mountain_catchment:
    type: source
    strategy: timeseries
    filepath: notebook_output/inflow_data.csv
    column: inflow
  
  # Storage reservoir
  main_reservoir:
    type: storage
    initial_storage: 30000.0  # Start half full
    max_storage: 60000.0      # 60,000 m³ capacity
    min_storage: 5000.0       # 5,000 m³ dead pool
    eav_table:
      elevations: [100.0, 105.0, 110.0, 115.0, 120.0]  # meters
      areas: [1200.0, 1800.0, 2400.0, 3000.0, 3600.0]  # m²
      volumes: [0.0, 7500.0, 22500.0, 42500.0, 67500.0] # m³
  
  # Municipal water demand
  riverside_city:
    type: demand
    demand_type: municipal
    population: 12000.0        # 12,000 people
    per_capita_demand: 0.25    # 250 L/person/day

links:
  # Catchment to reservoir
  inflow_pipe:
    source: mountain_catchment
    target: main_reservoir
    capacity: 8000.0  # m³/day maximum
    cost: 0.0         # No cost for natural inflow
  
  # Reservoir to city
  supply_pipe:
    source: main_reservoir
    target: riverside_city
    capacity: 4000.0  # m³/day maximum
    cost: 1.0         # Small cost for pumping
'''

# Save network configuration
with open('notebook_output/network_config.yaml', 'w') as f:
    f.write(network_config)

print("⚙️ Network configuration created!")
print("\n🏗️ Network components:")
print("  • 1 source node (mountain catchment)")
print("  • 1 storage node (main reservoir)")
print("  • 1 demand node (riverside city)")
print("  • 2 links (inflow + supply pipes)")

# Cell 4: Load and Validate Network
"""
## Step 3: Load and Validate Network

Let's load our configuration and make sure everything is set up correctly.
"""

# Parse the network configuration
parser = hs.YAMLParser('notebook_output/network_config.yaml')
network, climate_source, site_config = parser.parse()

print(f"📋 Network loaded successfully!")
print(f"  • Nodes: {len(network.nodes)}")
print(f"  • Links: {len(network.links)}")

# Show network composition
node_types = {}
for node in network.nodes.values():
    node_type = node.node_type
    node_types[node_type] = node_types.get(node_type, 0) + 1

print(f"\n🔍 Network composition:")
for node_type, count in sorted(node_types.items()):
    print(f"  • {count} {node_type} node(s)")

# Validate network topology
print(f"\n✅ Validating network...")
errors = network.validate()
if errors:
    print("❌ Validation errors found:")
    for error in errors:
        print(f"  • {error}")
else:
    print("✅ Network topology is valid!")

# Cell 5: Run Simulation
"""
## Step 4: Run Simulation

Now let's run our water system simulation for 30 days.
"""

# Set up simulation components
climate_engine = hs.ClimateEngine(climate_source, site_config, datetime(2024, 1, 1))
engine = hs.SimulationEngine(network, climate_engine)
writer = hs.ResultsWriter(output_dir="notebook_output", format="csv")

print("🚀 Starting simulation...")
print("\n📊 Daily Progress:")
print("Day | Storage (m³) | Inflow (m³/d) | Demand (m³/d) | Deficit (m³/d)")
print("-" * 70)

# Run simulation
simulation_results = []
for day in range(30):
    result = engine.step()
    writer.add_timestep(result)
    simulation_results.append(result)
    
    # Extract key values
    storage = result['node_states']['main_reservoir']['storage']
    inflow = result['node_states']['mountain_catchment']['inflow']
    demand = result['node_states']['riverside_city']['request']
    deficit = result['node_states']['riverside_city']['deficit']
    
    # Show progress every 5 days
    if day % 5 == 0 or day == 29:
        print(f"{day+1:3d} | {storage:11,.0f} | {inflow:12,.0f} | {demand:12,.0f} | {deficit:12,.1f}")

print("\n✅ Simulation completed successfully!")

# Cell 6: Analyze Results
"""
## Step 5: Analyze Results

Let's examine what happened during our simulation.
"""

# Export results to files
files = writer.write_all(prefix="notebook_tutorial")
print("📁 Results exported to:")
for file_type, filepath in files.items():
    print(f"  • {file_type}: {filepath}")

# Calculate summary statistics
results = writer.get_results()
print(f"\n📈 Simulation Summary (30 days)")
print("=" * 50)

# Storage analysis
initial_storage = results[0]['node_states']['main_reservoir']['storage']
final_storage = results[-1]['node_states']['main_reservoir']['storage']
max_storage = max(r['node_states']['main_reservoir']['storage'] for r in results)
min_storage = min(r['node_states']['main_reservoir']['storage'] for r in results)

print(f"💧 Reservoir Storage:")
print(f"  • Initial: {initial_storage:,.0f} m³")
print(f"  • Final:   {final_storage:,.0f} m³")
print(f"  • Maximum: {max_storage:,.0f} m³")
print(f"  • Minimum: {min_storage:,.0f} m³")
print(f"  • Net change: {final_storage - initial_storage:+,.0f} m³")

# Water supply analysis
total_demand = sum(r['node_states']['riverside_city']['request'] for r in results)
total_delivered = sum(r['node_states']['riverside_city']['delivered'] for r in results)
total_deficit = sum(r['node_states']['riverside_city']['deficit'] for r in results)
reliability = (total_delivered / total_demand * 100) if total_demand > 0 else 0

print(f"\n🏙️ Water Supply Performance:")
print(f"  • Total demand: {total_demand:,.0f} m³")
print(f"  • Total delivered: {total_delivered:,.0f} m³")
print(f"  • Total deficit: {total_deficit:,.0f} m³")
print(f"  • Supply reliability: {reliability:.1f}%")

# Inflow analysis
total_inflow = sum(r['node_states']['mountain_catchment']['inflow'] for r in results)
avg_inflow = total_inflow / len(results)

print(f"\n🏔️ Catchment Inflow:")
print(f"  • Total inflow: {total_inflow:,.0f} m³")
print(f"  • Average daily: {avg_inflow:,.0f} m³/day")

# Cell 7: Create Visualizations
"""
## Step 6: Visualize Results

Let's create some plots to better understand our simulation results.
"""

try:
    import matplotlib.pyplot as plt
    
    # Extract time series data
    days = list(range(1, 31))
    storage_values = [r['node_states']['main_reservoir']['storage'] for r in results]
    inflow_values = [r['node_states']['mountain_catchment']['inflow'] for r in results]
    demand_values = [r['node_states']['riverside_city']['request'] for r in results]
    delivered_values = [r['node_states']['riverside_city']['delivered'] for r in results]
    deficit_values = [r['node_states']['riverside_city']['deficit'] for r in results]
    
    # Create comprehensive visualization
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle('HydroSim Notebook Tutorial Results', fontsize=16, fontweight='bold')
    
    # Storage plot
    axes[0,0].plot(days, storage_values, 'b-', linewidth=2.5, label='Storage Volume')
    axes[0,0].axhline(y=60000, color='r', linestyle='--', alpha=0.7, label='Max Capacity')
    axes[0,0].axhline(y=5000, color='orange', linestyle='--', alpha=0.7, label='Dead Pool')
    axes[0,0].set_title('Reservoir Storage', fontsize=14, fontweight='bold')
    axes[0,0].set_xlabel('Day')
    axes[0,0].set_ylabel('Storage (m³)')
    axes[0,0].grid(True, alpha=0.3)
    axes[0,0].legend()
    axes[0,0].set_ylim(0, 70000)
    
    # Inflow plot
    axes[0,1].plot(days, inflow_values, 'g-', linewidth=2.5, label='Daily Inflow')
    axes[0,1].set_title('Catchment Inflow', fontsize=14, fontweight='bold')
    axes[0,1].set_xlabel('Day')
    axes[0,1].set_ylabel('Inflow (m³/day)')
    axes[0,1].grid(True, alpha=0.3)
    axes[0,1].legend()
    
    # Water supply plot
    axes[1,0].plot(days, demand_values, 'r-', linewidth=2.5, label='Water Demand')
    axes[1,0].plot(days, delivered_values, 'orange', linewidth=2.5, label='Water Delivered')
    axes[1,0].set_title('Water Supply vs Demand', fontsize=14, fontweight='bold')
    axes[1,0].set_xlabel('Day')
    axes[1,0].set_ylabel('Flow (m³/day)')
    axes[1,0].grid(True, alpha=0.3)
    axes[1,0].legend()
    
    # Deficit plot
    axes[1,1].plot(days, deficit_values, 'red', linewidth=2.5, label='Water Deficit')
    axes[1,1].set_title('Water Supply Deficit', fontsize=14, fontweight='bold')
    axes[1,1].set_xlabel('Day')
    axes[1,1].set_ylabel('Deficit (m³/day)')
    axes[1,1].grid(True, alpha=0.3)
    axes[1,1].legend()
    
    plt.tight_layout()
    plt.savefig('notebook_output/simulation_results.png', dpi=150, bbox_inches='tight')
    plt.show()
    
    print("📊 Visualization created and saved!")
    
except ImportError:
    print("📊 Matplotlib not available - install with: pip install matplotlib")

# Cell 8: Summary and Next Steps
"""
## 🎉 Congratulations!

You've successfully completed a HydroSim simulation! Here's what you accomplished:

### ✅ What You Did
- Created realistic sample data (climate and inflow)
- Configured a water network with source, storage, and demand
- Ran a 30-day simulation
- Analyzed water supply performance
- Created visualizations of the results

### 📊 Key Results
- The reservoir successfully managed water supply
- Supply reliability shows how well demands were met
- Storage levels show the reservoir's operational patterns
- Inflow patterns drive the system dynamics

### 🚀 Next Steps
1. **Modify the network**: Try changing reservoir capacity, demand levels, or adding more nodes
2. **Experiment with data**: Use real climate/inflow data for your region
3. **Explore advanced features**: Try weather generation, optimization settings, or multiple reservoirs
4. **Learn more**: Use `hs.examples()` and `hs.docs()` for additional resources

### 📁 Files Created
All results are saved in the `notebook_output/` directory:
- CSV files with detailed simulation results
- Network configuration file
- Visualization plots
- Sample data files

Happy modeling! 🌊
"""

print("🎯 Tutorial completed successfully!")
print("\n📚 Continue learning:")
print("  • Try: hs.examples() - for more advanced examples")
print("  • Try: hs.docs() - for comprehensive documentation")
print("  • Try: hs.help() - for quick reference")