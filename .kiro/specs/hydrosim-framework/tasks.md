# Implementation Plan

- [x] 1. Set up project structure and core abstractions





  - Create Python package structure with modules for nodes, links, solver, climate, and config
  - Implement abstract base classes (Node, GeneratorStrategy, DemandModel, Control, HydraulicModel, NetworkSolver)
  - Set up pytest and Hypothesis testing frameworks
  - Create requirements.txt with core dependencies (NumPy, Pandas, NetworkX, SciPy, PyYAML, pytest, Hypothesis)
  - _Requirements: 2.1, 2.2, 2.3_

- [ ]* 1.1 Write property test for project structure validation
  - **Property 23: YAML parsing completeness**
  - **Validates: Requirements 15.1, 15.2, 15.3, 15.5**

- [x] 2. Implement data models and network graph





  - Create ClimateState dataclass with all required fields (date, precip, t_max, t_min, solar, et0)
  - Create SiteConfig dataclass for latitude and elevation
  - Implement ElevationAreaVolume class with interpolation methods
  - Implement NetworkGraph class with node/link management and validation
  - _Requirements: 1.1, 1.2, 1.3, 16.1, 16.2, 16.3, 16.5_

- [ ]* 2.1 Write property test for network topology validation
  - **Property 1: Network topology validation**
  - **Validates: Requirements 1.3, 16.1, 16.2**

- [ ]* 2.2 Write property test for explicit flow paths
  - **Property 2: Explicit flow paths**
  - **Validates: Requirements 1.2, 11.1, 11.3**

- [ ]* 2.3 Write property test for EAV interpolation
  - **Property 18: EAV interpolation correctness**
  - **Validates: Requirements 12.2, 12.3**

- [ ]* 2.4 Write property test for topology validation completeness
  - **Property 24: Topology validation completeness**
  - **Validates: Requirements 16.3, 16.4, 16.5**

- [x] 3. Implement Climate Engine



  - Implement ClimateEngine class with timestep management
  - Implement Hargreaves ET0 calculation method
  - Implement TimeSeriesClimateSource for reading CSV data
  - Implement WGENClimateSource for stochastic weather generation
  - Add climate driver broadcasting to nodes
  - _Requirements: 3.1, 3.2, 3.4, 3.5, 14.1, 14.4_

- [ ]* 3.1 Write property test for climate data completeness
  - **Property 3: Climate data completeness**
  - **Validates: Requirements 3.1, 3.5**

- [ ]* 3.2 Write property test for ET0 calculation
  - **Property 4: ET0 calculation correctness**
  - **Validates: Requirements 3.2**

- [ ]* 3.3 Write property test for daily timestep increment
  - **Property 21: Daily timestep increment**
  - **Validates: Requirements 14.1**

- [x] 4. Implement Node types





  - Implement StorageNode with storage tracking, EAV integration, and evaporation calculation
  - Implement JunctionNode with stateless pass-through behavior
  - Implement SourceNode with strategy pattern support
  - Implement DemandNode with strategy pattern support and deficit tracking
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 12.1, 12.2, 12.3, 12.4, 12.5_

- [ ]* 4.1 Write property test for storage tracking
  - **Property 5: Storage tracking invariant**
  - **Validates: Requirements 4.1**

- [ ]* 4.2 Write property test for evaporation calculation
  - **Property 6: Evaporation calculation correctness**
  - **Validates: Requirements 4.2, 12.5**

- [ ]* 4.3 Write property test for junction mass balance
  - **Property 7: Junction mass balance**
  - **Validates: Requirements 4.3**

- [ ]* 4.4 Write property test for head query consistency
  - **Property 19: Head query consistency**
  - **Validates: Requirements 12.4, 13.3**

- [x] 5. Implement Generator strategies





  - Implement TimeSeriesStrategy for reading inflow from CSV
  - Implement basic HydrologyStrategy framework (Snow17 and AWBM models can be simplified initially)
  - Add strategy switching capability
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ]* 5.1 Write property test for strategy pluggability
  - **Property 8: Strategy pattern pluggability**
  - **Validates: Requirements 4.4, 4.5, 5.4, 6.5**

- [ ]* 5.2 Write property test for generator availability
  - **Property 9: Generator availability**
  - **Validates: Requirements 5.5**

- [x] 6. Implement Demand models




  - Implement MunicipalDemand with population-based calculation
  - Implement AgricultureDemand with crop coefficient and ET0
  - Add strategy switching capability
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [ ]* 6.1 Write property test for demand deficit tracking
  - **Property 10: Demand deficit tracking**
  - **Validates: Requirements 6.4**

- [x] 7. Implement Link and constraint system




  - Implement Link class with constraint funnel logic
  - Implement physical capacity constraints
  - Implement constraint calculation method that returns (q_min, q_max, cost)
  - _Requirements: 7.1, 7.4, 7.5, 11.1, 11.3, 11.4_

- [ ]* 7.1 Write property test for constraint funnel
  - **Property 11: Constraint funnel minimum**
  - **Validates: Requirements 7.4**

- [ ]* 7.2 Write property test for constraint output completeness
  - **Property 12: Constraint output completeness**
  - **Validates: Requirements 7.5**

- [x] 8. Implement Control systems




  - Implement FractionalControl for throttling (0.0 to 1.0)
  - Implement AbsoluteControl for hard caps
  - Implement SwitchControl for binary on/off
  - Integrate controls into Link constraint calculation
  - _Requirements: 7.3, 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 9. Implement Hydraulic models





  - Implement WeirModel with weir equation (Q = C × L × H^1.5)
  - Implement PipeModel with fixed capacity
  - Integrate hydraulic models into Link constraint calculation
  - _Requirements: 7.2, 13.1, 13.2, 13.3, 13.4, 13.5_

- [ ]* 9.1 Write property test for hydraulic limit recalculation
  - **Property 20: Hydraulic limit recalculation**
  - **Validates: Requirements 13.4**

- [x] 10. Implement Network Solver
  - Implement NetworkSolver using NetworkX and SciPy linprog
  - Construct network flow problem from nodes and links
  - Set up objective function (minimize cost)
  - Add mass balance constraints for all nodes
  - Add flow bound constraints for all links
  - Extract and return flow allocations
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [ ]* 10.1 Write property test for solver mass balance
  - **Property 13: Solver mass balance conservation**
  - **Validates: Requirements 9.3**

- [ ]* 10.2 Write property test for solver constraint satisfaction
  - **Property 14: Solver constraint satisfaction**
  - **Validates: Requirements 9.4**

- [ ]* 10.3 Write property test for solver solution completeness
  - **Property 15: Solver solution completeness**
  - **Validates: Requirements 9.5**

- [ ]* 10.4 Write property test for solver cost minimization
  - **Property 16: Solver cost minimization**
  - **Validates: Requirements 9.2**

- [x] 11. Implement simulation engine and timestep execution





  - Implement SimulationEngine class to orchestrate timestep execution
  - Implement strict execution order: environment → nodes → links → solver → state update
  - Add state update logic to move mass and update storage
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 18.3, 18.4, 18.5_

- [ ]* 11.1 Write property test for timestep execution order
  - **Property 17: Timestep execution order**
  - **Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.5**

- [ ]* 11.2 Write property test for stepwise optimization
  - **Property 26: Stepwise optimization without lookahead**
  - **Validates: Requirements 18.1, 18.2**

- [ ]* 11.3 Write property test for sequential timestep solving
  - **Property 27: Sequential timestep solving**
  - **Validates: Requirements 18.3, 18.4**

- [ ]* 11.4 Write property test for constraint update propagation
  - **Property 28: Constraint update propagation**
  - **Validates: Requirements 18.5**

- [x] 12. Checkpoint - Ensure all tests pass





  - Ensure all tests pass, ask the user if questions arise.

- [x] 13. Implement YAML configuration parser




  - Implement YAMLParser class to read configuration files
  - Parse node definitions (type, parameters)
  - Parse link definitions (source, target, capacity, cost)
  - Parse climate configuration (data source, site parameters)
  - Add error handling for invalid YAML syntax
  - Construct NetworkGraph from parsed configuration
  - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 1.1_

- [x] 14. Implement configuration validation





  - Add validation for link references to existing nodes
  - Add validation for orphaned nodes
  - Add validation for control parameters (fractional in [0,1], absolute non-negative)
  - Add validation to reject sub-daily timestep configurations
  - Report all validation errors with helpful messages
  - _Requirements: 1.5, 14.3, 16.1, 16.2, 16.3, 16.4_

- [x] 15. Implement results output system




  - Create ResultsWriter class for structured output
  - Output flow values for all links at each timestep
  - Output storage volumes for all StorageNodes at each timestep
  - Output demand deficits for all DemandNodes at each timestep
  - Output inflows for all SourceNodes at each timestep
  - Use structured format (CSV or JSON) for time series analysis
  - Ensure daily resolution output
  - _Requirements: 17.1, 17.2, 17.3, 17.4, 17.5, 14.5_

- [ ]* 15.1 Write property test for output completeness
  - **Property 25: Output completeness**
  - **Validates: Requirements 17.1, 17.2, 17.3, 17.4**

- [ ]* 15.2 Write property test for daily output resolution
  - **Property 22: Daily output resolution**
  - **Validates: Requirements 14.5**

- [x] 16. Implement error handling





  - Add error handling for negative storage (constrain outflow or raise error)
  - Add error handling for infeasible network flow (report conflicting constraints)
  - Add error handling for missing climate data (check data availability vs simulation period)
  - Add error handling for EAV interpolation out of bounds (extrapolate, clamp, or error)
  - Add logging for warnings (low storage, approaching table boundaries)
  - _Requirements: All error handling scenarios from design document_


- [x] 17. Add network visualization export


  - Implement method to export network graph structure
  - Support export to formats compatible with visualization tools (GraphML, DOT)
  - Include node types and link properties in export
  - _Requirements: 1.4_

- [ ]* 17.1 Write unit tests for visualization export
  - Test export produces valid format
  - Test exported graph contains all nodes and links
  - Test node and link properties are preserved

- [x] 18. Create example configurations and documentation




  - Create example YAML configuration for simple network
  - Create example YAML configuration for complex network with all node types
  - Add inline comments explaining configuration options
  - Create README with quick start guide
  - _Requirements: Supporting user adoption_


- [x] 19. Final checkpoint - Ensure all tests pass




  - Ensure all tests pass, ask the user if questions arise.
