"""
Run Your Custom HydroSim Network

This script runs your custom network configuration and shows you
how to analyze the results programmatically.
"""

from datetime import datetime
import webbrowser
import os
from hydrosim.config import YAMLParser
from hydrosim import (
    SimulationEngine, LinearProgrammingSolver, ResultsWriter, ClimateEngine,
    visualize_network, visualize_results
)


def main():
    print("🚀 Running Your Custom HydroSim Network!")
    print("=" * 50)
    
    # Load your custom configuration
    print("\n[1] Loading your custom network...")
    parser = YAMLParser('examples/my_custom_network.yaml')
    network, climate_source, site_config = parser.parse()
    print(f"   ✓ Network loaded: {len(network.nodes)} nodes, {len(network.links)} links")
    
    # Show network composition
    print("\n[2] Network composition:")
    for node_id, node in network.nodes.items():
        print(f"   - {node_id}: {node.node_type}")
    
    # Validate network
    print("\n[3] Validating network...")
    errors = network.validate()
    if errors:
        print("   ❌ Validation errors:")
        for error in errors:
            print(f"      - {error}")
        return
    print("   ✅ Network is valid!")
    
    # Set up simulation
    print("\n[4] Setting up simulation...")
    climate_engine = ClimateEngine(climate_source, site_config, datetime(2024, 1, 1))
    solver = LinearProgrammingSolver()
    engine = SimulationEngine(network, climate_engine, solver)
    writer = ResultsWriter(output_dir="output", format="csv")
    
    # Run simulation
    print("\n[5] Running 30-day simulation...")
    for day in range(30):
        result = engine.step()
        writer.add_timestep(result)
        
        if (day + 1) % 10 == 0:
            storage = result['node_states']['reservoir']['storage']
            city_deficit = result['node_states']['city']['deficit']
            farm_deficit = result['node_states']['farm']['deficit']
            print(f"   Day {day + 1}: Storage = {storage:8.1f} m³")
            print(f"            City deficit = {city_deficit:6.2f} m³")
            print(f"            Farm deficit = {farm_deficit:6.2f} m³")
    
    # Generate visualizations
    print("\n[6] Creating visualizations...")
    
    # Network map
    fig_network = visualize_network(network)
    fig_network.write_html('output/my_custom_topology.html')
    print("   ✓ Network topology: output/my_custom_topology.html")
    
    # Results plots
    viz_config = network.viz_config or {}
    visualize_results(
        results_writer=writer,
        network=network,
        viz_config=viz_config,
        output_file='output/my_custom_results.html'
    )
    print("   ✓ Results plots: output/my_custom_results.html")
    
    # Save data files
    print("\n[7] Saving data files...")
    files = writer.write_all(prefix="my_custom")
    for file_type, filepath in files.items():
        print(f"   ✓ {file_type}: {filepath}")
    
    # Analyze results
    print("\n[8] Results Analysis")
    print("-" * 50)
    results = writer.get_results()
    
    # Storage performance
    initial_storage = results[0]['node_states']['reservoir']['storage']
    final_storage = results[-1]['node_states']['reservoir']['storage']
    print(f"Storage Performance:")
    print(f"  Initial: {initial_storage:,.1f} m³")
    print(f"  Final:   {final_storage:,.1f} m³")
    print(f"  Change:  {final_storage - initial_storage:+,.1f} m³")
    
    # Demand performance
    print(f"\nDemand Performance:")
    for demand_name in ['city', 'farm']:
        total_request = sum(r['node_states'][demand_name]['request'] for r in results)
        total_delivered = sum(r['node_states'][demand_name]['delivered'] for r in results)
        total_deficit = sum(r['node_states'][demand_name]['deficit'] for r in results)
        reliability = (total_delivered / total_request * 100) if total_request > 0 else 0
        
        print(f"  {demand_name.title()}:")
        print(f"    Requested:  {total_request:,.1f} m³")
        print(f"    Delivered:  {total_delivered:,.1f} m³")
        print(f"    Deficit:    {total_deficit:,.1f} m³")
        print(f"    Reliability: {reliability:.1f}%")
    
    # Open visualizations
    print(f"\n[9] Opening visualizations in browser...")
    webbrowser.open(f'file://{os.path.abspath("output/my_custom_topology.html")}')
    webbrowser.open(f'file://{os.path.abspath("output/my_custom_results.html")}')
    
    print("\n🎉 Your custom network simulation is complete!")
    print("=" * 50)
    print("Next: Try modifying the YAML file to:")
    print("- Change reservoir capacity")
    print("- Add more demands")
    print("- Adjust population or farm area")
    print("- Add controls to links")
    print("=" * 50)


if __name__ == "__main__":
    main()