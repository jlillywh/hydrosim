# Design Document: Climate Data Acquisition & Parameterization Module

## Overview

The Climate Data Acquisition & Parameterization Module transforms HydroSim into a "batteries included" modeling workbench by providing automated tools for acquiring, processing, and parameterizing climate data. The module consists of three integrated components:

1. **GHCN Data Fetcher**: Downloads and parses observed climate data from NOAA's Global Historical Climatology Network
2. **WGEN Parameter Generator**: Calculates statistical parameters from observed data using algorithms ported from the legacy `wgenpar.f` FORTRAN code
3. **Simulation Driver**: Enforces consistency rules and provides climate data to simulations in two modes (Historical and Stochastic)

The design philosophy emphasizes rigid consistency: users cannot mix observed precipitation with synthetic temperature (or vice versa), and solar radiation is always generated synthetically due to the scarcity of observed solar data. This ensures physical validity and prevents common configuration errors.

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Climate Builder CLI                       │
│                  (User-facing interface)                     │
└────────────┬────────────────────────────────────────────────┘
             │
             ├──────────────────────────────────────────────────┐
             │                                                   │
             v                                                   v
┌────────────────────────┐                    ┌─────────────────────────────┐
│   GHCN Data Fetcher    │                    │  WGEN Parameter Generator   │
│                        │                    │                             │
│  - HTTP Downloader     │                    │  - Precipitation Analyzer   │
│  - DLY Parser          │                    │  - Temperature Analyzer     │
│  - Data Validator      │                    │  - Solar Analyzer           │
└────────────┬───────────┘                    └──────────┬──────────────────┘
             │                                           │
             │ observed_climate.csv                      │ wgen_params.csv
             │                                           │
             └───────────────────┬───────────────────────┘
                                 │
                                 v
                    ┌────────────────────────┐
                    │  Simulation Driver     │
                    │                        │
                    │  - Mode A (Historical) │
                    │  - Mode B (Stochastic) │
                    │  - Consistency Checker │
                    └────────────────────────┘
                                 │
                                 v
                    ┌────────────────────────┐
                    │   HydroSim Engine      │
                    └────────────────────────┘
```

### Data Flow

1. **Data Acquisition Phase**:
   - User provides Station ID and Latitude
   - CLI downloads `.dly` file from NOAA
   - Parser extracts Precip, Tmax, Tmin (skips Feb 29)
   - Outputs `data/raw/*.dly` and `data/processed/observed_climate.csv`

2. **Parameterization Phase**:
   - Parameter Generator reads `observed_climate.csv`
   - Calculates monthly Markov chains for precipitation
   - Fits Gamma distributions to wet day amounts
   - Computes Fourier series for temperature patterns
   - Calculates or estimates solar radiation parameters
   - Outputs `data/processed/wgen_params.csv`

3. **Simulation Phase**:
   - User configures YAML with mode (historical/stochastic)
   - Simulation Driver validates configuration
   - Mode A: Reads observed P/T, generates synthetic Solar
   - Mode B: Generates all variables synthetically
   - Provides daily climate data to HydroSim engine

## Components and Interfaces

### 1. GHCN Data Fetcher

**Purpose**: Download and parse observed climate data from NOAA GHCN stations.

**Public Interface**:
```python
class GHCNDataFetcher:
    def __init__(self, station_id: str, output_dir: Path):
        """Initialize fetcher with station ID and output directory."""
        
    def download_dly_file(self) -> Path:
        """Download .dly file from NOAA servers.
        
        Returns:
            Path to downloaded .dly file in data/raw/
            
        Raises:
            HTTPError: If station not found or download fails
        """
        
    def parse_dly_file(self, dly_path: Path) -> pd.DataFrame:
        """Parse GHCN fixed-width .dly format.
        
        Args:
            dly_path: Path to .dly file
            
        Returns:
            DataFrame with columns: date, precipitation_mm, tmax_c, tmin_c
            Missing values represented as NaN
            February 29th excluded
            
        Raises:
            ValueError: If file format is invalid
        """
        
    def save_processed_data(self, df: pd.DataFrame) -> Path:
        """Save processed data to CSV.
        
        Args:
            df: Processed climate data
            
        Returns:
            Path to data/processed/observed_climate.csv
        """
```

**Implementation Notes**:
- Use `requests` library for HTTP downloads
- NOAA URL pattern: `https://www1.ncdc.noaa.gov/pub/data/ghcn/daily/all/{STATION_ID}.dly`
- DLY format is fixed-width: positions 0-11 (station), 11-15 (year), 15-17 (month), 17-21 (element)
- Daily values start at position 21, 8 characters per day
- Convert tenths of mm/°C to mm/°C
- Missing value flag: -9999
- Skip February 29th to maintain 365-day calendar

### 2. WGEN Parameter Generator

**Purpose**: Calculate WGEN statistical parameters from observed climate data using algorithms from `wgenpar.f`.

**Public Interface**:
```python
class WGENParameterGenerator:
    def __init__(self, observed_data_path: Path, latitude: float, output_dir: Path):
        """Initialize generator with observed data and site latitude."""
        
    def generate_all_parameters(self) -> Dict[str, Any]:
        """Generate all WGEN parameters.
        
        Returns:
            Dictionary containing:
                - Monthly precipitation params: pww, pwd, alpha, beta (12 values each)
                - Temperature params: txmd, atx, txmw, tn, atn, cvtx, acvtx, cvtn, acvtn
                - Solar params: rmd, ar, rmw
                - Location: latitude
                
        Raises:
            ValueError: If insufficient data for parameter estimation
        """
        
    def calculate_precipitation_params(self, df: pd.DataFrame) -> Dict[str, List[float]]:
        """Calculate monthly Markov chain and Gamma parameters.
        
        Uses wet day threshold of 0.1 mm (WMO standard).
        
        Returns:
            Dict with keys: pww, pwd, alpha, beta (12 values each)
        """
        
    def calculate_temperature_params(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate temperature Fourier series parameters.
        
        Uses 13-period Fourier series for seasonal smoothing.
        Calculates separate statistics for wet and dry days.
        
        Returns:
            Dict with keys: txmd, atx, txmw, tn, atn, cvtx, acvtx, cvtn, acvtn
        """
        
    def calculate_solar_params(self, df: pd.DataFrame, has_solar_data: bool) -> Dict[str, float]:
        """Calculate or estimate solar radiation parameters.
        
        Args:
            df: Observed data (may or may not include solar column)
            has_solar_data: Whether observed solar data is available
            
        Returns:
            Dict with keys: rmd, ar, rmw
            
        Note:
            If has_solar_data=False, estimates RMD=0.75*theoretical_max, RMW=0.50*theoretical_max
        """
        
    def calculate_theoretical_solar_max(self, day_of_year: int) -> float:
        """Calculate theoretical maximum solar radiation for a day.
        
        Uses latitude-based solar geometry from wgenpar.f.
        
        CRITICAL: Returns MJ/m²/day (not Langleys).
        Solar constant coefficient: 37.6 MJ/m²/day (not 889 Langleys).
        
        Args:
            day_of_year: Day of year (1-365)
            
        Returns:
            Theoretical max solar radiation in MJ/m²/day
        """
        
    def save_parameters_to_csv(self, params: Dict[str, Any]) -> Path:
        """Save parameters to CSV file.
        
        Returns:
            Path to data/processed/wgen_params.csv
        """
```

**Implementation Notes - Precipitation**:
- Wet day threshold: 0.1 mm (WMO standard)
- Markov chain: Count transitions (WW, WD, DW, DD) by month
- PWW = NWW / (NWW + NDW)
- PWD = NWD / (NWD + NDD)
- Gamma fitting: Use method of moments or maximum likelihood
- Alpha (shape) and Beta (scale) parameters for each month
- Warn if month has < 10 wet days

**Implementation Notes - Temperature**:
- Divide year into 13 periods of 28 days each
- Calculate mean and std dev for each period, separately for wet/dry days
- Fit 13-period Fourier series: T = mean + amplitude * cos(2π(period-peak)/13)
- Extract Fourier coefficients: mean, amplitude, phase
- Calculate coefficient of variation (CV = std/mean)
- Tmax has separate parameters for wet (txmw) and dry (txmd) days
- Tmin uses combined wet/dry statistics

**Implementation Notes - Solar**:
- Theoretical max calculation (from wgenpar.f, converted to MJ/m²/day):
  ```python
  # Convert latitude to radians
  xlat = latitude * 2 * np.pi / 360
  
  # Solar declination
  sd = 0.4102 * np.sin(0.0172 * (day_of_year - 80.25))
  
  # Hour angle
  ch = -np.tan(xlat) * np.tan(sd)
  if ch > 1.0:
      h = 0.0
  elif ch < -1.0:
      h = np.pi
  else:
      h = np.arccos(ch)
  
  # Earth-sun distance factor
  dd = 1.0 + 0.0335 * np.sin(0.0172 * (day_of_year + 88.2))
  
  # Solar radiation (MJ/m²/day, not Langleys!)
  # Original FORTRAN used 889.2305 for Langleys
  # Conversion: 1 Langley = 0.04184 MJ/m²
  # Therefore: 889.2305 * 0.04184 ≈ 37.2 MJ/m²/day
  solar_constant = 37.2  # MJ/m²/day
  
  rc = solar_constant * dd * (
      (h * np.sin(xlat) * np.sin(sd)) + 
      (np.cos(xlat) * np.cos(sd) * np.sin(h))
  )
  
  # Apply atmospheric attenuation factor
  rc = rc * 0.80
  ```
- If observed solar data available: Calculate RMD (dry days) and RMW (wet days) by month
- If no observed solar: Estimate RMD = 0.75 * theoretical_max, RMW = 0.50 * theoretical_max
- Fit 13-period Fourier series to monthly means
- Extract amplitude (AR) parameter

### 3. Simulation Driver

**Purpose**: Provide climate data to simulations while enforcing consistency rules.

**Public Interface**:
```python
class ClimateSimulationDriver:
    def __init__(self, config: Dict[str, Any]):
        """Initialize driver from YAML configuration.
        
        Args:
            config: Climate section from YAML with keys:
                - mode: "historical" or "stochastic"
                - observed_data_file: Path (Mode A only)
                - wgen_params_file: Path (both modes)
                - latitude: float (both modes)
                - random_seed: int (Mode B only, optional)
                
        Raises:
            ValueError: If configuration is invalid or inconsistent
        """
        
    def validate_configuration(self) -> None:
        """Validate configuration for consistency.
        
        Raises:
            ValueError: If configuration violates consistency rules
        """
        
    def get_climate_for_date(self, date: datetime.date) -> ClimateData:
        """Get climate data for a specific date.
        
        Args:
            date: Simulation date
            
        Returns:
            ClimateData with fields:
                - precipitation_mm: float
                - tmax_c: float
                - tmin_c: float
                - solar_mjm2: float
                
        Raises:
            ValueError: If date is outside available data range (Mode A)
        """
```

**Mode A (Historical) Implementation**:
```python
class HistoricalClimateDriver(ClimateSimulationDriver):
    def __init__(self, observed_data: pd.DataFrame, wgen_params: WGENParams, latitude: float):
        """Initialize with observed data and WGEN parameters."""
        self.observed_data = observed_data
        self.wgen_params = wgen_params
        self.wgen_state = WGENState(current_date=None)
        
    def get_climate_for_date(self, date: datetime.date) -> ClimateData:
        """Get climate for date.
        
        - Reads precipitation and temperature from observed_data
        - Generates solar radiation using WGEN, correlated with observed wet/dry status
        """
        # Look up observed data
        obs = self.observed_data.loc[date]
        
        # Determine wet/dry status from observed precipitation
        is_wet = obs['precipitation_mm'] >= 0.1
        
        # Generate synthetic solar radiation correlated with wet/dry status
        solar = self._generate_solar(date, is_wet)
        
        return ClimateData(
            precipitation_mm=obs['precipitation_mm'],
            tmax_c=obs['tmax_c'],
            tmin_c=obs['tmin_c'],
            solar_mjm2=solar
        )
```

**Mode B (Stochastic) Implementation**:
```python
class StochasticClimateDriver(ClimateSimulationDriver):
    def __init__(self, wgen_params: WGENParams, start_date: datetime.date):
        """Initialize with WGEN parameters and start date."""
        self.wgen_params = wgen_params
        self.wgen_state = WGENState(
            is_wet=False,
            current_date=start_date
        )
        
    def get_climate_for_date(self, date: datetime.date) -> ClimateData:
        """Get climate for date.
        
        - Generates all variables (P, Tmax, Tmin, Solar) using WGEN
        """
        # Generate synthetic weather
        self.wgen_state, outputs = wgen_step(self.wgen_params, self.wgen_state)
        
        return ClimateData(
            precipitation_mm=outputs.precip_mm,
            tmax_c=outputs.tmax_c,
            tmin_c=outputs.tmin_c,
            solar_mjm2=outputs.solar_mjm2
        )
```

**Consistency Validation**:
```python
def validate_configuration(config: Dict[str, Any]) -> None:
    """Validate climate configuration for consistency.
    
    Rules:
    1. Mode must be "historical" or "stochastic"
    2. Mode A requires: observed_data_file, wgen_params_file, latitude
    3. Mode B requires: wgen_params_file, latitude
    4. Cannot specify observed data for some variables and synthetic for others
    5. Solar radiation is always synthetic (no observed_solar_file allowed)
    """
    mode = config.get('mode')
    
    if mode not in ['historical', 'stochastic']:
        raise ValueError(f"Invalid mode: {mode}. Must be 'historical' or 'stochastic'")
    
    if mode == 'historical':
        required = ['observed_data_file', 'wgen_params_file', 'latitude']
        missing = [f for f in required if f not in config]
        if missing:
            raise ValueError(f"Mode A (historical) requires: {', '.join(missing)}")
            
    elif mode == 'stochastic':
        required = ['wgen_params_file', 'latitude']
        missing = [f for f in required if f not in config]
        if missing:
            raise ValueError(f"Mode B (stochastic) requires: {', '.join(missing)}")
    
    # Reject any attempt to specify observed solar data
    if 'observed_solar_file' in config:
        raise ValueError(
            "Observed solar radiation is not supported. "
            "Solar radiation is always generated synthetically using WGEN algorithms."
        )
    
    # Reject mixing observed and synthetic for P/T
    has_observed = 'observed_data_file' in config
    has_synthetic_precip = config.get('synthetic_precip', False)
    has_synthetic_temp = config.get('synthetic_temp', False)
    
    if has_observed and (has_synthetic_precip or has_synthetic_temp):
        raise ValueError(
            "Cannot mix observed and synthetic climate data. "
            "Use mode='historical' for observed P/T with synthetic Solar, "
            "or mode='stochastic' for fully synthetic climate."
        )
```

### 4. Command-Line Interface

**Purpose**: Provide simple CLI for data acquisition and parameter generation.

**Interface**:
```bash
# Fetch data and generate parameters
hydrosim-climate-builder fetch --station-id USW00024233 --latitude 47.45 --output-dir ./my_project

# Create project structure only
hydrosim-climate-builder init --output-dir ./my_project

# Generate parameters from existing observed data
hydrosim-climate-builder generate-params --observed-data ./data/processed/observed_climate.csv --latitude 47.45 --output-dir ./my_project
```

**Implementation**:
```python
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(
        description="HydroSim Climate Data Acquisition & Parameterization Tool"
    )
    
    subparsers = parser.add_subparsers(dest='command')
    
    # Fetch command
    fetch_parser = subparsers.add_parser('fetch', help='Fetch GHCN data and generate parameters')
    fetch_parser.add_argument('--station-id', required=True, help='NOAA GHCN station ID')
    fetch_parser.add_argument('--latitude', type=float, required=True, help='Site latitude in decimal degrees')
    fetch_parser.add_argument('--output-dir', default='.', help='Project directory (default: current directory)')
    
    # Init command
    init_parser = subparsers.add_parser('init', help='Initialize project directory structure')
    init_parser.add_argument('--output-dir', default='.', help='Project directory (default: current directory)')
    
    # Generate params command
    gen_parser = subparsers.add_parser('generate-params', help='Generate WGEN parameters from observed data')
    gen_parser.add_argument('--observed-data', required=True, help='Path to observed_climate.csv')
    gen_parser.add_argument('--latitude', type=float, required=True, help='Site latitude in decimal degrees')
    gen_parser.add_argument('--output-dir', default='.', help='Project directory (default: current directory)')
    
    args = parser.parse_args()
    
    if args.command == 'fetch':
        fetch_and_generate(args.station_id, args.latitude, Path(args.output_dir))
    elif args.command == 'init':
        initialize_project_structure(Path(args.output_dir))
    elif args.command == 'generate-params':
        generate_parameters(Path(args.observed_data), args.latitude, Path(args.output_dir))
    else:
        parser.print_help()
```

## Data Models

### Observed Climate Data CSV

**File**: `data/processed/observed_climate.csv`

**Format**:
```csv
date,precipitation_mm,tmax_c,tmin_c
2010-01-01,5.2,12.3,4.5
2010-01-02,0.0,14.1,5.2
2010-01-03,2.1,11.8,6.3
...
```

**Schema**:
- `date`: ISO 8601 date string (YYYY-MM-DD)
- `precipitation_mm`: Daily precipitation in millimeters (float, >= 0, NaN for missing)
- `tmax_c`: Daily maximum temperature in degrees Celsius (float, NaN for missing)
- `tmin_c`: Daily minimum temperature in degrees Celsius (float, NaN for missing)

**Constraints**:
- No February 29th dates (365-day calendar)
- Date range determined by available GHCN data
- Missing values represented as NaN (not -9999)

### WGEN Parameters CSV

**File**: `data/processed/wgen_params.csv`

**Format**:
```csv
month,pww,pwd,alpha,beta
jan,0.45,0.25,1.2,8.5
feb,0.42,0.23,1.1,7.8
...
dec,0.48,0.27,1.3,9.2

parameter,value
txmd,20.0
atx,10.0
txmw,18.0
tn,10.0
atn,8.0
cvtx,0.1
acvtx,0.05
cvtn,0.1
acvtn,0.05

parameter,value
rmd,15.0
ar,5.0
rmw,12.0

parameter,value
latitude,47.45
random_seed,42
```

**Schema**:
- **Monthly Parameters Section**: 12 rows with columns month, pww, pwd, alpha, beta
- **Temperature Parameters Section**: 9 rows with columns parameter, value
- **Radiation Parameters Section**: 3 rows with columns parameter, value
- **Location Parameters Section**: 2 rows with columns parameter, value

**Compatibility**: This format is compatible with the existing `CSVWGENParamsParser` in `hydrosim/wgen_params.py`.

### YAML Configuration Schema

**Mode A (Historical)**:
```yaml
climate:
  mode: historical
  observed_data_file: data/processed/observed_climate.csv
  wgen_params_file: data/processed/wgen_params.csv
  latitude: 47.45
```

**Mode B (Stochastic)**:
```yaml
climate:
  mode: stochastic
  wgen_params_file: data/processed/wgen_params.csv
  latitude: 47.45
  random_seed: 42  # Optional
```

### Project Directory Structure

```
my_project/
├── config/
│   └── simulation.yaml
├── data/
│   ├── raw/
│   │   └── USW00024233.dly
│   └── processed/
│       ├── observed_climate.csv
│       ├── wgen_params.csv
│       └── data_quality_report.txt
└── outputs/
    └── (simulation results)
```

## 
Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

Based on the requirements analysis, the following correctness properties must hold for the Climate Builder system:

### Data Acquisition Properties

**Property 1: Invalid station ID rejection**
*For any* string that does not match GHCN station ID format, the fetcher should raise a clear error indicating the station could not be found.
**Validates: Requirements 1.3, 1.5**

**Property 2: Unit conversion consistency**
*For any* valid .dly file, all precipitation values should be converted from tenths of millimeters to millimeters, and all temperature values should be converted from tenths of degrees Celsius to degrees Celsius.
**Validates: Requirements 2.1, 2.2, 2.3**

**Property 3: Missing value handling**
*For any* .dly file containing -9999 flags, all such values should be represented as NaN in the output CSV.
**Validates: Requirements 2.4**

**Property 4: Invalid date handling**
*For any* .dly file containing invalid dates (including February 30, April 31, etc.), the parser should skip those records and continue processing valid records.
**Validates: Requirements 2.6**

**Property 5: Output schema consistency**
*For any* successfully parsed .dly file, the output CSV should contain exactly four columns: date, precipitation_mm, tmax_c, tmin_c.
**Validates: Requirements 2.7**

**Property 6: File placement consistency**
*For any* successful data fetch operation, raw .dly files should be placed in data/raw/ and processed CSV files should be placed in data/processed/.
**Validates: Requirements 7.5, 7.6**

### Parameter Generation Properties

**Property 7: Monthly parameter completeness**
*For any* observed climate dataset, precipitation parameter generation should produce exactly 12 values each for PWW, PWD, Alpha, and Beta.
**Validates: Requirements 3.1, 3.5, 3.6**

**Property 8: Wet day classification**
*For any* precipitation value, days with precipitation >= 0.1 mm should be classified as wet, and days with precipitation < 0.1 mm should be classified as dry.
**Validates: Requirements 3.2**

**Property 9: Markov chain calculation**
*For any* observed wet/dry sequence, PWW should equal NWW/(NWW+NDW) and PWD should equal NWD/(NWD+NDD), where NWW, NDW, NWD, NDD are transition counts.
**Validates: Requirements 3.3, 3.4**

**Property 10: Temperature Fourier completeness**
*For any* observed temperature dataset, Fourier parameter generation should produce mean, amplitude, and phase coefficients for both maximum and minimum temperatures.
**Validates: Requirements 4.1, 4.2, 4.3**

**Property 11: Wet/dry temperature separation**
*For any* observed dataset, maximum temperature parameters should be calculated separately for wet days (txmw) and dry days (txmd), while minimum temperature should use combined statistics.
**Validates: Requirements 4.4**

**Property 12: Temperature correlation parameters**
*For any* observed dataset, temperature parameter generation should produce coefficient of variation (CV) parameters for both maximum and minimum temperatures.
**Validates: Requirements 4.5**

**Property 13: Solar theoretical maximum**
*For any* latitude and day of year, the calculated theoretical maximum solar radiation should be non-negative and should follow the solar geometry equations from wgenpar.f.
**Validates: Requirements 5.1, 5.2**

**Property 14: Solar parameter estimation**
*For any* dataset without observed solar data, RMD should be estimated as 0.75 times theoretical maximum and RMW should be estimated as 0.50 times theoretical maximum for each month.
**Validates: Requirements 5.5**

**Property 15: Solar physical constraint**
*For any* calculated or observed solar radiation value, it should not exceed the theoretical maximum solar radiation for the given latitude and date.
**Validates: Requirements 5.7**

**Property 16: Parameter CSV schema**
*For any* generated parameter file, it should contain all required sections: monthly precipitation parameters (12 rows), temperature parameters (9 rows), radiation parameters (3 rows), and location parameters (2 rows).
**Validates: Requirements 6.2, 6.3, 6.4, 6.5**

**Property 17: Parameter CSV round-trip**
*For any* generated wgen_params.csv file, it should be parseable by the existing CSVWGENParamsParser without errors, and the parsed parameters should match the generated values.
**Validates: Requirements 6.7, 15.1**

### Simulation Driver Properties

**Property 18: Mode A solar generation**
*For any* date in Mode A (Historical), solar radiation should be generated synthetically using WGEN algorithms, not read from observed data.
**Validates: Requirements 8.3**

**Property 19: Mode A wet/dry correlation**
*For any* date in Mode A, generated solar radiation should correlate with observed wet/dry status, with dry days having higher mean solar than wet days.
**Validates: Requirements 8.4**

**Property 20: Mode A missing date error**
*For any* date in the simulation period that is missing from observed data, Mode A should raise an error indicating the data gap.
**Validates: Requirements 8.5**

**Property 21: Mode B Markov chain**
*For any* long stochastic sequence in Mode B, the observed transition probabilities (PWW, PWD) should converge to the specified parameter values.
**Validates: Requirements 9.3**

**Property 22: Mode B Gamma distribution**
*For any* long stochastic sequence in Mode B, precipitation amounts on wet days should follow the specified Gamma distribution (Alpha, Beta).
**Validates: Requirements 9.4**

**Property 23: Mode B seasonal patterns**
*For any* long stochastic sequence in Mode B, temperatures and solar radiation should exhibit seasonal patterns consistent with the Fourier series parameters.
**Validates: Requirements 9.5, 9.6**

**Property 24: Configuration mixing rejection**
*For any* YAML configuration that attempts to mix observed precipitation with synthetic temperature (or vice versa), the validation should reject the configuration with a clear error.
**Validates: Requirements 10.1, 10.2**

**Property 25: Observed solar rejection**
*For any* YAML configuration that specifies an observed_solar_file field, the validation should reject the configuration with an error explaining that solar is always synthetic.
**Validates: Requirements 10.5**

**Property 26: Solar always synthetic**
*For any* simulation (Mode A or Mode B), solar radiation should always be generated synthetically, never read from observed data files.
**Validates: Requirements 10.6**

**Property 27: Mode validation**
*For any* YAML configuration with mode field, only values "historical" and "stochastic" should be accepted; all other values should be rejected.
**Validates: Requirements 11.1**

**Property 28: Mode A required fields**
*For any* YAML configuration with mode="historical", the fields observed_data_file, wgen_params_file, and latitude must be present, or validation should fail.
**Validates: Requirements 11.2, 11.3, 11.4**

**Property 29: Mode B required fields**
*For any* YAML configuration with mode="stochastic", the fields wgen_params_file and latitude must be present, or validation should fail.
**Validates: Requirements 11.5, 11.6**

**Property 30: Path resolution**
*For any* relative file path in YAML configuration, it should be resolved relative to the configuration file's directory, not the current working directory.
**Validates: Requirements 11.9**

### Data Quality Properties

**Property 31: Missing data reporting**
*For any* observed dataset, the percentage of missing values should be calculated for each variable (precipitation, tmax, tmin).
**Validates: Requirements 13.1**

**Property 32: Missing data warning**
*For any* variable with more than 10% missing values, a warning should be issued.
**Validates: Requirements 13.2**

**Property 33: Unrealistic value detection**
*For any* generated WGEN parameters, physically unrealistic values (negative precipitation parameters, extreme temperatures) should trigger warnings.
**Validates: Requirements 13.3, 13.4**

**Property 34: Short dataset warning**
*For any* observed dataset with less than 10 years of data, a warning should be issued that parameter estimates may be unreliable.
**Validates: Requirements 13.5**

**Property 35: Warning logging**
*For any* warnings generated during processing, they should be logged to data/processed/data_quality_report.txt.
**Validates: Requirements 13.6**

### Backward Compatibility Properties

**Property 36: Inline YAML compatibility**
*For any* existing YAML configuration that specifies WGEN parameters inline (not using CSV files), the system should continue to work without modification.
**Validates: Requirements 15.4, 15.5**

## Error Handling

### Error Categories

1. **User Input Errors**:
   - Invalid station ID format
   - Invalid latitude (outside -90 to 90)
   - Missing required CLI arguments
   - Invalid YAML configuration

2. **Data Errors**:
   - Station not found (HTTP 404)
   - Network errors during download
   - Corrupted .dly file format
   - Insufficient data for parameter estimation

3. **Configuration Errors**:
   - Missing required YAML fields
   - Invalid mode specification
   - Mixing observed and synthetic data
   - Attempting to use observed solar data

4. **Runtime Errors**:
   - Missing dates in observed data (Mode A)
   - File not found errors
   - Permission errors writing to directories

### Error Handling Strategy

**Fail Fast**: Validate all inputs and configuration before beginning processing. Raise clear, actionable errors immediately when problems are detected.

**Clear Messages**: All error messages should:
- Explain what went wrong
- Indicate which requirement was violated
- Suggest how to fix the problem
- Include relevant context (file paths, parameter names, etc.)

**Example Error Messages**:
```python
# Invalid station ID
raise ValueError(
    f"Invalid GHCN station ID format: '{station_id}'\n"
    f"Expected format: 11-character code (e.g., 'USW00024233')\n"
    f"See https://www.ncdc.noaa.gov/ghcn-daily-description for station list"
)

# Missing configuration field
raise ValueError(
    f"Mode A (historical) requires 'observed_data_file' field in YAML configuration.\n"
    f"Add: observed_data_file: data/processed/observed_climate.csv"
)

# Mixing observed and synthetic
raise ValueError(
    "Cannot mix observed and synthetic climate data.\n"
    "Use mode='historical' for observed P/T with synthetic Solar,\n"
    "or mode='stochastic' for fully synthetic climate."
)

# Insufficient data
raise ValueError(
    f"Insufficient wet days in {month_name} for Gamma parameter estimation.\n"
    f"Found {wet_day_count} wet days, need at least 10.\n"
    f"Consider using data from a longer time period or neighboring months."
)
```

### Warnings vs Errors

**Errors** (raise exceptions, stop execution):
- Invalid configuration
- Missing required data
- File not found
- Format errors

**Warnings** (log to file, continue execution):
- High percentage of missing data (>10%)
- Short dataset (<10 years)
- Unrealistic parameter values
- Insufficient data for specific months (use fallback)

## Testing Strategy

### Unit Testing

Unit tests will verify specific functionality of individual components:

**GHCN Data Fetcher Tests**:
- Test parsing of known .dly file formats
- Test unit conversion (tenths to whole units)
- Test missing value handling (-9999 to NaN)
- Test February 29th exclusion
- Test invalid date handling

**Parameter Generator Tests**:
- Test PWW/PWD calculation with known sequences
- Test Gamma parameter fitting with known distributions
- Test Fourier series calculation with known seasonal patterns
- Test solar theoretical max calculation with known latitudes
- Test solar estimation fallback (0.75/0.50 multipliers)

**Simulation Driver Tests**:
- Test Mode A reads observed P/T and generates solar
- Test Mode B generates all variables
- Test configuration validation rejects invalid configs
- Test path resolution relative to YAML file

**CLI Tests**:
- Test argument parsing
- Test directory structure creation
- Test end-to-end workflow with mock HTTP requests

### Property-Based Testing

Property-based tests will verify universal properties across many randomly generated inputs:

**Testing Framework**: Use `hypothesis` library for Python property-based testing.

**Test Configuration**: Each property test should run a minimum of 100 iterations to ensure statistical coverage.

**Property Test Tagging**: Each property-based test must include a comment explicitly referencing the correctness property from this design document using the format:
```python
# Feature: climate-builder, Property 2: Unit conversion consistency
# Validates: Requirements 2.1, 2.2, 2.3
```

**Key Property Tests**:

1. **Unit Conversion Property** (Property 2):
   - Generate random .dly data with values in tenths
   - Verify all outputs are correctly converted to whole units
   - Check: output_mm = input_tenths / 10.0

2. **Missing Value Property** (Property 3):
   - Generate random .dly data with -9999 flags
   - Verify all -9999 values become NaN in output
   - Check: all -9999 inputs map to NaN outputs

3. **Wet Day Classification Property** (Property 8):
   - Generate random precipitation values around 0.1 mm threshold
   - Verify correct classification (>= 0.1 is wet, < 0.1 is dry)
   - Check: classification matches threshold rule

4. **Markov Chain Property** (Property 9):
   - Generate random wet/dry sequences
   - Calculate PWW and PWD
   - Verify: PWW = NWW/(NWW+NDW), PWD = NWD/(NWD+NDD)

5. **Solar Physical Constraint Property** (Property 15):
   - Generate random latitudes and dates
   - Calculate theoretical max and actual solar values
   - Verify: actual <= theoretical_max for all cases

6. **Parameter CSV Round-Trip Property** (Property 17):
   - Generate random WGEN parameters
   - Save to CSV
   - Parse CSV back
   - Verify: parsed parameters == original parameters

7. **Configuration Validation Property** (Property 24):
   - Generate random invalid configurations (mixing observed/synthetic)
   - Verify: all invalid configs are rejected with clear errors

8. **Mode B Markov Chain Property** (Property 21):
   - Generate long stochastic sequences (1000+ days)
   - Calculate empirical transition probabilities
   - Verify: empirical PWW/PWD converge to specified parameters (within tolerance)

9. **Path Resolution Property** (Property 30):
   - Generate random relative paths in YAML
   - Verify: paths are resolved relative to YAML file location

10. **Backward Compatibility Property** (Property 36):
    - Generate random inline YAML parameter specifications
    - Verify: system accepts and processes them correctly

### Integration Testing

Integration tests will verify that components work together correctly:

1. **End-to-End Workflow Test**:
   - Run CLI with test station ID
   - Verify all output files are created
   - Verify parameter CSV can be parsed
   - Verify simulation can run with generated parameters

2. **Mode A Integration Test**:
   - Create test observed data and parameters
   - Run simulation in Mode A
   - Verify observed P/T are used
   - Verify solar is generated synthetically

3. **Mode B Integration Test**:
   - Create test parameters
   - Run simulation in Mode B
   - Verify all variables are generated
   - Verify statistical properties match parameters

4. **Legacy Compatibility Test**:
   - Use existing YAML configs with inline parameters
   - Verify they still work
   - Verify outputs are unchanged

### Test Data

**Mock GHCN Data**: Create synthetic .dly files with known values for testing:
- Valid data with all variables
- Data with missing values (-9999)
- Data with February 29th
- Data with invalid dates
- Data with extreme values

**Reference Outputs**: Generate reference outputs from `wgenpar.f` for validation:
- Known station data → expected parameters
- Use for regression testing of parameter generation

**Test Configurations**: Create test YAML files for all scenarios:
- Valid Mode A configuration
- Valid Mode B configuration
- Invalid configurations (for error testing)
- Legacy inline parameter configurations

## Performance Considerations

### Expected Performance

- **GHCN Download**: 1-5 seconds per station (network dependent)
- **DLY Parsing**: < 1 second for 100 years of data
- **Parameter Generation**: < 5 seconds for 100 years of data
- **Simulation (Mode A)**: < 0.1 ms per day (file lookup + solar generation)
- **Simulation (Mode B)**: < 0.1 ms per day (WGEN generation)

### Optimization Strategies

1. **Caching**: Cache downloaded .dly files to avoid re-downloading
2. **Vectorization**: Use NumPy for bulk calculations in parameter generation
3. **Lazy Loading**: Load observed data only when needed
4. **Pre-computation**: Calculate theoretical solar max once per year, not per day

### Scalability

- **Single Station**: Designed for single-station analysis
- **Multiple Stations**: Users can run CLI multiple times for different stations
- **Long Simulations**: Mode B can generate unlimited length sequences
- **Large Datasets**: Parameter generation tested with 100+ years of data

## Dependencies

### External Libraries

- **requests**: HTTP downloads from NOAA
- **pandas**: Data manipulation and CSV I/O
- **numpy**: Numerical calculations (Fourier, Gamma fitting, solar geometry)
- **scipy**: Statistical distributions (Gamma fitting)
- **pyyaml**: YAML configuration parsing
- **hypothesis**: Property-based testing framework

### Internal Dependencies

- **hydrosim.wgen**: Existing WGEN implementation (WGENParams, WGENState, wgen_step)
- **hydrosim.wgen_params**: Existing CSV parameter parser (CSVWGENParamsParser)
- **hydrosim.config**: YAML configuration parsing

### Version Requirements

- Python >= 3.8 (for dataclasses, type hints)
- requests >= 2.25.0
- pandas >= 1.2.0
- numpy >= 1.20.0
- scipy >= 1.6.0
- pyyaml >= 5.4.0
- hypothesis >= 6.0.0 (dev dependency)

## Deployment and Installation

### Installation

```bash
# Install HydroSim with Climate Builder
pip install hydrosim[climate-builder]

# Or install from source
git clone https://github.com/your-org/hydrosim.git
cd hydrosim
pip install -e .[climate-builder]
```

### CLI Registration

The CLI tool will be registered as a console script in `setup.py`:

```python
entry_points={
    'console_scripts': [
        'hydrosim-climate-builder=hydrosim.climate_builder.cli:main',
    ],
}
```

### Configuration

No system-level configuration required. All configuration is per-project via YAML files.

### Documentation

Documentation will be provided in multiple formats:

1. **README.md**: Quick start guide and overview
2. **API Documentation**: Sphinx-generated API docs
3. **Examples**: Working example scripts and YAML files
4. **Tutorials**: Step-by-step guides for common workflows

## Future Enhancements

### Potential Extensions

1. **Multiple Station Support**: Aggregate data from multiple nearby stations
2. **Gap Filling**: Interpolate missing values in observed data
3. **Bias Correction**: Adjust WGEN parameters to match observed statistics
4. **Climate Change Scenarios**: Modify parameters to represent future climate
5. **Alternative Data Sources**: Support for other climate databases (PRISM, Daymet)
6. **GUI Interface**: Web-based interface for non-technical users
7. **Parallel Processing**: Process multiple stations in parallel
8. **Cloud Integration**: Direct access to cloud-hosted climate databases

### Backward Compatibility

All future enhancements will maintain backward compatibility with:
- Existing YAML configuration format
- Existing CSV parameter format
- Existing inline parameter specification
- Existing WGEN implementation

## References

### Technical References

1. Richardson, C.W. (1981). "Stochastic simulation of daily precipitation, temperature, and solar radiation." Water Resources Research, 17(1), 182-190.

2. Richardson, C.W., & Wright, D.A. (1984). "WGEN: A model for generating daily weather variables." U.S. Department of Agriculture, Agricultural Research Service, ARS-8.

3. NOAA GHCN Daily Documentation: https://www.ncdc.noaa.gov/ghcn-daily-description

4. Legacy FORTRAN Code: `.kiro/legacy_source/wgenpar.f`

### Implementation References

- Existing WGEN implementation: `hydrosim/wgen.py`
- Existing CSV parser: `hydrosim/wgen_params.py`
- Legacy Python processors: `.kiro/legacy_source/*.py`
