# Climate Builder Examples

This directory contains examples demonstrating how to use the Climate Builder module to acquire and process real climate data from NOAA's Global Historical Climatology Network (GHCN).

## Quick Start

### Fetch Real GHCN Data

The simplest way to get started is to run the complete fetch example:

```bash
python examples/climate_builder_fetch_example.py
```

This will:
1. Download real climate data from Seattle-Tacoma Airport
2. Parse and validate the data
3. Generate WGEN parameters
4. Save everything to `example_project/`

**Time required**: ~5-10 seconds (depending on internet speed)

## Available Examples

### 1. Complete Workflow: `climate_builder_fetch_example.py`
**Purpose**: End-to-end example with real GHCN data

Shows the complete workflow:
- Downloading .dly files from NOAA
- Parsing fixed-width format
- Data quality validation
- WGEN parameter generation
- Saving outputs

**Best for**: First-time users, understanding the full pipeline

### 2. Parameter Generation: `parameter_generator_example.py`
**Purpose**: Generate WGEN parameters from existing observed data

Shows how to:
- Use the WGENParameterGenerator
- Calculate precipitation, temperature, and solar parameters
- Save parameters to CSV

**Best for**: Users who already have observed climate data

### 3. Individual Components

- `precipitation_params_example.py` - Precipitation parameter calculation
- `temperature_params_example.py` - Temperature parameter calculation  
- `solar_params_example.py` - Solar radiation parameter calculation
- `data_quality_example.py` - Data quality validation

**Best for**: Understanding individual components, debugging

## Finding GHCN Stations

To use a different weather station:

1. **Find a station**: https://www.ncdc.noaa.gov/cdo-web/datatools/findstation
2. **Get the station ID**: 11-character code (e.g., `USW00024233`)
3. **Get the latitude**: Required for solar radiation calculations
4. **Update the example**: Modify `STATION_ID` and `LATITUDE` at the top of the script

### Popular Stations

| Location | Station ID | Latitude | Climate Type |
|----------|------------|----------|--------------|
| Seattle-Tacoma Airport, WA | USW00024233 | 47.45 | Maritime, rainy |
| Denver International Airport, CO | USW00023062 | 39.83 | Continental, dry |
| New York JFK Airport, NY | USW00014739 | 40.64 | Humid continental |
| Phoenix Sky Harbor Airport, AZ | USW00012960 | 33.43 | Hot desert |
| Honolulu International Airport, HI | USW00093134 | 21.32 | Tropical |

## Output Files

After running the fetch example, you'll have:

```
example_project/
├── data/
│   ├── raw/
│   │   └── USW00024233.dly              # Raw GHCN data
│   └── processed/
│       ├── observed_climate.csv         # Parsed climate data
│       ├── wgen_params.csv              # WGEN parameters
│       └── data_quality_report.txt      # Quality assessment
├── config/                              # (for YAML configs)
└── outputs/                             # (for simulation results)
```

## Using Generated Parameters

Once you have `wgen_params.csv`, you can use it in simulations:

### Option 1: YAML Configuration

```yaml
climate:
  source_type: wgen
  start_date: '2024-01-01'
  wgen_params_file: data/processed/wgen_params.csv
  site:
    latitude: 47.45
    elevation: 130.0
```

### Option 2: Python API

```python
from hydrosim.wgen_params import CSVWGENParamsParser
from hydrosim.wgen import WGENClimateSource

# Load parameters
params = CSVWGENParamsParser.parse('data/processed/wgen_params.csv')

# Create climate source
climate = WGENClimateSource(params, start_date='2024-01-01')

# Generate weather for a date
weather = climate.get_climate(date)
```

## Data Quality

The Climate Builder automatically validates data quality and generates a report. Check for:

- **Missing data**: Should be < 10% for reliable parameters
- **Dataset length**: Should be ≥ 10 years for stable statistics
- **Unrealistic values**: Extreme temperatures or negative precipitation
- **Tmax < Tmin**: Physical inconsistencies

Review `data_quality_report.txt` after processing.

## Troubleshooting

### "Station not found" error
- Verify the station ID is correct (11 characters)
- Check the station exists at: https://www.ncdc.noaa.gov/ghcn-daily-description
- Some stations may be discontinued

### "Insufficient data" warning
- Station may have gaps in the record
- Try a different station with more complete data
- Or accept the warning if you're okay with less reliable parameters

### Network errors
- Check your internet connection
- NOAA servers may be temporarily unavailable
- The script will reuse cached .dly files if they exist

### High missing data percentage
- Some stations have incomplete records
- Consider using a different station
- Or use data imputation techniques (not included in this module)

## Next Steps

After generating parameters:

1. **Review the quality report**: Check for any data issues
2. **Inspect the parameters**: Look at `wgen_params.csv`
3. **Run a simulation**: Use the parameters with WGEN
4. **Compare with observations**: Validate synthetic weather is realistic

See `examples/wgen_example.py` for simulation examples.

## Integration Tests

For developers, integration tests with real GHCN data are available:

```bash
# Run integration tests (downloads real data)
pytest -m integration

# Skip integration tests (default for CI)
pytest -m "not integration"
```

See `tests/test_climate_builder_integration.py` for details.

## References

- **GHCN Daily**: https://www.ncdc.noaa.gov/ghcn-daily-description
- **Station Finder**: https://www.ncdc.noaa.gov/cdo-web/datatools/findstation
- **WGEN Documentation**: Richardson & Wright (1984), USDA-ARS-8
- **Data Format**: https://www1.ncdc.noaa.gov/pub/data/ghcn/daily/readme.txt
