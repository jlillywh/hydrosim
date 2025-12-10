# HydroSim Framework

A Python-based water resources planning framework for daily timestep simulation of complex, interconnected water systems.

## Overview

HydroSim enables water resources engineers to model and analyze water distribution networks by combining:
- **Process-based simulation** - Hydrology, evaporation, and water demands
- **Network optimization** - Minimum cost flow allocation
- **Constraint-based modeling** - Physical, hydraulic, and operational limits

The framework operates on daily timesteps and uses a constraint-stacking approach where components calculate their own feasible limits before network-wide optimization.

## Key Features

✓ **Multiple Node Types**
  - Storage nodes (reservoirs, tanks) with elevation-area-volume relationships and active drawdown
  - Junction nodes for flow routing
  - Source nodes with pluggable generation strategies (time series, hydrology models)
  - Demand nodes with pluggable demand models (municipal, agricultural)

✓ **Flexible Link Modeling**
  - Physical capacity constraints
  - Hydraulic models (weir equations, pipe flow)
  - Control systems (fractional, absolute, switch)
  - Cost-based optimization

✓ **Climate Integration**
  - Time series climate data from CSV files
  - Stochastic weather generation (WGEN)
  - Hargreaves ET0 calculation
  - Daily timestep resolution

✓ **Network Optimization**
  - Minimum cost network flow solver
  - Mass balance conservation
  - Constraint satisfaction
  - Stepwise greedy optimization (no lookahead)
  - Active storage drawdown using virtual link architecture

✓ **Configuration & Results**
  - Human-readable YAML configuration files
  - Topology validation
  - Structured results output (CSV and JSON)
  - Daily resolution time series

✓ **Interactive Visualizations**
  - Network topology maps with colored nodes by type
  - Automated time series plots (climate, sources, reservoirs, demands)
  - Dual-axis support for multi-variable plots
  - YAML-configurable plot generation
  - Interactive Plotly charts with zoom, pan, and hover tooltips
  - Automatic browser opening for instant results viewing

## Use Cases

HydroSim is designed for:
- Water supply system planning and analysis
- Reservoir operation studies
- Demand management scenarios
- Climate impact assessment
- Multi-objective water allocation
- Educational purposes and research

## Storage Drawdown Feature

HydroSim implements **active storage drawdown** using a virtual link architecture that treats final storage as a decision variable in the network flow optimization. This enables realistic reservoir operations where storage nodes can:

- **Release water to meet demands** - Draw down storage when inflow is insufficient
- **Refill from excess inflow** - Store water when supply exceeds demand
- **Respect capacity constraints** - Enforce maximum storage and dead pool (minimum) levels
- **Prioritize water allocation** - Meet demands before storing, store before spilling

### How It Works

The solver creates virtual components for each storage node:
1. **Carryover Link** - Represents water staying in storage from one timestep to the next
2. **Virtual Sink** - Represents the future state of the storage node

The carryover link flow becomes the decision variable for final storage level, allowing the optimizer to balance:
- Meeting downstream demands (highest priority, cost = -1000)
- Maintaining storage for future use (medium priority, cost = -1)
- Spilling excess water (lowest priority, cost = 0)

### Configuration

Storage nodes require `max_storage` and `min_storage` (dead pool) parameters:

```yaml
reservoir:
  type: storage
  initial_storage: 50000.0  # m³
  max_storage: 60000.0      # m³ (maximum capacity)
  min_storage: 0.0          # m³ (dead pool - minimum level)
  eav_table:
    elevations: [100.0, 110.0, 120.0]
    areas: [1000.0, 2000.0, 3000.0]
    volumes: [0.0, 10000.0, 60000.0]
```

The solver automatically handles drawdown and refill operations based on network conditions. No additional configuration is needed - the virtual link architecture is transparent to users.

## Project Structure

```
hydrosim/
├── __init__.py          # Package initialization
├── nodes.py             # Node abstractions (Storage, Junction, Source, Demand)
├── links.py             # Link implementation for water transport
├── solver.py            # Network solver abstraction
├── climate.py           # Climate data structures and engine
├── climate_engine.py    # Climate engine implementation
├── climate_sources.py   # Climate data sources (TimeSeries, WGEN)
├── config.py            # Configuration parsing and network graph
├── strategies.py        # Generator and demand model strategies
├── controls.py          # Control system abstractions
├── hydraulics.py        # Hydraulic model abstractions
├── simulation.py        # Simulation engine for timestep orchestration
├── results.py           # Results output system (CSV/JSON)
└── wgen.py              # WGEN stochastic weather generator

tests/
├── __init__.py
└── test_structure.py    # Basic structure validation tests
```

## Installation

### Option 1: Install from PyPI (Recommended)

HydroSim is available on the Python Package Index (PyPI). Install it with pip:

```bash
pip install hydrosim
```

This will automatically install all required dependencies.

**Verify installation:**
```bash
python -c "import hydrosim; print(f'HydroSim {hydrosim.__version__} installed successfully!')"
```

### Option 2: Development Installation

For development or to access the latest features:

1. **Clone the repository:**
```bash
git clone https://github.com/jlillywh/hydrosim.git
cd hydrosim
```

2. **Create a virtual environment:**
```bash
python -m venv .venv
```

3. **Activate the virtual environment:**
- **Windows**: `.venv\Scripts\activate`
- **Unix/MacOS**: `source .venv/bin/activate`

4. **Install in development mode:**
```bash
pip install -e .
```

5. **Install development dependencies (optional):**
```bash
pip install -e .[dev]
```

6. **Verify installation:**
```bash
python verify_installation.py  # Comprehensive verification script
# OR
pytest  # Run tests (if dev dependencies installed)
# OR  
python -c "import hydrosim; print(hydrosim.__version__)"
```

### Prerequisites

- **Python 3.8 or higher**
- **pip package manager**

### Dependencies

HydroSim automatically installs these required packages:
- **NumPy** (≥1.24.0) - Numerical computations
- **Pandas** (≥2.0.0) - Data manipulation and time series
- **SciPy** (≥1.10.0) - Optimization (linear programming)
- **NetworkX** (≥3.0) - Graph algorithms and network analysis
- **PyYAML** (≥6.0) - YAML configuration parsing
- **Plotly** (≥5.0.0) - Interactive visualizations
- **Requests** (≥2.25.0) - HTTP requests for climate data fetching

### Development Dependencies (Optional)

Install with `pip install hydrosim[dev]`:
- **pytest** (≥7.4.0) - Testing framework
- **hypothesis** (≥6.82.0) - Property-based testing
- **pytest-cov** (≥4.1.0) - Test coverage reporting

## Running Tests

```bash
pytest
```

For verbose output:
```bash
pytest -v
```

For coverage report:
```bash
pytest --cov=hydrosim
```

## WGEN Stochastic Weather Generation

HydroSim includes the WGEN (Weather GENerator) algorithm for generating synthetic daily climate data. WGEN produces precipitation, maximum temperature, minimum temperature, and solar radiation values that drive hydrological processes in your simulations.

### Why Use WGEN?

WGEN is useful when you need to:
- Generate synthetic climate data for locations without historical records
- Create long-term climate scenarios for risk analysis
- Test system behavior under stochastic weather conditions
- Perform Monte Carlo simulations with different weather realizations

### CSV Parameter Configuration

WGEN requires 62 parameters to define weather statistics. To simplify configuration, HydroSim supports loading these parameters from CSV files instead of embedding them in YAML.

#### Benefits of CSV Configuration

✓ **Maintainable** - Separate parameter files from network configuration  
✓ **Reusable** - Share parameter sets across multiple simulations  
✓ **Organized** - Manage complex parameter sets in spreadsheet format  
✓ **Version Control** - Track parameter changes independently  

#### Quick Start with CSV Parameters

1. **Create a template CSV file:**
```python
from hydrosim.wgen_params import CSVWGENParamsParser

CSVWGENParamsParser.create_template('my_wgen_params.csv')
```

2. **Edit the CSV file** with parameters for your location (see parameter descriptions below)

3. **Reference the CSV in your YAML configuration:**
```yaml
climate:
  source_type: wgen
  start_date: "2024-01-01"
  wgen_params_file: my_wgen_params.csv  # Relative to YAML file location
  site:
    latitude: 45.0
    elevation: 1000.0
```

4. **Run your simulation** - parameters are loaded automatically

#### CSV File Format

The CSV file must have:
- **Header row** with parameter names as column identifiers
- **One data row** with parameter values
- **Monthly parameters** with month suffixes: `pww_jan`, `pww_feb`, ..., `pww_dec`
- **Constant parameters** without suffixes: `txmd`, `atx`, `latitude`

Example structure:
```csv
pww_jan,pww_feb,pww_mar,...,latitude,random_seed
0.45,0.42,0.40,...,45.0,42
```

### WGEN Parameter Reference

#### Precipitation Parameters (48 total)

**PWW (Probability Wet|Wet)** - 12 monthly values  
Probability that a wet day follows a wet day  
- Range: [0, 1]  
- Higher values = longer wet spells  
- Example: `pww_jan=0.45` means 45% chance of rain after a rainy day in January

**PWD (Probability Wet|Dry)** - 12 monthly values  
Probability that a wet day follows a dry day  
- Range: [0, 1]  
- Higher values = more frequent rain events  
- Example: `pwd_jan=0.25` means 25% chance of rain after a dry day in January

**ALPHA (Gamma Shape)** - 12 monthly values  
Shape parameter for gamma distribution of precipitation amounts  
- Range: (0, ∞), typically [0.5, 3.0]  
- Lower values = more variable precipitation amounts  
- Higher values = more consistent precipitation amounts

**BETA (Gamma Scale)** - 12 monthly values  
Scale parameter for gamma distribution of precipitation amounts (mm)  
- Range: (0, ∞), typically [2.0, 15.0]  
- Controls mean precipitation amount on wet days  
- Mean precipitation = ALPHA × BETA

#### Temperature Parameters (9 total)

**TXMD** - Mean maximum temperature on dry days (°C)  
- Range: [-50, 50], typically [10, 35]  
- Annual mean, seasonal variation added via Fourier function

**ATX** - Amplitude of seasonal variation in maximum temperature (°C)  
- Range: [0, 30], typically [5, 15]  
- Difference between summer and winter max temperatures

**TXMW** - Mean maximum temperature on wet days (°C)  
- Range: [-50, 50], typically [8, 30]  
- Usually 1-3°C cooler than TXMD

**TN** - Mean minimum temperature (°C)  
- Range: [-60, 40], typically [0, 20]  
- Annual mean, seasonal variation added via Fourier function

**ATN** - Amplitude of seasonal variation in minimum temperature (°C)  
- Range: [0, 25], typically [5, 12]  
- Difference between summer and winter min temperatures

**CVTX** - Coefficient of variation for maximum temperature  
- Range: [0.01, 0.5], typically [0.05, 0.15]  
- Controls day-to-day variability in max temperature  
- Higher values = more variable temperatures

**ACVTX** - Amplitude of seasonal variation in CVTX  
- Range: [0, 0.2], typically [0.02, 0.08]  
- Allows temperature variability to change seasonally

**CVTN** - Coefficient of variation for minimum temperature  
- Range: [0.01, 0.5], typically [0.05, 0.15]  
- Controls day-to-day variability in min temperature

**ACVTN** - Amplitude of seasonal variation in CVTN  
- Range: [0, 0.2], typically [0.02, 0.08]  
- Allows temperature variability to change seasonally

#### Radiation Parameters (3 total)

**RMD** - Mean solar radiation on dry days (MJ/m²/day)  
- Range: [0, 40], typically [12, 25]  
- Higher at lower latitudes and in summer

**AR** - Amplitude of seasonal variation in solar radiation (MJ/m²/day)  
- Range: [0, 20], typically [3, 10]  
- Larger at higher latitudes

**RMW** - Mean solar radiation on wet days (MJ/m²/day)  
- Range: [0, 35], typically [8, 18]  
- Usually 20-40% lower than RMD due to cloud cover

#### Location Parameters (1 total)

**LATITUDE** - Site latitude in degrees  
- Range: [-90, 90]  
- Used for seasonal timing in Fourier functions  
- Positive = Northern Hemisphere, Negative = Southern Hemisphere

#### Optional Parameters (1 total)

**RANDOM_SEED** - Random seed for reproducibility  
- Integer value or empty/blank  
- Use same seed to reproduce exact weather sequences  
- Leave empty for different sequences each run

### Parameter Estimation Guidelines

To estimate WGEN parameters for your location:

1. **Obtain historical daily weather data** (at least 20-30 years recommended)
2. **Calculate monthly statistics:**
   - PWW: Count transitions from wet→wet days by month
   - PWD: Count transitions from dry→wet days by month
   - ALPHA, BETA: Fit gamma distribution to wet day precipitation amounts by month
3. **Calculate temperature statistics:**
   - TXMD, TN: Mean temperatures by wet/dry status
   - ATX, ATN: Fit Fourier functions to seasonal temperature patterns
   - CVTX, CVTN: Calculate coefficient of variation by month
4. **Calculate radiation statistics:**
   - RMD, RMW: Mean radiation by wet/dry status
   - AR: Fit Fourier function to seasonal radiation pattern

Alternatively, use published WGEN parameters for nearby locations with similar climate.

### Inline YAML Configuration (Alternative)

You can still specify parameters directly in YAML if preferred:

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

**Note:** You cannot specify both `wgen_params` and `wgen_params_file` - choose one method.

### Migration from Inline to CSV

If you have existing YAML configurations with inline parameters:

1. **No action required** - Inline configurations continue to work
2. **Optional migration** to CSV format:
   ```python
   from hydrosim.wgen_params import CSVWGENParamsParser
   
   # Create template
   CSVWGENParamsParser.create_template('my_params.csv')
   
   # Edit the CSV file with your inline parameter values
   # Update YAML to use: wgen_params_file: my_params.csv
   # Remove the wgen_params: dictionary from YAML
   ```

### Example Files

See the `examples/` directory for complete working examples:
- `wgen_params_template.csv` - Template CSV with realistic mid-latitude parameters
- `wgen_example.yaml` - YAML configuration using CSV parameters
- `wgen_example.py` - Python script demonstrating WGEN simulation

## Core Abstractions

### Nodes
Represent locations in the water network that handle vertical physics (environmental interactions):
- `Node` - Abstract base class
- `StorageNode` - Reservoir with active drawdown and refill capabilities
- `JunctionNode` - Stateless connection point
- `SourceNode` - Water source with pluggable generation strategies
- `DemandNode` - Water demand with pluggable demand models

### Links
Represent connections between nodes that handle horizontal physics (transport constraints):
- `Link` - Concrete class with constraint funnel logic

### Solver
Performs minimum cost network flow optimization:
- `NetworkSolver` - Abstract interface for optimization

### Climate
Manages temporal and climatic context:
- `ClimateState` - Dataclass for climate drivers
- `SiteConfig` - Site-specific parameters

### Strategies
Pluggable algorithms for generation and demand:
- `GeneratorStrategy` - Abstract base for inflow generation
- `DemandModel` - Abstract base for demand calculation

### Controls
Operational rules and automated control logic:
- `Control` - Abstract base for link control

### Hydraulics
Physical flow capacity calculations:
- `HydraulicModel` - Abstract base for hydraulic equations

### Results Output
Structured output of simulation results:
- `ResultsWriter` - Exports results in CSV or JSON format
- Outputs flow values, storage states, demand deficits, and source inflows
- Daily resolution output for time series analysis

### Visualization
Interactive visualization of networks and results:
- `visualize_network()` - Generate network topology maps
- `visualize_results()` - Generate time series plots
- `ResultsVisualizer` - Automated plot generation from YAML config
- YAML-driven configuration for all visualizations

## Quick Start

### Option 1: Install and Try the Examples

After installing HydroSim from PyPI:

```bash
# Install HydroSim
pip install hydrosim

# Download example files (if you want to run the examples)
# Clone the repository to get example files:
git clone https://github.com/jlillywh/hydrosim.git
cd hydrosim

# Run the quick start example
python examples/quick_start.py
```

This will:
1. Load and validate two example networks (simple and complex)
2. Run 30-day simulations
3. Generate interactive visualizations (network maps + time series plots)
4. Automatically open the visualizations in your browser
5. Export results to CSV/JSON files
6. Print summary statistics

### Option 2: Basic Usage (No Examples Needed)

You can start using HydroSim immediately after installation:

```python
import hydrosim
from datetime import datetime

# Create a simple network programmatically
network = hydrosim.NetworkGraph()

# Add a storage node (reservoir)
eav = hydrosim.ElevationAreaVolume(
    elevations=[100.0, 110.0, 120.0],
    areas=[1000.0, 2000.0, 3000.0], 
    volumes=[0.0, 10000.0, 30000.0]
)
reservoir = hydrosim.StorageNode('reservoir', initial_storage=20000.0, eav_table=eav)
network.add_node(reservoir)

# Add a demand node
demand = hydrosim.DemandNode('city', hydrosim.MunicipalDemand(population=10000, per_capita_demand=0.2))
network.add_node(demand)

# Connect them with a link
link = hydrosim.Link('delivery', reservoir, demand, physical_capacity=3000.0, cost=1.0)
network.add_link(link)

# Set up simulation
climate_engine = hydrosim.ClimateEngine(
    climate_source=hydrosim.TimeSeriesClimateSource('climate_data.csv'),
    site_config=hydrosim.SiteConfig(latitude=45.0, elevation=1000.0),
    start_date=datetime(2024, 1, 1)
)
solver = hydrosim.LinearProgrammingSolver()
engine = hydrosim.SimulationEngine(network, climate_engine, solver)

# Run simulation
writer = hydrosim.ResultsWriter(output_dir="output", format="csv")
for day in range(30):  # 30 days
    result = engine.step()
    writer.add_timestep(result)

# Export results
files = writer.write_all(prefix="simulation")
print(f"Results written to: {files}")
```

### Option 3: Using YAML Configuration (Recommended for Projects)

Create your own water network using YAML configuration (requires example files from the repository):

```python
from datetime import datetime
from hydrosim import (
    YAMLParser, SimulationEngine, LinearProgrammingSolver, 
    ResultsWriter, ClimateEngine, visualize_network, visualize_results
)

# Load configuration from YAML
parser = YAMLParser('examples/simple_network.yaml')
network, climate_source, site_config = parser.parse()

# Set up simulation
climate_engine = ClimateEngine(climate_source, site_config, datetime(2024, 1, 1))
solver = LinearProgrammingSolver()
engine = SimulationEngine(network, climate_engine, solver)

# Run simulation and capture results
writer = ResultsWriter(output_dir="output", format="csv")
for _ in range(30):  # 30 days
    result = engine.step()
    writer.add_timestep(result)

# Generate visualizations
fig_network = visualize_network(network)
fig_network.write_html('output/network_map.html')

fig_results = visualize_results(
    results_writer=writer,
    network=network,
    viz_config=network.viz_config,
    output_file='output/results.html'
)

# Export data files
files = writer.write_all(prefix="simulation")
print(f"Results written to: {files}")
```

### Option 4: Advanced Programmatic Construction

For more control, you can build networks programmatically:

```python
from hydrosim import (
    NetworkGraph, StorageNode, DemandNode, Link,
    ElevationAreaVolume, MunicipalDemand,
    SimulationEngine, LinearProgrammingSolver, ResultsWriter
)

# Create network
network = NetworkGraph()

# Create nodes
eav = ElevationAreaVolume(
    elevations=[100.0, 110.0, 120.0],
    areas=[1000.0, 2000.0, 3000.0],
    volumes=[0.0, 10000.0, 30000.0]
)
storage = StorageNode('reservoir', initial_storage=20000.0, eav_table=eav)
demand = DemandNode('city', MunicipalDemand(population=10000, per_capita_demand=0.2))

network.add_node(storage)
network.add_node(demand)

# Create link
link = Link('delivery', storage, demand, physical_capacity=3000.0, cost=1.0)
network.add_link(link)

# Set up and run simulation (see Option 1 for complete example)
```

### Running the Examples

To access the examples, you'll need to clone the repository (examples are not included in the PyPI package):

```bash
# Clone repository for examples
git clone https://github.com/jlillywh/hydrosim.git
cd hydrosim

# Install HydroSim (if not already installed)
pip install hydrosim

# Run the examples
python examples/quick_start.py                    # Complete workflow demo
python examples/network_visualization_demo.py    # Network topology visualization
python examples/results_visualization_demo.py    # Time series results visualization
python examples/results_output_example.py        # Programmatic usage example
```

The `examples/` directory contains:
- **Configuration Files:**
  - `simple_network.yaml` - Basic reservoir-demand system
  - `complex_network.yaml` - Multi-reservoir system with controls
  - `storage_drawdown_example.yaml` - Active storage drawdown demo
  - `wgen_example.yaml` - Stochastic weather generation example
- **Python Scripts:**
  - `quick_start.py` - Complete workflow with automatic visualization
  - `*_demo.py` - Various feature demonstrations
  - `*_example.py` - Usage examples for specific components
- **Data Files:**
  - `climate_data.csv`, `inflow_data.csv` - Sample time series data
  - `wgen_params_template.csv` - WGEN parameter template
- **Documentation:**
  - `README.md` - Detailed configuration guide
  - `CLIMATE_BUILDER_README.md` - Climate data tools guide

### YAML Visualization Configuration

Configure visualizations directly in your YAML files:

```yaml
model_name: "My Water Network"
author: "Your Name"

visualization:
  # Network map settings
  network_map:
    width: 600
    height: 1200
    layout: hierarchical  # or 'circular'
    output_file: "network_topology.html"
  
  # Time series plots
  plots:
    - type: climate
      title: "Climate Conditions"
      y1_axis:
        label: "Precipitation (mm/day)"
        variables: [precip]
      y2_axis:
        label: "Temperature (°C)"
        variables: [tmax, tmin]
    
    - type: reservoir
      auto: true  # Auto-generate for all reservoirs
      title_template: "{node_id} Operations"
      y1_axis:
        label: "Storage (m³)"
        variables: [storage]
      y2_axis:
        label: "Flow (m³/day)"
        variables: [inflow, outflow, evap_loss, spill]
  
  layout:
    width: 1200
    height: 400
    output_file: "simulation_results.html"

# ... rest of your network configuration
```

## Development

This project follows a spec-driven development approach. See `.kiro/specs/hydrosim-framework/` for:
- `requirements.md` - Detailed requirements
- `design.md` - Architecture and design decisions
- `tasks.md` - Implementation plan

## License

MIT License - see [LICENSE](LICENSE) file for details
