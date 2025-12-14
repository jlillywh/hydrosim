"""
HydroSim Starter Notebook - Complete Self-Contained Example

This file contains everything needed to run a HydroSim simulation.
No external files required - everything is built-in!

Perfect for Jupyter notebooks - just copy each section into separate cells.
"""

# Cell 1: Setup and Imports
import hydrosim as hs
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

print("🎉 HydroSim Starter Notebook")
print(f"📦 HydroSim Version: {hs.__version__}")
print("✅ All imports successful!")

# Cell 2: Create Sample Data (Built-in - No External Files!)
print("\n📊 Creating sample data...")

# Create 30 days of sample climate data
dates = pd.date_range('2024-01-01', periods=30, freq='D')
np.random.seed(42)  # For reproducible results

climate_data = pd.DataFrame({
    'precip': np.random.exponential(2.5, 30),  # Precipitation (mm/day)
    't_max': 20 + 10 * np.sin(np.arange(30) * 2 * np.pi / 365) + np.random.normal(0, 3, 30),  # Max temp
    't_min': 10 + 8 * np.sin(np.arange(30) * 2 * np.pi / 365) + np.random.normal(0, 2, 30),   # Min temp
    'solar': 15 + 5 * np.sin(np.arange(30) * 2 * np.pi / 365) + np.random.normal(0, 1, 30),  # Solar radiation
}, index=dates)  # Use dates as index, not as a column

# Create inflow data (river flow into reservoir)
inflow_data = pd.DataFrame({
    'inflow': 1000 + 500 * np.sin(np.arange(30) * 2 * np.pi / 30) + np.random.normal(0, 200, 30)  # m³/day
}, index=dates)  # Use dates as index, not as a column

# Make sure inflows are positive
inflow_data['inflow'] = np.maximum(inflow_data['inflow'], 100)

print(f"✅ Created {len(climate_data)} days of climate data")
print(f"✅ Created {len(inflow_data)} days of inflow data")
print(f"   Average inflow: {inflow_data['inflow'].mean():.1f} m³/day")

# Cell 3: Build the Water Network (Programmatically - No YAML!)
print("\n🏗️ Building water network...")

# Create the network
network = hs.NetworkGraph()

# Create elevation-area-volume table for reservoir
eav = hs.ElevationAreaVolume(
    elevations=[100.0, 110.0, 120.0, 130.0],  # meters
    areas=[1000.0, 2000.0, 3000.0, 4000.0],   # m²
    volumes=[0.0, 10000.0, 30000.0, 60000.0]  # m³
)

# Create nodes
print("   Creating nodes...")

# 1. Source node (river inflow)
river_strategy = hs.TimeSeriesStrategy(inflow_data, 'inflow')
river = hs.SourceNode('river', river_strategy)

# 2. Storage node (reservoir)
reservoir = hs.StorageNode(
    'reservoir',
    initial_storage=40000.0,  # Start half full
    eav_table=eav,
    max_storage=60000.0,
    min_storage=0.0
)

# 3. Demand node (city)
city_demand = hs.MunicipalDemand(population=5000, per_capita_demand=0.3)  # m³/person/day
city = hs.DemandNode('city', city_demand)

# Add nodes to network
network.add_node(river)
network.add_node(reservoir)
network.add_node(city)

print(f"   ✅ Created {len(network.nodes)} nodes")

# Create links
print("   Creating links...")

# 1. River to reservoir
river_to_reservoir = hs.Link('river_to_reservoir', river, reservoir, 
                            physical_capacity=5000.0, cost=0.0)

# 2. Reservoir to city
reservoir_to_city = hs.Link('reservoir_to_city', reservoir, city,
                           physical_capacity=2000.0, cost=hs.COST_DEMAND)

# Add links to network
network.add_link(river_to_reservoir)
network.add_link(reservoir_to_city)

print(f"   ✅ Created {len(network.links)} links")

# Validate network
errors = network.validate()
if errors:
    print("   ❌ Network validation errors:")
    for error in errors:
        print(f"      - {error}")
else:
    print("   ✅ Network validation passed!")

# Cell 4: Set Up Climate and Simulation
print("\n🌤️ Setting up climate and simulation...")

# Create climate source
climate_source = hs.TimeSeriesClimateSource(climate_data)

# Create site configuration
site_config = hs.SiteConfig(latitude=45.0, elevation=1000.0)

# Create climate engine
climate_engine = hs.ClimateEngine(climate_source, site_config, datetime(2024, 1, 1))

# Create simulation engine
engine = hs.SimulationEngine(network, climate_engine)

# Create results writer
os.makedirs('output', exist_ok=True)
writer = hs.ResultsWriter(output_dir="output", format="csv")

print("✅ Simulation setup complete!")

# Cell 5: Run the Simulation
print("\n🚀 Running simulation...")

num_days = 30
print(f"   Simulating {num_days} days...")

# Run simulation day by day
for day in range(num_days):
    result = engine.step()
    writer.add_timestep(result)
    
    # Print progress every 5 days
    if (day + 1) % 5 == 0 or day == 0:
        storage = result['node_states']['reservoir']['storage']
        delivered = result['node_states']['city']['delivered']
        deficit = result['node_states']['city']['deficit']
        print(f"      Day {day + 1:2d}: Storage = {storage:8.1f} m³, "
              f"Delivered = {delivered:6.1f} m³, Deficit = {deficit:5.1f} m³")

print(f"✅ Simulation complete!")

# Cell 6: Analyze Results
print("\n📊 Analyzing results...")

# Get all results
results = writer.get_results()

# Calculate summary statistics
initial_storage = results[0]['node_states']['reservoir']['storage']
final_storage = results[-1]['node_states']['reservoir']['storage']
total_inflow = sum(r['node_states']['river']['inflow'] for r in results)
total_demand = sum(r['node_states']['city']['request'] for r in results)
total_delivered = sum(r['node_states']['city']['delivered'] for r in results)
total_deficit = sum(r['node_states']['city']['deficit'] for r in results)

print("📈 Simulation Summary:")
print(f"   Reservoir:")
print(f"      Initial storage: {initial_storage:,.0f} m³")
print(f"      Final storage:   {final_storage:,.0f} m³")
print(f"      Change:          {final_storage - initial_storage:+,.0f} m³")
print(f"   Water Supply:")
print(f"      Total inflow:    {total_inflow:,.0f} m³")
print(f"      Total demand:    {total_demand:,.0f} m³")
print(f"      Total delivered: {total_delivered:,.0f} m³")
print(f"      Total deficit:   {total_deficit:,.0f} m³")

# Calculate reliability
reliability = (total_delivered / total_demand * 100) if total_demand > 0 else 0
print(f"      Reliability:     {reliability:.1f}%")

# Cell 7: Visualize Network Diagram
print("\n�️ rCreating network diagram...")

# Create interactive network visualization
network_fig = hs.visualize_network(network)

# Save the network diagram
network_fig.write_html('output/network_diagram.html')
print("✅ Network diagram saved: output/network_diagram.html")

# Display the network (works in Jupyter notebooks)
try:
    network_fig.show()
    print("✅ Network diagram displayed!")
except:
    print("💡 Network diagram saved to file (open output/network_diagram.html in browser)")

print(f"\n📋 Network Summary:")
print(f"   Nodes: {len(network.nodes)}")
for node_id, node in network.nodes.items():
    print(f"      - {node_id}: {node.node_type}")
print(f"   Links: {len(network.links)}")
for link_id, link in network.links.items():
    print(f"      - {link_id}: {link.source.node_id} → {link.target.node_id}")

# Cell 8: Create Time Series Visualizations
print("\n📈 Creating time series visualizations...")

# Extract time series data for plotting
dates = [datetime(2024, 1, 1) + timedelta(days=i) for i in range(len(results))]
storage_values = [r['node_states']['reservoir']['storage'] for r in results]
inflow_values = [r['node_states']['river']['inflow'] for r in results]
demand_values = [r['node_states']['city']['request'] for r in results]
delivered_values = [r['node_states']['city']['delivered'] for r in results]
deficit_values = [r['node_states']['city']['deficit'] for r in results]

# Create plots
fig, axes = plt.subplots(2, 2, figsize=(15, 10))
fig.suptitle('HydroSim Simulation Results', fontsize=16, fontweight='bold')

# Storage plot
axes[0, 0].plot(dates, storage_values, 'b-', linewidth=2, label='Storage')
axes[0, 0].axhline(y=60000, color='r', linestyle='--', alpha=0.7, label='Max Capacity')
axes[0, 0].set_title('Reservoir Storage')
axes[0, 0].set_ylabel('Storage (m³)')
axes[0, 0].legend()
axes[0, 0].grid(True, alpha=0.3)

# Inflow plot
axes[0, 1].plot(dates, inflow_values, 'g-', linewidth=2, label='Inflow')
axes[0, 1].set_title('River Inflow')
axes[0, 1].set_ylabel('Flow (m³/day)')
axes[0, 1].legend()
axes[0, 1].grid(True, alpha=0.3)

# Demand vs delivery plot
axes[1, 0].plot(dates, demand_values, 'r-', linewidth=2, label='Demand')
axes[1, 0].plot(dates, delivered_values, 'b-', linewidth=2, label='Delivered')
axes[1, 0].fill_between(dates, delivered_values, demand_values, 
                       where=np.array(demand_values) > np.array(delivered_values),
                       alpha=0.3, color='red', label='Deficit')
axes[1, 0].set_title('Water Demand vs Delivery')
axes[1, 0].set_ylabel('Flow (m³/day)')
axes[1, 0].legend()
axes[1, 0].grid(True, alpha=0.3)

# Deficit plot
axes[1, 1].plot(dates, deficit_values, 'r-', linewidth=2, label='Deficit')
axes[1, 1].fill_between(dates, 0, deficit_values, alpha=0.3, color='red')
axes[1, 1].set_title('Water Supply Deficit')
axes[1, 1].set_ylabel('Deficit (m³/day)')
axes[1, 1].legend()
axes[1, 1].grid(True, alpha=0.3)

# Format x-axes
for ax in axes.flat:
    ax.tick_params(axis='x', rotation=45)

plt.tight_layout()
plt.savefig('output/simulation_results.png', dpi=150, bbox_inches='tight')
plt.show()

print("✅ Visualization complete!")

# Cell 9: Export Results
print("\n💾 Exporting results...")

# Write results to CSV files
files = writer.write_all(prefix="starter_simulation")
print("📁 Files created:")
for file_type, filepath in files.items():
    print(f"   {file_type}: {filepath}")

# Also save the input data for reference
climate_data.to_csv('output/input_climate_data.csv', index=True)  # Save with date index
inflow_data.to_csv('output/input_inflow_data.csv', index=True)    # Save with date index
print("   input_data: output/input_climate_data.csv")
print("   input_data: output/input_inflow_data.csv")
print("   network_diagram: output/network_diagram.html")

# Show sample of the data
print(f"\n📋 Sample climate data:")
print(climate_data.head(3).round(1))
print(f"\n📋 Sample inflow data:")
print(inflow_data.head(3).round(1))

print("\n🎉 Starter simulation complete!")
print("\n📋 Next Steps:")
print("   1. Open 'output/network_diagram.html' to see the interactive network diagram")
print("   2. Check the 'output' folder for all results and plots")
print("   3. Try changing the reservoir size or city population above")
print("   4. Run the simulation again to see different results")
print("   5. Explore the CSV files to understand the data structure")
print("\n💡 Tips:")
print("   - Increase population to see more water stress")
print("   - Change initial_storage to see different scenarios")
print("   - Modify the inflow pattern to test drought conditions")
print("   - The network diagram shows how water flows through the system")