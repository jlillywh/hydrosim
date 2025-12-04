"""
Example demonstrating the results output system.

This example shows how to use the ResultsWriter to capture and export
simulation results in both CSV and JSON formats.
"""

from datetime import datetime
import pandas as pd

from hydrosim import (
    NetworkGraph,
    ElevationAreaVolume,
    StorageNode,
    SourceNode,
    DemandNode,
    Link,
    TimeSeriesStrategy,
    MunicipalDemand,
    ClimateEngine,
    TimeSeriesClimateSource,
    SiteConfig,
    LinearProgrammingSolver,
    SimulationEngine,
    ResultsWriter
)
from hydrosim.solver import COST_DEMAND, COST_SPILL


def create_example_network():
    """Create a simple example network: Source -> Storage -> Demand"""
    network = NetworkGraph()
    
    # Create EAV table for storage
    eav = ElevationAreaVolume(
        elevations=[100.0, 110.0, 120.0, 130.0],
        areas=[1000.0, 1500.0, 2000.0, 2500.0],
        volumes=[0.0, 12500.0, 30000.0, 52500.0]
    )
    
    # Create inflow time series
    inflow_data = pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=30, freq='D'),
        'inflow': [100.0] * 30
    })
    
    # Create nodes
    source = SourceNode('river_inflow', TimeSeriesStrategy(inflow_data, 'inflow'))
    storage = StorageNode('reservoir', initial_storage=20000.0, eav_table=eav, max_storage=50000.0, min_storage=0.0)
    demand = DemandNode('city_demand', MunicipalDemand(population=500, per_capita_demand=0.15))
    
    # Add nodes to network
    network.add_node(source)
    network.add_node(storage)
    network.add_node(demand)
    
    # Create links
    inflow_link = Link('inflow_link', source, storage, physical_capacity=200.0, cost=COST_SPILL)
    delivery_link = Link('delivery_link', storage, demand, physical_capacity=150.0, cost=COST_DEMAND)
    
    # Add links to network
    network.add_link(inflow_link)
    network.add_link(delivery_link)
    
    return network


def create_climate_engine():
    """Create a climate engine with example data."""
    # Create climate data
    climate_data = pd.DataFrame({
        'precip': [5.0] * 30,
        't_max': [25.0] * 30,
        't_min': [15.0] * 30,
        'solar': [20.0] * 30
    }, index=pd.date_range('2024-01-01', periods=30, freq='D'))
    
    source = TimeSeriesClimateSource(climate_data)
    site_config = SiteConfig(latitude=40.0, elevation=100.0)
    
    return ClimateEngine(source, site_config, datetime(2024, 1, 1))


def main():
    """Run example simulation with results output."""
    print("HydroSim Results Output Example")
    print("=" * 50)
    
    # Create network and climate engine
    print("\n1. Creating network and climate engine...")
    network = create_example_network()
    climate_engine = create_climate_engine()
    
    # Create solver and simulation engine
    print("2. Initializing simulation engine...")
    solver = LinearProgrammingSolver()
    engine = SimulationEngine(network, climate_engine, solver)
    
    # Create results writers for both CSV and JSON formats
    print("3. Creating results writers...")
    csv_writer = ResultsWriter(output_dir="output", format="csv")
    json_writer = ResultsWriter(output_dir="output", format="json")
    
    # Run simulation
    print("4. Running simulation for 30 days...")
    num_timesteps = 30
    
    for i in range(num_timesteps):
        result = engine.step()
        
        # Add results to both writers
        csv_writer.add_timestep(result)
        json_writer.add_timestep(result)
        
        # Print progress every 10 timesteps
        if (i + 1) % 10 == 0:
            print(f"   Completed {i + 1}/{num_timesteps} timesteps")
    
    # Write results to files
    print("\n5. Writing results to files...")
    
    print("   Writing CSV files...")
    csv_files = csv_writer.write_all(prefix="example_simulation")
    for file_type, filepath in csv_files.items():
        print(f"      - {file_type}: {filepath}")
    
    print("   Writing JSON file...")
    json_files = json_writer.write_all(prefix="example_simulation")
    for file_type, filepath in json_files.items():
        print(f"      - {file_type}: {filepath}")
    
    # Print summary statistics
    print("\n6. Simulation Summary:")
    print("=" * 50)
    
    results = csv_writer.get_results()
    
    # Calculate total inflow
    total_inflow = sum(r['flows']['inflow_link'] for r in results)
    print(f"   Total inflow: {total_inflow:.2f} m³")
    
    # Calculate total delivery
    total_delivery = sum(r['flows']['delivery_link'] for r in results)
    print(f"   Total delivery: {total_delivery:.2f} m³")
    
    # Calculate total deficit
    total_deficit = sum(r['node_states']['city_demand']['deficit'] for r in results)
    print(f"   Total deficit: {total_deficit:.2f} m³")
    
    # Final storage
    final_storage = results[-1]['node_states']['reservoir']['storage']
    initial_storage = results[0]['node_states']['reservoir']['storage']
    print(f"   Initial storage: {initial_storage:.2f} m³")
    print(f"   Final storage: {final_storage:.2f} m³")
    print(f"   Storage change: {final_storage - initial_storage:.2f} m³")
    
    print("\n" + "=" * 50)
    print("Results have been written to the 'output' directory.")
    print("CSV files: flows, storage, demands, sources")
    print("JSON file: all data in structured format")


if __name__ == "__main__":
    main()
