# Requirements Document

## Introduction

This specification defines the integration of WGEN (Weather GENerator) stochastic weather generation into the HydroSim framework with CSV-based parameter configuration. WGEN generates daily synthetic weather data including precipitation, maximum temperature, minimum temperature, and solar radiation. These climate variables drive critical hydrological processes including lake evaporation, water demand calculations, catchment snowpack accumulation and melt, and runoff generation.

Currently, WGEN parameters must be specified directly in YAML configuration files, requiring 48 precipitation parameters plus numerous temperature and radiation parameters to be embedded inline. This approach is verbose, error-prone, and difficult to maintain. This feature will enable users to define WGEN parameters in separate CSV files that can be referenced by name from the YAML configuration, improving maintainability, reusability, and reducing configuration complexity.

## Glossary

- **WGEN**: Weather GENerator - A stochastic weather generation algorithm that produces synthetic daily climate data
- **HydroSim**: The water resources simulation framework
- **CSV**: Comma-Separated Values file format
- **YAML**: YAML Ain't Markup Language - the configuration file format used by HydroSim
- **Climate Source**: A component that provides daily climate data to the simulation
- **Parameter File**: A CSV file containing WGEN parameters
- **Configuration Directory**: The directory containing the YAML configuration file
- **Monthly Parameters**: WGEN parameters that vary by month (12 values each)
- **Constant Parameters**: WGEN parameters that remain constant throughout the year
- **Precipitation Parameters**: PWW, PWD, ALPHA, BETA - control wet/dry day transitions and precipitation amounts
- **Temperature Parameters**: TXMD, ATX, TXMW, TN, ATN, CVTX, ACVTX, CVTN, ACVTN - control temperature generation
- **Radiation Parameters**: RMD, AR, RMW - control solar radiation generation
- **YAMLParser**: The component responsible for parsing YAML configuration files

## Requirements

### Requirement 1

**User Story:** As a hydrologist, I want to define WGEN parameters in a CSV file, so that I can manage complex parameter sets more easily and reuse them across multiple simulations.

#### Acceptance Criteria

1. WHEN a user specifies a WGEN parameter CSV file in the YAML configuration THEN the YAMLParser SHALL load and parse the CSV file from the configuration directory
2. WHEN the CSV file path is relative THEN the YAMLParser SHALL resolve it relative to the YAML configuration file's directory
3. WHEN the CSV file path is absolute THEN the YAMLParser SHALL use the absolute path directly
4. WHEN the CSV file does not exist THEN the YAMLParser SHALL raise a FileNotFoundError with a clear message indicating the expected file location
5. WHERE a WGEN parameter CSV is specified, the YAML configuration SHALL reference it by filename in the climate section

### Requirement 2

**User Story:** As a user, I want the CSV parameter file to have a clear, documented structure, so that I can create and modify parameter files without confusion.

#### Acceptance Criteria

1. THE CSV file SHALL contain a header row with parameter names as column identifiers
2. THE CSV file SHALL contain exactly one data row with parameter values
3. WHEN the CSV file contains monthly parameters THEN the CSV SHALL use column names with month suffixes (e.g., pww_jan, pww_feb, ..., pww_dec)
4. WHEN the CSV file contains constant parameters THEN the CSV SHALL use single column names without suffixes (e.g., txmd, atx, latitude)
5. THE system SHALL provide a template CSV file with all required parameters and example values

### Requirement 3

**User Story:** As a developer, I want the CSV parser to validate all WGEN parameters, so that configuration errors are caught early with clear error messages.

#### Acceptance Criteria

1. WHEN parsing a CSV file THEN the system SHALL validate that all required WGEN parameters are present
2. WHEN a required parameter is missing THEN the system SHALL raise a ValueError listing all missing parameters
3. WHEN parameter values are invalid THEN the system SHALL raise a ValueError with specific details about which parameters are invalid and why
4. WHEN monthly parameters have incorrect counts THEN the system SHALL raise a ValueError indicating the expected count of 12 values
5. WHEN probability parameters are outside the range [0,1] THEN the system SHALL raise a ValueError specifying the valid range

### Requirement 4

**User Story:** As a user, I want to specify WGEN parameters either inline in YAML or via CSV file, so that I have flexibility in how I configure my simulations.

#### Acceptance Criteria

1. WHEN the climate configuration specifies wgen_params as a dictionary THEN the YAMLParser SHALL parse parameters directly from YAML
2. WHEN the climate configuration specifies wgen_params_file as a string THEN the YAMLParser SHALL load parameters from the CSV file
3. WHEN both wgen_params and wgen_params_file are specified THEN the YAMLParser SHALL raise a ValueError indicating that only one method should be used
4. WHEN neither wgen_params nor wgen_params_file are specified for WGEN climate source THEN the YAMLParser SHALL raise a ValueError indicating that parameters must be provided

### Requirement 5

**User Story:** As a simulation modeler, I want WGEN to generate precipitation, temperature, and solar radiation on a daily basis, so that these variables can drive hydrological processes in my model.

#### Acceptance Criteria

1. WHEN the simulation requests climate data for a date THEN the WGENClimateSource SHALL generate precipitation in millimeters per day
2. WHEN the simulation requests climate data for a date THEN the WGENClimateSource SHALL generate maximum temperature in degrees Celsius
3. WHEN the simulation requests climate data for a date THEN the WGENClimateSource SHALL generate minimum temperature in degrees Celsius
4. WHEN the simulation requests climate data for a date THEN the WGENClimateSource SHALL generate solar radiation in megajoules per square meter per day
5. WHEN generating weather data THEN the WGEN algorithm SHALL use monthly precipitation parameters based on the current simulation date's month

### Requirement 6

**User Story:** As a user, I want clear documentation and examples showing how to configure WGEN with CSV parameter files, so that I can quickly set up my simulations correctly.

#### Acceptance Criteria

1. THE system SHALL provide an example YAML configuration file demonstrating WGEN with CSV parameter file reference
2. THE system SHALL provide an example CSV parameter file with realistic parameter values
3. THE system SHALL provide a Python example script demonstrating how to run a simulation with WGEN climate source
4. THE documentation SHALL explain the meaning and valid ranges of all WGEN parameters
5. THE documentation SHALL explain how WGEN parameters affect the generated climate variables

### Requirement 7

**User Story:** As a developer, I want the CSV parsing functionality to be well-tested, so that I can be confident in the correctness of parameter loading.

#### Acceptance Criteria

1. THE system SHALL include unit tests for CSV file parsing with valid parameter files
2. THE system SHALL include unit tests for error handling when CSV files are missing
3. THE system SHALL include unit tests for error handling when CSV files have missing parameters
4. THE system SHALL include unit tests for error handling when CSV files have invalid parameter values
5. THE system SHALL include integration tests demonstrating end-to-end WGEN simulation with CSV parameter files
