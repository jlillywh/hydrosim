"""
Results Visualization Demo

This example demonstrates automated time series plotting based on YAML configuration.
The visualization system automatically generates plots for:
- Climate conditions (precipitation, temperature)
- Source/catchment runoff
- Reservoir operations (storage, inflows, outflows, evaporation, spills)
- Demand supply vs request
"""

from hydrosim import (
    YAMLParser, SimulationEngine, ResultsWriter, ClimateEngine,
    LinearProgrammingSolver, visualize_results, visualize_network
)
from datetime import datetime, timedelta

# Parse configuration
parser = YAMLParser('storage_drawdown_example.yaml')
network, climate_source, site_config = parser.parse()

# Setup simulation components
start_date = datetime(2024, 1, 1)
end_date = datetime(2024, 1, 30)
results_writer = ResultsWriter(output_dir='../output', format='csv')

climate_engine = ClimateEngine(climate_source, site_config, start_date)
solver = LinearProgrammingSolver()

engine = SimulationEngine(
    network=network,
    climate_engine=climate_engine,
    solver=solver
)

# Run simulation
print("Running simulation...")
current_date = start_date
while current_date <= end_date:
    result = engine.step()
    result['date'] = current_date
    results_writer.add_timestep(result)
    current_date += timedelta(days=1)
print(f"Simulation complete: {len(results_writer.get_results())} timesteps")

# Generate network visualization (uses YAML config)
print("\nGenerating network visualization...")
fig_network = visualize_network(network)
network_config = (network.viz_config or {}).get('network_map', {})
network_file = network_config.get('output_file', 'network_topology.html')
fig_network.write_html(f'../output/{network_file}')
print(f"Network topology saved to output/{network_file}")

# Generate results time series plots
print("\nGenerating results visualizations...")
viz_config = network.viz_config or {}
output_file = viz_config.get('layout', {}).get('output_file', 'simulation_results.html')

fig_results = visualize_results(
    results_writer=results_writer,
    network=network,
    viz_config=viz_config,
    output_file=f'../output/{output_file}'
)

print(f"Results visualization saved to output/{output_file}")
print("\nVisualization Summary:")
print(f"  Model: {network.model_name}")
print(f"  Author: {network.author}")
print(f"  Nodes: {len(network.nodes)}")
print(f"  Links: {len(network.links)}")
print(f"  Timesteps: {len(results_writer.get_results())}")

# Write CSV results
print("\nWriting CSV results...")
files = results_writer.write_all(prefix='simulation')
for output_type, filepath in files.items():
    print(f"  {output_type}: {filepath}")
