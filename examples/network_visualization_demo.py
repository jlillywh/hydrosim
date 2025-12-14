"""
# Network Visualization Demo

This example demonstrates how to visualize a HydroSim network using Plotly.

## Features Demonstrated
- Interactive network topology visualization
- Nodes colored by type (storage=blue, demand=red, junction=purple, source=green)
- Links with arrows showing flow direction
- Interactive hover tooltips with node/link information
- Model name and author in the title

## Notebook Usage
In Jupyter notebooks, use `fig.show()` to display the interactive plot inline.
For terminal usage, the plot will open in your default browser.

## Requirements
- plotly (automatically installed with hydrosim)
- A valid network configuration file
"""

from hydrosim import YAMLParser, visualize_network, save_network_visualization

# Step 1: Parse the network configuration
print("📋 Loading network configuration...")
parser = YAMLParser('storage_drawdown_example.yaml')
network, climate_source, site_config = parser.parse()

print(f"✅ Network loaded successfully!")
print(f"  • Model: {network.model_name}")
print(f"  • Author: {network.author}")
print(f"  • Nodes: {len(network.nodes)}")
print(f"  • Links: {len(network.links)}")

# Step 2: Create interactive visualization
print("\n🎨 Creating interactive visualization...")

# Create the visualization
# Sized for optimal display (600px wide, 1200px tall)
fig = visualize_network(
    network,
    width=600,
    height=1200,
    layout='hierarchical'  # Options: 'circular', 'hierarchical'
)

print("✅ Visualization created!")

# Step 3: Display the visualization
print("\n📊 Displaying visualization...")

# For Jupyter notebooks: display inline
# For terminal: opens in browser
fig.show()

# Step 4: Save to HTML file
print("\n💾 Saving visualization to file...")
import os
os.makedirs('output', exist_ok=True)

save_network_visualization(
    network,
    filepath='output/network_visualization.html',
    width=600,
    height=1200
)

print("✅ Visualization saved to output/network_visualization.html")

# Step 5: Display network summary
print(f"\n📈 Network Summary:")
print(f"  • Model: {network.model_name}")
print(f"  • Author: {network.author}")
print(f"  • Nodes: {len(network.nodes)}")
print(f"  • Links: {len(network.links)}")

# Show node types
node_types = {}
for node in network.nodes.values():
    node_type = node.node_type
    node_types[node_type] = node_types.get(node_type, 0) + 1

print(f"\n🔍 Node composition:")
for node_type, count in sorted(node_types.items()):
    print(f"  • {count} {node_type} node(s)")

print(f"\n💡 Tip: In Jupyter notebooks, the plot displays inline.")
print(f"    In terminal, it opens in your default browser.")
