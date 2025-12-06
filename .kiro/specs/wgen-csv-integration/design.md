# Design Document

## Overview

This design document describes the integration of CSV-based parameter configuration for the WGEN (Weather GENerator) stochastic weather generation system in HydroSim. The implementation will extend the existing YAML configuration parser to support loading WGEN parameters from external CSV files, providing a more maintainable and reusable approach to managing the 48+ parameters required for weather generation.

The design maintains backward compatibility with inline YAML parameter specification while adding the new CSV file option. The CSV format will use a clear, documented structure with column names that map directly to WGEN parameter names, making it easy for users to create and modify parameter files.

## Architecture

### Component Overview

The implementation involves modifications and additions to the following components:

1. **YAMLParser** (`hydrosim/config.py`) - Extended to support CSV parameter file loading
2. **CSV Parameter Parser** (new module `hydrosim/wgen_params.py`) - Dedicated parser for WGEN CSV files
3. **WGENParams** (`hydrosim/wgen.py`) - No changes required, existing validation is sufficient
4. **WGENClimateSource** (`hydrosim/climate_sources.py`) - No changes required
5. **Example Files** - New example CSV file and updated YAML examples

### Data Flow

```
YAML Config File
    ↓
YAMLParser._parse_wgen_climate()
    ↓
    ├─→ Inline YAML params → WGENParams object
    │
    └─→ CSV file reference → CSVWGENParamsParser.parse()
                                ↓
                            WGENParams object
                                ↓
                        WGENClimateSource
                                ↓
                        Climate data generation
```

### File Organization

```
hydrosim/
├── wgen.py                    # Existing WGEN implementation (no changes)
├── wgen_params.py             # NEW: CSV parameter parser
├── config.py                  # Modified: Add CSV loading support
└── climate_sources.py         # Existing (no changes)

examples/
├── wgen_params_template.csv   # NEW: Template CSV with all parameters
├── wgen_example.yaml          # NEW: Example using CSV parameters
└── wgen_example.py            # NEW: Python example script

tests/
├── test_wgen_csv_parser.py    # NEW: Unit tests for CSV parser
└── test_wgen_integration.py   # NEW: Integration tests
```

## Components and Interfaces

### 1. CSV Parameter Parser Module (`hydrosim/wgen_params.py`)

A new module dedicated to parsing WGEN parameters from CSV files.

#### Class: `CSVWGENParamsParser`

```python
class CSVWGENParamsParser:
    """Parser for WGEN parameters from CSV files."""
    
    def __init__(self, filepath: str):
        """
        Initialize parser with CSV file path.
        
        Args:
            filepath: Path to CSV parameter file
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        
    @staticmethod
    def parse(filepath: str) -> WGENParams:
        """
        Parse WGEN parameters from CSV file.
        
        Args:
            filepath: Path to CSV parameter file
            
        Returns:
            WGENParams object with validated parameters
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If CSV format is invalid or parameters are missing/invalid
        """
        
    @staticmethod
    def _validate_csv_structure(df: pd.DataFrame) -> None:
        """
        Validate CSV file structure.
        
        Args:
            df: DataFrame loaded from CSV
            
        Raises:
            ValueError: If structure is invalid
        """
        
    @staticmethod
    def _extract_monthly_params(df: pd.DataFrame, param_name: str) -> List[float]:
        """
        Extract monthly parameters from CSV columns.
        
        Args:
            df: DataFrame with parameter data
            param_name: Base parameter name (e.g., 'pww')
            
        Returns:
            List of 12 monthly values
            
        Raises:
            ValueError: If any monthly columns are missing
        """
        
    @staticmethod
    def _extract_constant_param(df: pd.DataFrame, param_name: str) -> float:
        """
        Extract constant parameter from CSV.
        
        Args:
            df: DataFrame with parameter data
            param_name: Parameter name
            
        Returns:
            Parameter value as float
            
        Raises:
            ValueError: If parameter is missing
        """
        
    @staticmethod
    def create_template(filepath: str) -> None:
        """
        Create a template CSV file with all required parameters.
        
        Args:
            filepath: Path where template should be created
        """
```

### 2. Modified YAMLParser (`hydrosim/config.py`)

Extend the existing `_parse_wgen_climate()` method to support CSV file loading.

#### Modified Method: `_parse_wgen_climate()`

```python
def _parse_wgen_climate(self, climate_config: Dict[str, Any]) -> WGENClimateSource:
    """
    Parse WGEN climate source configuration.
    
    Supports two parameter specification methods:
    1. Inline YAML: wgen_params dictionary
    2. CSV file: wgen_params_file string
    
    Args:
        climate_config: Climate configuration dictionary
        
    Returns:
        WGENClimateSource instance
        
    Raises:
        ValueError: If configuration is invalid
    """
    # Check for parameter specification
    has_inline = 'wgen_params' in climate_config
    has_csv = 'wgen_params_file' in climate_config
    
    # Validate mutually exclusive options
    if has_inline and has_csv:
        raise ValueError(
            "Cannot specify both 'wgen_params' and 'wgen_params_file'. "
            "Use one method to provide WGEN parameters."
        )
    
    if not has_inline and not has_csv:
        raise ValueError(
            "WGEN climate source requires either 'wgen_params' (inline) "
            "or 'wgen_params_file' (CSV file path)."
        )
    
    # Load parameters from appropriate source
    if has_inline:
        # Existing inline parsing logic
        params = WGENParams(**climate_config['wgen_params'])
    else:
        # New CSV file parsing logic
        csv_path = climate_config['wgen_params_file']
        
        # Resolve relative paths
        if not Path(csv_path).is_absolute():
            csv_path = self.config_dir / csv_path
        
        # Parse CSV file
        from hydrosim.wgen_params import CSVWGENParamsParser
        params = CSVWGENParamsParser.parse(str(csv_path))
    
    # Rest of method unchanged (start_date parsing, etc.)
    ...
```

## Data Models

### CSV File Format

The CSV file will have a header row with parameter names and exactly one data row with values.

#### Column Naming Convention

**Monthly Parameters** (12 columns each):
- Format: `{param_name}_{month_abbrev}`
- Months: `jan`, `feb`, `mar`, `apr`, `may`, `jun`, `jul`, `aug`, `sep`, `oct`, `nov`, `dec`
- Examples: `pww_jan`, `pww_feb`, ..., `pww_dec`

**Constant Parameters** (single column):
- Format: `{param_name}`
- Examples: `txmd`, `atx`, `latitude`

#### Complete Parameter List

**Precipitation Parameters (48 columns total):**
- `pww_jan` through `pww_dec` - Probability wet|wet (12 columns)
- `pwd_jan` through `pwd_dec` - Probability wet|dry (12 columns)
- `alpha_jan` through `alpha_dec` - Gamma shape parameter (12 columns)
- `beta_jan` through `beta_dec` - Gamma scale parameter (12 columns)

**Temperature Parameters (9 columns):**
- `txmd` - Mean max temp on dry days (°C)
- `atx` - Amplitude of max temp variation (°C)
- `txmw` - Mean max temp on wet days (°C)
- `tn` - Mean min temperature (°C)
- `atn` - Amplitude of min temp variation (°C)
- `cvtx` - Coefficient of variation for max temp
- `acvtx` - Amplitude of CV variation for max temp
- `cvtn` - Coefficient of variation for min temp
- `acvtn` - Amplitude of CV variation for min temp

**Radiation Parameters (3 columns):**
- `rmd` - Mean radiation on dry days (MJ/m²/day)
- `ar` - Amplitude of radiation variation (MJ/m²/day)
- `rmw` - Mean radiation on wet days (MJ/m²/day)

**Location Parameters (1 column):**
- `latitude` - Site latitude in degrees (-90 to 90)

**Optional Parameters (1 column):**
- `random_seed` - Random seed for reproducibility (optional, can be empty)

**Total: 62 columns**

#### Example CSV Structure

```csv
pww_jan,pww_feb,...,pww_dec,pwd_jan,...,pwd_dec,alpha_jan,...,alpha_dec,beta_jan,...,beta_dec,txmd,atx,txmw,tn,atn,cvtx,acvtx,cvtn,acvtn,rmd,ar,rmw,latitude,random_seed
0.45,0.42,...,0.48,0.25,0.23,...,0.27,1.2,1.1,...,1.3,8.5,7.8,...,9.2,20.0,10.0,18.0,10.0,8.0,0.1,0.05,0.1,0.05,15.0,5.0,12.0,45.0,42
```

### YAML Configuration Format

#### Option 1: Inline Parameters (Existing)

```yaml
climate:
  source_type: wgen
  start_date: "2024-01-01"
  wgen_params:
    pww: [0.45, 0.42, 0.40, 0.38, 0.35, 0.30, 0.25, 0.28, 0.32, 0.38, 0.42, 0.48]
    pwd: [0.25, 0.23, 0.22, 0.20, 0.18, 0.15, 0.12, 0.15, 0.18, 0.22, 0.25, 0.27]
    alpha: [1.2, 1.1, 1.0, 0.9, 0.8, 0.7, 0.6, 0.7, 0.8, 1.0, 1.1, 1.3]
    beta: [8.5, 7.8, 7.2, 6.5, 5.8, 5.0, 4.5, 5.2, 6.0, 7.0, 7.8, 9.2]
    txmd: 20.0
    atx: 10.0
    txmw: 18.0
    tn: 10.0
    atn: 8.0
    cvtx: 0.1
    acvtx: 0.05
    cvtn: 0.1
    acvtn: 0.05
    rmd: 15.0
    ar: 5.0
    rmw: 12.0
    latitude: 45.0
    random_seed: 42
  site:
    latitude: 45.0
    elevation: 1000.0
```

#### Option 2: CSV File Reference (New)

```yaml
climate:
  source_type: wgen
  start_date: "2024-01-01"
  wgen_params_file: wgen_params.csv  # Relative to YAML file location
  site:
    latitude: 45.0
    elevation: 1000.0
```

### Error Messages

The implementation will provide clear, actionable error messages:

**File Not Found:**
```
FileNotFoundError: WGEN parameter file not found: /path/to/wgen_params.csv
Expected location: Same directory as YAML configuration file
```

**Missing Parameters:**
```
ValueError: WGEN parameter CSV is missing required parameters:
  - pww_jan, pww_feb, pww_mar
  - alpha_dec
  - latitude
See examples/wgen_params_template.csv for the complete parameter list.
```

**Invalid Parameter Values:**
```
ValueError: Invalid WGEN parameters in CSV file:
  - pww_jan = 1.5 (must be in range [0, 1])
  - alpha_mar = -0.5 (must be > 0)
  - latitude = 95.0 (must be in range [-90, 90])
```

**Conflicting Configuration:**
```
ValueError: Cannot specify both 'wgen_params' and 'wgen_params_file'.
Use either inline YAML parameters or CSV file, not both.
```

**Invalid CSV Structure:**
```
ValueError: WGEN parameter CSV must have exactly one data row, found 3 rows.
The CSV should contain a header row and one row of parameter values.
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property Reflection

Before defining the correctness properties, I reviewed all testable criteria from the prework analysis to eliminate redundancy:

- Properties 1.1, 1.2, and 1.3 all relate to path resolution and CSV loading. These can be combined into a single comprehensive property about CSV file loading.
- Properties 2.1, 2.3, and 2.4 all relate to CSV parsing and parameter extraction. These can be combined into a single property about correct parameter extraction.
- Properties 3.1 covers validation, while edge cases 3.2-3.5 cover specific error conditions. The property should focus on successful validation; edge cases will be handled by unit tests.
- Properties 4.1 and 4.2 cover the two configuration methods. These should remain separate as they test different code paths.
- Properties 5.1-5.4 all relate to output units and can be combined into a single property about correct output format.
- Property 5.5 stands alone as it tests monthly parameter selection logic.

After reflection, the following properties provide comprehensive, non-redundant coverage:

### Property 1: CSV file loading and path resolution

*For any* valid CSV file containing WGEN parameters, when referenced from a YAML configuration (with either relative or absolute path), the YAMLParser should successfully load the file and create a valid WGENParams object with all parameters correctly extracted.

**Validates: Requirements 1.1, 1.2, 1.3**

### Property 2: CSV parameter extraction correctness

*For any* valid CSV file with proper header row and data row, the parser should correctly extract all monthly parameters (using month suffix naming) and all constant parameters (using single column names) into the corresponding WGENParams fields.

**Validates: Requirements 2.1, 2.3, 2.4**

### Property 3: Parameter validation completeness

*For any* CSV file containing all required WGEN parameters with valid values, the parser should successfully create a WGENParams object that passes all validation checks (probability ranges, positive values, latitude bounds, monthly counts).

**Validates: Requirements 3.1**

### Property 4: Inline YAML parameter parsing preservation

*For any* YAML configuration with inline wgen_params dictionary, the YAMLParser should parse parameters directly from YAML and create a valid WGENParams object, maintaining backward compatibility with existing configurations.

**Validates: Requirements 4.1**

### Property 5: CSV file parameter loading

*For any* YAML configuration with wgen_params_file string, the YAMLParser should load parameters from the referenced CSV file and create a valid WGENParams object equivalent to inline specification.

**Validates: Requirements 4.2**

### Property 6: WGEN output format consistency

*For any* valid WGENParams and simulation date, the WGENClimateSource should generate climate data with precipitation in mm/day, temperatures in °C, and solar radiation in MJ/m²/day, with all values being finite numbers.

**Validates: Requirements 5.1, 5.2, 5.3, 5.4**

### Property 7: Monthly parameter selection correctness

*For any* simulation date and valid WGENParams, the WGEN algorithm should use the precipitation parameters (pww, pwd, alpha, beta) corresponding to the date's month (1-12 mapping to array indices 0-11).

**Validates: Requirements 5.5**

## Error Handling

### Error Categories

1. **File System Errors**
   - Missing CSV file
   - Unreadable CSV file
   - Invalid file permissions

2. **CSV Format Errors**
   - Missing header row
   - Wrong number of data rows (not exactly 1)
   - Missing required columns
   - Invalid column names

3. **Parameter Validation Errors**
   - Missing required parameters
   - Invalid parameter values (out of range)
   - Wrong number of monthly values
   - Type conversion errors

4. **Configuration Errors**
   - Both inline and CSV specified
   - Neither inline nor CSV specified
   - Invalid path format

### Error Handling Strategy

All errors will be caught at configuration parsing time (before simulation starts) and will raise exceptions with clear, actionable messages that:

1. Identify the specific problem
2. Indicate the location (file path, line number if applicable)
3. Suggest how to fix the issue
4. Reference documentation or examples when helpful

### Exception Hierarchy

```python
# Use existing Python exceptions
FileNotFoundError  # For missing CSV files
ValueError         # For invalid parameters, format errors, configuration errors
pd.errors.ParserError  # For CSV parsing errors (caught and re-raised as ValueError)
```

## Testing Strategy

### Dual Testing Approach

The implementation will use both unit testing and property-based testing to ensure comprehensive coverage:

- **Unit tests** verify specific examples, edge cases, and error conditions
- **Property tests** verify universal properties that should hold across all inputs
- Together they provide comprehensive coverage: unit tests catch concrete bugs, property tests verify general correctness

### Unit Testing

Unit tests will cover:

**CSV Parser (`test_wgen_csv_parser.py`):**
- Valid CSV file parsing with complete parameters
- Template CSV file generation
- Missing parameter detection
- Invalid parameter value detection
- Wrong number of data rows
- Missing header row
- File not found errors
- Path resolution (relative and absolute)

**YAML Parser Integration (`test_config.py` additions):**
- Inline YAML parameter parsing (existing functionality)
- CSV file parameter loading
- Conflicting configuration detection (both inline and CSV)
- Missing configuration detection (neither inline nor CSV)
- Relative path resolution from YAML directory
- Absolute path handling

**Integration Tests (`test_wgen_integration.py`):**
- End-to-end simulation with CSV parameters
- Comparison of inline vs CSV parameter results (should be identical)
- Multi-month simulation using CSV parameters
- Climate data output validation

### Property-Based Testing

Property-based tests will use the `hypothesis` library (already in requirements.txt) configured to run a minimum of 100 iterations per test.

**Test Library:** `hypothesis` for Python

**Property Tests (`test_wgen_csv_properties.py`):**

Each property-based test will be tagged with a comment explicitly referencing the correctness property from the design document using this format: `# Feature: wgen-csv-integration, Property {number}: {property_text}`

1. **Property 1 Test: CSV file loading and path resolution**
   - Generate random valid CSV files with WGEN parameters
   - Test with both relative and absolute paths
   - Verify successful loading and correct parameter extraction
   - Tag: `# Feature: wgen-csv-integration, Property 1: CSV file loading and path resolution`

2. **Property 2 Test: CSV parameter extraction correctness**
   - Generate random CSV files with varying parameter values
   - Verify all monthly and constant parameters are correctly extracted
   - Tag: `# Feature: wgen-csv-integration, Property 2: CSV parameter extraction correctness`

3. **Property 3 Test: Parameter validation completeness**
   - Generate random valid parameter sets
   - Verify all validation checks pass
   - Tag: `# Feature: wgen-csv-integration, Property 3: Parameter validation completeness`

4. **Property 4 Test: Inline YAML parameter parsing preservation**
   - Generate random inline YAML configurations
   - Verify backward compatibility
   - Tag: `# Feature: wgen-csv-integration, Property 4: Inline YAML parameter parsing preservation`

5. **Property 5 Test: CSV file parameter loading**
   - Generate random CSV files and YAML configs
   - Verify CSV loading produces valid WGENParams
   - Tag: `# Feature: wgen-csv-integration, Property 5: CSV file parameter loading`

6. **Property 6 Test: WGEN output format consistency**
   - Generate random valid WGENParams
   - Verify output units and finite values
   - Tag: `# Feature: wgen-csv-integration, Property 6: WGEN output format consistency`

7. **Property 7 Test: Monthly parameter selection correctness**
   - Generate random dates and parameters
   - Verify correct monthly parameter selection
   - Tag: `# Feature: wgen-csv-integration, Property 7: Monthly parameter selection correctness`

### Test Data Generators

For property-based testing, we'll create custom generators:

```python
from hypothesis import strategies as st

@st.composite
def valid_wgen_params(draw):
    """Generate valid WGEN parameters."""
    return {
        'pww': [draw(st.floats(min_value=0.0, max_value=1.0)) for _ in range(12)],
        'pwd': [draw(st.floats(min_value=0.0, max_value=1.0)) for _ in range(12)],
        'alpha': [draw(st.floats(min_value=0.1, max_value=5.0)) for _ in range(12)],
        'beta': [draw(st.floats(min_value=1.0, max_value=20.0)) for _ in range(12)],
        'txmd': draw(st.floats(min_value=-10.0, max_value=40.0)),
        'atx': draw(st.floats(min_value=0.0, max_value=20.0)),
        'txmw': draw(st.floats(min_value=-10.0, max_value=40.0)),
        'tn': draw(st.floats(min_value=-20.0, max_value=30.0)),
        'atn': draw(st.floats(min_value=0.0, max_value=15.0)),
        'cvtx': draw(st.floats(min_value=0.01, max_value=0.5)),
        'acvtx': draw(st.floats(min_value=0.0, max_value=0.2)),
        'cvtn': draw(st.floats(min_value=0.01, max_value=0.5)),
        'acvtn': draw(st.floats(min_value=0.0, max_value=0.2)),
        'rmd': draw(st.floats(min_value=5.0, max_value=30.0)),
        'ar': draw(st.floats(min_value=0.0, max_value=15.0)),
        'rmw': draw(st.floats(min_value=3.0, max_value=25.0)),
        'latitude': draw(st.floats(min_value=-90.0, max_value=90.0)),
        'random_seed': draw(st.one_of(st.none(), st.integers(min_value=0, max_value=10000)))
    }
```

### Test Coverage Goals

- Line coverage: > 90% for new code
- Branch coverage: > 85% for new code
- All error paths tested with unit tests
- All success paths tested with property tests

## Implementation Notes

### Backward Compatibility

The implementation maintains full backward compatibility:
- Existing YAML configurations with inline `wgen_params` continue to work unchanged
- No changes to `WGENParams`, `WGENState`, or `wgen_step()` function
- No changes to `WGENClimateSource` interface

### Performance Considerations

- CSV parsing happens once at configuration load time (not per timestep)
- Pandas is already a dependency, so no new dependencies required
- CSV files are small (1 header + 1 data row), so parsing is fast
- No impact on simulation performance

### Code Organization

The new `wgen_params.py` module keeps CSV parsing logic separate from:
- Core WGEN algorithm (`wgen.py`)
- Configuration parsing (`config.py`)
- Climate sources (`climate_sources.py`)

This separation of concerns makes the code easier to test and maintain.

### Documentation Requirements

1. **Module docstrings** - Clear explanation of CSV format and usage
2. **Function docstrings** - Complete parameter and return value documentation
3. **Example files** - Template CSV and example YAML configurations
4. **README updates** - Add section on WGEN CSV configuration
5. **Inline comments** - Explain complex parsing logic

## Dependencies

No new dependencies required. The implementation uses:
- `pandas` - Already in requirements.txt for CSV parsing
- `pathlib` - Python standard library for path handling
- `typing` - Python standard library for type hints
- `hypothesis` - Already in requirements.txt for property-based testing

## Migration Path

For users with existing inline YAML configurations:

1. **No action required** - Inline configurations continue to work
2. **Optional migration** - Users can convert to CSV format if desired:
   ```python
   from hydrosim.wgen_params import CSVWGENParamsParser
   
   # Create template
   CSVWGENParamsParser.create_template('my_params.csv')
   
   # Edit template with your parameters
   # Update YAML to reference CSV file
   ```

## Future Enhancements

Potential future improvements (not in scope for this feature):

1. **Parameter estimation** - Tool to estimate WGEN parameters from historical data
2. **Multiple parameter sets** - Support for multiple CSV files (e.g., different climate scenarios)
3. **Parameter validation tool** - Standalone script to validate CSV files
4. **GUI parameter editor** - Visual tool for editing WGEN parameters
5. **Parameter library** - Collection of pre-calibrated parameters for different regions
