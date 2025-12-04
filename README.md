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

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Setup Steps

1. Clone or download the repository:
```bash
git clone https://github.com/jlillywh/hydrosim.git
cd hydrosim
```

2. Create a virtual environment:
```bash
python -m venv .venv
```

3. Activate the virtual environment:
- **Windows**: `.venv\Scripts\activate`
- **Unix/MacOS**: `source .venv/bin/activate`

4. Install dependencies:
```bash
pip install -r requirements.txt
```

5. Verify installation by running tests:
```bash
pytest
```

### Dependencies

HydroSim requires the following Python packages:
- **NumPy** - Numerical computations
- **Pandas** - Data manipulation and time series
- **NetworkX** - Graph algorithms
- **SciPy** - Optimization (linear programming)
- **PyYAML** - YAML configuration parsing
- **pytest** - Testing framework
- **hypothesis** - Property-based testing

All dependencies are listed in `requirements.txt` and will be installed automatically.

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

## Quick Start

### Option 1: Using YAML Configuration (Recommended)

The easiest way to get started is using YAML configuration files:

```python
from hydrosim.config import YAMLParser
from hydrosim import SimulationEngine, LinearProgrammingSolver, ResultsWriter

# Load configuration from YAML
parser = YAMLParser('examples/simple_network.yaml')
network, climate_source, site_config = parser.parse()

# Set up simulation
solver = LinearProgrammingSolver()
engine = SimulationEngine(network, climate_source, solver, site_config)

# Run simulation and capture results
writer = ResultsWriter(output_dir="output", format="csv")
for _ in range(30):  # 30 days
    result = engine.step()
    writer.add_timestep(result)

# Export results
files = writer.write_all(prefix="simulation")
print(f"Results written to: {files}")
```

### Option 2: Programmatic Network Construction

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

Try the included examples to see HydroSim in action:

```bash
# Run the quick start example (recommended first step)
python examples/quick_start.py

# Run the results output example
python examples/results_output_example.py
```

See the `examples/` directory for:
- `simple_network.yaml` - Basic reservoir-demand system
- `complex_network.yaml` - Multi-reservoir system with controls
- `quick_start.py` - Complete workflow demonstration
- `results_output_example.py` - Programmatic usage example
- `README.md` - Detailed configuration guide
- Sample data files (`climate_data.csv`, `inflow_data.csv`)

## Development

This project follows a spec-driven development approach. See `.kiro/specs/hydrosim-framework/` for:
- `requirements.md` - Detailed requirements
- `design.md` - Architecture and design decisions
- `tasks.md` - Implementation plan

## License

MIT License - see [LICENSE](LICENSE) file for details
