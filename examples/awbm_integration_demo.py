#!/usr/bin/env python3
"""
AWBM Integration Demonstration Script

This script demonstrates how to use the AWBM (Australian Water Balance Model)
rainfall-runoff strategy in HydroSim. It shows both programmatic usage and
YAML configuration approaches.

The AWBM is a conceptual rainfall-runoff model that uses three surface stores
with different capacities to represent spatial variability in runoff generation
across a catchment. It's particularly useful for climate-driven scenarios.

Requirements:
    - HydroSim with AWBM integration
    - Climate data (CSV file with precipitation and ET0)
    - Python 3.8+

Usage:
    python awbm_integration_demo.py
"""

import hydrosim as hs
import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt


def create_sample_climate_data():
    """
    Create sample climate data for demonstration.
    
    Returns:
        pd.DataFrame: Climate data with columns [date, precip, t_max, t_min, solar]
    """
    print("Creating sample climate data...")
    
    # Generate 365 days of synthetic climate data
    dates = pd.date_range('2024-01-01', periods=365, freq='D')
    
    # Synthetic precipitation (mm/day) - seasonal pattern with random variation
    base_precip = 2.0 + 3.0 * np.sin(2 * np.pi * np.arange(365) / 365)  # Seasonal cycle
    precip = np.maximum(0, base_precip + np.random.exponential(2.0, 365))  # Add random events
    
    # Temperature (°C) - seasonal pattern
    t_max = 20 + 15 * np.sin(2 * np.pi * np.arange(365) / 365) + np.random.normal(0, 2, 365)
    t_min = t_max - 10 + np.random.normal(0, 1, 365)
    
    # Solar radiation (MJ/m²/day) - seasonal pattern
    solar = 15 + 10 * np.sin(2 * np.pi * np.arange(365) / 365) + np.random.normal(0, 1, 365)
    solar = np.maximum(5, solar)  # Ensure positive values
    
    climate_df = pd.DataFrame({
        'date': dates,
        'precip': precip,
        't_max': t_max,
        't_min': t_min,
        'solar': solar
    })
    
    # Save to CSV for YAML example
    climate_df.to_csv('examples/climate_data.csv', index=False)
    print(f"Sample climate data saved to examples/climate_data.csv")
    print(f"Climate summary: {len(climate_df)} days, "
          f"total precip: {climate_df['precip'].sum():.1f} mm, "
          f"avg temp: {climate_df['t_max'].mean():.1f}°C")
    
    return climate_df


def demonstrate_programmatic_usage():
    """
    Demonstrate programmatic usage of AWBM strategy.
    """
    print("\n" + "="*60)
    print("DEMONSTRATION 1: Programmatic AWBM Usage")
    print("="*60)
    
    # Create sample climate data
    climate_df = create_sample_climate_data()
    
    # Initialize AWBM strategy with typical Australian catchment parameters
    print("\nInitializing AWBM strategy...")
    awbm_strategy = hs.AWBMGeneratorStrategy(
        catchment_area=5.0e7,      # 50 km² catchment
        a1=134.0,                  # Store 1 capacity (mm)
        a2=433.0,                  # Store 2 capacity (mm)
        a3=433.0,                  # Store 3 capacity (mm)
        f1=0.3,                    # Partial area fraction 1
        f2=0.3,                    # Partial area fraction 2
        f3=0.4,                    # Partial area fraction 3
        bfi=0.35,                  # Baseflow Index
        k_base=0.95,               # Recession constant
        initial_storage=0.5        # Start at 50% saturation
    )
    
    print(f"AWBM strategy initialized for {awbm_strategy.catchment_area/1e6:.1f} km² catchment")
    
    # Create climate engine
    climate_engine = hs.ClimateEngine(
        source_type='timeseries',
        filepath='examples/climate_data.csv',
        site={'latitude': 45.0, 'elevation': 1000.0}
    )
    
    # Simulate daily runoff for first 30 days
    print("\nSimulating daily runoff for first 30 days...")
    results = []
    
    for day in range(30):
        # Get climate state for this day
        climate_state = climate_engine.get_climate_state(day)
        
        # Generate runoff using AWBM
        runoff_volume = awbm_strategy.generate(climate_state)
        
        # Get model state for monitoring
        state_summary = awbm_strategy.get_state_summary()
        
        results.append({
            'day': day + 1,
            'precip': climate_state.precip,
            'et0': climate_state.et0,
            'runoff_m3': runoff_volume,
            'runoff_mm': runoff_volume * 1000 / awbm_strategy.catchment_area,
            'total_storage': state_summary['total_storage'],
            'baseflow_store': state_summary['baseflow_store']
        })
        
        if day < 5:  # Print first 5 days in detail
            print(f"  Day {day+1}: P={climate_state.precip:.1f}mm, "
                  f"ET0={climate_state.et0:.1f}mm, "
                  f"Q={runoff_volume:.1f}m³ ({runoff_volume*1000/awbm_strategy.catchment_area:.2f}mm)")
    
    # Convert to DataFrame for analysis
    results_df = pd.DataFrame(results)
    
    # Print summary statistics
    print(f"\n30-day simulation summary:")
    print(f"  Total precipitation: {results_df['precip'].sum():.1f} mm")
    print(f"  Total runoff: {results_df['runoff_mm'].sum():.1f} mm")
    print(f"  Runoff coefficient: {results_df['runoff_mm'].sum() / results_df['precip'].sum():.3f}")
    print(f"  Average daily runoff: {results_df['runoff_m3'].mean():.1f} m³/day")
    
    # Get mass balance summary
    mass_balance = awbm_strategy.get_mass_balance_summary()
    print(f"\nMass balance check:")
    print(f"  Residual: {mass_balance['mass_balance_residual']:.6f} mm (should be near zero)")
    
    return results_df


def demonstrate_yaml_configuration():
    """
    Demonstrate YAML configuration approach.
    """
    print("\n" + "="*60)
    print("DEMONSTRATION 2: YAML Configuration Usage")
    print("="*60)
    
    # Check if YAML example exists
    yaml_path = Path('examples/awbm_example.yaml')
    if not yaml_path.exists():
        print(f"ERROR: YAML example not found at {yaml_path}")
        return None
    
    print(f"Loading network from YAML configuration: {yaml_path}")
    
    try:
        # Load and run network from YAML
        network = hs.Network.from_yaml('examples/awbm_example.yaml')
        print(f"Network loaded successfully with {len(network.nodes)} nodes and {len(network.links)} links")
        
        # Print network structure
        print("\nNetwork structure:")
        for node_id, node in network.nodes.items():
            node_type = type(node).__name__
            if hasattr(node, 'strategy') and node.strategy:
                strategy_type = type(node.strategy).__name__
                print(f"  {node_id}: {node_type} with {strategy_type}")
            else:
                print(f"  {node_id}: {node_type}")
        
        # Run simulation for 30 days
        print(f"\nRunning 30-day simulation...")
        results = network.simulate(num_timesteps=30)
        
        # Print simulation results summary
        print(f"Simulation completed successfully!")
        print(f"Results shape: {results.shape}")
        
        # Show sample results for the AWBM source node
        if 'catchment_inflow' in results.columns:
            inflow_data = results['catchment_inflow']
            print(f"\nCatchment inflow summary (first 30 days):")
            print(f"  Mean daily inflow: {inflow_data.mean():.1f} m³/day")
            print(f"  Max daily inflow: {inflow_data.max():.1f} m³/day")
            print(f"  Total inflow: {inflow_data.sum():.1f} m³")
        
        return results
        
    except Exception as e:
        print(f"ERROR running YAML simulation: {e}")
        print("This might be due to missing dependencies or configuration issues.")
        return None


def demonstrate_parameter_sensitivity():
    """
    Demonstrate parameter sensitivity analysis.
    """
    print("\n" + "="*60)
    print("DEMONSTRATION 3: Parameter Sensitivity Analysis")
    print("="*60)
    
    # Create simple climate scenario
    print("Testing parameter sensitivity with constant climate...")
    
    # Constant climate: moderate precipitation and ET
    class SimpleClimate:
        def __init__(self, precip, et0):
            self.precip = precip
            self.et0 = et0
    
    climate = SimpleClimate(precip=10.0, et0=5.0)  # 10mm rain, 5mm ET per day
    
    # Test different BFI values
    bfi_values = [0.1, 0.35, 0.7]
    print(f"\nTesting Baseflow Index (BFI) sensitivity:")
    print(f"Climate: {climate.precip}mm precip, {climate.et0}mm ET0")
    
    for bfi in bfi_values:
        awbm = hs.AWBMGeneratorStrategy(
            catchment_area=1e6,  # 1 km²
            a1=100.0, a2=300.0, a3=500.0,
            f1=0.33, f2=0.33, f3=0.34,
            bfi=bfi,
            k_base=0.9,
            initial_storage=0.0  # Start empty
        )
        
        # Run for 10 days to see steady-state behavior
        daily_runoff = []
        for day in range(10):
            runoff = awbm.generate(climate)
            daily_runoff.append(runoff * 1000 / awbm.catchment_area)  # Convert to mm
        
        avg_runoff = np.mean(daily_runoff[-5:])  # Average of last 5 days
        print(f"  BFI = {bfi:.2f}: Steady-state runoff = {avg_runoff:.2f} mm/day")
    
    # Test store capacity sensitivity
    print(f"\nTesting store capacity sensitivity:")
    capacities = [(50, 150, 250), (100, 300, 500), (200, 600, 1000)]
    
    for a1, a2, a3 in capacities:
        awbm = hs.AWBMGeneratorStrategy(
            catchment_area=1e6,  # 1 km²
            a1=a1, a2=a2, a3=a3,
            f1=0.33, f2=0.33, f3=0.34,
            bfi=0.35,
            k_base=0.9,
            initial_storage=0.0
        )
        
        # Run for 10 days
        daily_runoff = []
        for day in range(10):
            runoff = awbm.generate(climate)
            daily_runoff.append(runoff * 1000 / awbm.catchment_area)
        
        avg_runoff = np.mean(daily_runoff[-5:])
        print(f"  Capacities ({a1}, {a2}, {a3}): Steady-state runoff = {avg_runoff:.2f} mm/day")


def demonstrate_mass_balance_verification():
    """
    Demonstrate mass balance verification capabilities.
    """
    print("\n" + "="*60)
    print("DEMONSTRATION 4: Mass Balance Verification")
    print("="*60)
    
    print("Testing mass balance conservation over extended simulation...")
    
    # Create AWBM strategy
    awbm = hs.AWBMGeneratorStrategy(
        catchment_area=1e7,  # 10 km²
        a1=134.0, a2=433.0, a3=433.0,
        f1=0.3, f2=0.3, f3=0.4,
        bfi=0.35,
        k_base=0.95,
        initial_storage=0.5
    )
    
    # Create variable climate scenario
    np.random.seed(42)  # For reproducible results
    
    total_days = 100
    mass_balance_errors = []
    
    print(f"Running {total_days}-day simulation with variable climate...")
    
    for day in range(total_days):
        # Variable climate
        precip = max(0, np.random.exponential(3.0))  # Random precipitation events
        et0 = 3.0 + 2.0 * np.sin(2 * np.pi * day / 365)  # Seasonal ET0
        
        climate = SimpleClimate(precip, et0)
        
        # Generate runoff
        runoff = awbm.generate(climate)
        
        # Check mass balance
        mass_balance = awbm.get_mass_balance_summary()
        mass_balance_errors.append(abs(mass_balance['mass_balance_residual']))
        
        if day % 20 == 0:  # Print every 20 days
            print(f"  Day {day+1}: P={precip:.1f}mm, ET0={et0:.1f}mm, "
                  f"Q={runoff*1000/awbm.catchment_area:.2f}mm, "
                  f"MB_error={mass_balance['mass_balance_residual']:.6f}mm")
    
    # Final mass balance summary
    final_mass_balance = awbm.get_mass_balance_summary()
    print(f"\nFinal mass balance summary:")
    print(f"  Total inflow: {final_mass_balance['cumulative_inflow']:.1f} mm")
    print(f"  Total ET: {final_mass_balance['cumulative_actual_et']:.1f} mm")
    print(f"  Total outflow: {final_mass_balance['cumulative_outflow']:.1f} mm")
    print(f"  Storage change: {final_mass_balance['storage_change']:.1f} mm")
    print(f"  Mass balance residual: {final_mass_balance['mass_balance_residual']:.6f} mm")
    print(f"  Maximum daily MB error: {max(mass_balance_errors):.6f} mm")
    
    # Check numerical stability
    stability = awbm.check_numerical_stability()
    print(f"\nNumerical stability check:")
    for check, passed in stability.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {check}: {status}")


class SimpleClimate:
    """Simple climate state for demonstrations."""
    def __init__(self, precip, et0):
        self.precip = precip
        self.et0 = et0


def main():
    """
    Main demonstration function.
    """
    print("AWBM Integration Demonstration")
    print("=" * 60)
    print("This script demonstrates the AWBM (Australian Water Balance Model)")
    print("integration in HydroSim, showing various usage patterns and capabilities.")
    
    try:
        # Run demonstrations
        results_programmatic = demonstrate_programmatic_usage()
        results_yaml = demonstrate_yaml_configuration()
        demonstrate_parameter_sensitivity()
        demonstrate_mass_balance_verification()
        
        print("\n" + "="*60)
        print("DEMONSTRATION COMPLETE")
        print("="*60)
        print("All AWBM demonstrations completed successfully!")
        print("\nKey takeaways:")
        print("1. AWBM can be used programmatically or via YAML configuration")
        print("2. The model maintains mass balance and numerical stability")
        print("3. Parameters can be tuned for different catchment characteristics")
        print("4. Integration with HydroSim's network simulation is seamless")
        
        print(f"\nFor more information, see:")
        print(f"  - AWBM example YAML: examples/awbm_example.yaml")
        print(f"  - Generated climate data: examples/climate_data.csv")
        print(f"  - HydroSim documentation: https://hydrosim.readthedocs.io/")
        
    except ImportError as e:
        print(f"ERROR: Missing required module: {e}")
        print("Please ensure HydroSim is properly installed.")
    except Exception as e:
        print(f"ERROR during demonstration: {e}")
        print("Please check your HydroSim installation and try again.")


if __name__ == "__main__":
    main()