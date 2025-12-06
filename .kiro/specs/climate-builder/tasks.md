# Implementation Plan

## Overview

This implementation plan breaks down the Climate Builder feature into discrete, manageable tasks that build incrementally. Each task focuses on a specific component or functionality, with testing integrated throughout to catch issues early.

The plan follows a bottom-up approach: build core data structures and utilities first, then layer on the GHCN fetcher, parameter generator, and simulation driver. Property-based tests are placed immediately after implementing the functionality they validate.

## Tasks

- [x] 1. Set up project structure and core data models





  - Create `hydrosim/climate_builder/` package directory
  - Define core data models: `ObservedClimateData`, `ClimateData`, `DataQualityReport`
  - Create `__init__.py` with package exports
  - _Requirements: All requirements (foundational)_

- [ ]* 1.1 Write unit tests for data models
  - Test data model instantiation and validation
  - Test data model serialization/deserialization
  - _Requirements: All requirements (foundational)_

- [x] 2. Implement project directory structure management





  - Create `ProjectStructure` class to manage directory creation
  - Implement methods: `initialize_structure()`, `get_raw_data_dir()`, `get_processed_data_dir()`, `get_config_dir()`, `get_outputs_dir()`
  - Ensure directories are created if they don't exist
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

- [ ]* 2.1 Write unit tests for project structure
  - Test directory creation in empty directory
  - Test directory creation when some directories already exist
  - Test path resolution
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

- [ ]* 2.2 Write property test for file placement
  - **Property 6: File placement consistency**
  - **Validates: Requirements 7.5, 7.6**

- [x] 3. Implement GHCN data fetcher





  - Create `GHCNDataFetcher` class
  - Implement `download_dly_file()` method with HTTP requests to NOAA
  - Handle HTTP errors (404, timeouts, network errors)
  - Save raw .dly files to `data/raw/` directory
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [ ]* 3.1 Write unit tests for GHCN fetcher
  - Test download with mock HTTP responses
  - Test error handling for invalid station IDs
  - Test file saving to correct directory
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [ ]* 3.2 Write property test for station ID validation
  - **Property 1: Invalid station ID rejection**
  - **Validates: Requirements 1.3, 1.5**





- [ ] 4. Implement GHCN .dly file parser

  - Create `DLYParser` class
  - Implement fixed-width format parsing (positions 0-11, 11-15, 15-17, 17-21, 21+)
  - Extract PRCP, TMAX, TMIN elements
  - Convert tenths of mm/°C to mm/°C
  - Handle missing value flags (-9999 → NaN)
  - Skip February 29th records
  - Skip other invalid dates
  - Output DataFrame with columns: date, precipitation_mm, tmax_c, tmin_c
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

- [ ]* 4.1 Write property test for unit conversion
  - **Property 2: Unit conversion consistency**
  - **Validates: Requirements 2.1, 2.2, 2.3**

- [ ]* 4.2 Write property test for missing value handling
  - **Property 3: Missing value handling**
  - **Validates: Requirements 2.4**

- [ ]* 4.3 Write property test for invalid date handling
  - **Property 4: Invalid date handling**
  - **Validates: Requirements 2.6**





- [ ]* 4.4 Write property test for output schema
  - **Property 5: Output schema consistency**
  - **Validates: Requirements 2.7**

- [ ] 5. Implement data quality validation

  - Create `DataQualityValidator` class
  - Calculate percentage of missing values for each variable
  - Check for physically unrealistic values
  - Check dataset length (warn if < 10 years)
  - Generate warnings for quality issues
  - Save quality report to `data/processed/data_quality_report.txt`
  - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6_

- [ ]* 5.1 Write property test for missing data reporting
  - **Property 31: Missing data reporting**
  - **Validates: Requirements 13.1**

- [ ]* 5.2 Write property test for missing data warning
  - **Property 32: Missing data warning**
  - **Validates: Requirements 13.2**

- [ ]* 5.3 Write property test for unrealistic value detection
  - **Property 33: Unrealistic value detection**
  - **Validates: Requirements 13.3, 13.4**


- [ ]* 5.4 Write property test for short dataset warning
  - **Property 34: Short dataset warning**
  - **Validates: Requirements 13.5**

- [ ]* 5.5 Write property test for warning logging
  - **Property 35: Warning logging**
  - **Validates: Requirements 13.6**

- [x] 6. Implement precipitation parameter calculator




  - Create `PrecipitationParameterCalculator` class
  - Implement wet/dry day classification (threshold = 0.1 mm)
  - Calculate monthly transition counts (NWW, NDW, NWD, NDD)
  - Calculate PWW = NWW/(NWW+NDW) and PWD = NWD/(NWD+NDD) for each month
  - Fit Gamma distributions to wet day precipitation amounts by month
  - Calculate Alpha (shape) and Beta (scale) parameters
  - Handle months with insufficient wet days (warn and use neighboring months)
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

- [ ]* 6.1 Write property test for monthly parameter completeness
  - **Property 7: Monthly parameter completeness**
  - **Validates: Requirements 3.1, 3.5, 3.6**

- [ ]* 6.2 Write property test for wet day classification
  - **Property 8: Wet day classification**
  - **Validates: Requirements 3.2**

- [ ]* 6.3 Write property test for Markov chain calculation
  - **Property 9: Markov chain calculation**
  - **Validates: Requirements 3.3, 3.4**

- [x] 7. Implement temperature parameter calculator





  - Create `TemperatureParameterCalculator` class
  - Divide year into 13 periods of 28 days each
  - Calculate mean and std dev for each period, separately for wet/dry days (Tmax) and combined (Tmin)
  - Fit 13-period Fourier series: T = mean + amplitude * cos(2π(period-peak)/13)
  - Extract Fourier coefficients: mean, amplitude, phase
  - Calculate coefficient of variation (CV = std/mean)
  - Generate parameters: txmd, atx, txmw (Tmax wet/dry), tn, atn (Tmin), cvtx, acvtx, cvtn, acvtn
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

- [ ]* 7.1 Write property test for temperature Fourier completeness
  - **Property 10: Temperature Fourier completeness**
  - **Validates: Requirements 4.1, 4.2, 4.3**

- [ ]* 7.2 Write property test for wet/dry temperature separation
  - **Property 11: Wet/dry temperature separation**
  - **Validates: Requirements 4.4**

- [ ]* 7.3 Write property test for temperature correlation parameters
  - **Property 12: Temperature correlation parameters**
  - **Validates: Requirements 4.5**


- [x] 8. Implement solar radiation parameter calculator




  - Create `SolarParameterCalculator` class
  - Implement theoretical solar max calculation using wgenpar.f equations
  - CRITICAL: Use solar constant coefficient of 37.2 MJ/m²/day (not 889 Langleys)
  - Calculate theoretical max for all 365 days based on latitude
  - If observed solar data available: Calculate RMD (dry days) and RMW (wet days) by month
  - If no observed solar: Estimate RMD = 0.75 * theoretical_max, RMW = 0.50 * theoretical_max
  - Fit 13-period Fourier series to monthly solar means
  - Extract amplitude (AR) parameter
  - Ensure all solar values <= theoretical max
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_

- [ ]* 8.1 Write property test for solar theoretical maximum
  - **Property 13: Solar theoretical maximum**
  - **Validates: Requirements 5.1, 5.2**

- [ ]* 8.2 Write property test for solar parameter estimation
  - **Property 14: Solar parameter estimation**
  - **Validates: Requirements 5.5**

- [ ]* 8.3 Write property test for solar physical constraint
  - **Property 15: Solar physical constraint**
  - **Validates: Requirements 5.7**


- [x] 9. Implement WGEN parameter generator orchestrator




  - Create `WGENParameterGenerator` class that coordinates all calculators
  - Implement `generate_all_parameters()` method
  - Call precipitation, temperature, and solar calculators
  - Combine results into unified parameter dictionary
  - Validate parameter ranges and physical constraints
  - _Requirements: All parameter generation requirements_

- [ ]* 9.1 Write integration test for parameter generation
  - Test end-to-end parameter generation with sample observed data
  - Verify all required parameters are present
  - Verify parameter values are within valid ranges
  - _Requirements: All parameter generation requirements_


- [x] 10. Implement parameter CSV writer




  - Create `ParameterCSVWriter` class
  - Implement structured CSV format with sections:
    - Monthly precipitation parameters (12 rows)
    - Temperature parameters (9 rows)
    - Radiation parameters (3 rows)
    - Location parameters (2 rows)
  - Ensure compatibility with existing `CSVWGENParamsParser`
  - Save to `data/processed/wgen_params.csv`
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7_

- [ ]* 10.1 Write property test for parameter CSV schema
  - **Property 16: Parameter CSV schema**
  - **Validates: Requirements 6.2, 6.3, 6.4, 6.5**

- [ ]* 10.2 Write property test for parameter CSV round-trip
  - **Property 17: Parameter CSV round-trip**
  - **Validates: Requirements 6.7, 15.1**

- [x] 11. Checkpoint - Ensure all tests pass




  - Ensure all tests pass, ask the user if questions arise.

- [ ] 12. Implement simulation driver base class
  - Create `ClimateSimulationDriver` abstract base class
  - Define interface: `__init__(config)`, `validate_configuration()`, `get_climate_for_date(date)`
  - Implement configuration validation logic:
    - Check mode is "historical" or "stochastic"
    - Validate required fields for each mode
    - Reject mixing observed/synthetic data
    - Reject observed solar data
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 11.1, 11.8_

- [ ]* 12.1 Write property test for configuration mixing rejection
  - **Property 24: Configuration mixing rejection**
  - **Validates: Requirements 10.1, 10.2**

- [ ]* 12.2 Write property test for observed solar rejection
  - **Property 25: Observed solar rejection**
  - **Validates: Requirements 10.5**

- [ ]* 12.3 Write property test for mode validation
  - **Property 27: Mode validation**
  - **Validates: Requirements 11.1**

- [ ] 13. Implement Mode A (Historical) driver
  - Create `HistoricalClimateDriver` class extending `ClimateSimulationDriver`
  - Load observed data from CSV
  - Load WGEN parameters from CSV
  - Implement `get_climate_for_date()`:
    - Read precipitation and temperature from observed data
    - Determine wet/dry status from observed precipitation
    - Generate synthetic solar radiation using WGEN, correlated with wet/dry status
  - Raise error if date is missing from observed data
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 11.2, 11.3, 11.4_

- [ ]* 13.1 Write property test for Mode A solar generation
  - **Property 18: Mode A solar generation**
  - **Validates: Requirements 8.3**

- [ ]* 13.2 Write property test for Mode A wet/dry correlation
  - **Property 19: Mode A wet/dry correlation**
  - **Validates: Requirements 8.4**

- [ ]* 13.3 Write property test for Mode A missing date error
  - **Property 20: Mode A missing date error**
  - **Validates: Requirements 8.5**

- [ ]* 13.4 Write property test for Mode A required fields
  - **Property 28: Mode A required fields**
  - **Validates: Requirements 11.2, 11.3, 11.4**

- [ ] 14. Implement Mode B (Stochastic) driver
  - Create `StochasticClimateDriver` class extending `ClimateSimulationDriver`
  - Load WGEN parameters from CSV
  - Initialize WGEN state with start date and random seed
  - Implement `get_climate_for_date()`:
    - Generate all variables (P, Tmax, Tmin, Solar) using WGEN
    - Use existing `wgen_step()` function from `hydrosim.wgen`
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 11.5, 11.6, 11.7_

- [ ]* 14.1 Write property test for Mode B Markov chain
  - **Property 21: Mode B Markov chain**
  - **Validates: Requirements 9.3**

- [ ]* 14.2 Write property test for Mode B Gamma distribution
  - **Property 22: Mode B Gamma distribution**
  - **Validates: Requirements 9.4**

- [ ]* 14.3 Write property test for Mode B seasonal patterns
  - **Property 23: Mode B seasonal patterns**
  - **Validates: Requirements 9.5, 9.6**

- [ ]* 14.4 Write property test for Mode B required fields
  - **Property 29: Mode B required fields**
  - **Validates: Requirements 11.5, 11.6**

- [ ]* 14.5 Write property test for solar always synthetic
  - **Property 26: Solar always synthetic**
  - **Validates: Requirements 10.6**

- [ ] 15. Implement YAML configuration integration
  - Create `ClimateConfigParser` class
  - Parse climate section from YAML configuration
  - Validate mode and required fields
  - Resolve file paths relative to YAML file directory
  - Instantiate appropriate driver (Historical or Stochastic) based on mode
  - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.8, 11.9_

- [ ]* 15.1 Write property test for path resolution
  - **Property 30: Path resolution**
  - **Validates: Requirements 11.9**

- [ ]* 15.2 Write integration test for YAML parsing
  - Test parsing valid Mode A configuration
  - Test parsing valid Mode B configuration
  - Test rejection of invalid configurations
  - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.8, 11.9_

- [ ] 16. Implement command-line interface
  - Create `hydrosim/climate_builder/cli.py` module
  - Implement argument parser with subcommands: `fetch`, `init`, `generate-params`
  - Implement `fetch` command:
    - Accept --station-id and --latitude as required arguments
    - Accept --output-dir as optional argument
    - Download GHCN data, parse, generate parameters, save outputs
    - Print summary of data period, records, and output locations
  - Implement `init` command:
    - Accept --output-dir as optional argument
    - Create project directory structure
  - Implement `generate-params` command:
    - Accept --observed-data and --latitude as required arguments
    - Accept --output-dir as optional argument
    - Generate parameters from existing observed data
  - Handle errors with clear, actionable messages
  - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7_

- [ ]* 16.1 Write integration test for CLI
  - Test `fetch` command with mock HTTP requests
  - Test `init` command
  - Test `generate-params` command
  - Test error handling for missing arguments
  - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7_

- [ ] 17. Register CLI as console script
  - Update `setup.py` to register `hydrosim-climate-builder` console script
  - Test installation and CLI availability
  - _Requirements: 12.1_

- [ ] 18. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 19. Create example YAML configurations
  - Create `examples/climate_mode_a_example.yaml` for Mode A (Historical)
  - Create `examples/climate_mode_b_example.yaml` for Mode B (Stochastic)
  - Include comments explaining each field
  - _Requirements: 14.3, 14.4_

- [ ] 20. Create example Python scripts
  - Create `examples/climate_builder_fetch_example.py` demonstrating data fetch
  - Create `examples/climate_builder_simulation_example.py` demonstrating simulation with both modes
  - Include comments explaining workflow
  - _Requirements: 14.2, 14.7_

- [ ] 21. Write backward compatibility tests
  - Test that existing YAML configs with inline WGEN parameters still work
  - Test that existing simulations using `WGENClimateSource` directly still work
  - Verify no breaking changes to existing API
  - _Requirements: 15.4, 15.5_

- [ ]* 21.1 Write property test for inline YAML compatibility
  - **Property 36: Inline YAML compatibility**
  - **Validates: Requirements 15.4, 15.5**

- [ ] 22. Create documentation
  - Write README.md for Climate Builder module
  - Document workflow: fetch → generate → simulate
  - Document YAML configuration schema
  - Document parameter CSV format
  - Include troubleshooting section for common errors
  - Document WGEN parameter meanings and valid ranges
  - _Requirements: 14.1, 14.5, 14.6_

- [ ] 23. Create reference test data
  - Generate reference outputs from `wgenpar.f` for validation
  - Create test .dly files with known values
  - Create test YAML configurations for all scenarios
  - Document expected outputs for regression testing
  - _Requirements: 4.6 (wgenpar.f fidelity)_

- [ ] 24. Final integration testing
  - Run end-to-end workflow: fetch → generate → simulate (Mode A)
  - Run end-to-end workflow: fetch → generate → simulate (Mode B)
  - Verify all outputs are created in correct locations
  - Verify simulation results are physically reasonable
  - Test with multiple different GHCN stations
  - _Requirements: All requirements_

- [ ] 25. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Testing Summary

### Property-Based Tests (22 tests)
- Property 1: Invalid station ID rejection
- Property 2: Unit conversion consistency
- Property 3: Missing value handling
- Property 4: Invalid date handling
- Property 5: Output schema consistency
- Property 6: File placement consistency
- Property 7: Monthly parameter completeness
- Property 8: Wet day classification
- Property 9: Markov chain calculation
- Property 10: Temperature Fourier completeness
- Property 11: Wet/dry temperature separation
- Property 12: Temperature correlation parameters
- Property 13: Solar theoretical maximum
- Property 14: Solar parameter estimation
- Property 15: Solar physical constraint
- Property 16: Parameter CSV schema
- Property 17: Parameter CSV round-trip
- Property 18: Mode A solar generation
- Property 19: Mode A wet/dry correlation
- Property 20: Mode A missing date error
- Property 21: Mode B Markov chain
- Property 22: Mode B Gamma distribution
- Property 23: Mode B seasonal patterns
- Property 24: Configuration mixing rejection
- Property 25: Observed solar rejection
- Property 26: Solar always synthetic
- Property 27: Mode validation
- Property 28: Mode A required fields
- Property 29: Mode B required fields
- Property 30: Path resolution
- Property 31: Missing data reporting
- Property 32: Missing data warning
- Property 33: Unrealistic value detection
- Property 34: Short dataset warning
- Property 35: Warning logging
- Property 36: Inline YAML compatibility

### Unit Tests
- Data model tests
- Project structure tests
- GHCN fetcher tests
- Parameter generation tests
- Simulation driver tests
- CLI tests

### Integration Tests
- End-to-end workflow tests
- Mode A integration tests
- Mode B integration tests
- Backward compatibility tests
- YAML parsing tests

## Implementation Notes

### Testing Framework
- Use `hypothesis` for property-based testing
- Configure each property test to run minimum 100 iterations
- Tag each property test with comment: `# Feature: climate-builder, Property X: <name>`

### Error Handling
- All errors should include clear, actionable messages
- Validate inputs early (fail fast)
- Distinguish between errors (stop execution) and warnings (log and continue)

### Code Organization
```
hydrosim/
├── climate_builder/
│   ├── __init__.py
│   ├── data_models.py
│   ├── project_structure.py
│   ├── ghcn_fetcher.py
│   ├── dly_parser.py
│   ├── data_quality.py
│   ├── precipitation_params.py
│   ├── temperature_params.py
│   ├── solar_params.py
│   ├── parameter_generator.py
│   ├── parameter_csv.py
│   ├── simulation_driver.py
│   ├── config_parser.py
│   └── cli.py
├── wgen.py (existing)
└── wgen_params.py (existing)

tests/
├── test_climate_builder_data_models.py
├── test_climate_builder_project_structure.py
├── test_climate_builder_ghcn_fetcher.py
├── test_climate_builder_dly_parser.py
├── test_climate_builder_data_quality.py
├── test_climate_builder_precipitation_params.py
├── test_climate_builder_temperature_params.py
├── test_climate_builder_solar_params.py
├── test_climate_builder_parameter_generator.py
├── test_climate_builder_parameter_csv.py
├── test_climate_builder_simulation_driver.py
├── test_climate_builder_config_parser.py
├── test_climate_builder_cli.py
├── test_climate_builder_integration.py
└── test_climate_builder_backward_compat.py

examples/
├── climate_mode_a_example.yaml
├── climate_mode_b_example.yaml
├── climate_builder_fetch_example.py
└── climate_builder_simulation_example.py
```

### Dependencies
Add to `requirements.txt`:
```
requests>=2.25.0
pandas>=1.2.0
numpy>=1.20.0
scipy>=1.6.0
pyyaml>=5.4.0
```

Add to `requirements-dev.txt`:
```
hypothesis>=6.0.0
pytest>=6.2.0
pytest-cov>=2.12.0
```
