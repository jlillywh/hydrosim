# Requirements Document

## Introduction

This feature enables active storage drawdown in HydroSim by implementing a virtual link architecture that treats final storage as a linear decision variable. Currently, storage nodes act as passive buffers where outflow equals inflow minus evaporation. This enhancement allows storage nodes to actively release water to meet downstream demands, enabling realistic reservoir operations where drawdown occurs when needed.

## Glossary

- **HydroSim**: The water resources planning framework system
- **StorageNode**: A node representing a reservoir or tank with mass storage capability
- **LinearProgrammingSolver**: The network solver that performs minimum cost network flow optimization
- **Carryover Link**: A virtual link representing water staying in the reservoir from timestep t to t+1
- **Virtual Sink**: A temporary node representing the future state of a storage node
- **Drawdown**: The process of releasing water from storage when outflow exceeds inflow
- **Dead Pool**: The minimum storage level below which water cannot be released
- **Available Mass**: The water volume available for allocation, calculated as current storage minus evaporation
- **Cost Hierarchy**: The relative cost values that guide solver decisions on water allocation priorities

## Requirements

### Requirement 1

**User Story:** As a water resources engineer, I want storage nodes to enable active drawdown, so that reservoirs can release water to meet downstream demands even when inflow is insufficient.

#### Acceptance Criteria

1. WHEN a StorageNode has available storage and downstream demand exists THEN the system SHALL release water from storage to meet the demand
2. WHEN a StorageNode has zero inflow and positive storage THEN the system SHALL allow outflow up to the available storage minus dead pool
3. WHEN a StorageNode receives inflow exceeding demand THEN the system SHALL store the excess water up to maximum capacity
4. WHEN a StorageNode is at maximum capacity and receives additional inflow THEN the system SHALL spill the excess water
5. WHEN a StorageNode reaches dead pool level THEN the system SHALL prevent further drawdown

### Requirement 2

**User Story:** As a water resources engineer, I want storage represented as a decision variable in the network flow problem, so that the solver can optimize storage levels alongside flow allocations.

#### Acceptance Criteria

1. WHEN the solver constructs the network flow problem THEN the system SHALL create a carryover link for each StorageNode representing water remaining at timestep end
2. WHEN the solver constructs the network flow problem THEN the system SHALL create a virtual sink node for each StorageNode representing future storage state
3. WHEN the solver optimizes THEN the system SHALL treat carryover link flow as the decision variable for final storage level
4. WHEN the solver completes THEN the system SHALL update StorageNode storage based on the carryover link flow value
5. WHEN multiple storage nodes exist THEN the system SHALL create independent carryover links and virtual sinks for each node

### Requirement 3

**User Story:** As a water resources engineer, I want storage nodes to expose their available mass, so that the solver can correctly account for water already in the reservoir.

#### Acceptance Criteria

1. WHEN a StorageNode calculates available mass THEN the system SHALL return current storage minus evaporation loss
2. WHEN evaporation exceeds current storage THEN the system SHALL clamp available mass to zero and reduce evaporation to match storage
3. WHEN the solver constructs boundary conditions THEN the system SHALL add the StorageNode available mass as a source term
4. WHEN the solver constructs boundary conditions THEN the system SHALL set the virtual sink demand equal to the StorageNode available mass
5. WHEN available mass is calculated THEN the system SHALL ensure the value is non-negative

### Requirement 4

**User Story:** As a water resources engineer, I want the solver to prioritize meeting demands over storing water, so that critical water needs are satisfied before filling reservoirs.

#### Acceptance Criteria

1. WHEN the solver assigns costs THEN the system SHALL set demand link cost to -1000
2. WHEN the solver assigns costs THEN the system SHALL set carryover link cost to -1
3. WHEN the solver assigns costs THEN the system SHALL set spillway link cost to 0
4. WHEN the solver optimizes with insufficient water for both demand and storage THEN the system SHALL allocate water to demand before storage
5. WHEN the solver optimizes with excess water after meeting demand THEN the system SHALL allocate water to storage before spilling

### Requirement 5

**User Story:** As a water resources engineer, I want carryover links to respect storage capacity constraints, so that reservoirs cannot be overfilled.

#### Acceptance Criteria

1. WHEN a carryover link is created THEN the system SHALL set the upper bound to the StorageNode maximum storage capacity
2. WHEN a carryover link is created THEN the system SHALL set the lower bound to the StorageNode dead pool level
3. WHEN the solver allocates flow to a carryover link THEN the system SHALL ensure the flow is within the capacity bounds
4. WHEN final storage would exceed maximum capacity THEN the system SHALL limit carryover flow to maximum storage
5. WHEN final storage would fall below dead pool THEN the system SHALL limit outflow to prevent violation

### Requirement 6

**User Story:** As a water resources engineer, I want the virtual link architecture to integrate seamlessly with existing solver logic, so that no changes to the core optimization algorithm are required.

#### Acceptance Criteria

1. WHEN virtual links are added THEN the system SHALL maintain the standard network flow formulation where sum of inflows minus sum of outflows equals zero
2. WHEN the solver constructs the problem THEN the system SHALL treat carryover links identically to physical links
3. WHEN the solver completes THEN the system SHALL extract carryover link flows using the same mechanism as physical link flows
4. WHEN virtual sinks are added THEN the system SHALL include them in the node set for mass balance constraints
5. WHEN the network is validated THEN the system SHALL exclude virtual nodes and links from topology validation

### Requirement 7

**User Story:** As a water resources engineer, I want to verify that drawdown behavior works correctly, so that I can trust the model to operate reservoirs realistically.

#### Acceptance Criteria

1. WHEN a reservoir has 50000 storage, 0 inflow, and 2000 downstream demand THEN the system SHALL release 2000 from storage
2. WHEN a reservoir has 0 storage, 5000 inflow, and 0 demand THEN the system SHALL store the 5000 inflow in the reservoir
3. WHEN a reservoir has storage at dead pool level and downstream demand exists THEN the system SHALL release zero flow
4. WHEN a reservoir has 10000 storage, 3000 inflow, 5000 demand, and 8000 maximum capacity THEN the system SHALL meet demand and store remaining water up to capacity
5. WHEN a reservoir is at maximum capacity and receives inflow THEN the system SHALL spill the excess after meeting demand

### Requirement 8

**User Story:** As a water resources engineer, I want cost constants defined centrally, so that the cost hierarchy is consistent and maintainable across the system.

#### Acceptance Criteria

1. WHEN cost constants are defined THEN the system SHALL create COST_DEMAND constant with value -1000
2. WHEN cost constants are defined THEN the system SHALL create COST_STORAGE constant with value -1
3. WHEN cost constants are defined THEN the system SHALL create COST_SPILL constant with value 0
4. WHEN links are created THEN the system SHALL reference the central cost constants rather than hardcoded values
5. WHEN cost hierarchy needs adjustment THEN the system SHALL allow modification in a single location
