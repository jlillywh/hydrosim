"""
Integration tests for storage drawdown functionality.

These tests verify that the virtual link architecture correctly enables
active storage drawdown and refill operations.
"""

import pytest
from datetime import datetime

from hydrosim.config import ElevationAreaVolume
from hydrosim.nodes import StorageNode, SourceNode, DemandNode, JunctionNode
from hydrosim.links import Link
from hydrosim.solver import LinearProgrammingSolver, COST_DEMAND
from hydrosim.strategies import GeneratorStrategy, DemandModel
from hydrosim.climate import ClimateState


class ConstantGeneratorStrategy(GeneratorStrategy):
    """Generator strategy that returns a constant value."""
    
    def __init__(self, value: float):
        self.value = value
    
    def generate(self, climate: ClimateState) -> float:
        return self.value


class ConstantDemandModel(DemandModel):
    """Demand model that returns a constant value."""
    
    def __init__(self, value: float):
        self.value = value
    
    def calculate(self, climate: ClimateState) -> float:
        return self.value


def create_test_climate() -> ClimateState:
    """Create a test climate state with minimal evaporation."""
    return ClimateState(
        date=datetime(2024, 1, 1),
        precip=0.0,
        t_max=20.0,
        t_min=10.0,
        solar=15.0,
        et0=0.0  # Zero evaporation for simpler testing
    )


def create_simple_eav() -> ElevationAreaVolume:
    """Create a simple EAV table with minimal surface area."""
    return ElevationAreaVolume(
        elevations=[100.0, 200.0],
        areas=[0.1, 0.1],  # Very small area to minimize evaporation
        volumes=[0.0, 100000.0]
    )


def create_test_climate_with_evaporation() -> ClimateState:
    """Create a test climate state with significant evaporation."""
    return ClimateState(
        date=datetime(2024, 1, 1),
        precip=0.0,
        t_max=30.0,
        t_min=20.0,
        solar=25.0,
        et0=5.0  # 5mm/day evaporation rate
    )


def create_eav_with_surface_area() -> ElevationAreaVolume:
    """Create an EAV table with significant surface area for evaporation testing."""
    return ElevationAreaVolume(
        elevations=[100.0, 200.0],
        areas=[100.0, 100.0],  # 100 units² surface area
        volumes=[0.0, 100000.0]
    )


def test_drawdown_scenario():
    """
    Test storage drawdown scenario.
    
    Network: Source (0 inflow) -> Storage (50k initial, 0 dead pool) -> Demand (2k request)
    
    Expected behavior:
    - Demand is met (delivered = 2k)
    - Storage decreased (final storage = 50k - 2k = 48k)
    - Carryover flow = 48k
    
    Requirements: 7.1, 1.1
    
    NOTE: This test uses the Universal Sink architecture which ensures
    strict mass conservation (sum(b_eq) = 0). All water entering the system
    (sources + storage) must exit through the Universal Sink via either:
    - Demand-to-sink links (representing satisfied demands)
    - Carryover links (representing water stored for next timestep)
    """
    # Create nodes
    source = SourceNode("source1", ConstantGeneratorStrategy(0.0))
    
    storage = StorageNode(
        "storage1",
        initial_storage=50000.0,
        eav_table=create_simple_eav(),
        max_storage=100000.0,
        min_storage=0.0
    )
    
    demand = DemandNode("demand1", ConstantDemandModel(2000.0))
    
    # Create links
    link1 = Link("link1", source, storage, physical_capacity=10000.0, cost=1.0)
    link2 = Link("link2", storage, demand, physical_capacity=10000.0, cost=COST_DEMAND)
    
    # Set up connections
    source.outflows.append(link1)
    storage.inflows.append(link1)
    storage.outflows.append(link2)
    demand.inflows.append(link2)
    
    # Run node steps
    climate = create_test_climate()
    source.step(climate)
    storage.step(climate)
    demand.step(climate)
    
    # Calculate constraints
    constraints = {
        "link1": link1.calculate_constraints(),
        "link2": link2.calculate_constraints(),
    }
    
    # Solve
    solver = LinearProgrammingSolver()
    flows = solver.solve([source, storage, demand], [link1, link2], constraints)
    
    # Verify demand is met (delivered = 2k)
    assert flows["link2"] == pytest.approx(2000.0, abs=1e-6), \
        f"Expected demand delivery of 2000.0, got {flows['link2']}"
    
    # Verify storage decreased (final storage = 50k - 2k = 48k)
    assert storage.storage == pytest.approx(48000.0, abs=1e-6), \
        f"Expected final storage of 48000.0, got {storage.storage}"
    
    # Verify carryover flow = 48k
    # The carryover flow is internal to the solver, but we can verify it
    # indirectly through the final storage value
    expected_carryover = 48000.0
    assert storage.storage == pytest.approx(expected_carryover, abs=1e-6), \
        f"Expected carryover flow of {expected_carryover}, got {storage.storage}"
    
    # Verify mass balance: initial storage - outflow = final storage
    # 50000 - 2000 = 48000
    initial_storage = 50000.0
    outflow = flows["link2"]
    expected_final = initial_storage - outflow
    assert storage.storage == pytest.approx(expected_final, abs=1e-6), \
        f"Mass balance violated: {initial_storage} - {outflow} != {storage.storage}"


def test_drawdown_scenario_with_evaporation():
    """
    Test storage drawdown scenario with evaporation loss.
    
    Network: Source (0 inflow) -> Storage (50k initial, 0 dead pool) -> Demand (2k request)
    With evaporation: 5mm/day * 100 m² / 1000 = 0.5 m³ evaporation
    
    Expected behavior:
    - Available mass = 50k - 0.5 = 49999.5
    - Demand is met (delivered = 2k)
    - Storage decreased accounting for evaporation
    - Final storage = 50k - 0.5 (evap) - 2k (demand) = 47999.5
    - Carryover flow = 47999.5
    
    Requirements: 7.1, 1.1, 3.1, 3.2
    
    This test verifies that:
    1. Evaporation is correctly calculated and reduces available mass
    2. The solver accounts for evaporation when allocating water
    3. Mass balance includes evaporation: initial - evap - outflow = final
    """
    # Create nodes
    source = SourceNode("source1", ConstantGeneratorStrategy(0.0))
    
    storage = StorageNode(
        "storage1",
        initial_storage=50000.0,
        eav_table=create_eav_with_surface_area(),
        max_storage=100000.0,
        min_storage=0.0
    )
    
    demand = DemandNode("demand1", ConstantDemandModel(2000.0))
    
    # Create links
    link1 = Link("link1", source, storage, physical_capacity=10000.0, cost=1.0)
    link2 = Link("link2", storage, demand, physical_capacity=10000.0, cost=COST_DEMAND)
    
    # Set up connections
    source.outflows.append(link1)
    storage.inflows.append(link1)
    storage.outflows.append(link2)
    demand.inflows.append(link2)
    
    # Run node steps
    climate = create_test_climate_with_evaporation()
    source.step(climate)
    storage.step(climate)
    demand.step(climate)
    
    # Verify evaporation was calculated
    # ET0 = 5mm/day, Surface Area = 100 m²
    # Evaporation = 100 * 5 / 1000 = 0.5 m³
    expected_evaporation = 0.5
    assert storage.evap_loss == pytest.approx(expected_evaporation, abs=1e-6), \
        f"Expected evaporation of {expected_evaporation}, got {storage.evap_loss}"
    
    # Verify available mass accounts for evaporation
    # Available mass = 50000 - 0.5 = 49999.5
    expected_available_mass = 49999.5
    available_mass = storage.get_available_mass()
    assert available_mass == pytest.approx(expected_available_mass, abs=1e-6), \
        f"Expected available mass of {expected_available_mass}, got {available_mass}"
    
    # Calculate constraints
    constraints = {
        "link1": link1.calculate_constraints(),
        "link2": link2.calculate_constraints(),
    }
    
    # Solve
    solver = LinearProgrammingSolver()
    flows = solver.solve([source, storage, demand], [link1, link2], constraints)
    
    # Verify demand is met (delivered = 2k)
    assert flows["link2"] == pytest.approx(2000.0, abs=1e-6), \
        f"Expected demand delivery of 2000.0, got {flows['link2']}"
    
    # Verify storage decreased accounting for evaporation
    # Final storage = initial - evaporation - outflow
    # 50000 - 0.5 - 2000 = 47999.5
    expected_final_storage = 47999.5
    assert storage.storage == pytest.approx(expected_final_storage, abs=1e-6), \
        f"Expected final storage of {expected_final_storage}, got {storage.storage}"
    
    # Verify carryover flow = 47999.5
    expected_carryover = 47999.5
    assert storage.storage == pytest.approx(expected_carryover, abs=1e-6), \
        f"Expected carryover flow of {expected_carryover}, got {storage.storage}"
    
    # Verify mass balance with evaporation:
    # initial storage - evaporation - outflow = final storage
    # 50000 - 0.5 - 2000 = 47999.5
    initial_storage = 50000.0
    evaporation = expected_evaporation
    outflow = flows["link2"]
    expected_final = initial_storage - evaporation - outflow
    assert storage.storage == pytest.approx(expected_final, abs=1e-6), \
        f"Mass balance violated: {initial_storage} - {evaporation} - {outflow} != {storage.storage}"



def test_refill_scenario():
    """
    Test storage refill scenario.
    
    Network: Source (5k inflow) -> Storage (0 initial, 10k max) -> Demand (0 request)
    
    Expected behavior:
    - Storage increased (final storage = 5k)
    - Carryover flow = 5k
    
    Requirements: 7.2, 1.3
    
    NOTE: This test verifies that when inflow exceeds demand, the excess water
    is stored in the reservoir up to its maximum capacity. The carryover link
    represents water staying in storage for the next timestep.
    """
    # Create nodes
    source = SourceNode("source1", ConstantGeneratorStrategy(5000.0))
    
    storage = StorageNode(
        "storage1",
        initial_storage=0.0,
        eav_table=create_simple_eav(),
        max_storage=10000.0,
        min_storage=0.0
    )
    
    demand = DemandNode("demand1", ConstantDemandModel(0.0))
    
    # Create links
    link1 = Link("link1", source, storage, physical_capacity=10000.0, cost=1.0)
    link2 = Link("link2", storage, demand, physical_capacity=10000.0, cost=COST_DEMAND)
    
    # Set up connections
    source.outflows.append(link1)
    storage.inflows.append(link1)
    storage.outflows.append(link2)
    demand.inflows.append(link2)
    
    # Run node steps
    climate = create_test_climate()
    source.step(climate)
    storage.step(climate)
    demand.step(climate)
    
    # Calculate constraints
    constraints = {
        "link1": link1.calculate_constraints(),
        "link2": link2.calculate_constraints(),
    }
    
    # Solve
    solver = LinearProgrammingSolver()
    flows = solver.solve([source, storage, demand], [link1, link2], constraints)
    
    # Verify storage increased (final storage = 5k)
    assert storage.storage == pytest.approx(5000.0, abs=1e-6), \
        f"Expected final storage of 5000.0, got {storage.storage}"
    
    # Verify carryover flow = 5k
    # The carryover flow is internal to the solver, but we can verify it
    # indirectly through the final storage value
    expected_carryover = 5000.0
    assert storage.storage == pytest.approx(expected_carryover, abs=1e-6), \
        f"Expected carryover flow of {expected_carryover}, got {storage.storage}"
    
    # Verify mass balance: initial storage + inflow - outflow = final storage
    # 0 + 5000 - 0 = 5000
    initial_storage = 0.0
    inflow = flows["link1"]
    outflow = flows["link2"]
    expected_final = initial_storage + inflow - outflow
    assert storage.storage == pytest.approx(expected_final, abs=1e-6), \
        f"Mass balance violated: {initial_storage} + {inflow} - {outflow} != {storage.storage}"
    
    # Verify no demand was delivered (since demand request was 0)
    assert flows["link2"] == pytest.approx(0.0, abs=1e-6), \
        f"Expected no demand delivery, got {flows['link2']}"
    
    # Verify inflow was fully captured
    assert flows["link1"] == pytest.approx(5000.0, abs=1e-6), \
        f"Expected inflow of 5000.0, got {flows['link1']}"


def test_dead_pool_scenario():
    """
    Test dead pool constraint enforcement.
    
    Network: Source (0 inflow) -> Storage (1k initial, 1k dead pool) -> Demand (2k request)
    
    Expected behavior:
    - Storage remains at dead pool (final storage = 1k)
    - Carryover flow = 1k
    - Demand deficit = 2k (unmet)
    
    Requirements: 7.3, 1.5
    
    NOTE: This test verifies that the dead pool constraint prevents further
    drawdown. When storage is at the dead pool level, the carryover link's
    lower bound (min_flow = dead_pool) prevents the solver from allocating
    water below this threshold, even when downstream demand exists.
    """
    # Create nodes
    source = SourceNode("source1", ConstantGeneratorStrategy(0.0))
    
    storage = StorageNode(
        "storage1",
        initial_storage=1000.0,
        eav_table=create_simple_eav(),
        max_storage=10000.0,
        min_storage=1000.0  # Dead pool = 1k
    )
    
    demand = DemandNode("demand1", ConstantDemandModel(2000.0))
    
    # Create links
    link1 = Link("link1", source, storage, physical_capacity=10000.0, cost=1.0)
    link2 = Link("link2", storage, demand, physical_capacity=10000.0, cost=COST_DEMAND)
    
    # Set up connections
    source.outflows.append(link1)
    storage.inflows.append(link1)
    storage.outflows.append(link2)
    demand.inflows.append(link2)
    
    # Run node steps
    climate = create_test_climate()
    source.step(climate)
    storage.step(climate)
    demand.step(climate)
    
    # Calculate constraints
    constraints = {
        "link1": link1.calculate_constraints(),
        "link2": link2.calculate_constraints(),
    }
    
    # Solve
    solver = LinearProgrammingSolver()
    flows = solver.solve([source, storage, demand], [link1, link2], constraints)
    
    # Verify storage remains at dead pool (final storage = 1k)
    assert storage.storage == pytest.approx(1000.0, abs=1e-6), \
        f"Expected final storage at dead pool (1000.0), got {storage.storage}"
    
    # Verify carryover flow = 1k
    # The carryover flow equals the final storage, which should be the dead pool
    expected_carryover = 1000.0
    assert storage.storage == pytest.approx(expected_carryover, abs=1e-6), \
        f"Expected carryover flow of {expected_carryover}, got {storage.storage}"
    
    # Verify demand deficit = 2k (unmet)
    # Since there's no inflow and storage is at dead pool, no water can be delivered
    assert flows["link2"] == pytest.approx(0.0, abs=1e-6), \
        f"Expected no demand delivery (dead pool constraint), got {flows['link2']}"
    
    # Calculate demand deficit
    demand_request = 2000.0
    demand_delivered = flows["link2"]
    demand_deficit = demand_request - demand_delivered
    assert demand_deficit == pytest.approx(2000.0, abs=1e-6), \
        f"Expected demand deficit of 2000.0, got {demand_deficit}"
    
    # Verify mass balance: initial storage + inflow - outflow = final storage
    # 1000 + 0 - 0 = 1000
    initial_storage = 1000.0
    inflow = flows["link1"]
    outflow = flows["link2"]
    expected_final = initial_storage + inflow - outflow
    assert storage.storage == pytest.approx(expected_final, abs=1e-6), \
        f"Mass balance violated: {initial_storage} + {inflow} - {outflow} != {storage.storage}"
    
    # Verify no inflow occurred
    assert flows["link1"] == pytest.approx(0.0, abs=1e-6), \
        f"Expected no inflow, got {flows['link1']}"
    
    # Verify dead pool constraint was enforced
    # The storage should not have gone below the dead pool level
    assert storage.storage >= storage.min_storage - 1e-6, \
        f"Storage {storage.storage} violated dead pool constraint {storage.min_storage}"


def test_complex_scenario():
    """
    Test complex scenario with inflow, storage drawdown, and capacity constraint.
    
    Network: Source (3k inflow) -> Storage (10k initial, 10k max, 0 dead pool) -> Demand (5k request)
    
    Expected behavior:
    - Demand is met (delivered = 5k)
    - Storage at final level (final storage = 8k)
    - Mass balance: 10k + 3k - 5k - evap = 8k (so evap = 0 for this test)
    
    Requirements: 7.4
    
    NOTE: This test verifies a complex scenario where:
    1. Storage has initial water (10k)
    2. Inflow provides additional water (3k)
    3. Demand requires water (5k)
    4. Final storage is 8k (initial + inflow - demand)
    
    The solver must:
    - Meet the demand first (priority via COST_DEMAND = -1000)
    - Store remaining water (priority via COST_STORAGE = -1)
    - Handle the mass balance correctly
    
    Mass balance: initial + inflow - demand - evap = final
    10k + 3k - 5k - 0 = 8k ✓
    
    This tests the interaction between:
    - Initial storage providing water
    - Inflow adding water
    - Demand consuming water
    - Final storage being the result of all flows
    """
    # Create nodes
    source = SourceNode("source1", ConstantGeneratorStrategy(3000.0))
    
    storage = StorageNode(
        "storage1",
        initial_storage=10000.0,
        eav_table=create_simple_eav(),
        max_storage=10000.0,  # Max capacity allows initial storage
        min_storage=0.0
    )
    
    demand = DemandNode("demand1", ConstantDemandModel(5000.0))
    
    # Create links
    link1 = Link("link1", source, storage, physical_capacity=10000.0, cost=1.0)
    link2 = Link("link2", storage, demand, physical_capacity=10000.0, cost=COST_DEMAND)
    
    # Set up connections
    source.outflows.append(link1)
    storage.inflows.append(link1)
    storage.outflows.append(link2)
    demand.inflows.append(link2)
    
    # Run node steps
    climate = create_test_climate()
    source.step(climate)
    storage.step(climate)
    demand.step(climate)
    
    # Calculate constraints
    constraints = {
        "link1": link1.calculate_constraints(),
        "link2": link2.calculate_constraints(),
    }
    
    # Solve
    solver = LinearProgrammingSolver()
    flows = solver.solve([source, storage, demand], [link1, link2], constraints)
    
    # Verify demand is met (delivered = 5k)
    assert flows["link2"] == pytest.approx(5000.0, abs=1e-6), \
        f"Expected demand delivery of 5000.0, got {flows['link2']}"
    
    # Verify storage at capacity (final storage = 8k)
    assert storage.storage == pytest.approx(8000.0, abs=1e-6), \
        f"Expected final storage at capacity (8000.0), got {storage.storage}"
    
    # Verify mass balance: initial + inflow - demand - evap = final
    # 10k + 3k - 5k - 0 = 8k
    initial_storage = 10000.0
    inflow = flows["link1"]
    outflow = flows["link2"]
    evaporation = storage.evap_loss  # Should be ~0 with create_test_climate()
    expected_final = initial_storage + inflow - outflow - evaporation
    
    assert storage.storage == pytest.approx(expected_final, abs=1e-6), \
        f"Mass balance violated: {initial_storage} + {inflow} - {outflow} - {evaporation} != {storage.storage}"
    
    # Verify evaporation is minimal (as expected with test climate)
    assert evaporation < 1.0, \
        f"Expected minimal evaporation, got {evaporation}"
    
    # Verify inflow was captured
    assert flows["link1"] == pytest.approx(3000.0, abs=1e-6), \
        f"Expected inflow of 3000.0, got {flows['link1']}"
    
    # Verify storage capacity constraint was respected
    assert storage.storage <= storage.max_storage + 1e-6, \
        f"Storage {storage.storage} exceeded max capacity {storage.max_storage}"
    
    # Verify carryover flow equals final storage
    expected_carryover = 8000.0
    assert storage.storage == pytest.approx(expected_carryover, abs=1e-6), \
        f"Expected carryover flow of {expected_carryover}, got {storage.storage}"
    
    # Additional verification: total water available vs. total water allocated
    # Available water = initial storage + inflow = 10k + 3k = 13k
    # Allocated water = demand + final storage = 5k + 8k = 13k ✓
    total_available = initial_storage + inflow
    total_allocated = outflow + storage.storage
    assert total_available == pytest.approx(total_allocated, abs=1e-6), \
        f"Water accounting error: available {total_available} != allocated {total_allocated}"


def test_spilling_scenario():
    """
    Test spilling scenario with storage approaching capacity.
    
    Network: Source (5k inflow) -> Storage (8k initial, 10k max) -> Demand (2k request)
    
    Expected behavior:
    - Demand is met (delivered = 2k)
    - Storage at capacity (final storage = 10k)
    - Implicit spill = 1k (excess after meeting demand and filling storage)
    
    Requirements: 7.5, 1.4
    
    NOTE: This test verifies the cost hierarchy:
    1. COST_DEMAND (-1000): Demand is met first (2k)
    2. COST_STORAGE (-1): Storage fills to capacity (10k)
    3. Excess water (1k) is implicitly spilled (not stored or delivered)
    
    Mass balance: initial + inflow = demand + final_storage + implicit_spill
    8k + 5k = 2k + 10k + 1k ✓
    
    The solver must:
    - Meet demand first (highest priority)
    - Fill storage to capacity (medium priority)
    - Allow excess to be spilled (lowest priority)
    
    In the Universal Sink architecture:
    - Total supply = source inflow + storage available mass = 5k + 8k = 13k
    - Universal Sink demands this total (13k)
    - Demand-to-sink link delivers 2k
    - Carryover link stores 10k
    - Remaining 1k represents spilled water (not explicitly tracked)
    """
    # Create nodes
    source = SourceNode("source1", ConstantGeneratorStrategy(5000.0))
    
    storage = StorageNode(
        "storage1",
        initial_storage=8000.0,  # Not at capacity yet
        eav_table=create_simple_eav(),
        max_storage=10000.0,
        min_storage=0.0
    )
    
    demand = DemandNode("demand1", ConstantDemandModel(2000.0))
    
    # Create links
    link1 = Link("link1", source, storage, physical_capacity=10000.0, cost=1.0)
    link2 = Link("link2", storage, demand, physical_capacity=10000.0, cost=COST_DEMAND)
    
    # Set up connections
    source.outflows.append(link1)
    storage.inflows.append(link1)
    storage.outflows.append(link2)
    demand.inflows.append(link2)
    
    # Run node steps
    climate = create_test_climate()
    source.step(climate)
    storage.step(climate)
    demand.step(climate)
    
    # Calculate constraints
    constraints = {
        "link1": link1.calculate_constraints(),
        "link2": link2.calculate_constraints(),
    }
    
    # Solve
    solver = LinearProgrammingSolver()
    flows = solver.solve(
        [source, storage, demand], 
        [link1, link2], 
        constraints
    )
    
    # Verify demand is met (delivered = 2k)
    assert flows["link2"] == pytest.approx(2000.0, abs=1e-6), \
        f"Expected demand delivery of 2000.0, got {flows['link2']}"
    
    # Verify storage at capacity (final storage = 10k)
    assert storage.storage == pytest.approx(10000.0, abs=1e-6), \
        f"Expected final storage at capacity (10000.0), got {storage.storage}"
    
    # Calculate implicit spill
    # Total available = initial storage + inflow = 8k + 5k = 13k
    # Demand = 2k, Final storage = 10k
    # Implicit spill = 13k - 2k - 10k = 1k
    initial_storage = 8000.0
    inflow = flows["link1"]
    demand_flow = flows["link2"]
    final_storage = storage.storage
    evaporation = storage.evap_loss  # Should be ~0 with create_test_climate()
    
    total_available = initial_storage + inflow
    total_allocated = demand_flow + final_storage
    implicit_spill = total_available - total_allocated - evaporation
    
    # Verify implicit spill = 1k
    assert implicit_spill == pytest.approx(1000.0, abs=1e-6), \
        f"Expected implicit spill of 1000.0, got {implicit_spill}"
    
    # Verify mass balance: initial + inflow = demand + final_storage + spill + evap
    # 8k + 5k = 2k + 10k + 1k + 0
    expected_total = demand_flow + final_storage + implicit_spill + evaporation
    assert total_available == pytest.approx(expected_total, abs=1e-6), \
        f"Mass balance violated: {total_available} != {expected_total}"
    
    # Verify cost hierarchy was respected:
    # 1. Demand was met (COST_DEMAND = -1000)
    assert flows["link2"] == pytest.approx(2000.0, abs=1e-6), \
        "Demand should be met first (highest priority)"
    
    # 2. Storage was maintained at capacity (COST_STORAGE = -1)
    assert storage.storage == pytest.approx(10000.0, abs=1e-6), \
        "Storage should be at capacity (medium priority)"
    
    # 3. Excess was spilled (implicit, lowest priority)
    assert implicit_spill > 0, \
        "Excess water should be spilled (lowest priority)"
    
    # Verify storage capacity constraint was respected
    assert storage.storage <= storage.max_storage + 1e-6, \
        f"Storage {storage.storage} exceeded max capacity {storage.max_storage}"
    
    # Verify inflow was captured
    assert flows["link1"] == pytest.approx(5000.0, abs=1e-6), \
        f"Expected inflow of 5000.0, got {flows['link1']}"
    
    # Additional verification: storage should not exceed capacity
    # Even with 5k inflow and 10k initial storage, final should be capped at 10k max
    assert storage.storage == storage.max_storage, \
        f"Storage should be at max capacity when excess water is available"


def test_demand_prioritization():
    """
    Test demand prioritization over storage.
    
    Network: Source (1k inflow) -> Storage (2k initial, 10k max, 0 dead pool) -> Demand (3k request)
    
    Expected behavior:
    - Demand is met (delivered = 3k from 1k inflow + 2k drawdown)
    - Storage is drawn down (final storage = 0k)
    - Carryover flow = 0k
    
    Requirements: 4.4
    
    NOTE: This test verifies the cost hierarchy prioritizes demand over storage.
    When total available water (inflow + storage) is insufficient to meet both
    demand and maintain storage, the solver should:
    1. Meet demand first (COST_DEMAND = -1000, highest priority)
    2. Draw down storage to zero if necessary (COST_STORAGE = -1, lower priority)
    
    Mass balance: initial + inflow = demand + final_storage
    2k + 1k = 3k + 0k ✓
    
    The solver must:
    - Allocate all available water to demand (3k total)
    - Draw storage down to zero (carryover = 0k)
    - Prioritize demand satisfaction over storage preservation
    """
    # Create nodes
    source = SourceNode("source1", ConstantGeneratorStrategy(1000.0))
    
    storage = StorageNode(
        "storage1",
        initial_storage=2000.0,
        eav_table=create_simple_eav(),
        max_storage=10000.0,
        min_storage=0.0  # No dead pool
    )
    
    demand = DemandNode("demand1", ConstantDemandModel(3000.0))
    
    # Create links
    link1 = Link("link1", source, storage, physical_capacity=10000.0, cost=1.0)
    link2 = Link("link2", storage, demand, physical_capacity=10000.0, cost=COST_DEMAND)
    
    # Set up connections
    source.outflows.append(link1)
    storage.inflows.append(link1)
    storage.outflows.append(link2)
    demand.inflows.append(link2)
    
    # Run node steps
    climate = create_test_climate()
    source.step(climate)
    storage.step(climate)
    demand.step(climate)
    
    # Calculate constraints
    constraints = {
        "link1": link1.calculate_constraints(),
        "link2": link2.calculate_constraints(),
    }
    
    # Solve
    solver = LinearProgrammingSolver()
    flows = solver.solve([source, storage, demand], [link1, link2], constraints)
    
    # Verify demand is met (delivered = 3k from 1k inflow + 2k drawdown)
    assert flows["link2"] == pytest.approx(3000.0, abs=1e-6), \
        f"Expected demand delivery of 3000.0, got {flows['link2']}"
    
    # Verify storage is drawn down (final storage = 0k)
    assert storage.storage == pytest.approx(0.0, abs=1e-6), \
        f"Expected final storage of 0.0, got {storage.storage}"
    
    # Verify carryover flow = 0k
    # The carryover flow equals the final storage, which should be zero
    expected_carryover = 0.0
    assert storage.storage == pytest.approx(expected_carryover, abs=1e-6), \
        f"Expected carryover flow of {expected_carryover}, got {storage.storage}"
    
    # Verify mass balance: initial + inflow - demand = final_storage
    # 2k + 1k - 3k = 0k
    initial_storage = 2000.0
    inflow = flows["link1"]
    demand_flow = flows["link2"]
    evaporation = storage.evap_loss  # Should be ~0 with create_test_climate()
    expected_final = initial_storage + inflow - demand_flow - evaporation
    
    assert storage.storage == pytest.approx(expected_final, abs=1e-6), \
        f"Mass balance violated: {initial_storage} + {inflow} - {demand_flow} - {evaporation} != {storage.storage}"
    
    # Verify cost hierarchy was respected:
    # Demand was fully met (COST_DEMAND = -1000) at the expense of storage (COST_STORAGE = -1)
    assert flows["link2"] == pytest.approx(3000.0, abs=1e-6), \
        "Demand should be fully met (highest priority)"
    
    assert storage.storage == pytest.approx(0.0, abs=1e-6), \
        "Storage should be drawn down to zero to meet demand (lower priority)"
    
    # Verify inflow was captured
    assert flows["link1"] == pytest.approx(1000.0, abs=1e-6), \
        f"Expected inflow of 1000.0, got {flows['link1']}"
    
    # Verify total water available equals total water allocated
    # Available water = initial storage + inflow = 2k + 1k = 3k
    # Allocated water = demand + final storage = 3k + 0k = 3k ✓
    total_available = initial_storage + inflow
    total_allocated = demand_flow + storage.storage + evaporation
    assert total_available == pytest.approx(total_allocated, abs=1e-6), \
        f"Water accounting error: available {total_available} != allocated {total_allocated}"
    
    # Verify storage did not go below dead pool (which is 0 in this case)
    assert storage.storage >= storage.min_storage - 1e-6, \
        f"Storage {storage.storage} violated dead pool constraint {storage.min_storage}"
    
    # Additional verification: demand prioritization
    # With 3k total available water and 3k demand, all water should go to demand
    # This demonstrates that demand (cost -1000) is prioritized over storage (cost -1)
    assert demand_flow == total_available - evaporation, \
        f"All available water should be allocated to demand when demand exceeds supply"
