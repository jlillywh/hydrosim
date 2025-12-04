# Requirements Document

## Introduction

HydroSim is a Python-based water resources planning framework designed for daily timestep simulation of complex, interconnected water systems. The framework unifies process-based simulation (hydrology and water demands) with network allocation (systems analysis) to enable engineers to model systems where flow decisions are driven by physical constraints, local control rules, and global network optimization. The system operates on a strict 1-day timestep and uses a constraint-stacking approach where components calculate their own feasible limits before a solver performs network-wide optimization.

## Glossary

- **HydroSim**: The water resources planning framework system
- **Node**: A component representing a location in the water network that handles vertical physics (interactions with environment)
- **Link**: A component representing a connection between nodes that handles horizontal physics (transport constraints)
- **Solver**: The component that performs minimum cost network flow optimization
- **Climate Engine**: The subsystem that manages temporal and climatic context including precipitation, temperature, and evapotranspiration
- **Constraint Funnel**: The process by which Links narrow down feasible flow through physical, hydraulic, and control layers
- **Vertical Physics**: Environmental interactions at a node (rain, evaporation, demand)
- **Horizontal Physics**: Transport constraints between nodes via links
- **Mass Balance**: The principle that total inflow equals total outflow plus change in storage
- **ET0**: Reference evapotranspiration calculated globally using the Hargreaves method
- **Strategy Pattern**: A design pattern allowing pluggable algorithms for generation and demand calculation
- **Timestep**: A single day in the simulation

## Requirements

### Requirement 1

**User Story:** As a water resources engineer, I want to define a water network topology explicitly through nodes and links, so that I can visualize and validate the system structure before simulation.

#### Acceptance Criteria

1. WHEN a user provides a YAML configuration file THEN the HydroSim SHALL parse the file and construct a network graph from the node and link definitions
2. WHEN the network is constructed THEN the HydroSim SHALL validate that every connection between nodes is represented by an explicit Link object
3. WHEN a Link references a source or target node THEN the HydroSim SHALL verify that both nodes exist in the network definition
4. WHEN the network topology is loaded THEN the HydroSim SHALL provide a method to export the graph structure for visualization
5. WHERE a Link is defined without both source and target nodes THEN the HydroSim SHALL reject the configuration and report the malformed link

### Requirement 2

**User Story:** As a water resources engineer, I want the framework to separate vertical physics (node behavior) from horizontal physics (link behavior) from optimization decisions (solver), so that the model is maintainable and each component has clear responsibilities.

#### Acceptance Criteria

1. WHEN a Node is implemented THEN the HydroSim SHALL ensure it only handles environmental interactions and does not contain transport logic
2. WHEN a Link is implemented THEN the HydroSim SHALL ensure it only handles transport constraints and does not contain environmental interaction logic
3. WHEN the Solver is invoked THEN the HydroSim SHALL ensure it only performs network optimization using constraints provided by Links
4. WHEN a StorageNode calculates evaporation THEN the HydroSim SHALL not include any flow routing logic within the node
5. WHEN a Link calculates flow constraints THEN the HydroSim SHALL not include any demand calculation or runoff generation logic within the link

### Requirement 3

**User Story:** As a water resources engineer, I want the Climate Engine to provide consistent environmental drivers across all timesteps, so that all components receive synchronized climate data.

#### Acceptance Criteria

1. WHEN a simulation timestep begins THEN the Climate Engine SHALL provide precipitation, maximum temperature, minimum temperature, and solar radiation values
2. WHEN climate drivers are updated THEN the Climate Engine SHALL calculate reference evapotranspiration using the Hargreaves method
3. WHERE a user specifies time series climate data THEN the Climate Engine SHALL read values from CSV files
4. WHERE a user specifies stochastic generation THEN the Climate Engine SHALL generate climate values using the WGEN method
5. WHEN ET0 is calculated THEN the Climate Engine SHALL broadcast the value to all nodes that require it

### Requirement 4

**User Story:** As a water resources engineer, I want to model different types of nodes (storage, junction, source, demand), so that I can represent diverse components in a water system.

#### Acceptance Criteria

1. WHEN a StorageNode is created THEN the HydroSim SHALL track storage volume and calculate change in storage over time
2. WHEN a StorageNode calculates evaporation THEN the HydroSim SHALL use surface area from an elevation-area-volume table and global ET0
3. WHEN a JunctionNode is evaluated THEN the HydroSim SHALL enforce that total inflow equals total outflow without storing mass
4. WHEN a SourceNode is created THEN the HydroSim SHALL use a pluggable Generator strategy to determine water volume injection
5. WHEN a DemandNode is created THEN the HydroSim SHALL use a pluggable DemandModel strategy to calculate water request

### Requirement 5

**User Story:** As a water resources engineer, I want SourceNodes to support multiple generation strategies, so that I can model both observed inflows and simulated hydrology.

#### Acceptance Criteria

1. WHERE a SourceNode uses TimeSeriesStrategy THEN the HydroSim SHALL read inflow values from CSV files
2. WHERE a SourceNode uses HydrologyStrategy THEN the HydroSim SHALL simulate runoff using Snow17 and AWBM physics models
3. WHEN a HydrologyStrategy executes THEN the HydroSim SHALL use climate drivers from the Climate Engine to calculate runoff
4. WHEN a user switches generation strategies THEN the HydroSim SHALL apply the new strategy without modifying other node properties
5. WHEN a SourceNode generates inflow THEN the HydroSim SHALL make the volume available for the solver allocation step

### Requirement 6

**User Story:** As a water resources engineer, I want DemandNodes to support multiple demand calculation strategies, so that I can model different types of water users.

#### Acceptance Criteria

1. WHERE a DemandNode uses Municipal strategy THEN the HydroSim SHALL calculate demand based on population parameters
2. WHERE a DemandNode uses Agriculture strategy THEN the HydroSim SHALL calculate demand based on crop coefficient and reference ET0
3. WHEN a DemandModel calculates a request THEN the HydroSim SHALL treat the value as a high-priority target for the solver
4. WHEN the solver cannot fully satisfy a demand THEN the HydroSim SHALL track the shortfall as deficit
5. WHEN a user switches demand strategies THEN the HydroSim SHALL apply the new strategy without modifying other node properties

### Requirement 7

**User Story:** As a water resources engineer, I want Links to implement a constraint funnel that combines physical, hydraulic, and control limits, so that the solver receives accurate feasible flow bounds.

#### Acceptance Criteria

1. WHEN a Link calculates constraints THEN the HydroSim SHALL apply physical limits based on static capacity values
2. WHEN a Link calculates constraints THEN the HydroSim SHALL apply hydraulic limits based on current system state using appropriate equations
3. WHEN a Link calculates constraints THEN the HydroSim SHALL apply control limits based on logic rules
4. WHEN multiple constraint layers are evaluated THEN the HydroSim SHALL compute the final limit as the minimum of physical, hydraulic, and control limits
5. WHEN a Link provides constraints to the solver THEN the HydroSim SHALL include both minimum flow, maximum flow, and cost parameters

### Requirement 8

**User Story:** As a water resources engineer, I want Links to support continuous control mechanisms (fractional, absolute, switch), so that I can model operational rules and automated controls.

#### Acceptance Criteria

1. WHERE a Link uses fractional control THEN the HydroSim SHALL throttle capacity using a value between 0.0 and 1.0
2. WHERE a Link uses absolute control THEN the HydroSim SHALL set a hard flow cap in absolute units
3. WHERE a Link uses switch control THEN the HydroSim SHALL enable or disable flow using binary on/off logic
4. WHEN fractional control is applied THEN the HydroSim SHALL support PID and proportional control logic
5. WHEN absolute control is applied THEN the HydroSim SHALL support rule curve logic

### Requirement 9

**User Story:** As a water resources engineer, I want the Solver to perform minimum cost network flow optimization, so that water is allocated efficiently across the system.

#### Acceptance Criteria

1. WHEN the Solver executes THEN the HydroSim SHALL construct a network flow problem from current node states and link constraints
2. WHEN the Solver optimizes THEN the HydroSim SHALL minimize the sum of flow times cost across all links
3. WHEN the Solver completes THEN the HydroSim SHALL ensure mass balance is conserved at all nodes
4. WHEN the Solver allocates flow THEN the HydroSim SHALL respect the minimum and maximum flow bounds provided by each Link
5. WHEN the Solver produces a solution THEN the HydroSim SHALL return flow values for all links in the network

### Requirement 10

**User Story:** As a water resources engineer, I want the simulation to execute timesteps in a strict order (environment, nodes, links, solver, state update), so that global optimization respects local controls and physics.

#### Acceptance Criteria

1. WHEN a timestep begins THEN the HydroSim SHALL first update climate drivers and calculate global ET0
2. WHEN the environment step completes THEN the HydroSim SHALL execute the node step to run generators, demand models, and calculate evaporation
3. WHEN the node step completes THEN the HydroSim SHALL execute the link step to update constraints based on current system state
4. WHEN the link step completes THEN the HydroSim SHALL execute the solver step to perform network allocation
5. WHEN the solver step completes THEN the HydroSim SHALL update storage states and move mass according to allocated flows

### Requirement 11

**User Story:** As a water resources engineer, I want all water transfers to be represented by explicit Link objects, so that I can trace and validate all flows in the system.

#### Acceptance Criteria

1. WHEN water moves from one node to another THEN the HydroSim SHALL require an explicit Link object connecting the nodes
2. WHEN a node attempts to send water without a corresponding Link THEN the HydroSim SHALL prevent the transfer and report an error
3. WHEN the simulation executes THEN the HydroSim SHALL ensure no hidden or implicit flow paths exist
4. WHEN a user queries flows THEN the HydroSim SHALL provide complete flow information for every Link in the network
5. WHEN validating network topology THEN the HydroSim SHALL verify that all intended connections have corresponding Link definitions

### Requirement 12

**User Story:** As a water resources engineer, I want StorageNodes to calculate hydraulic properties (head, surface area) from elevation-area-volume relationships, so that storage-dependent constraints are accurate.

#### Acceptance Criteria

1. WHEN a StorageNode is configured THEN the HydroSim SHALL accept an elevation-area-volume (EAV) table
2. WHEN a StorageNode storage volume changes THEN the HydroSim SHALL interpolate elevation from the EAV table
3. WHEN a StorageNode elevation is known THEN the HydroSim SHALL interpolate surface area from the EAV table
4. WHEN a Link queries a StorageNode for head THEN the HydroSim SHALL provide the current elevation value
5. WHEN calculating evaporation losses THEN the HydroSim SHALL use the interpolated surface area and global ET0

### Requirement 13

**User Story:** As a water resources engineer, I want Links to calculate hydraulic limits using appropriate equations (weir equations, pipe flow), so that physical constraints are accurately represented.

#### Acceptance Criteria

1. WHERE a Link represents a weir THEN the HydroSim SHALL calculate maximum flow using weir equations based on upstream head
2. WHERE a Link represents a pipe THEN the HydroSim SHALL calculate maximum flow based on pipe capacity and hydraulic grade
3. WHEN a Link queries upstream storage THEN the HydroSim SHALL retrieve current head or elevation from the source node
4. WHEN hydraulic conditions change THEN the HydroSim SHALL recalculate flow limits before each solver execution
5. WHEN head is insufficient for flow THEN the HydroSim SHALL set the maximum flow limit to zero or the minimum feasible value

### Requirement 14

**User Story:** As a water resources engineer, I want the framework to operate strictly on 1-day timesteps, so that the scope remains focused on strategic planning rather than sub-daily hydraulic transients.

#### Acceptance Criteria

1. WHEN the simulation advances time THEN the HydroSim SHALL increment by exactly one day
2. WHEN flow is calculated within a timestep THEN the HydroSim SHALL assume steady-state conditions
3. WHEN a user attempts to configure sub-daily timesteps THEN the HydroSim SHALL reject the configuration
4. WHEN climate data is provided THEN the HydroSim SHALL expect daily resolution values
5. WHEN results are output THEN the HydroSim SHALL report values at daily intervals

### Requirement 15

**User Story:** As a water resources engineer, I want to configure models using YAML files, so that I can define complex systems in a human-readable and version-controllable format.

#### Acceptance Criteria

1. WHEN a user provides a YAML configuration THEN the HydroSim SHALL parse node definitions including type and parameters
2. WHEN a user provides a YAML configuration THEN the HydroSim SHALL parse link definitions including source, target, constraints, and costs
3. WHEN a user provides a YAML configuration THEN the HydroSim SHALL parse climate configuration including data sources and site parameters
4. WHEN parsing fails due to invalid syntax THEN the HydroSim SHALL report the specific error location and type
5. WHEN the configuration is valid THEN the HydroSim SHALL construct all model components and validate the complete network topology

### Requirement 16

**User Story:** As a water resources engineer, I want the framework to validate that the network topology can be drawn as a graph from the YAML configuration, so that I can ensure the model structure is correct before running simulations.

#### Acceptance Criteria

1. WHEN the configuration is loaded THEN the HydroSim SHALL verify that all Link source references point to existing nodes
2. WHEN the configuration is loaded THEN the HydroSim SHALL verify that all Link target references point to existing nodes
3. WHEN the configuration is loaded THEN the HydroSim SHALL verify that no orphaned nodes exist without any connections
4. WHEN topology validation fails THEN the HydroSim SHALL report all malformed connections and missing references
5. WHEN topology validation succeeds THEN the HydroSim SHALL confirm that the network can be represented as a directed graph

### Requirement 17

**User Story:** As a water resources engineer, I want simulation results to include flows, storage levels, deficits, and other key metrics, so that I can analyze system performance.

#### Acceptance Criteria

1. WHEN a simulation completes THEN the HydroSim SHALL output flow values for all links at each timestep
2. WHEN a simulation completes THEN the HydroSim SHALL output storage volumes for all StorageNodes at each timestep
3. WHEN a simulation completes THEN the HydroSim SHALL output demand deficits for all DemandNodes at each timestep
4. WHEN a simulation completes THEN the HydroSim SHALL output inflows for all SourceNodes at each timestep
5. WHEN results are written THEN the HydroSim SHALL use a structured format that supports time series analysis

### Requirement 18

**User Story:** As a water resources engineer, I want the Solver to operate in a stepwise greedy manner, so that each day is optimized based on current constraints without requiring perfect foresight.

#### Acceptance Criteria

1. WHEN the Solver executes for a timestep THEN the HydroSim SHALL optimize based only on current day constraints
2. WHEN the Solver executes THEN the HydroSim SHALL not use future climate data or future system states
3. WHEN multiple timesteps are simulated THEN the HydroSim SHALL solve each timestep independently in sequence
4. WHEN the Solver completes a timestep THEN the HydroSim SHALL update system state before proceeding to the next timestep
5. WHEN constraints change between timesteps THEN the HydroSim SHALL use the updated constraints for the next optimization
