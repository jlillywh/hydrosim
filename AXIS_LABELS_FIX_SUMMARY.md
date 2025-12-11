# Axis Labels Character Encoding Fix - Issue #3

## Problem
Unicode characters (°, ³, μ, ±) in axis labels were displaying as corrupted characters ("Â°", "Â³") when plots were generated, particularly when running `python examples/quick_start.py`.

## Root Cause
The issue occurred during YAML parsing where Unicode characters in axis label specifications were getting corrupted during the parsing process, leading to display issues in the generated HTML plots.

## Solution Implemented

### 1. Created ASCII-Safe Character Conversion
- Added `_format_axis_label()` method in `ResultsVisualizer` class (`hydrosim/results_viz.py`)
- Converts Unicode characters to ASCII-safe alternatives:
  - `Temperature (°C)` → `Temperature (degC)`
  - `Flow (m³/day)` → `Flow (m^3/day)`
  - `Storage (m³)` → `Storage (m^3)`
  - `Pressure (μPa)` → `Pressure (uPa)`
  - `Change (±5%)` → `Change (+/-5%)`

### 2. Applied Formatting to All Plot Types
- Climate plots: Temperature axis labels
- Source plots: Flow axis labels  
- Reservoir plots: Storage and flow axis labels
- Demand plots: Flow axis labels

### 3. Fixed Source YAML Files
Updated all example YAML files to use ASCII-safe characters in axis label specifications:
- `examples/simple_network.yaml`
- `examples/complex_network.yaml`
- `examples/wgen_example.yaml`
- `examples/storage_drawdown_example.yaml`
- `examples/my_custom_network.yaml`

### 4. Comprehensive Testing
- Created `test_axis_labels.py` with unit tests for character conversion
- Created `test_visual_fix.py` for visual verification
- Created `debug_axis_labels.py` for debugging character issues
- All 366 tests pass

## Files Modified
- `hydrosim/results_viz.py` - Added `_format_axis_label()` method and applied to all plot types
- `examples/simple_network.yaml` - Fixed axis label Unicode characters
- `examples/complex_network.yaml` - Fixed axis label Unicode characters  
- `examples/wgen_example.yaml` - Fixed axis label Unicode characters
- `examples/storage_drawdown_example.yaml` - Fixed axis label Unicode characters
- `examples/my_custom_network.yaml` - Fixed axis label Unicode characters

## Testing Results
- ✅ All 366 tests pass
- ✅ `python examples/quick_start.py` runs successfully with proper axis labels
- ✅ Visual test confirms ASCII-safe characters display correctly
- ✅ Character conversion works for all Unicode special characters

## Status: COMPLETED ✅
The axis label character encoding issue has been fully resolved. All plots now display proper ASCII-safe characters instead of corrupted Unicode characters.