# Implementation Plan

- [x] 1. Define cost constants in central configuration





  - Create COST_DEMAND = -1000.0 constant
  - Create COST_STORAGE = -1.0 constant
  - Create COST_SPILL = 0.0 constant
  - Add constants to hydrosim/config.py or hydrosim/solver.py
  - Document the cost hierarchy and its purpose
  - _Requirements: 8.1, 8.2, 8.3, 4.1, 4.2, 4.3_

- [ ]* 1.1 Write unit tests for cost constants
  - Test that constants are defined with correct values
  - Test that constants maintain correct hierarchy (COST_DEMAND < COST_STORAGE < COST_SPILL)
  - _Requirements: 8.1, 8.2, 8.3_

- [x] 2. Add storage capacity parameters to StorageNode





  - Add max_storage parameter to StorageNode.__init__()
  - Add min_storage parameter (dead pool) to StorageNode.__init__()
  - Validate that min_storage <= initial_storage <= max_storage
  - Validate that min_storage <= max_storage
  - Update existing StorageNode instantiations in tests and examples
  - _Requirements: 5.1, 5.2_

- [ ]* 2.1 Write unit tests for storage capacity validation
  - Test that invalid capacity ranges raise configuration errors
  - Test that initial storage outside bounds raises errors
  - _Requirements: 5.1, 5.2_

- [x] 3. Implement get_available_mass() method in StorageNode





  - Calculate available mass as storage - evaporation
  - Implement clamping when evaporation > storage
  - Reduce evaporation to match storage when clamping occurs
  - Log warning when clamping occurs with node ID and values
  - Ensure returned value is always non-negative
  - _Requirements: 3.1, 3.2, 3.5_

- [ ]* 3.1 Write property test for available mass calculation
  - **Property 8: Available mass calculation**
  - **Validates: Requirements 3.1, 3.5**

- [ ]* 3.2 Write property test for evaporation clamping
  - **Property 9: Evaporation clamping**
  - **Validates: Requirements 3.2**

- [x] 4. Implement update_storage_from_carryover() method in StorageNode





  - Accept carryover_flow parameter
  - Set self.storage = carryover_flow
  - This replaces the old update_storage() method for storage nodes
  - _Requirements: 2.4_

- [ ]* 4.1 Write unit test for storage update from carryover
  - Test that storage is set to carryover flow value
  - Test with various carryover flow values
  - _Requirements: 2.4_

- [x] 5. Create virtual network component classes





  - Create VirtualSink dataclass with node_id, demand, node_type, inflows, outflows
  - Create CarryoverLink dataclass with link_id, source, target, min_flow, max_flow, cost
  - Add these to hydrosim/nodes.py or create new hydrosim/virtual.py module
  - _Requirements: 2.1, 2.2_

- [ ]* 5.1 Write unit tests for virtual components
  - Test VirtualSink creation with correct attributes
  - Test CarryoverLink creation with correct attributes
  - _Requirements: 2.1, 2.2_

- [x] 6. Implement _create_virtual_network() in LinearProgrammingSolver





  - Iterate through all nodes to find StorageNodes
  - For each StorageNode:
    - Call get_available_mass() to get available mass
    - Create VirtualSink with node_id = f"{node.node_id}_future", demand = available_mass
    - Create CarryoverLink with link_id = f"{node.node_id}_carryover"
    - Set carryover link bounds: min_flow = node.min_storage, max_flow = node.max_storage
    - Set carryover link cost = COST_STORAGE
    - Add virtual sink to augmented_nodes list
    - Add carryover link to augmented_links list
    - Add carryover link to augmented_constraints dict
    - Update node.outflows and virtual_sink.inflows
  - Return (augmented_nodes, augmented_links, augmented_constraints)
  - _Requirements: 2.1, 2.2, 2.5, 5.1, 5.2_

- [ ]* 6.1 Write property test for carryover link creation
  - **Property 4: Carryover link creation**
  - **Validates: Requirements 2.1, 5.1, 5.2**

- [ ]* 6.2 Write property test for virtual sink creation
  - **Property 5: Virtual sink creation**
  - **Validates: Requirements 2.2**

- [ ]* 6.3 Write property test for independent storage handling
  - **Property 7: Independent storage handling**
  - **Validates: Requirements 2.5**

- [x] 7. Update _solve_lp() to handle virtual components





  - Modify boundary condition (b_eq) calculation for StorageNode:
    - CRITICAL: b_eq[node_idx] = -node.get_available_mass() (negative for source)
  - Add boundary condition calculation for VirtualSink:
    - CRITICAL: b_eq[node_idx] = node.demand (positive for sink, equals available_mass)
  - Ensure virtual sinks are included in node_indices mapping
  - Ensure carryover links are included in link_indices mapping
  - Verify that sum(b_eq) == 0 for mass balance (log warning if not)
  - _Requirements: 3.3, 3.4, 6.1, 6.2, 6.4_

- [ ]* 7.1 Write property test for boundary condition construction
  - **Property 10: Boundary condition construction**
  - **Validates: Requirements 3.3, 3.4**

- [ ]* 7.2 Write property test for mass balance with virtual links
  - **Property 14: Mass balance with virtual links**
  - **Validates: Requirements 6.1**

- [ ]* 7.3 Write property test for uniform link treatment
  - **Property 15: Uniform link treatment**
  - **Validates: Requirements 6.2, 6.3**

- [ ]* 7.4 Write property test for virtual components in mass balance
  - **Property 16: Virtual components in mass balance**
  - **Validates: Requirements 6.4**

- [x] 8. Implement _update_storage_from_carryover() in LinearProgrammingSolver





  - Iterate through all nodes to find StorageNodes
  - For each StorageNode:
    - Get carryover link ID: f"{node.node_id}_carryover"
    - Extract carryover flow from flow_allocations dict
    - Call node.update_storage_from_carryover(carryover_flow)
  - _Requirements: 2.4_

- [ ]* 8.1 Write property test for carryover flow equals final storage
  - **Property 6: Carryover flow equals final storage**
  - **Validates: Requirements 2.3, 2.4**

- [x] 9. Refactor solve() method to use virtual network





  - Call _create_virtual_network() to get augmented components
  - Call _solve_lp() with augmented components
  - Extract physical flows (exclude links ending with "_carryover")
  - Call _update_storage_from_carryover() to update storage nodes
  - Return physical flows only
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 6.2, 6.3_

- [ ]* 9.1 Write property test for carryover flow bounds satisfaction
  - **Property 13: Carryover flow bounds satisfaction**
  - **Validates: Requirements 5.3, 5.4, 5.5**

- [x] 10. Update topology validation to exclude virtual components





  - Modify NetworkGraph.validate() to skip nodes with node_type == "virtual_sink"
  - Modify NetworkGraph.validate() to skip links with link_id ending in "_carryover"
  - Ensure validation passes with virtual components present
  - _Requirements: 6.5_

- [ ]* 10.1 Write property test for topology validation exclusion
  - **Property 17: Topology validation exclusion**
  - **Validates: Requirements 6.5**

- [x] 11. Checkpoint - Ensure all tests pass





  - Ensure all tests pass, ask the user if questions arise.

- [x] 12. Write integration test for drawdown scenario




  - Create network: Source (0 inflow) -> Storage (50k initial, 0 dead pool) -> Demand (2k request)
  - Run solver
  - Verify demand is met (delivered = 2k)
  - Verify storage decreased (final storage = 50k - 2k = 48k)
  - Verify carryover flow = 48k
  - _Requirements: 7.1, 1.1_

- [ ]* 12.1 Write property test for storage drawdown enables outflow
  - **Property 1: Storage drawdown enables outflow**
  - **Validates: Requirements 1.1, 1.2**

- [x] 13. Write integration test for refill scenario




  - Create network: Source (5k inflow) -> Storage (0 initial, 10k max) -> Demand (0 request)
  - Run solver
  - Verify storage increased (final storage = 5k)
  - Verify carryover flow = 5k
  - _Requirements: 7.2, 1.3_

- [ ]* 13.1 Write property test for storage refill from excess inflow
  - **Property 2: Storage refill from excess inflow**
  - **Validates: Requirements 1.3**

- [x] 14. Write integration test for dead pool scenario





  - Create network: Source (0 inflow) -> Storage (1k initial, 1k dead pool) -> Demand (2k request)
  - Run solver
  - Verify storage remains at dead pool (final storage = 1k)
  - Verify carryover flow = 1k
  - Verify demand deficit = 2k (unmet)
  - _Requirements: 7.3, 1.5_

- [ ]* 14.1 Write property test for dead pool constraint enforcement
  - **Property 3: Dead pool constraint enforcement**
  - **Validates: Requirements 1.5**

- [x] 15. Write integration test for complex scenario




  - Create network: Source (3k inflow) -> Storage (10k initial, 8k max, 0 dead pool) -> Demand (5k request)
  - Run solver
  - Verify demand is met (delivered = 5k)
  - Verify storage at capacity (final storage = 8k)
  - Verify mass balance: 10k + 3k - 5k - evap = 8k (so evap = 0 for this test)
  - _Requirements: 7.4_

- [x] 16. Write integration test for spilling scenario




  - Create network: Source (5k inflow) -> Storage (10k initial, 10k max) -> Demand (2k request) -> Spillway (0 cost)
  - Run solver
  - Verify demand is met (delivered = 2k)
  - Verify storage at capacity (final storage = 10k)
  - Verify spillway flow = 3k (excess after meeting demand and filling storage)
  - _Requirements: 7.5, 1.4_

- [ ]* 16.1 Write property test for storage prioritization over spilling
  - **Property 12: Storage prioritization over spilling**
  - **Validates: Requirements 4.5**

- [x] 17. Write integration test for demand prioritization




  - Create network: Source (1k inflow) -> Storage (2k initial, 10k max, 0 dead pool) -> Demand (3k request)
  - Run solver
  - Verify demand is met (delivered = 3k from 1k inflow + 2k drawdown)
  - Verify storage is drawn down (final storage = 0k)
  - Verify carryover flow = 0k
  - _Requirements: 4.4_

- [ ]* 17.1 Write property test for demand prioritization over storage
  - **Property 11: Demand prioritization over storage**
  - **Validates: Requirements 4.4**


- [x] 18. Update existing demand and spillway links to use cost constants



  - Search codebase for hardcoded cost values on demand links
  - Replace with COST_DEMAND constant
  - Search codebase for hardcoded cost values on spillway links
  - Replace with COST_SPILL constant
  - _Requirements: 8.4_

- [ ]* 18.1 Write property test for cost constant usage
  - **Property 18: Cost constant usage**
  - **Validates: Requirements 8.4**


- [x] 19. Add error handling for invalid storage configurations




  - Add validation in StorageNode.__init__() for min_storage <= max_storage
  - Add validation for initial_storage within bounds
  - Raise clear configuration errors with helpful messages
  - Add validation in solver for cost hierarchy (COST_DEMAND < COST_STORAGE < COST_SPILL)
  - _Requirements: Error handling from design document_

- [ ]* 19.1 Write unit tests for configuration error handling
  - Test invalid capacity ranges
  - Test invalid initial storage
  - Test invalid cost hierarchy
  - _Requirements: Error handling from design document_


- [x] 20. Add runtime warnings for edge cases



  - Add warning when storage approaches dead pool (within 10%)
  - Add warning when evaporation is high relative to storage (> 50%)
  - Use logging.warning() with node ID and relevant values
  - _Requirements: Error handling from design document_

- [ ]* 20.1 Write unit tests for runtime warnings
  - Test low storage warning is logged
  - Test high evaporation warning is logged
  - _Requirements: Error handling from design document_


- [x] 21. Update documentation and examples




  - Update README with storage drawdown explanation
  - Add example YAML configuration with storage drawdown
  - Update existing examples to include max_storage and min_storage parameters
  - Add docstrings to new methods explaining virtual link architecture
  - _Requirements: Supporting user adoption_

- [x] 22. Final checkpoint - Ensure all tests pass





  - Ensure all tests pass, ask the user if questions arise.
