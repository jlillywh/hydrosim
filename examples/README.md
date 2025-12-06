# HydroSim Configuration Examples

This directory contains example YAML configuration files and Python scripts demonstrating how to set up and run water network simulations using HydroSim.

## Getting Started

### Quick Start (5 minutes)

1. Make sure you've installed HydroSim and its dependencies (see main README.md)

2. Run the quick start example:
   ```bash
   python examples/quick_start.py
   ```

3. Check the `output/` directory for results:
   - `simple_network_flows.csv` - Flow values for all links
   - `simple_network_storage.csv` - Storage volumes and properties
   - `simple_network_demands.csv` - Demand requests, deliveries, and deficits
   - `simple_network_sources.csv` - Source inflow values
   - `complex_network_all.json` - Complete results in JSON format

4. Modify the YAML files to create your own network configuration

### Learning Path

1. **Start here**: Run `quick_start.py` to see the complete workflow
2. **Understand configuration**: Read through `simple_network.yaml` with inline comments
3. **Explore features**: Examine `complex_network.yaml` for advanced options
4. **Programmatic usage**: Study `results_output_example.py` for Python API
5. **Create your own**: Use this README as a reference for configuration options

## Files

### Configuration Files

#### simple_network.yaml
A basic example showing:
- Single storage reservoir with drawdown
- Municipal demand
- Time series climate data
- Simple link connection

**Best for**: Learning the basics, testing simple scenarios

#### complex_network.yaml
A more advanced example showing:
- Multiple storage nodes with independent drawdown
- Source node with time series inflow
- Multiple demand types (municipal and agricultural)
- Junction nodes for flow routing
- Links with hydraulic models (weir)
- Links with controls (fractional and absolute)

**Best for**: Understanding advanced features, real-world applications

#### storage_drawdown_example.yaml
A focused example demonstrating storage drawdown scenarios:
- Drawdown when demand exceeds inflow
- Refill when inflow exceeds demand
- Dead pool protection (minimum storage)
- Capacity constraints and automatic spilling
- Cost-based prioritization (demands > storage > spilling)

**Best for**: Understanding storage operations, testing drawdown behavior

### Data Files

#### climate_data.csv
Sample climate data for 30 days including:
- Date
- Precipitation (mm)
- Maximum temperature (°C)
- Minimum temperature (°C)
- Solar radiation (MJ/m²/day)

#### inflow_data.csv
Sample inflow time series for 30 days:
- Date
- Inflow volume (m³/day)

#### wgen_params_template.csv
Template CSV file containing all 62 WGEN (Weather GENerator) parameters for stochastic climate generation. This file provides realistic parameter values calibrated for a mid-latitude location (approximately 45°N) with a temperate climate.

**Parameter Categories:**

1. **Precipitation Parameters (48 columns):**
   - `pww_jan` through `pww_dec` - Probability of wet day following wet day (0-1)
   - `pwd_jan` through `pwd_dec` - Probability of wet day following dry day (0-1)
   - `alpha_jan` through `alpha_dec` - Gamma distribution shape parameter for precipitation amount (>0)
   - `beta_jan` through `beta_dec` - Gamma distribution scale parameter for precipitation amount (>0)

2. **Temperature Parameters (9 columns):**
   - `txmd` - Mean maximum temperature on dry days (°C)
   - `atx` - Amplitude of maximum temperature annual variation (°C)
   - `txmw` - Mean maximum temperature on wet days (°C)
   - `tn` - Mean minimum temperature (°C)
   - `atn` - Amplitude of minimum temperature annual variation (°C)
   - `cvtx` - Coefficient of variation for maximum temperature (0-1)
   - `acvtx` - Amplitude of CV variation for maximum temperature (0-1)
   - `cvtn` - Coefficient of variation for minimum temperature (0-1)
   - `acvtn` - Amplitude of CV variation for minimum temperature (0-1)

3. **Solar Radiation Parameters (3 columns):**
   - `rmd` - Mean solar radiation on dry days (MJ/m²/day)
   - `ar` - Amplitude of solar radiation annual variation (MJ/m²/day)
   - `rmw` - Mean solar radiation on wet days (MJ/m²/day)

4. **Location Parameters (1 column):**
   - `latitude` - Site latitude in decimal degrees (-90 to 90)

5. **Optional Parameters (1 column):**
   - `random_seed` - Random seed for reproducibility (integer or empty)

**Template Values:**
The template uses realistic values for a mid-latitude temperate climate:
- Winter months (Dec-Feb): Higher precipitation probability, lower temperatures
- Summer months (Jun-Aug): Lower precipitation probability, higher temperatures
- Spring/Fall (Mar-May, Sep-Nov): Transitional values
- Latitude: 45.0°N (typical for northern US, southern Canada, central Europe)

**Usage:**
1. Copy this template to create your own parameter file
2. Modify values to match your study location's climate
3. Reference the CSV file in your YAML configuration using `wgen_params_file`
4. See WGEN Climate Configuration section below for details

### Python Examples

#### quick_start.py
**Recommended starting point!** Complete workflow demonstration showing:
- How to load YAML configuration
- How to validate network topology
- How to set up and run simulation
- How to export and analyze results
- Both simple and complex network examples

Run with: `python examples/quick_start.py`

#### results_output_example.py
Programmatic usage example demonstrating:
- How to build networks in Python code
- How to run a simulation
- How to use ResultsWriter to capture results
- How to export results in CSV and JSON formats
- How to access and analyze simulation results

Run with: `python examples/results_output_example.py`

#### storage_drawdown_demo.py
**Storage drawdown demonstration!** Shows three key scenarios:
- Drawdown: Storage releases water when demand exceeds inflow
- Refill: Storage fills when inflow exceeds demand
- Dead pool: Minimum storage level is protected

Each scenario demonstrates the virtual link architecture in action with clear before/after comparisons.

Run with: `python examples/storage_drawdown_demo.py`

## Configuration Structure

All HydroSim configuration files follow this structure:

```yaml
climate:
  source_type: timeseries | wgen
  # ... climate-specific parameters

nodes:
  node_id:
    type: storage | junction | source | demand
    # ... node-specific parameters

links:
  link_id:
    source: source_node_id
    target: target_node_id
    capacity: float
    cost: float
    # ... optional control and hydraulic parameters
```

## Node Types

### Storage Node
Represents a reservoir or tank with mass storage and active drawdown capability.

**Required Parameters:**
- `initial_storage` - Starting storage volume (m³)
- `max_storage` - Maximum storage capacity (m³)
- `min_storage` - Dead pool level, minimum storage that cannot be released (m³)
- `eav_table` - Elevation-area-volume relationship for evaporation calculations

**Storage Drawdown:**
The solver automatically enables active drawdown, allowing the reservoir to release water to meet downstream demands even when inflow is insufficient. The optimizer balances meeting demands, maintaining storage, and spilling excess water based on a cost hierarchy.

```yaml
reservoir:
  type: storage
  initial_storage: 50000.0  # m³
  max_storage: 60000.0      # m³ (maximum capacity)
  min_storage: 0.0          # m³ (dead pool)
  eav_table:
    elevations: [100.0, 110.0, 120.0]  # meters
    areas: [1000.0, 2000.0, 3000.0]    # m²
    volumes: [0.0, 10000.0, 60000.0]   # m³
```

### Junction Node
Stateless connection point with no storage.

```yaml
junction1:
  type: junction
```

### Source Node
Water source with pluggable generation strategy.

**Time Series Strategy:**
```yaml
catchment:
  type: source
  strategy: timeseries
  filepath: inflow_data.csv
  column: inflow
```

**Hydrology Strategy:**
```yaml
catchment:
  type: source
  strategy: hydrology
  area: 1000000.0  # m²
  snow17_params:
    melt_factor: 2.5
    rain_temp: 2.0
    snow_temp: 0.0
  awbm_params:
    c1: 0.134
    c2: 0.433
    c3: 0.433
    a1: 0.3
    a2: 0.3
    a3: 0.4
    baseflow_coeff: 0.35
    surface_coeff: 0.1
```

### Demand Node
Water demand with pluggable demand model.

**Municipal Demand:**
```yaml
city:
  type: demand
  demand_type: municipal
  population: 10000.0
  per_capita_demand: 0.2  # m³/person/day
```

**Agricultural Demand:**
```yaml
farm:
  type: demand
  demand_type: agriculture
  area: 50000.0           # m²
  crop_coefficient: 0.8
```

## Link Configuration

### Basic Link
```yaml
link1:
  source: node1
  target: node2
  capacity: 1000.0  # m³/day
  cost: 1.0         # cost per m³
```

### Link with Hydraulic Model

**Weir:**
```yaml
weir_link:
  source: reservoir
  target: junction
  capacity: 5000.0
  cost: 1.0
  hydraulic:
    type: weir
    coefficient: 1.5
    length: 10.0
    crest_elevation: 105.0
```

**Pipe:**
```yaml
pipe_link:
  source: junction1
  target: junction2
  capacity: 1000.0
  cost: 1.0
  hydraulic:
    type: pipe
    capacity: 800.0
```

### Link with Control

**Fractional Control:**
```yaml
controlled_link:
  source: node1
  target: node2
  capacity: 1000.0
  cost: 1.0
  control:
    type: fractional
    fraction: 0.5  # Throttle to 50%
```

**Absolute Control:**
```yaml
controlled_link:
  source: node1
  target: node2
  capacity: 1000.0
  cost: 1.0
  control:
    type: absolute
    max_flow: 500.0  # Hard cap
```

**Switch Control:**
```yaml
controlled_link:
  source: node1
  target: node2
  capacity: 1000.0
  cost: 1.0
  control:
    type: switch
    is_on: true  # or false
```

## Climate Configuration

### Time Series Climate
```yaml
climate:
  source_type: timeseries
  filepath: climate_data.csv
  date_col: date        # optional, default: 'date'
  precip_col: precip    # optional, default: 'precip'
  tmax_col: t_max       # optional, default: 't_max'
  tmin_col: t_min       # optional, default: 't_min'
  solar_col: solar      # optional, default: 'solar'
  site:
    latitude: 45.0
    elevation: 1000.0
```

### WGEN Stochastic Climate

WGEN (Weather GENerator) generates synthetic daily climate data using stochastic methods. Parameters can be specified either inline in YAML or in a separate CSV file.

**Option 1: CSV Parameter File (Recommended)**
```yaml
climate:
  source_type: wgen
  start_date: '2024-01-01'
  wgen_params_file: wgen_params_template.csv  # Relative to YAML file location
  site:
    latitude: 45.0
    elevation: 1000.0
```

**Option 2: Inline YAML Parameters**
```yaml
climate:
  source_type: wgen
  start_date: '2024-01-01'
  wgen_params:
    pww: [0.6, 0.6, 0.5, ...]  # 12 monthly values
    pwd: [0.3, 0.3, 0.2, ...]  # 12 monthly values
    alpha: [0.5, 0.5, ...]     # 12 monthly values
    beta: [2.0, 2.0, ...]      # 12 monthly values
    txmd: 25.0
    atx: 5.0
    txmw: 23.0
    tn: 15.0
    atn: 3.0
    cvtx: 0.1
    acvtx: 0.05
    cvtn: 0.1
    acvtn: 0.05
    rmd: 20.0
    ar: 5.0
    rmw: 15.0
    latitude: 45.0
  site:
    latitude: 45.0
    elevation: 1000.0
```

**CSV File Benefits:**
- Easier to manage 62 parameters in spreadsheet format
- Reusable across multiple simulations
- Can be version controlled separately
- Reduces YAML file complexity
- See `wgen_params_template.csv` for complete parameter list and documentation

**Important Notes:**
- Use either `wgen_params` (inline) OR `wgen_params_file` (CSV), not both
- CSV file path can be relative (to YAML file) or absolute
- All 62 parameters must be present in CSV file
- Monthly parameters use suffix naming: `pww_jan`, `pww_feb`, etc.
- See `wgen_params_template.csv` for parameter descriptions and valid ranges

## Usage

### Using YAML Configuration Files

To use these configuration files with HydroSim:

```python
from hydrosim.config import YAMLParser

# Parse configuration
parser = YAMLParser('examples/simple_network.yaml')
network, climate_source, site_config = parser.parse()

# Use the parsed components to set up simulation
# (See simulation examples for complete usage)
```

### Capturing and Exporting Results

HydroSim provides a `ResultsWriter` class for structured output of simulation results:

```python
from hydrosim import ResultsWriter, SimulationEngine

# Create results writer (CSV or JSON format)
writer = ResultsWriter(output_dir="output", format="csv")

# Run simulation and capture results
for _ in range(num_timesteps):
    result = engine.step()
    writer.add_timestep(result)

# Write results to files
files = writer.write_all(prefix="simulation")
```

**CSV Format Output:**
- `{prefix}_flows.csv` - Flow values for all links at each timestep
- `{prefix}_storage.csv` - Storage volumes and properties for all StorageNodes
- `{prefix}_demands.csv` - Demand requests, deliveries, and deficits for all DemandNodes
- `{prefix}_sources.csv` - Inflow values for all SourceNodes

**JSON Format Output:**
- `{prefix}_all.json` - All simulation data in structured JSON format

All outputs are at daily resolution as required by the framework.

For a complete working example, see `results_output_example.py`.

## Storage Drawdown Scenarios

HydroSim's storage drawdown feature enables realistic reservoir operations. Here are common scenarios:

### Drawdown Scenario
When inflow is insufficient to meet demand, the reservoir releases stored water:

```yaml
# Reservoir with 50,000 m³ storage, no inflow, 2,000 m³/day demand
# Result: Storage decreases to 48,000 m³, demand is fully met
```

### Refill Scenario
When inflow exceeds demand, excess water is stored:

```yaml
# Reservoir with 0 m³ storage, 5,000 m³/day inflow, no demand
# Result: Storage increases to 5,000 m³
```

### Dead Pool Protection
The minimum storage level (dead pool) is enforced:

```yaml
reservoir:
  min_storage: 10000.0  # Cannot release water below this level
```

### Capacity Constraints
Maximum storage capacity is enforced, with excess water spilled:

```yaml
reservoir:
  max_storage: 60000.0  # Excess water above this level is spilled
```

### Priority Hierarchy
The solver prioritizes water allocation:
1. **Meet demands first** (cost = -1000) - Highest priority
2. **Store water** (cost = -1) - Medium priority
3. **Spill excess** (cost = 0) - Lowest priority

This ensures critical water needs are satisfied before filling reservoirs, and water is stored before being spilled.

## Common Patterns

### Creating a Simple Network

The minimal configuration requires:
1. Climate configuration (source and site parameters)
2. At least two nodes (e.g., storage and demand)
3. At least one link connecting the nodes

```yaml
climate:
  source_type: timeseries
  filepath: climate_data.csv
  site:
    latitude: 45.0
    elevation: 1000.0

nodes:
  reservoir:
    type: storage
    initial_storage: 50000.0
    eav_table:
      elevations: [100.0, 120.0]
      areas: [1000.0, 3000.0]
      volumes: [0.0, 60000.0]
  
  demand:
    type: demand
    demand_type: municipal
    population: 10000.0
    per_capita_demand: 0.2

links:
  delivery:
    source: reservoir
    target: demand
    capacity: 3000.0
    cost: 1.0
```

### Adding Controls to Links

Controls allow you to model operational rules:

```yaml
# Throttle to 80% of capacity
control:
  type: fractional
  fraction: 0.8

# Hard cap at specific flow rate
control:
  type: absolute
  max_flow: 500.0

# Binary on/off
control:
  type: switch
  is_on: true
```

### Adding Hydraulic Models

Hydraulic models calculate capacity based on system state:

```yaml
# Weir flow (depends on upstream head)
hydraulic:
  type: weir
  coefficient: 1.5
  length: 10.0
  crest_elevation: 105.0

# Pipe flow (fixed capacity)
hydraulic:
  type: pipe
  capacity: 800.0
```

## Troubleshooting

### Configuration Errors

**Error: "Link references non-existent node"**
- Check that all `source` and `target` fields in links match node IDs exactly
- Node IDs are case-sensitive

**Error: "Invalid YAML syntax"**
- Ensure proper indentation (use spaces, not tabs)
- Check that all colons have a space after them
- Verify that lists use proper YAML syntax with square brackets or dashes

**Error: "Fractional control value must be between 0.0 and 1.0"**
- Check that `fraction` parameter in fractional controls is in valid range
- Use absolute control for values outside this range

### Runtime Errors

**Error: "Infeasible network flow"**
- Check that demands can be satisfied by available sources
- Verify that link capacities are sufficient
- Ensure storage nodes have adequate initial storage

**Error: "Negative storage"**
- Initial storage may be too low
- Evaporation losses may be too high
- Outflow may exceed available storage

**Error: "Missing climate data"**
- Ensure CSV file has enough rows for simulation period
- Check that date ranges match simulation period
- Verify column names match configuration

### Data File Issues

**Climate data CSV format:**
```csv
date,precip,t_max,t_min,solar
2024-01-01,2.5,18.0,8.0,15.5
2024-01-02,0.0,20.0,10.0,16.2
```

**Inflow data CSV format:**
```csv
date,inflow
2024-01-01,150.0
2024-01-02,120.0
```

**Tips:**
- Dates should be in YYYY-MM-DD format
- All numeric values should be positive (except temperatures)
- No missing values allowed
- Column names must match exactly (case-sensitive)

## Tips and Best Practices

1. **Start simple**: Begin with a basic network and add complexity gradually
2. **Validate early**: Run validation before long simulations
3. **Check units**: All volumes in m³, flows in m³/day, areas in m², elevations in m
4. **Use meaningful IDs**: Node and link IDs should be descriptive
5. **Comment your config**: Add inline comments to explain design decisions
6. **Version control**: Keep YAML files in version control (e.g., git)
7. **Test with short runs**: Use 7-30 days for testing before long simulations
8. **Monitor storage**: Watch storage levels to ensure they stay in valid range
9. **Check mass balance**: Total inflow should roughly equal outflow + storage change
10. **Export results**: Always use ResultsWriter to capture detailed results

## Additional Resources

- **Main README**: See `../README.md` for installation and core concepts
- **Design Document**: See `.kiro/specs/hydrosim-framework/design.md` for architecture details
- **Requirements**: See `.kiro/specs/hydrosim-framework/requirements.md` for specifications
- **Tests**: See `tests/` directory for usage examples in test code
