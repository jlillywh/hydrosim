# Simulation Configuration Feature - Issue #5

## Overview
Added the ability to specify simulation start and end dates directly in YAML configuration files, eliminating the need to hardcode simulation periods in Python scripts.

## Feature Description
Users can now configure simulation periods in their YAML files using a new `simulation` section with flexible options:

### Option 1: Date Range (start_date + end_date)
```yaml
simulation:
  start_date: "2024-01-01"  # Simulation start date (YYYY-MM-DD)
  end_date: "2024-12-31"    # Simulation end date (YYYY-MM-DD)
```

### Option 2: Fixed Duration (start_date + num_timesteps)
```yaml
simulation:
  start_date: "2024-01-01"  # Simulation start date (YYYY-MM-DD)
  num_timesteps: 365        # Number of days to simulate
```

### Option 3: Defaults (optional section)
```yaml
# No simulation section - uses defaults:
# start_date: 2024-01-01
# num_timesteps: 30
```

## Implementation Details

### 1. YAML Parser Enhancement
- Added `_parse_simulation_config()` method to `YAMLParser` class
- Validates date formats (YYYY-MM-DD)
- Ensures logical consistency (end_date > start_date)
- Prevents conflicting specifications (both end_date and num_timesteps)
- Calculates num_timesteps from date range when end_date is provided

### 2. NetworkGraph Extension
- Added `simulation_config` attribute to store parsed configuration
- Contains: `start_date`, `end_date`, `num_timesteps`

### 3. Quick Start Integration
- Updated `examples/quick_start.py` to use YAML-specified dates
- Displays simulation period information in console output
- Automatically uses the correct start date for ClimateEngine

### 4. Example Files Updated
All example YAML files now include simulation configuration:
- `examples/simple_network.yaml`: 30-day simulation using end_date
- `examples/complex_network.yaml`: 30-day simulation using num_timesteps  
- `examples/wgen_example.yaml`: Full year simulation (365 days)
- `examples/storage_drawdown_example.yaml`: 90-day simulation

## Validation Rules

### Date Format
- Must use ISO format: `YYYY-MM-DD` (e.g., "2024-01-01")
- Invalid formats raise `ValueError` with helpful message

### Logical Consistency
- `end_date` must be after `start_date`
- Cannot specify both `end_date` and `num_timesteps`
- `num_timesteps` must be positive integer

### Default Behavior
- `start_date`: defaults to "2024-01-01"
- `num_timesteps`: defaults to 30 days if no end_date specified
- Fully backward compatible - existing YAML files work unchanged

## Usage Examples

### Before (hardcoded in Python)
```python
# Old way - hardcoded dates
climate_engine = ClimateEngine(climate_source, site_config, datetime(2024, 1, 1))
num_days = 30  # Hardcoded
for day in range(num_days):
    result = engine.step()
```

### After (configured in YAML)
```python
# New way - dates from YAML
sim_config = network.simulation_config
start_date = sim_config['start_date']
num_days = sim_config['num_timesteps']

climate_engine = ClimateEngine(climate_source, site_config, start_date)
for day in range(num_days):
    result = engine.step()
```

## Console Output Enhancement
The quick_start.py now shows simulation period information:

```
[Step 3] Setting up simulation engine...
   ✓ Simulation engine initialized (start: 2024-01-01)

[Step 5] Running simulation...
   Simulating from 2024-01-01 to 2024-01-30...  # end_date specified
   # OR
   Simulating from 2024-01-01 for 30 days...    # num_timesteps specified
```

## Testing
- Comprehensive test suite in `tests/test_simulation_config.py`
- Tests all configuration options and validation rules
- All 375 tests pass (366 existing + 9 new)

## Backward Compatibility
- Existing YAML files without simulation section work unchanged
- Default values ensure no breaking changes
- Python scripts can still override dates if needed

## Files Modified
- `hydrosim/config.py`: Added simulation config parsing
- `examples/quick_start.py`: Updated to use YAML dates
- `examples/*.yaml`: Added simulation sections
- `tests/test_simulation_config.py`: Comprehensive test coverage

## Benefits
1. **User-friendly**: Configure simulation periods in YAML, not code
2. **Flexible**: Choose between date ranges or fixed durations  
3. **Validated**: Automatic validation prevents configuration errors
4. **Consistent**: Same approach across all example files
5. **Backward compatible**: No breaking changes to existing workflows

## Status: COMPLETED ✅
Issue #5 has been fully implemented and tested. Users can now specify simulation start and end dates directly in their YAML configuration files.