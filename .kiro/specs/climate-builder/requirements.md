# Requirements Document

## Introduction

This specification defines the Climate Data Acquisition & Parameterization Module for HydroSim, transforming it from a calculation engine into a full-featured modeling workbench with "batteries included" climate data capabilities. Currently, acquiring climate data and generating stochastic weather parameters is a manual, error-prone process requiring users to hunt for data sources, manually process files, and configure complex parameter sets. This module standardizes climate data acquisition, parameter generation, and simulation integration with rigid consistency rules to ensure physical validity.

The module implements three core components: (1) a GHCN data fetcher for observed climate data, (2) a WGEN parameter generator that ports the legacy `wgenpar.f` statistical algorithms, and (3) a simulation driver that enforces consistency between observed and synthetic climate data. The system mandates that every model includes Precipitation and Temperature time series, and always generates Solar Radiation synthetically using WGEN algorithms due to the scarcity of observed solar data.

## Glossary

- **HydroSim**: The water resources simulation framework being enhanced with climate data capabilities
- **GHCN**: Global Historical Climatology Network - NOAA's database of daily climate observations
- **NOAA**: National Oceanic and Atmospheric Administration
- **WGEN**: Weather GENerator - A stochastic weather generation algorithm that produces synthetic daily climate data
- **Station ID**: NOAA GHCN station identifier (e.g., "USW00024233")
- **DLY File**: GHCN Daily format fixed-width text file containing climate observations
- **Climate Builder**: The unified tool for fetching, processing, and parameterizing climate data
- **WGEN Parameters**: Statistical parameters that control synthetic weather generation (Markov chains, Gamma distributions, Fourier series)
- **Markov Chain**: Statistical model for wet/dry day transitions (P_Wet|Wet, P_Wet|Dry)
- **Gamma Distribution**: Statistical distribution for precipitation amounts (Alpha, Beta parameters)
- **Fourier Series**: Mathematical representation of seasonal cycles (13-period for temperature and solar)
- **PWW**: Probability of a wet day following a wet day
- **PWD**: Probability of a wet day following a dry day
- **Alpha**: Gamma distribution shape parameter for precipitation amounts
- **Beta**: Gamma distribution scale parameter for precipitation amounts
- **RMD**: Mean solar radiation on dry days
- **RMW**: Mean solar radiation on wet days
- **Observed Climate**: Historical climate data from GHCN stations
- **Synthetic Climate**: Stochastically generated climate data from WGEN
- **Project Directory**: Standardized folder structure for organizing climate data and configuration files
- **Simulation Driver**: The component that enforces consistency rules and provides climate data to simulations
- **Mode A (Historical)**: Simulation mode using observed Precip/Temp with synthetic Solar
- **Mode B (Stochastic)**: Simulation mode using fully synthetic climate data
- **Solar Radiation**: Daily solar energy flux in megajoules per square meter per day (MJ/m²/day)
- **Latitude**: Geographic coordinate in decimal degrees required for solar radiation calculations (must be provided by user, not available in GHCN .dly files)
- **Theoretical Solar Max**: Maximum possible solar radiation based on latitude and day of year
- **Wet Day**: A day with precipitation greater than or equal to 0.1 mm (WMO standard threshold)
- **Leap Year**: Years with 366 days; WGEN operates on a strict 365-day calendar and February 29th must be excluded

## Requirements

### Requirement 1: GHCN Data Fetcher

**User Story:** As a hydrologist, I want to download observed climate data from NOAA GHCN stations with a single command, so that I can quickly obtain historical precipitation and temperature records without manual data processing.

#### Acceptance Criteria

1. WHEN a user provides a NOAA Station ID THEN the Climate Builder SHALL download the corresponding `.dly` file via direct HTTP request from NOAA servers
2. WHEN downloading GHCN data THEN the Climate Builder SHALL use direct HTTP access without requiring API tokens or authentication
3. WHEN the Station ID is invalid or the file does not exist THEN the Climate Builder SHALL raise a clear error message indicating the station could not be found
4. WHEN the download completes successfully THEN the Climate Builder SHALL save the raw `.dly` file to the `data/raw/` directory within the project structure
5. WHERE the user provides a Station ID, the Climate Builder SHALL validate the format matches GHCN station identifier patterns

### Requirement 2: GHCN Data Parser

**User Story:** As a user, I want the system to automatically parse GHCN fixed-width format files, so that I can work with clean, standardized climate data without writing custom parsing code.

#### Acceptance Criteria

1. WHEN parsing a `.dly` file THEN the Climate Builder SHALL extract daily precipitation values in tenths of millimeters and convert to millimeters
2. WHEN parsing a `.dly` file THEN the Climate Builder SHALL extract daily maximum temperature values in tenths of degrees Celsius and convert to degrees Celsius
3. WHEN parsing a `.dly` file THEN the Climate Builder SHALL extract daily minimum temperature values in tenths of degrees Celsius and convert to degrees Celsius
4. WHEN the parser encounters missing value flags (-9999) THEN the Climate Builder SHALL represent these as NaN in the output dataset
5. WHEN the parser encounters February 29th (leap day) THEN the Climate Builder SHALL skip that record to maintain 365-day calendar compatibility with WGEN
6. WHEN the parser encounters other invalid dates (e.g., February 30) THEN the Climate Builder SHALL skip those records and continue processing
7. WHEN parsing completes THEN the Climate Builder SHALL output a CSV file with columns: date, precipitation_mm, tmax_c, tmin_c
7. WHEN the output CSV is created THEN the Climate Builder SHALL save it to `data/processed/observed_climate.csv` within the project structure

### Requirement 3: WGEN Parameter Generator - Precipitation

**User Story:** As a modeler, I want the system to calculate WGEN precipitation parameters from observed data using the validated `wgenpar.f` algorithm, so that I can generate statistically valid synthetic precipitation sequences.

#### Acceptance Criteria

1. WHEN generating precipitation parameters THEN the Climate Builder SHALL calculate monthly Markov chain transition probabilities (PWW, PWD) for all 12 months
2. WHEN determining wet/dry day status THEN the Climate Builder SHALL classify days with precipitation greater than or equal to 0.1 mm as wet days
3. WHEN calculating PWW for a month THEN the Climate Builder SHALL compute the probability of a wet day following a wet day based on observed wet/dry sequences
4. WHEN calculating PWD for a month THEN the Climate Builder SHALL compute the probability of a wet day following a dry day based on observed wet/dry sequences
5. WHEN generating precipitation parameters THEN the Climate Builder SHALL fit monthly Gamma distributions to observed precipitation amounts on wet days
6. WHEN fitting Gamma distributions THEN the Climate Builder SHALL calculate Alpha (shape) and Beta (scale) parameters for all 12 months
7. WHEN a month has insufficient wet days for parameter estimation THEN the Climate Builder SHALL raise a warning and use neighboring month values
7. WHERE precipitation parameters are calculated, the Climate Builder SHALL use the same statistical methods as the legacy `wgenpar.f` FORTRAN code

### Requirement 4: WGEN Parameter Generator - Temperature

**User Story:** As a user, I want the system to calculate WGEN temperature parameters using 13-period Fourier series smoothing, so that synthetic temperatures exhibit realistic seasonal patterns.

#### Acceptance Criteria

1. WHEN generating temperature parameters THEN the Climate Builder SHALL calculate 13-period Fourier series coefficients for maximum temperature means
2. WHEN generating temperature parameters THEN the Climate Builder SHALL calculate 13-period Fourier series coefficients for minimum temperature means
3. WHEN calculating Fourier coefficients THEN the Climate Builder SHALL compute mean, amplitude, and phase parameters for each harmonic
4. WHEN generating temperature parameters THEN the Climate Builder SHALL calculate temperature standard deviations separately for wet and dry days
5. WHEN generating temperature parameters THEN the Climate Builder SHALL calculate cross-correlation coefficients between maximum and minimum temperatures
6. WHERE temperature parameters are calculated, the Climate Builder SHALL replicate the mathematical approach from `wgenpar.f` to ensure statistical validity

### Requirement 5: WGEN Parameter Generator - Solar Radiation

**User Story:** As a modeler, I want the system to generate solar radiation parameters based on latitude, so that I can simulate solar energy inputs even when observed solar data is unavailable.

#### Acceptance Criteria

1. WHEN a user provides site latitude THEN the Climate Builder SHALL calculate theoretical maximum solar radiation for each day of the year
2. WHEN calculating theoretical solar max THEN the Climate Builder SHALL use the latitude-based solar geometry equations from `wgenpar.f`
3. WHEN observed solar radiation data is available THEN the Climate Builder SHALL calculate mean solar radiation on dry days (RMD) for each month
4. WHEN observed solar radiation data is available THEN the Climate Builder SHALL calculate mean solar radiation on wet days (RMW) for each month
5. WHEN observed solar radiation data is NOT available THEN the Climate Builder SHALL estimate RMD as 0.75 times theoretical solar max and RMW as 0.50 times theoretical solar max for each month
6. WHEN generating solar parameters THEN the Climate Builder SHALL calculate 13-period Fourier series coefficients for solar radiation patterns
7. WHERE solar parameters are calculated, the Climate Builder SHALL ensure values do not exceed theoretical maximum solar radiation for the given latitude and date

### Requirement 6: WGEN Parameter Output

**User Story:** As a user, I want WGEN parameters saved in a standardized CSV format, so that I can review, modify, and reuse parameter sets across multiple simulations.

#### Acceptance Criteria

1. WHEN parameter generation completes THEN the Climate Builder SHALL save all parameters to `data/processed/wgen_params.csv`
2. WHEN creating the parameter CSV THEN the Climate Builder SHALL include monthly precipitation parameters (pww_jan through pww_dec, pwd_jan through pwd_dec, alpha_jan through alpha_dec, beta_jan through beta_dec)
3. WHEN creating the parameter CSV THEN the Climate Builder SHALL include temperature Fourier series coefficients with descriptive column names
4. WHEN creating the parameter CSV THEN the Climate Builder SHALL include solar radiation parameters (rmd_jan through rmd_dec, rmw_jan through rmw_dec)
5. WHEN creating the parameter CSV THEN the Climate Builder SHALL include the site latitude as a parameter
6. THE parameter CSV SHALL contain a header row with parameter names and exactly one data row with parameter values
7. THE parameter CSV SHALL be compatible with the existing WGEN CSV integration functionality in HydroSim

### Requirement 7: Project Directory Structure

**User Story:** As a user, I want the system to automatically create and manage a standardized project directory structure, so that I can organize climate data and configuration files consistently across projects.

#### Acceptance Criteria

1. WHEN initializing a new climate project THEN the Climate Builder SHALL create a `config/` directory for YAML configuration files
2. WHEN initializing a new climate project THEN the Climate Builder SHALL create a `data/raw/` directory for original downloaded data files
3. WHEN initializing a new climate project THEN the Climate Builder SHALL create a `data/processed/` directory for cleaned and processed data files
4. WHEN initializing a new climate project THEN the Climate Builder SHALL create an `outputs/` directory for simulation results
5. WHEN the Climate Builder saves files THEN it SHALL place raw `.dly` files in `data/raw/`
6. WHEN the Climate Builder saves files THEN it SHALL place `observed_climate.csv` and `wgen_params.csv` in `data/processed/`
7. THE Climate Builder SHALL enforce this directory structure and SHALL NOT allow users to manually specify arbitrary file locations

### Requirement 8: Simulation Driver - Mode A (Historical)

**User Story:** As a modeler, I want to run simulations using observed precipitation and temperature with synthetic solar radiation, so that I can analyze historical climate impacts while accounting for solar energy dynamics.

#### Acceptance Criteria

1. WHEN the YAML configuration specifies Mode A (Historical) THEN the Simulation Driver SHALL read precipitation and temperature from `observed_climate.csv`
2. WHEN running in Mode A THEN the Simulation Driver SHALL read WGEN parameters from `wgen_params.csv`
3. WHEN running in Mode A THEN the Simulation Driver SHALL generate synthetic solar radiation daily using WGEN algorithms
4. WHEN generating synthetic solar in Mode A THEN the Simulation Driver SHALL correlate solar radiation with the observed wet/dry status for that day
5. WHEN a date in the simulation period is missing from observed data THEN the Simulation Driver SHALL raise an error indicating the data gap
6. WHERE Mode A is configured, the YAML SHALL specify paths to both `observed_climate.csv` and `wgen_params.csv`

### Requirement 9: Simulation Driver - Mode B (Stochastic)

**User Story:** As a modeler, I want to run fully stochastic simulations generating all climate variables synthetically, so that I can explore climate variability and uncertainty beyond the historical record.

#### Acceptance Criteria

1. WHEN the YAML configuration specifies Mode B (Stochastic) THEN the Simulation Driver SHALL generate precipitation, maximum temperature, minimum temperature, and solar radiation using WGEN algorithms
2. WHEN running in Mode B THEN the Simulation Driver SHALL read WGEN parameters from `wgen_params.csv`
3. WHEN running in Mode B THEN the Simulation Driver SHALL use monthly Markov chains to generate wet/dry day sequences
4. WHEN running in Mode B THEN the Simulation Driver SHALL use Gamma distributions to generate precipitation amounts on wet days
5. WHEN running in Mode B THEN the Simulation Driver SHALL use Fourier series and stochastic residuals to generate temperatures
6. WHEN running in Mode B THEN the Simulation Driver SHALL use Fourier series and wet/dry correlations to generate solar radiation
7. WHERE Mode B is configured, the YAML SHALL specify only the path to `wgen_params.csv`

### Requirement 10: Consistency Enforcement

**User Story:** As a system architect, I want the simulation driver to prevent physically inconsistent climate configurations, so that users cannot accidentally create invalid model setups.

#### Acceptance Criteria

1. WHEN the YAML configuration attempts to mix observed precipitation with synthetic temperature THEN the Simulation Driver SHALL reject the configuration and raise a validation error
2. WHEN the YAML configuration attempts to mix synthetic precipitation with observed temperature THEN the Simulation Driver SHALL reject the configuration and raise a validation error
3. WHEN the YAML configuration specifies observed precipitation and temperature THEN the Simulation Driver SHALL require Mode A configuration
4. WHEN the YAML configuration specifies synthetic precipitation and temperature THEN the Simulation Driver SHALL require Mode B configuration
5. THE Simulation Driver SHALL NOT allow users to specify observed solar radiation as a standalone input
6. THE Simulation Driver SHALL always generate solar radiation synthetically regardless of whether precipitation and temperature are observed or synthetic

### Requirement 11: YAML Configuration Schema

**User Story:** As a user, I want a clear YAML configuration schema for climate modes, so that I can easily specify whether to use observed or synthetic climate data.

#### Acceptance Criteria

1. THE YAML configuration SHALL include a `climate` section with a `mode` field accepting values "historical" or "stochastic"
2. WHEN mode is "historical" THEN the YAML SHALL require an `observed_data_file` field pointing to `observed_climate.csv`
3. WHEN mode is "historical" THEN the YAML SHALL require a `wgen_params_file` field pointing to `wgen_params.csv`
4. WHEN mode is "historical" THEN the YAML SHALL require a `latitude` field in decimal degrees for solar radiation generation
5. WHEN mode is "stochastic" THEN the YAML SHALL require a `wgen_params_file` field pointing to `wgen_params.csv`
6. WHEN mode is "stochastic" THEN the YAML SHALL require a `latitude` field in decimal degrees (which should match the latitude used during parameter generation)
7. WHEN mode is "stochastic" THEN the YAML SHALL optionally accept a `random_seed` field for reproducible stochastic generation
8. THE YAML parser SHALL validate that all required fields are present for the specified mode
9. THE YAML parser SHALL validate that file paths are relative to the configuration file directory

### Requirement 12: Command-Line Interface

**User Story:** As a user, I want a simple command-line interface to fetch data and generate parameters, so that I can quickly set up climate data for new projects.

#### Acceptance Criteria

1. THE Climate Builder SHALL provide a command-line tool accepting station ID and latitude in decimal degrees as required arguments
2. WHEN the user runs the CLI tool THEN it SHALL download GHCN data, parse it, generate WGEN parameters, and save all outputs to the project directory structure
3. THE CLI tool SHALL require latitude as a user-provided argument because GHCN .dly files do not contain station coordinate metadata
4. WHEN the CLI tool completes successfully THEN it SHALL print a summary of the data period, number of records, and output file locations
5. WHEN the CLI tool encounters errors THEN it SHALL print clear error messages indicating what went wrong and how to fix it
6. THE CLI tool SHALL accept an optional project directory argument, defaulting to the current working directory
7. THE CLI tool SHALL create the project directory structure if it does not already exist

### Requirement 13: Data Quality Validation

**User Story:** As a modeler, I want the system to validate data quality and warn me about potential issues, so that I can make informed decisions about whether the data is suitable for my analysis.

#### Acceptance Criteria

1. WHEN parsing observed data THEN the Climate Builder SHALL calculate the percentage of missing values for each variable
2. WHEN missing data exceeds 10% for any variable THEN the Climate Builder SHALL issue a warning
3. WHEN generating WGEN parameters THEN the Climate Builder SHALL check for physically unrealistic values (e.g., negative precipitation, temperatures outside reasonable bounds)
4. WHEN unrealistic values are detected THEN the Climate Builder SHALL issue a warning with details about which parameters are suspect
5. WHEN the observed data period is less than 10 years THEN the Climate Builder SHALL issue a warning that parameter estimates may be unreliable
6. THE Climate Builder SHALL log all warnings to a `data/processed/data_quality_report.txt` file

### Requirement 14: Documentation and Examples

**User Story:** As a new user, I want comprehensive documentation and working examples, so that I can quickly learn how to use the Climate Builder and set up my first simulation.

#### Acceptance Criteria

1. THE system SHALL provide a README document explaining the Climate Builder workflow from data acquisition to simulation
2. THE system SHALL provide an example showing how to fetch data for a specific GHCN station and generate parameters
3. THE system SHALL provide an example YAML configuration for Mode A (Historical) simulation
4. THE system SHALL provide an example YAML configuration for Mode B (Stochastic) simulation
5. THE documentation SHALL explain the physical meaning of WGEN parameters and how they affect generated climate
6. THE documentation SHALL include a troubleshooting section for common errors and data quality issues
7. THE system SHALL provide a Python script demonstrating the complete workflow from data fetch to simulation execution

### Requirement 15: Integration with Existing WGEN Implementation

**User Story:** As a developer, I want the Climate Builder to integrate seamlessly with the existing WGEN implementation in HydroSim, so that users can leverage both inline YAML parameters and CSV parameter files.

#### Acceptance Criteria

1. THE Climate Builder SHALL generate parameter CSV files compatible with the existing `wgen_params.py` parser
2. WHEN the Simulation Driver loads WGEN parameters THEN it SHALL use the existing `WGENParams` class
3. WHEN the Simulation Driver generates synthetic climate THEN it SHALL use the existing `WGENClimateSource` class
4. THE Climate Builder SHALL NOT break existing functionality for users who specify WGEN parameters inline in YAML
5. THE system SHALL support both the new Climate Builder workflow and the legacy manual parameter specification
