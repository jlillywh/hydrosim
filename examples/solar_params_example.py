"""
Example: Solar Radiation Parameter Calculation

This example demonstrates how to use the SolarParameterCalculator to:
1. Calculate theoretical maximum solar radiation for a location
2. Calculate solar parameters from observed data (when available)
3. Estimate solar parameters when no observed data is available
4. Enforce physical constraints (solar <= theoretical max)

The calculator follows the algorithms from wgenpar.f and uses the correct
solar constant coefficient of 37.2 MJ/m²/day (not 889 Langleys).
"""

import pandas as pd
import numpy as np
from datetime import date, timedelta
from hydrosim.climate_builder import SolarParameterCalculator


def example_theoretical_max():
    """Example 1: Calculate theoretical maximum solar radiation."""
    print("=" * 70)
    print("Example 1: Theoretical Maximum Solar Radiation")
    print("=" * 70)
    
    # Create calculator for Seattle, WA (latitude 47.45°N)
    latitude = 47.45
    calculator = SolarParameterCalculator(latitude=latitude)
    
    print(f"\nLocation: Latitude {latitude}°N")
    print("\nTheoretical Maximum Solar Radiation by Season:")
    print("-" * 70)
    
    # Calculate for representative days
    seasons = [
        ("Winter Solstice", 355),  # Dec 21
        ("Spring Equinox", 80),    # Mar 21
        ("Summer Solstice", 172),  # Jun 21
        ("Fall Equinox", 264),     # Sep 21
    ]
    
    for season_name, day_of_year in seasons:
        theoretical_max = calculator.calculate_theoretical_solar_max(day_of_year)
        print(f"{season_name:20s} (Day {day_of_year:3d}): {theoretical_max:6.2f} MJ/m²/day")
    
    print("\n" + "=" * 70 + "\n")


def example_with_observed_solar():
    """Example 2: Calculate parameters with observed solar data."""
    print("=" * 70)
    print("Example 2: Parameters with Observed Solar Data")
    print("=" * 70)
    
    # Create synthetic observed data with solar radiation
    np.random.seed(42)
    
    start_date = date(2010, 1, 1)
    # Generate dates, skipping February 29th (leap years)
    dates = []
    current_date = start_date
    for _ in range(365 * 5):  # 5 years
        if not (current_date.month == 2 and current_date.day == 29):
            dates.append(current_date)
        current_date += timedelta(days=1)
    
    # Generate synthetic precipitation (wet/dry pattern)
    precip = np.random.gamma(2.0, 5.0, len(dates))
    precip[np.random.random(len(dates)) > 0.3] = 0.0  # 70% dry days
    
    # Generate synthetic solar radiation correlated with wet/dry
    latitude = 47.45
    calculator = SolarParameterCalculator(latitude=latitude)
    
    solar = []
    for i, d in enumerate(dates):
        # Calculate day of year for 365-day calendar (no leap days)
        day_of_year = (d - date(d.year, 1, 1)).days + 1
        # Adjust for leap years: if after Feb 29, subtract 1
        if d.year % 4 == 0 and (d.year % 100 != 0 or d.year % 400 == 0):
            if d.month > 2:
                day_of_year -= 1
        day_of_year = min(day_of_year, 365)  # Cap at 365
        theoretical = calculator.calculate_theoretical_solar_max(day_of_year)
        
        # Dry days get ~75% of theoretical, wet days get ~50%
        if precip[i] < 0.1:
            solar_value = theoretical * (0.75 + np.random.normal(0, 0.1))
        else:
            solar_value = theoretical * (0.50 + np.random.normal(0, 0.1))
        
        solar.append(max(0, min(solar_value, theoretical)))  # Constrain to [0, theoretical]
    
    # Create DataFrame
    df = pd.DataFrame({
        'date': dates,
        'precipitation_mm': precip,
        'solar_mjm2': solar
    })
    
    print(f"\nDataset: {len(dates)} days ({len(dates)/365:.1f} years)")
    print(f"Location: Latitude {latitude}°N")
    
    # Calculate parameters
    params = calculator.calculate_parameters(df, has_solar_data=True)
    
    print("\nCalculated Solar Parameters:")
    print("-" * 70)
    print("\nMonthly Mean Solar Radiation (MJ/m²/day):")
    print(f"{'Month':<10s} {'RMD (Dry)':<15s} {'RMW (Wet)':<15s}")
    print("-" * 70)
    
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    for i, month in enumerate(months):
        rmd = params['rmd'][i]
        rmw = params['rmw'][i]
        print(f"{month:<10s} {rmd:6.2f}          {rmw:6.2f}")
    
    print(f"\nFourier Series Amplitude (AR): {params['ar']:.2f} MJ/m²/day")
    print(f"Latitude: {params['latitude']:.2f}°")
    
    print("\n" + "=" * 70 + "\n")


def example_without_observed_solar():
    """Example 3: Estimate parameters without observed solar data."""
    print("=" * 70)
    print("Example 3: Parameters WITHOUT Observed Solar Data (Estimation)")
    print("=" * 70)
    
    # Create observed data WITHOUT solar radiation
    np.random.seed(42)
    
    start_date = date(2010, 1, 1)
    # Generate dates, skipping February 29th (leap years)
    dates = []
    current_date = start_date
    for _ in range(365 * 10):  # 10 years
        if not (current_date.month == 2 and current_date.day == 29):
            dates.append(current_date)
        current_date += timedelta(days=1)
    
    # Generate synthetic precipitation
    precip = np.random.gamma(2.0, 5.0, len(dates))
    precip[np.random.random(len(dates)) > 0.3] = 0.0  # 70% dry days
    
    # Create DataFrame (no solar column)
    df = pd.DataFrame({
        'date': dates,
        'precipitation_mm': precip
    })
    
    latitude = 47.45
    calculator = SolarParameterCalculator(latitude=latitude)
    
    print(f"\nDataset: {len(dates)} days ({len(dates)/365:.1f} years)")
    print(f"Location: Latitude {latitude}°N")
    print("\nNo observed solar data available - using estimation:")
    print("  RMD = 0.75 × theoretical_max (dry days)")
    print("  RMW = 0.50 × theoretical_max (wet days)")
    
    # Calculate parameters (estimation mode)
    params = calculator.calculate_parameters(df, has_solar_data=False)
    
    print("\nEstimated Solar Parameters:")
    print("-" * 70)
    print("\nMonthly Mean Solar Radiation (MJ/m²/day):")
    print(f"{'Month':<10s} {'RMD (Dry)':<15s} {'RMW (Wet)':<15s} {'Theoretical':<15s}")
    print("-" * 70)
    
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    for i, month in enumerate(months):
        rmd = params['rmd'][i]
        rmw = params['rmw'][i]
        
        # Get theoretical max for mid-month
        mid_month_day = calculator._get_mid_month_day(i + 1)
        theoretical = calculator.theoretical_max[mid_month_day - 1]
        
        print(f"{month:<10s} {rmd:6.2f}          {rmw:6.2f}          {theoretical:6.2f}")
    
    print(f"\nFourier Series Amplitude (AR): {params['ar']:.2f} MJ/m²/day")
    print(f"Latitude: {params['latitude']:.2f}°")
    
    print("\n" + "=" * 70 + "\n")


def example_physical_constraints():
    """Example 4: Demonstrate physical constraint enforcement."""
    print("=" * 70)
    print("Example 4: Physical Constraint Enforcement")
    print("=" * 70)
    
    # Create data with some unrealistic solar values
    np.random.seed(42)
    
    start_date = date(2015, 1, 1)
    # Generate dates, skipping February 29th (leap years)
    dates = []
    current_date = start_date
    for _ in range(365):
        if not (current_date.month == 2 and current_date.day == 29):
            dates.append(current_date)
        current_date += timedelta(days=1)
    
    latitude = 47.45
    calculator = SolarParameterCalculator(latitude=latitude)
    
    # Generate precipitation
    precip = np.random.gamma(2.0, 5.0, len(dates))
    precip[np.random.random(len(dates)) > 0.3] = 0.0
    
    # Generate solar with some values exceeding theoretical max
    solar = []
    for i, d in enumerate(dates):
        # Calculate day of year for 365-day calendar (no leap days)
        day_of_year = (d - date(d.year, 1, 1)).days + 1
        # Adjust for leap years: if after Feb 29, subtract 1
        if d.year % 4 == 0 and (d.year % 100 != 0 or d.year % 400 == 0):
            if d.month > 2:
                day_of_year -= 1
        day_of_year = min(day_of_year, 365)  # Cap at 365
        theoretical = calculator.calculate_theoretical_solar_max(day_of_year)
        
        # Intentionally create some values that exceed theoretical max
        if i % 50 == 0:
            # Every 50th day, create an unrealistic value
            solar_value = theoretical * 1.2  # 120% of theoretical max
        else:
            solar_value = theoretical * np.random.uniform(0.4, 0.8)
        
        solar.append(solar_value)
    
    df = pd.DataFrame({
        'date': dates,
        'precipitation_mm': precip,
        'solar_mjm2': solar
    })
    
    print(f"\nDataset: {len(dates)} days")
    print(f"Location: Latitude {latitude}°N")
    print("\nNote: Dataset contains some solar values exceeding theoretical maximum")
    print("      (simulating measurement errors or data quality issues)")
    
    # Calculate parameters - should enforce constraints
    print("\nCalculating parameters with physical constraint enforcement...")
    params = calculator.calculate_parameters(df, has_solar_data=True)
    
    print("\nPhysical constraints enforced:")
    print("  - All solar values capped at theoretical maximum")
    print("  - Warnings issued for values exceeding theoretical max")
    
    print("\n" + "=" * 70 + "\n")


def example_latitude_comparison():
    """Example 5: Compare solar radiation across different latitudes."""
    print("=" * 70)
    print("Example 5: Solar Radiation Across Different Latitudes")
    print("=" * 70)
    
    # Compare several locations
    locations = [
        ("Equator", 0.0),
        ("Miami, FL", 25.8),
        ("Seattle, WA", 47.6),
        ("Anchorage, AK", 61.2),
        ("Barrow, AK", 71.3),
    ]
    
    print("\nTheoretical Maximum Solar Radiation by Location and Season:")
    print("-" * 70)
    print(f"{'Location':<20s} {'Winter':<12s} {'Spring':<12s} {'Summer':<12s} {'Fall':<12s}")
    print("-" * 70)
    
    for location_name, latitude in locations:
        calculator = SolarParameterCalculator(latitude=latitude)
        
        # Calculate for solstices and equinoxes
        winter = calculator.calculate_theoretical_solar_max(355)  # Dec 21
        spring = calculator.calculate_theoretical_solar_max(80)   # Mar 21
        summer = calculator.calculate_theoretical_solar_max(172)  # Jun 21
        fall = calculator.calculate_theoretical_solar_max(264)    # Sep 21
        
        print(f"{location_name:<20s} {winter:6.2f}       {spring:6.2f}       "
              f"{summer:6.2f}       {fall:6.2f}")
    
    print("\nNote: Values in MJ/m²/day")
    print("      Higher latitudes show greater seasonal variation")
    print("      Polar regions can have zero solar in winter (polar night)")
    
    print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    print("\n")
    print("*" * 70)
    print("SOLAR RADIATION PARAMETER CALCULATOR EXAMPLES")
    print("*" * 70)
    print("\n")
    
    # Run all examples
    example_theoretical_max()
    example_with_observed_solar()
    example_without_observed_solar()
    example_physical_constraints()
    example_latitude_comparison()
    
    print("*" * 70)
    print("All examples completed successfully!")
    print("*" * 70)
    print("\n")
