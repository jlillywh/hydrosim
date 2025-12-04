"""
HydroSim Quick Start Example

This example demonstrates the complete workflow for setting up and running
a water network simulation using HydroSim:

1. Load configuration from YAML file
2. Set up simulation engine
3. Run simulation
4. Export and analyze results

This is the recommended way to use HydroSim for most applications.
"""

from datetime import datetime
from hydrosim.config import YAMLParser
from hydrosim import SimulationEngine, LinearProgrammingSolver, ResultsWriter, ClimateEngine


def run_simple_example():
    """Run the simple network example."""
    print("=" * 70)
    print("HydroSim Quick Start - Simple Network Example")
    print("=" * 70)
    
    # Step 1: Parse YAML configuration
    print("\n[Step 1] Loading configuration from YAML file...")
    parser = YAMLParser('examples/simple_network.yaml')
    network, climate_source, site_config = parser.parse()
    print(f"   ✓ Loaded network with {len(network.nodes)} nodes and {len(network.links)} links")
    
    # Step 2: Validate network topology
    print("\n[Step 2] Validating network topology...")
    errors = network.validate()
    if errors:
        print("   ✗ Validation errors found:")
        for error in errors:
            print(f"      - {error}")
        return
    print("   ✓ Network topology is valid")
    
    # Step 3: Set up simulation engine
    print("\n[Step 3] Setting up simulation engine...")
    climate_engine = ClimateEngine(climate_source, site_config, datetime(2024, 1, 1))
    solver = LinearProgrammingSolver()
    engine = SimulationEngine(network, climate_engine, solver)
    print("   ✓ Simulation engine initialized")
    
    # Step 4: Create results writer
    print("\n[Step 4] Creating results writer...")
    writer = ResultsWriter(output_dir="output", format="csv")
    print("   ✓ Results writer ready (CSV format)")
    
    # Step 5: Run simulation
    print("\n[Step 5] Running simulation...")
    num_days = 30
    print(f"   Simulating {num_days} days...")
    
    for day in range(num_days):
        result = engine.step()
        writer.add_timestep(result)
        
        # Print progress
        if (day + 1) % 10 == 0 or day == 0:
            storage = result['node_states']['reservoir']['storage']
            deficit = result['node_states']['city']['deficit']
            print(f"      Day {day + 1:2d}: Storage = {storage:8.1f} m³, Deficit = {deficit:6.2f} m³")
    
    print(f"   ✓ Completed {num_days} days of simulation")
    
    # Step 6: Write results to files
    print("\n[Step 6] Writing results to files...")
    files = writer.write_all(prefix="simple_network")
    for file_type, filepath in files.items():
        print(f"   ✓ {file_type}: {filepath}")
    
    # Step 7: Print summary statistics
    print("\n[Step 7] Simulation Summary")
    print("-" * 70)
    results = writer.get_results()
    
    # Storage statistics
    initial_storage = results[0]['node_states']['reservoir']['storage']
    final_storage = results[-1]['node_states']['reservoir']['storage']
    print(f"   Storage:")
    print(f"      Initial: {initial_storage:,.1f} m³")
    print(f"      Final:   {final_storage:,.1f} m³")
    print(f"      Change:  {final_storage - initial_storage:+,.1f} m³")
    
    # Demand statistics
    total_demand = sum(r['node_states']['city']['request'] for r in results)
    total_delivered = sum(r['flows']['reservoir_to_city'] for r in results)
    total_deficit = sum(r['node_states']['city']['deficit'] for r in results)
    reliability = (total_delivered / total_demand * 100) if total_demand > 0 else 0
    
    print(f"\n   Demand:")
    print(f"      Total requested: {total_demand:,.1f} m³")
    print(f"      Total delivered: {total_delivered:,.1f} m³")
    print(f"      Total deficit:   {total_deficit:,.1f} m³")
    print(f"      Reliability:     {reliability:.1f}%")
    
    print("\n" + "=" * 70)
    print("✓ Simulation complete! Results saved to 'output' directory.")
    print("=" * 70)


def run_complex_example():
    """Run the complex network example."""
    print("\n\n")
    print("=" * 70)
    print("HydroSim Quick Start - Complex Network Example")
    print("=" * 70)
    
    # Step 1: Parse YAML configuration
    print("\n[Step 1] Loading configuration from YAML file...")
    parser = YAMLParser('examples/complex_network.yaml')
    network, climate_source, site_config = parser.parse()
    print(f"   ✓ Loaded network with {len(network.nodes)} nodes and {len(network.links)} links")
    
    # List node types
    node_types = {}
    for node in network.nodes.values():
        node_type = node.node_type
        node_types[node_type] = node_types.get(node_type, 0) + 1
    
    print("   Network composition:")
    for node_type, count in sorted(node_types.items()):
        print(f"      - {count} {node_type} node(s)")
    
    # Step 2: Validate network topology
    print("\n[Step 2] Validating network topology...")
    errors = network.validate()
    if errors:
        print("   ✗ Validation errors found:")
        for error in errors:
            print(f"      - {error}")
        return
    print("   ✓ Network topology is valid")
    
    # Step 3: Set up simulation engine
    print("\n[Step 3] Setting up simulation engine...")
    climate_engine = ClimateEngine(climate_source, site_config, datetime(2024, 1, 1))
    solver = LinearProgrammingSolver()
    engine = SimulationEngine(network, climate_engine, solver)
    print("   ✓ Simulation engine initialized")
    
    # Step 4: Create results writer (JSON format for complex networks)
    print("\n[Step 4] Creating results writer...")
    writer = ResultsWriter(output_dir="output", format="json")
    print("   ✓ Results writer ready (JSON format)")
    
    # Step 5: Run simulation
    print("\n[Step 5] Running simulation...")
    num_days = 30
    print(f"   Simulating {num_days} days...")
    
    for day in range(num_days):
        result = engine.step()
        writer.add_timestep(result)
        
        # Print progress every 10 days
        if (day + 1) % 10 == 0 or day == 0:
            upstream_storage = result['node_states']['upstream_reservoir']['storage']
            downstream_storage = result['node_states']['downstream_reservoir']['storage']
            city_deficit = result['node_states']['city']['deficit']
            farm_deficit = result['node_states']['farm']['deficit']
            print(f"      Day {day + 1:2d}: Upstream = {upstream_storage:9.1f} m³, "
                  f"Downstream = {downstream_storage:8.1f} m³")
            print(f"              City deficit = {city_deficit:6.2f} m³, "
                  f"Farm deficit = {farm_deficit:6.2f} m³")
    
    print(f"   ✓ Completed {num_days} days of simulation")
    
    # Step 6: Write results to files
    print("\n[Step 6] Writing results to files...")
    files = writer.write_all(prefix="complex_network")
    for file_type, filepath in files.items():
        print(f"   ✓ {file_type}: {filepath}")
    
    # Step 7: Print summary statistics
    print("\n[Step 7] Simulation Summary")
    print("-" * 70)
    results = writer.get_results()
    
    # Inflow statistics
    total_inflow = sum(r['node_states']['catchment']['inflow'] for r in results)
    print(f"   Catchment inflow:")
    print(f"      Total: {total_inflow:,.1f} m³")
    print(f"      Average: {total_inflow / num_days:,.1f} m³/day")
    
    # Storage statistics
    print(f"\n   Storage volumes:")
    for storage_name in ['upstream_reservoir', 'downstream_reservoir']:
        initial = results[0]['node_states'][storage_name]['storage']
        final = results[-1]['node_states'][storage_name]['storage']
        print(f"      {storage_name}:")
        print(f"         Initial: {initial:,.1f} m³")
        print(f"         Final:   {final:,.1f} m³")
        print(f"         Change:  {final - initial:+,.1f} m³")
    
    # Demand statistics
    print(f"\n   Demand performance:")
    for demand_name, demand_label in [('city', 'Municipal'), ('farm', 'Agricultural')]:
        total_request = sum(r['node_states'][demand_name]['request'] for r in results)
        total_delivered = sum(r['node_states'][demand_name]['delivered'] for r in results)
        total_deficit = sum(r['node_states'][demand_name]['deficit'] for r in results)
        reliability = (total_delivered / total_request * 100) if total_request > 0 else 0
        
        print(f"      {demand_label} ({demand_name}):")
        print(f"         Requested: {total_request:,.1f} m³")
        print(f"         Delivered: {total_delivered:,.1f} m³")
        print(f"         Deficit:   {total_deficit:,.1f} m³")
        print(f"         Reliability: {reliability:.1f}%")
    
    print("\n" + "=" * 70)
    print("✓ Simulation complete! Results saved to 'output' directory.")
    print("=" * 70)


def main():
    """Run both examples."""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 20 + "HydroSim Quick Start" + " " * 28 + "║")
    print("║" + " " * 15 + "Water Resources Planning Framework" + " " * 19 + "║")
    print("╚" + "═" * 68 + "╝")
    
    # Run simple example
    run_simple_example()
    
    # Run complex example
    run_complex_example()
    
    print("\n")
    print("=" * 70)
    print("Next Steps:")
    print("=" * 70)
    print("1. Examine the output files in the 'output' directory")
    print("2. Modify the YAML configuration files to create your own network")
    print("3. See examples/README.md for detailed configuration options")
    print("4. See examples/results_output_example.py for programmatic usage")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()

