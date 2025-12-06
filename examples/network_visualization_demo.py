"""
Network Visualization Demo

This example demonstrates how to visualize a HydroSim network using Plotly.
The visualization shows:
- Nodes colored by type (storage=blue, demand=red, junction=purple, source=green)
- Links with arrows showing flow direction
- Interactive hover tooltips with node/link information
- Model name and author in the title
"""

from hydrosim import YAMLParser, visualize_network, save_network_visualization

# Parse the network configuration
parser = YAMLParser('storage_drawdown_example.yaml')
network, climate_source, site_config = parser.parse()

# Create interactive visualization
# Sized for 1/3 screen width (600px) and full height (1200px)
fig = visualize_network(
    network,
    width=600,
    height=1200,
    layout='hierarchical'  # Options: 'circular', 'hierarchical'
)

# Display in browser (for Jupyter, use fig.show())
fig.show()

# Save to HTML file
save_network_visualization(
    network,
    filepath='../output/network_visualization.html',
    width=600,
    height=1200
)

print("Visualization saved to output/network_visualization.html")
print(f"Model: {network.model_name}")
print(f"Author: {network.author}")
print(f"Nodes: {len(network.nodes)}")
print(f"Links: {len(network.links)}")
