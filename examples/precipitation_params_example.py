"""
Example: Precipitation Parameter Calculation

This example demonstrates how to use the PrecipitationParameterCalculator
to calculate WGEN precipitation parameters from observed climate data.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from hydrosim.climate_builder.precipitation_params import PrecipitationParameterCalculator


def generate_synthetic_data():
    """Generate synthetic precipitation data for demonstration."""
    # Create 10 years of daily data
    start_date = datetime(2010, 1, 1)
    dates = [start_date + timedelta(days=i) for i in range(3650)]
    
    # Generate precipitation with seasonal pattern
    np.random.seed(42)
    precip = []
    
    for date in dates:
        # Higher precipitation probability and amounts in winter months
        if date.month in [11, 12, 1, 2]:
            # Winter: 60% chance of precipitation
            if np.random.random() < 0.6:
                # Gamma distribution with higher mean
                p = np.random.gamma(2.5, 6.0)
            else:
                p = 0.0
        elif date.month in [3, 4, 5]:
            # Spring: 40% chance of precipitation
            if np.random.random() < 0.4:
                p = np.random.gamma(2.0, 4.0)
            else:
                p = 0.0
        elif date.month in [6, 7, 8]:
            # Summer: 20% chance of precipitation
            if np.random.random() < 0.2:
                p = np.random.gamma(1.5, 3.0)
            else:
                p = 0.0
        else:
            # Fall: 50% chance of precipitation
            if np.random.random() < 0.5:
                p = np.random.gamma(2.0, 5.0)
            else:
                p = 0.0
        
        precip.append(p)
    
    # Create DataFrame
    df = pd.DataFrame({
        'date': dates,
        'precipitation_mm': precip
    })
    
    return df


def main():
    """Main example function."""
    print("=" * 70)
    print("Precipitation Parameter Calculation Example")
    print("=" * 70)
    print()
    
    # Generate synthetic data
    print("Generating synthetic precipitation data (10 years)...")
    df = generate_synthetic_data()
    print(f"Generated {len(df)} days of data")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")
    print()
    
    # Calculate basic statistics
    print("Basic Statistics:")
    print(f"  Mean precipitation: {df['precipitation_mm'].mean():.2f} mm/day")
    print(f"  Max precipitation: {df['precipitation_mm'].max():.2f} mm")
    wet_days = (df['precipitation_mm'] >= 0.1).sum()
    print(f"  Wet days (>= 0.1 mm): {wet_days} ({100*wet_days/len(df):.1f}%)")
    print()
    
    # Initialize calculator
    print("Initializing PrecipitationParameterCalculator...")
    calc = PrecipitationParameterCalculator(
        wet_day_threshold=0.1,  # WMO standard
        min_wet_days=10
    )
    print()
    
    # Calculate parameters
    print("Calculating WGEN precipitation parameters...")
    params = calc.calculate_parameters(df)
    print("Done!")
    print()
    
    # Display results
    print("=" * 70)
    print("WGEN Precipitation Parameters")
    print("=" * 70)
    print()
    
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    print("Markov Chain Transition Probabilities:")
    print("-" * 70)
    print(f"{'Month':<8} {'PWW':>8} {'PWD':>8}")
    print("-" * 70)
    for i, month in enumerate(months):
        pww = params['pww'][i]
        pwd = params['pwd'][i]
        print(f"{month:<8} {pww:>8.3f} {pwd:>8.3f}")
    print()
    
    print("Gamma Distribution Parameters:")
    print("-" * 70)
    print(f"{'Month':<8} {'Alpha':>8} {'Beta':>8} {'Mean (mm)':>12}")
    print("-" * 70)
    for i, month in enumerate(months):
        alpha = params['alpha'][i]
        beta = params['beta'][i]
        mean = alpha * beta  # Mean of Gamma distribution
        print(f"{month:<8} {alpha:>8.3f} {beta:>8.3f} {mean:>12.2f}")
    print()
    
    # Interpretation
    print("=" * 70)
    print("Interpretation:")
    print("=" * 70)
    print()
    print("PWW (P_Wet|Wet): Probability of a wet day following a wet day")
    print("  - Higher values indicate wet spells tend to persist")
    print("  - Winter months show higher PWW (wet periods last longer)")
    print()
    print("PWD (P_Wet|Dry): Probability of a wet day following a dry day")
    print("  - Higher values indicate more frequent precipitation events")
    print("  - Winter months show higher PWD (more frequent storms)")
    print()
    print("Alpha & Beta: Gamma distribution parameters for wet day amounts")
    print("  - Mean precipitation = Alpha × Beta")
    print("  - Variance = Alpha × Beta²")
    print("  - Winter months show higher mean precipitation amounts")
    print()
    
    # Seasonal summary
    print("Seasonal Summary:")
    print("-" * 70)
    seasons = {
        'Winter (DJF)': [11, 0, 1],  # Dec, Jan, Feb (0-indexed)
        'Spring (MAM)': [2, 3, 4],
        'Summer (JJA)': [5, 6, 7],
        'Fall (SON)': [8, 9, 10]
    }
    
    for season_name, month_indices in seasons.items():
        avg_pww = np.mean([params['pww'][i] for i in month_indices])
        avg_pwd = np.mean([params['pwd'][i] for i in month_indices])
        avg_mean = np.mean([params['alpha'][i] * params['beta'][i] for i in month_indices])
        print(f"{season_name:<15} PWW={avg_pww:.3f}  PWD={avg_pwd:.3f}  Mean={avg_mean:.2f} mm")
    print()
    
    print("=" * 70)
    print("These parameters can be used with WGEN to generate synthetic")
    print("precipitation sequences that match the statistical properties")
    print("of the observed data.")
    print("=" * 70)


if __name__ == '__main__':
    main()
