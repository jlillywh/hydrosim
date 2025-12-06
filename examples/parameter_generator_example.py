"""
Example: WGEN Parameter Generator

This example demonstrates how to use the WGENParameterGenerator to generate
all WGEN parameters from observed climate data.

The generator orchestrates three calculators:
1. PrecipitationParameterCalculator - Markov chains and Gamma distributions
2. TemperatureParameterCalculator - Fourier series for seasonal patterns
3. SolarParameterCalculator - Solar radiation parameters

Usage:
    python examples/parameter_generator_example.py
"""

from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from hydrosim.climate_builder import WGENParameterGenerator


def create_sample_observed_data(output_path: Path, num_years: int = 10):
    """Create sample observed climate data for demonstration.
    
    Args:
        output_path: Path to save the CSV file
        num_years: Number of years of data to generate
    """
    print(f"Creating {num_years} years of sample observed data...")
    
    # Generate dates (excluding Feb 29)
    start_date = datetime(2010, 1, 1)
    dates = []
    current_date = start_date
    
    for _ in range(num_years * 365):
        # Skip February 29th
        if not (current_date.month == 2 and current_date.day == 29):
            dates.append(current_date)
        current_date += timedelta(days=1)
        
        # Skip Feb 29 if we hit it
        if current_date.month == 2 and current_date.day == 29:
            current_date += timedelta(days=1)
    
    # Generate synthetic climate data with realistic patterns
    data = []
    
    for date in dates:
        day_of_year = date.timetuple().tm_yday
        
        # Seasonal temperature pattern (warmer in summer)
        base_tmax = 15 + 10 * np.sin(2 * np.pi * (day_of_year - 80) / 365)
        base_tmin = base_tmax - 8
        
        # Add random variation
        tmax = base_tmax + np.random.normal(0, 3)
        tmin = base_tmin + np.random.normal(0, 2)
        
        # Ensure tmax > tmin
        if tmax <= tmin:
            tmax = tmin + 2
        
        # Precipitation (random with seasonal pattern)
        # Higher probability in winter
        wet_prob = 0.3 + 0.1 * np.sin(2 * np.pi * (day_of_year - 180) / 365)
        
        if np.random.random() < wet_prob:
            # Wet day - Gamma distributed precipitation
            precip = np.random.gamma(1.5, 5.0)
        else:
            # Dry day
            precip = 0.0
        
        data.append({
            'date': date.strftime('%Y-%m-%d'),
            'precipitation_mm': precip,
            'tmax_c': tmax,
            'tmin_c': tmin
        })
    
    # Create DataFrame and save
    df = pd.DataFrame(data)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    
    print(f"Sample data saved to: {output_path}")
    print(f"  Total days: {len(df)}")
    print(f"  Date range: {df['date'].iloc[0]} to {df['date'].iloc[-1]}")
    print(f"  Mean precipitation: {df['precipitation_mm'].mean():.2f} mm/day")
    print(f"  Mean Tmax: {df['tmax_c'].mean():.2f}°C")
    print(f"  Mean Tmin: {df['tmin_c'].mean():.2f}°C")
    print()


def main():
    """Main example function."""
    print("=" * 70)
    print("WGEN Parameter Generator Example")
    print("=" * 70)
    print()
    
    # Set up paths
    project_dir = Path("./example_project")
    observed_data_path = project_dir / "data" / "processed" / "observed_climate.csv"
    
    # Create sample observed data if it doesn't exist
    if not observed_data_path.exists():
        create_sample_observed_data(observed_data_path, num_years=15)
    else:
        print(f"Using existing observed data: {observed_data_path}")
        print()
    
    # Site latitude (Seattle, WA)
    latitude = 47.45
    
    print(f"Site latitude: {latitude}°")
    print()
    
    # Initialize parameter generator
    print("Initializing WGEN Parameter Generator...")
    generator = WGENParameterGenerator(
        observed_data_path=observed_data_path,
        latitude=latitude,
        output_dir=project_dir
    )
    print()
    
    # Generate all parameters
    print("Generating WGEN parameters...")
    print("-" * 70)
    params = generator.generate_all_parameters(has_solar_data=False)
    print("-" * 70)
    print()
    
    # Display parameter summary
    print("Parameter Summary:")
    print("=" * 70)
    
    print("\nPrecipitation Parameters (Monthly):")
    print("  Month  |  PWW   |  PWD   |  Alpha  |  Beta")
    print("  " + "-" * 50)
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    for i, month in enumerate(month_names):
        print(f"  {month:5s}  | {params['pww'][i]:6.3f} | {params['pwd'][i]:6.3f} | "
              f"{params['alpha'][i]:7.3f} | {params['beta'][i]:6.3f}")
    
    print("\nTemperature Parameters:")
    print(f"  Tmax dry mean (txmd):     {params['txmd']:7.2f}°C")
    print(f"  Tmax dry amplitude (atx): {params['atx']:7.2f}°C")
    print(f"  Tmax wet mean (txmw):     {params['txmw']:7.2f}°C")
    print(f"  Tmin mean (tn):           {params['tn']:7.2f}°C")
    print(f"  Tmin amplitude (atn):     {params['atn']:7.2f}°C")
    print(f"  Tmax CV (cvtx):           {params['cvtx']:7.4f}")
    print(f"  Tmax CV amplitude (acvtx):{params['acvtx']:7.4f}")
    print(f"  Tmin CV (cvtn):           {params['cvtn']:7.4f}")
    print(f"  Tmin CV amplitude (acvtn):{params['acvtn']:7.4f}")
    
    print("\nSolar Radiation Parameters (Monthly):")
    print("  Month  |   RMD   |   RMW")
    print("  " + "-" * 30)
    for i, month in enumerate(month_names):
        print(f"  {month:5s}  | {params['rmd'][i]:7.2f} | {params['rmw'][i]:7.2f}")
    print(f"\n  Solar amplitude (AR):     {params['ar']:7.2f} MJ/m²/day")
    
    print("\nLocation Parameters:")
    print(f"  Latitude:                 {params['latitude']:7.2f}°")
    
    print("\n" + "=" * 70)
    print()
    
    # Save parameters to CSV
    print("Saving parameters to CSV...")
    output_path = generator.save_parameters_to_csv(params)
    print()
    
    print("=" * 70)
    print("Example complete!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("  1. Review the generated parameters in:", output_path)
    print("  2. Use these parameters for WGEN simulation")
    print("  3. See climate_builder_simulation_example.py for simulation usage")
    print()


if __name__ == "__main__":
    main()
