"""
WGEN Stochastic Weather Generation Example

This example demonstrates HydroSim's WGEN (Weather GENerator) integration
for stochastic climate data generation. WGEN produces synthetic daily weather
including precipitation, temperature, and solar radiation.

Key Features Demonstrated:
1. CSV-based parameter configuration (recommended for 62 parameters)
2. Inline YAML parameter configuration (alternative approach)
3. Stochastic weather generation with monthly parameter variation
4. Climate-driven water network simulation
5. Comparison of results between configuration methods

WGEN generates:
- Precipitation (mm/day)
- Maximum temperature (°C)
- Minimum temperature (°C)
- Solar radiation (MJ/m²/day)

These climate variables drive:
- Reservoir evaporation
- Agricultural water demand (crop ET)
- Catchment runoff (in real applications)
"""

from datetime import datetime
import os
import pandas as pd
from hydrosim.config import YAMLParser
from hydrosim import (
    SimulationEngine, LinearProgrammingSolver, ResultsWriter, ClimateEngine,
    NetworkGraph, StorageNode, SourceNode, DemandNode, Link,
    ElevationAreaVolume, TimeSeriesStrategy, MunicipalDemand, AgricultureDemand,
    WGENClimateSource, WGENParams, SiteConfig
)


def run_csv_parameter_example():
    """
    Example 1: WGEN with CSV Parameter File (Recommended)
    
    This approach uses a CSV file to specify all 62 WGEN parameters,
    making configuration more maintainable and reusable.
    """
    print("=" * 70)
    print("Example 1: WGEN with CSV Parameter File")
    print("=" * 70)
    print("Configuration: examples/wgen_example.yaml")
    print("Parameters: examples/wgen_params_template.csv")
    print()
    
    # Step 1: Parse YAML configuration with CSV parameter reference
    print("[Step 1] Loading configuration from YAML file...")
    parser = YAMLParser('examples/wgen_example.yaml')
    network, climate_source, site_config = parser.parse()
    print(f"   ✓ Loaded network with {len(network.nodes)} nodes and {len(network.links)} links")
    print(f"   ✓ Climate source: {type(climate_source).__name__}")
    print(f"   ✓ WGEN parameters loaded from CSV file")
    
    # Step 2: Validate network
    print("\n[Step 2] Validating network topology...")
    errors = network.validate()
    if errors:
        print("   ✗ Validation errors:")
        for error in errors:
            print(f"      - {error}")
        return None
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
    print("   ✓ Results writer ready")
    
    # Step 5: Run simulation
    print("\n[Step 5] Running 30-day simulation with stochastic weather...")
    num_days = 30
    
    for day in range(num_days):
        result = engine.step()
        writer.add_timestep(result)
        
        # Print progress every 10 days
        if (day + 1) % 10 == 0 or day == 0:
            climate = result['climate']
            storage = result['node_states']['main_reservoir']['storage']
            city_deficit = result['node_states']['city']['deficit']
            farm_deficit = result['node_states']['farm']['deficit']
            
            print(f"      Day {day + 1:2d}: Precip = {climate.precip:5.1f} mm, "
                  f"Tmax = {climate.t_max:5.1f}°C, "
                  f"Storage = {storage:8.1f} m³")
            print(f"              City deficit = {city_deficit:6.2f} m³, "
                  f"Farm deficit = {farm_deficit:6.2f} m³")
    
    print(f"   ✓ Completed {num_days} days of simulation")
    
    # Step 6: Print summary statistics
    print("\n[Step 6] Climate Summary")
    print("-" * 70)
    results = writer.get_results()
    
    # Climate statistics
    total_precip = sum(r['climate'].precip for r in results)
    avg_tmax = sum(r['climate'].t_max for r in results) / len(results)
    avg_tmin = sum(r['climate'].t_min for r in results) / len(results)
    avg_solar = sum(r['climate'].solar for r in results) / len(results)
    
    print(f"   Generated Weather (30 days):")
    print(f"      Total precipitation: {total_precip:.1f} mm")
    print(f"      Average Tmax: {avg_tmax:.1f}°C")
    print(f"      Average Tmin: {avg_tmin:.1f}°C")
    print(f"      Average solar radiation: {avg_solar:.1f} MJ/m²/day")
    
    # Storage statistics
    initial_storage = results[0]['node_states']['main_reservoir']['storage']
    final_storage = results[-1]['node_states']['main_reservoir']['storage']
    total_evap = sum(r['node_states']['main_reservoir']['evap_loss'] for r in results)
    
    print(f"\n   Reservoir Operations:")
    print(f"      Initial storage: {initial_storage:,.1f} m³")
    print(f"      Final storage: {final_storage:,.1f} m³")
    print(f"      Change: {final_storage - initial_storage:+,.1f} m³")
    print(f"      Total evaporation: {total_evap:,.1f} m³")
    
    # Demand statistics
    city_request = sum(r['node_states']['city']['request'] for r in results)
    city_delivered = sum(r['node_states']['city']['delivered'] for r in results)
    city_deficit = sum(r['node_states']['city']['deficit'] for r in results)
    city_reliability = (city_delivered / city_request * 100) if city_request > 0 else 0
    
    farm_request = sum(r['node_states']['farm']['request'] for r in results)
    farm_delivered = sum(r['node_states']['farm']['delivered'] for r in results)
    farm_deficit = sum(r['node_states']['farm']['deficit'] for r in results)
    farm_reliability = (farm_delivered / farm_request * 100) if farm_request > 0 else 0
    
    print(f"\n   Demand Performance:")
    print(f"      Municipal (city):")
    print(f"         Requested: {city_request:,.1f} m³")
    print(f"         Delivered: {city_delivered:,.1f} m³")
    print(f"         Deficit: {city_deficit:,.1f} m³")
    print(f"         Reliability: {city_reliability:.1f}%")
    print(f"      Agricultural (farm):")
    print(f"         Requested: {farm_request:,.1f} m³")
    print(f"         Delivered: {farm_delivered:,.1f} m³")
    print(f"         Deficit: {farm_deficit:,.1f} m³")
    print(f"         Reliability: {farm_reliability:.1f}%")
    
    print("\n" + "=" * 70)
    print("✓ CSV parameter example complete!")
    print("=" * 70)
    
    return writer


def run_inline_parameter_example():
    """
    Example 2: WGEN with Inline YAML Parameters (Alternative)
    
    This approach specifies all parameters directly in the YAML configuration.
    Useful for simple cases or when parameters are tightly coupled to a
    specific configuration.
    """
    print("\n\n")
    print("=" * 70)
    print("Example 2: WGEN with Inline Parameters (Programmatic)")
    print("=" * 70)
    print("Configuration: Created programmatically in Python")
    print()
    
    # Step 1: Create network programmatically
    print("[Step 1] Creating network programmatically...")
    network = NetworkGraph()
    
    # Create EAV table for reservoir
    eav = ElevationAreaVolume(
        elevations=[100.0, 105.0, 110.0, 115.0, 120.0],
        areas=[1500.0, 2500.0, 3500.0, 4500.0, 5500.0],
        volumes=[0.0, 10000.0, 30000.0, 55000.0, 85000.0]
    )
    
    # Load inflow data
    inflow_data = pd.read_csv('examples/inflow_data.csv')
    
    # Create nodes
    source = SourceNode(
        'mountain_catchment',
        TimeSeriesStrategy(inflow_data, 'inflow')
    )
    
    storage = StorageNode(
        'main_reservoir',
        initial_storage=40000.0,
        eav_table=eav,
        max_storage=80000.0,
        min_storage=2000.0
    )
    
    city = DemandNode(
        'city',
        MunicipalDemand(population=8000.0, per_capita_demand=0.25)
    )
    
    farm = DemandNode(
        'farm',
        AgricultureDemand(area=25000.0, crop_coefficient=0.75)
    )
    
    network.add_node(source)
    network.add_node(storage)
    network.add_node(city)
    network.add_node(farm)
    
    # Create links
    link1 = Link('catchment_to_reservoir', source, storage, 
                 physical_capacity=8000.0, cost=0.0)
    link2 = Link('reservoir_to_city', storage, city,
                 physical_capacity=3000.0, cost=0.0)
    link3 = Link('reservoir_to_farm', storage, farm,
                 physical_capacity=2000.0, cost=0.0)
    
    network.add_link(link1)
    network.add_link(link2)
    network.add_link(link3)
    
    print(f"   ✓ Created network with {len(network.nodes)} nodes and {len(network.links)} links")
    
    # Step 2: Create WGEN climate source with inline parameters
    print("\n[Step 2] Creating WGEN climate source with inline parameters...")
    
    # Define WGEN parameters inline (same values as CSV template)
    wgen_params = WGENParams(
        # Precipitation parameters (monthly)
        pww=[0.45, 0.42, 0.40, 0.38, 0.35, 0.30, 0.25, 0.28, 0.32, 0.38, 0.42, 0.48],
        pwd=[0.25, 0.23, 0.22, 0.20, 0.18, 0.15, 0.12, 0.15, 0.18, 0.22, 0.25, 0.27],
        alpha=[1.2, 1.1, 1.0, 0.9, 0.8, 0.7, 0.6, 0.7, 0.8, 1.0, 1.1, 1.3],
        beta=[8.5, 7.8, 7.2, 6.5, 5.8, 5.0, 4.5, 5.2, 6.0, 7.0, 7.8, 9.2],
        # Temperature parameters
        txmd=20.0,
        atx=10.0,
        txmw=18.0,
        tn=10.0,
        atn=8.0,
        cvtx=0.1,
        acvtx=0.05,
        cvtn=0.1,
        acvtn=0.05,
        # Radiation parameters
        rmd=15.0,
        ar=5.0,
        rmw=12.0,
        # Location
        latitude=45.0,
        random_seed=42  # Same seed for reproducibility
    )
    
    climate_source = WGENClimateSource(wgen_params, datetime(2024, 1, 1))
    site_config = SiteConfig(latitude=45.0, elevation=1000.0)
    
    print("   ✓ WGEN climate source created with inline parameters")
    
    # Step 3: Set up simulation engine
    print("\n[Step 3] Setting up simulation engine...")
    climate_engine = ClimateEngine(climate_source, site_config, datetime(2024, 1, 1))
    solver = LinearProgrammingSolver()
    engine = SimulationEngine(network, climate_engine, solver)
    print("   ✓ Simulation engine initialized")
    
    # Step 4: Run simulation
    print("\n[Step 4] Running 30-day simulation...")
    num_days = 30
    results = []
    
    for day in range(num_days):
        result = engine.step()
        results.append(result)
        
        # Print progress every 10 days
        if (day + 1) % 10 == 0 or day == 0:
            climate = result['climate']
            storage = result['node_states']['main_reservoir']['storage']
            
            print(f"      Day {day + 1:2d}: Precip = {climate.precip:5.1f} mm, "
                  f"Tmax = {climate.t_max:5.1f}°C, "
                  f"Storage = {storage:8.1f} m³")
    
    print(f"   ✓ Completed {num_days} days of simulation")
    
    # Step 5: Print summary
    print("\n[Step 5] Summary")
    print("-" * 70)
    
    total_precip = sum(r['climate'].precip for r in results)
    avg_tmax = sum(r['climate'].t_max for r in results) / len(results)
    
    print(f"   Generated Weather:")
    print(f"      Total precipitation: {total_precip:.1f} mm")
    print(f"      Average Tmax: {avg_tmax:.1f}°C")
    
    initial_storage = results[0]['node_states']['main_reservoir']['storage']
    final_storage = results[-1]['node_states']['main_reservoir']['storage']
    
    print(f"\n   Reservoir:")
    print(f"      Initial storage: {initial_storage:,.1f} m³")
    print(f"      Final storage: {final_storage:,.1f} m³")
    print(f"      Change: {final_storage - initial_storage:+,.1f} m³")
    
    print("\n" + "=" * 70)
    print("✓ Inline parameter example complete!")
    print("=" * 70)
    
    return results


def compare_approaches():
    """
    Compare CSV vs Inline parameter approaches.
    """
    print("\n\n")
    print("=" * 70)
    print("Comparison: CSV vs Inline Parameters")
    print("=" * 70)
    print()
    print("CSV Parameter File Approach:")
    print("   ✓ Recommended for production use")
    print("   ✓ Easier to manage 62 parameters")
    print("   ✓ Reusable across multiple configurations")
    print("   ✓ Version control friendly")
    print("   ✓ Can be shared between projects")
    print("   ✓ Cleaner YAML configuration files")
    print()
    print("Inline YAML Parameter Approach:")
    print("   ✓ Good for simple examples")
    print("   ✓ Self-contained configuration")
    print("   ✓ No external file dependencies")
    print("   ✓ Useful for programmatic generation")
    print("   ✗ Verbose (62 parameters in YAML)")
    print("   ✗ Harder to maintain and reuse")
    print()
    print("Both approaches produce identical results when using the same")
    print("parameter values and random seed.")
    print("=" * 70)


def main():
    """Run WGEN demonstration examples."""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 18 + "WGEN Weather Generator" + " " * 28 + "║")
    print("║" + " " * 12 + "Stochastic Climate Data Generation" + " " * 22 + "║")
    print("╚" + "═" * 68 + "╝")
    
    # Run CSV parameter example
    csv_writer = run_csv_parameter_example()
    
    # Run inline parameter example
    inline_results = run_inline_parameter_example()
    
    # Compare approaches
    compare_approaches()
    
    # Write results to files
    if csv_writer:
        print("\n")
        print("=" * 70)
        print("Writing Results to Files")
        print("=" * 70)
        files = csv_writer.write_all(prefix="wgen_example")
        for file_type, filepath in files.items():
            print(f"   ✓ {file_type}: {filepath}")
        print("=" * 70)
    
    print("\n")
    print("=" * 70)
    print("Next Steps")
    print("=" * 70)
    print("1. Examine the generated climate data in output/wgen_example_*.csv")
    print("2. Modify wgen_params_template.csv to test different climate scenarios")
    print("3. Run multiple simulations with different random seeds for")
    print("   uncertainty analysis")
    print("4. Create parameter files for different climate regions")
    print("5. See design.md for parameter meanings and valid ranges")
    print()
    print("WGEN Parameters:")
    print("   - 48 precipitation parameters (pww, pwd, alpha, beta × 12 months)")
    print("   - 9 temperature parameters (txmd, atx, txmw, tn, atn, cv*)")
    print("   - 3 radiation parameters (rmd, ar, rmw)")
    print("   - 1 location parameter (latitude)")
    print("   - 1 optional parameter (random_seed)")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()
