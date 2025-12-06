"""
Example: Fetch Real GHCN Climate Data and Generate Parameters

This example demonstrates the complete workflow for acquiring real climate data
from NOAA's Global Historical Climatology Network (GHCN) and generating WGEN
parameters for stochastic weather generation.

Workflow:
1. Download observed climate data from NOAA GHCN
2. Parse the .dly file format
3. Generate WGEN statistical parameters
4. Save parameters for use in simulations

This example uses real data from Seattle-Tacoma International Airport.

Usage:
    python examples/climate_builder_fetch_example.py

Requirements:
    - Internet connection (to download from NOAA)
    - ~5-10 seconds for download and processing
"""

from pathlib import Path
from hydrosim.climate_builder import (
    GHCNDataFetcher,
    WGENParameterGenerator,
    DataQualityValidator,
)

# ============================================================================
# Configuration
# ============================================================================

# GHCN Station Information
# Find stations at: https://www.ncdc.noaa.gov/cdo-web/datatools/findstation
STATION_ID = "USW00024233"  # Seattle-Tacoma International Airport
LATITUDE = 47.45  # Decimal degrees (required for solar calculations)
STATION_NAME = "Seattle-Tacoma Airport, WA"

# Output directory
PROJECT_DIR = Path("./example_project")

print("=" * 80)
print("Climate Builder: Fetch Real GHCN Data Example")
print("=" * 80)
print()
print(f"Station: {STATION_NAME}")
print(f"Station ID: {STATION_ID}")
print(f"Latitude: {LATITUDE}°")
print(f"Output Directory: {PROJECT_DIR}")
print()

# ============================================================================
# Step 1: Download GHCN Data
# ============================================================================

print("Step 1: Downloading GHCN Data")
print("-" * 80)

# Initialize the GHCN data fetcher
# This will create the project directory structure if it doesn't exist
fetcher = GHCNDataFetcher(STATION_ID, PROJECT_DIR)

print(f"Downloading .dly file from NOAA servers...")
print(f"URL: https://www1.ncdc.noaa.gov/pub/data/ghcn/daily/all/{STATION_ID}.dly")

# Download the .dly file
# If the file already exists, it will be reused (not re-downloaded)
dly_path = fetcher.download_dly_file()

print(f"✓ Downloaded to: {dly_path}")
print(f"  File size: {dly_path.stat().st_size:,} bytes")
print()

# ============================================================================
# Step 2: Parse .dly File
# ============================================================================

print("Step 2: Parsing .dly File")
print("-" * 80)

print("Extracting precipitation and temperature data...")
print("  - Converting units (tenths of mm/°C → mm/°C)")
print("  - Handling missing values (-9999 → NaN)")
print("  - Excluding February 29th (WGEN uses 365-day calendar)")

# Parse the fixed-width .dly format
df = fetcher.parse_dly_file(dly_path)

print(f"✓ Parsed {len(df):,} days of data")
print(f"  Date range: {df['date'].min()} to {df['date'].max()}")

# Calculate data period
date_range = df['date'].max() - df['date'].min()
years = date_range.days / 365.25
print(f"  Period: {years:.1f} years")

# Show data summary
print()
print("Data Summary:")
print(f"  Mean Precipitation: {df['precipitation_mm'].mean():.2f} mm/day")
print(f"  Mean Tmax: {df['tmax_c'].mean():.1f}°C")
print(f"  Mean Tmin: {df['tmin_c'].mean():.1f}°C")
print(f"  Missing Precip: {df['precipitation_mm'].isna().sum():,} days ({df['precipitation_mm'].isna().mean()*100:.1f}%)")
print(f"  Missing Tmax: {df['tmax_c'].isna().sum():,} days ({df['tmax_c'].isna().mean()*100:.1f}%)")
print(f"  Missing Tmin: {df['tmin_c'].isna().sum():,} days ({df['tmin_c'].isna().mean()*100:.1f}%)")
print()

# ============================================================================
# Step 3: Validate Data Quality
# ============================================================================

print("Step 3: Validating Data Quality")
print("-" * 80)

# Run data quality validation
validator = DataQualityValidator(df, station_id=STATION_ID)
report = validator.validate()

print(f"Data Quality Report:")
print(f"  Total days: {report.total_days:,}")
print(f"  Missing data: Precip {report.missing_precip_pct:.1f}%, "
      f"Tmax {report.missing_tmax_pct:.1f}%, Tmin {report.missing_tmin_pct:.1f}%")

if report.has_sufficient_data():
    print("  ✓ Data quality is sufficient (< 10% missing)")
else:
    print("  ⚠ Warning: High percentage of missing data")

if report.has_sufficient_length():
    print("  ✓ Dataset length is sufficient (>= 10 years)")
else:
    print("  ⚠ Warning: Dataset is relatively short (< 10 years)")

# Show warnings if any
if report.warnings:
    print()
    print("  Warnings:")
    for warning in report.warnings[:5]:  # Show first 5 warnings
        print(f"    - {warning}")
    if len(report.warnings) > 5:
        print(f"    ... and {len(report.warnings) - 5} more warnings")

# Save quality report
report_path = fetcher.project.get_data_quality_report_path()
validator.save_report(report, report_path)
print(f"\n  Report saved to: {report_path}")
print()

# ============================================================================
# Step 4: Save Observed Climate Data
# ============================================================================

print("Step 4: Saving Observed Climate Data")
print("-" * 80)

# Save to CSV in standard format
csv_path = fetcher.save_processed_data(df)

print(f"✓ Saved to: {csv_path}")
print(f"  Format: CSV with columns [date, precipitation_mm, tmax_c, tmin_c]")
print()

# ============================================================================
# Step 5: Generate WGEN Parameters
# ============================================================================

print("Step 5: Generating WGEN Parameters")
print("-" * 80)

print("Initializing parameter generator...")
generator = WGENParameterGenerator(
    observed_data_path=csv_path,
    latitude=LATITUDE,
    output_dir=PROJECT_DIR
)

print("Calculating statistical parameters:")
print("  - Precipitation: Markov chains (PWW, PWD) and Gamma distributions (Alpha, Beta)")
print("  - Temperature: Fourier series for seasonal patterns")
print("  - Solar: Theoretical maximum and estimated parameters")
print()

# Generate all parameters
# has_solar_data=False means we'll estimate solar parameters
params = generator.generate_all_parameters(has_solar_data=False)

print()
print("Parameter Summary:")
print("-" * 80)

# Show precipitation parameters for a few months
print("\nPrecipitation Parameters (sample months):")
print("  Month  |  PWW   |  PWD   |  Alpha  |  Beta")
print("  " + "-" * 50)
month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
               'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
for i in [0, 3, 6, 9]:  # Show Jan, Apr, Jul, Oct
    print(f"  {month_names[i]:5s}  | {params['pww'][i]:6.3f} | {params['pwd'][i]:6.3f} | "
          f"{params['alpha'][i]:7.3f} | {params['beta'][i]:6.3f}")

# Show temperature parameters
print("\nTemperature Parameters:")
print(f"  Tmax dry mean (txmd):     {params['txmd']:7.2f}°C")
print(f"  Tmax dry amplitude (atx): {params['atx']:7.2f}°C")
print(f"  Tmax wet mean (txmw):     {params['txmw']:7.2f}°C")
print(f"  Tmin mean (tn):           {params['tn']:7.2f}°C")
print(f"  Tmin amplitude (atn):     {params['atn']:7.2f}°C")

# Show solar parameters (monthly values averaged to annual)
import numpy as np
print("\nSolar Radiation Parameters:")
print(f"  Mean RMD (dry days):      {np.mean(params['rmd']):7.2f} MJ/m²/day")
print(f"  Mean RMW (wet days):      {np.mean(params['rmw']):7.2f} MJ/m²/day")
print(f"  Amplitude (AR):           {params['ar']:7.2f} MJ/m²/day")

print()

# ============================================================================
# Step 6: Save Parameters to CSV
# ============================================================================

print("Step 6: Saving Parameters to CSV")
print("-" * 80)

# Save parameters in format compatible with WGEN
params_csv = generator.save_parameters_to_csv(params)

print(f"✓ Parameters saved to: {params_csv}")
print()

# ============================================================================
# Summary
# ============================================================================

print("=" * 80)
print("SUCCESS! Climate data acquired and parameters generated")
print("=" * 80)
print()
print("Generated Files:")
print(f"  1. Raw data:        {dly_path}")
print(f"  2. Observed data:   {csv_path}")
print(f"  3. Quality report:  {report_path}")
print(f"  4. WGEN parameters: {params_csv}")
print()
print("Next Steps:")
print("  1. Review the data quality report for any issues")
print("  2. Inspect the generated parameters in the CSV file")
print("  3. Use these parameters in a WGEN simulation")
print("  4. See 'examples/wgen_example.py' for simulation usage")
print()
print("To use these parameters in a YAML configuration:")
print()
print("  climate:")
print("    source_type: wgen")
print("    start_date: '2024-01-01'")
print(f"    wgen_params_file: {params_csv.relative_to(PROJECT_DIR)}")
print("    site:")
print(f"      latitude: {LATITUDE}")
print("      elevation: 130.0  # meters")
print()
print("=" * 80)
print()

# ============================================================================
# Optional: Try a different station
# ============================================================================

print("Want to try a different station?")
print()
print("Popular GHCN stations:")
print("  - USW00023062: Denver International Airport, CO (lat: 39.83)")
print("  - USW00014739: New York JFK Airport, NY (lat: 40.64)")
print("  - USW00012960: Phoenix Sky Harbor Airport, AZ (lat: 33.43)")
print("  - USW00093134: Honolulu International Airport, HI (lat: 21.32)")
print()
print("Find more stations at:")
print("  https://www.ncdc.noaa.gov/cdo-web/datatools/findstation")
print()
print("To use a different station, modify the configuration at the top of this file:")
print("  STATION_ID = 'USW00023062'  # Your station ID")
print("  LATITUDE = 39.83            # Your station latitude")
print()
