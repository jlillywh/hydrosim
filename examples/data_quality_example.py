"""
Example: Data Quality Validation

This example demonstrates how to use the DataQualityValidator to assess
the quality of observed climate data.

The validator checks for:
- Missing data (percentage of NaN values)
- Physically unrealistic values
- Dataset length (<10 years warning)

It generates a detailed report that can be saved to a text file.
"""

import pandas as pd
from pathlib import Path
from hydrosim.climate_builder import DataQualityValidator, ProjectStructure

# Example 1: Validate data from a CSV file
# ==========================================

# Load observed climate data
observed_data_path = Path("data/processed/observed_climate.csv")
if observed_data_path.exists():
    df = pd.read_csv(observed_data_path, parse_dates=['date'])
    
    # Create validator
    validator = DataQualityValidator(df, station_id="USW00024233")
    
    # Run validation
    report = validator.validate()
    
    # Check results
    print(f"Station: {report.station_id}")
    print(f"Data Period: {report.data_period_start} to {report.data_period_end}")
    print(f"Total Days: {report.total_days}")
    print(f"Missing Precipitation: {report.missing_precip_pct:.1f}%")
    print(f"Missing Tmax: {report.missing_tmax_pct:.1f}%")
    print(f"Missing Tmin: {report.missing_tmin_pct:.1f}%")
    
    # Check data quality
    if report.has_sufficient_data():
        print("✓ Data quality is sufficient (< 10% missing)")
    else:
        print("⚠ High percentage of missing data")
    
    if report.has_sufficient_length():
        print("✓ Dataset length is sufficient (>= 10 years)")
    else:
        print("⚠ Dataset is relatively short")
    
    # Print warnings
    if report.warnings:
        print("\nWarnings:")
        for warning in report.warnings:
            print(f"  - {warning}")
    
    # Save report to file
    project = ProjectStructure(".")
    report_path = project.get_data_quality_report_path()
    validator.save_report(report, report_path)
    print(f"\nReport saved to: {report_path}")


# Example 2: Validate data using convenience method
# ==================================================

if observed_data_path.exists():
    df = pd.read_csv(observed_data_path, parse_dates=['date'])
    
    # Validate and save in one call
    project = ProjectStructure(".")
    report_path = project.get_data_quality_report_path()
    
    report = DataQualityValidator.validate_and_save(
        df,
        report_path,
        station_id="USW00024233"
    )
    
    print(f"\nValidation complete. Report saved to: {report_path}")


# Example 3: Create sample data with quality issues
# ==================================================

print("\n" + "="*70)
print("Example with synthetic data containing quality issues")
print("="*70)

# Create sample data with various quality issues
dates = pd.date_range('2015-01-01', '2019-12-31', freq='D')
sample_data = pd.DataFrame({
    'date': dates,
    'precipitation_mm': [5.0] * len(dates),
    'tmax_c': [20.0] * len(dates),
    'tmin_c': [10.0] * len(dates),
})

# Add some missing values (15%)
sample_data.loc[::7, 'precipitation_mm'] = None

# Add an unrealistic value
sample_data.loc[100, 'tmax_c'] = -150.0  # Extreme temperature

# Add tmax < tmin issue
sample_data.loc[200, 'tmax_c'] = 5.0
sample_data.loc[200, 'tmin_c'] = 15.0

# Validate
validator = DataQualityValidator(sample_data, station_id="SAMPLE001")
report = validator.validate()

# Print report
print(report.to_text_report())

# Check specific issues
print(f"\nFound {len(report.unrealistic_values)} days with unrealistic values")
if report.unrealistic_values:
    print("First few issues:")
    for item in report.unrealistic_values[:3]:
        print(f"  {item['date']}: {', '.join(item['issues'])}")
