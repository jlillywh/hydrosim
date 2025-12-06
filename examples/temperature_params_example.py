"""
Example demonstrating temperature parameter calculation for WGEN.

This script shows how to use the TemperatureParameterCalculator to generate
WGEN temperature parameters from observed climate data.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from hydrosim.climate_builder.temperature_params import TemperatureParameterCalculator


def create_sample_data():
    """Create sample observed climate data with seasonal patterns."""
    # Generate 5 years of daily data
    start_date = datetime(2015, 1, 1)
    dates = [start_date + timedelta(days=i) for i in range(5 * 365)]
    
    # Create seasonal temperature patterns
    day_of_year = np.array([d.timetuple().tm_yday for d in dates])
    
    # Maximum temperature: warm in summer (day 180), cold in winter
    # Mean around 20°C with 15°C amplitude
    tmax_base = 20 + 15 * np.cos(2 * np.pi * (day_of_year - 180) / 365)
    tmax = tmax_base + np.random.normal(0, 3, len(dates))
    
    # Minimum temperature: follows similar pattern but lower
    # Mean around 10°C with 10°C amplitude
    tmin_base = 10 + 10 * np.cos(2 * np.pi * (day_of_year - 180) / 365)
    tmin = tmin_base + np.random.normal(0, 2, len(dates))
    
    # Precipitation: random with seasonal variation
    # More precipitation in winter
    precip_prob = 0.3 + 0.2 * np.cos(2 * np.pi * (day_of_year - 0) / 365)
    is_wet = np.random.random(len(dates)) < precip_prob
    precip = np.where(is_wet, np.random.exponential(8, len(dates)), 0.0)
    
    # Create DataFrame
    df = pd.DataFrame({
        'date': dates,
        'precipitation_mm': precip,
        'tmax_c': tmax,
        'tmin_c': tmin
    })
    
    return df


def main():
    """Main example function."""
    print("=" * 70)
    print("Temperature Parameter Calculation Example")
    print("=" * 70)
    print()
    
    # Create sample data
    print("Creating sample observed climate data...")
    df = create_sample_data()
    print(f"  Data period: {df['date'].min().date()} to {df['date'].max().date()}")
    print(f"  Total days: {len(df)}")
    print()
    
    # Show sample of data
    print("Sample of observed data:")
    print(df.head(10).to_string(index=False))
    print()
    
    # Initialize calculator
    print("Initializing temperature parameter calculator...")
    calc = TemperatureParameterCalculator(wet_day_threshold=0.1, num_periods=13)
    print(f"  Wet day threshold: {calc.wet_day_threshold} mm")
    print(f"  Number of periods: {calc.num_periods}")
    print(f"  Days per period: {calc.days_per_period}")
    print()
    
    # Calculate parameters
    print("Calculating temperature parameters...")
    params = calc.calculate_parameters(df)
    print()
    
    # Display results
    print("=" * 70)
    print("CALCULATED TEMPERATURE PARAMETERS")
    print("=" * 70)
    print()
    
    print("Maximum Temperature (Dry Days):")
    print(f"  Mean (txmd):      {params['txmd']:.2f} °C")
    print(f"  Amplitude (atx):  {params['atx']:.2f} °C")
    print()
    
    print("Maximum Temperature (Wet Days):")
    print(f"  Mean (txmw):      {params['txmw']:.2f} °C")
    print()
    
    print("Minimum Temperature:")
    print(f"  Mean (tn):        {params['tn']:.2f} °C")
    print(f"  Amplitude (atn):  {params['atn']:.2f} °C")
    print()
    
    print("Coefficient of Variation (Maximum Temperature):")
    print(f"  Mean (cvtx):      {params['cvtx']:.4f}")
    print(f"  Amplitude (acvtx):{params['acvtx']:.4f}")
    print()
    
    print("Coefficient of Variation (Minimum Temperature):")
    print(f"  Mean (cvtn):      {params['cvtn']:.4f}")
    print(f"  Amplitude (acvtn):{params['acvtn']:.4f}")
    print()
    
    print("=" * 70)
    print()
    
    # Interpretation
    print("INTERPRETATION:")
    print()
    print("These parameters describe the seasonal temperature patterns:")
    print()
    print("1. Mean temperatures (txmd, txmw, tn):")
    print("   - Average temperature across the year")
    print(f"   - Dry days are typically warmer: {params['txmd']:.1f}°C vs {params['txmw']:.1f}°C")
    print()
    print("2. Amplitudes (atx, atn):")
    print("   - Seasonal variation in temperature")
    print(f"   - Tmax varies by ±{params['atx']:.1f}°C throughout the year")
    print(f"   - Tmin varies by ±{params['atn']:.1f}°C throughout the year")
    print()
    print("3. Coefficient of Variation (CV):")
    print("   - Day-to-day variability relative to mean")
    print(f"   - Tmax CV: {params['cvtx']:.2%} (std/mean)")
    print(f"   - Tmin CV: {params['cvtn']:.2%} (std/mean)")
    print()
    print("These parameters will be used by WGEN to generate synthetic")
    print("temperature sequences that match the observed statistical properties.")
    print()
    
    print("=" * 70)
    print("Example complete!")
    print("=" * 70)


if __name__ == '__main__':
    main()
