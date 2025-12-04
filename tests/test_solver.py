"""
Tests for network solver implementations.

This module tests the NetworkSolver implementations, particularly the
LinearProgrammingSolver.
"""

import pytest
from datetime import datetime
from hydrosim.climate import ClimateState
from hydrosim.config import ElevationAreaVolume
from hydrosim.nodes import StorageNode, JunctionNode, SourceNode, DemandNode
from hydrosim.links import Link
from hydrosim.solver import LinearProgrammingSolver
from hydrosim.strategies import GeneratorStrategy, DemandModel


class MockGeneratorStrategy(GeneratorStrategy):
    """Mock generator strategy for testing."""
    
    def __init__(self, value: float):
        self.value = value
    
    def generate(self, climate: ClimateState) -> float:
        return self.value


class MockDemandModel(DemandModel):
    """Mock demand model for testing."""
    
    def __init__(self, value: float):
        self.value = value
    
    def calculate(self, climate: ClimateState) -> float:
        return self.value


def create_test_climate() -> ClimateState:
    """Create a test climate state."""
    return ClimateState(
        date=datetime(2024, 1, 1),
        precip=10.0,
        t_max=25.0,
        t_min=15.0,
        solar=20.0,
        et0=5.0
    )


def test_solver_simple_source_to_demand():
    """Test solver with simple source to demand network."""
    # Create nodes
    source = SourceNode("source1", MockGeneratorStrategy(100.0))
    demand = DemandNode("demand1", MockDemandModel(50.0))
    
    # Create link
    link = Link("link1", source, demand, physical_capacity=200.0, cost=1.0)
    source.outflows.append(link)
    demand.inflows.append(link)
    
    # Run node steps to generate supply and demand
    climate = create_test_climate()
    source.step(climate)
    demand.step(climate)
    
    # Calculate constraints
    constraints = {
        "link1": link.calculate_constraints()
    }
    
    # Solve
    solver = LinearProgrammingSolver()
    flows = solver.solve([source, demand], [link], constraints)
    
    # Verify solution
    assert "link1" in flows
    assert flows["link1"] == pytest.approx(50.0)  # Should match demand


def test_solver_multiple_links():
    """Test solver with multiple links."""
    # Create nodes
    source = SourceNode("source1", MockGeneratorStrategy(100.0))
    junction = JunctionNode("junction1")
    demand1 = DemandNode("demand1", MockDemandModel(30.0))
    demand2 = DemandNode("demand2", MockDemandModel(40.0))
    
    # Create links
    link1 = Link("link1", source, junction, physical_capacity=200.0, cost=1.0)
    link2 = Link("link2", junction, demand1, physical_capacity=50.0, cost=1.0)
    link3 = Link("link3", junction, demand2, physical_capacity=50.0, cost=1.0)
    
    source.outflows.append(link1)
    junction.inflows.append(link1)
    junction.outflows.extend([link2, link3])
    demand1.inflows.append(link2)
    demand2.inflows.append(link3)
    
    # Run node steps
    climate = create_test_climate()
    source.step(climate)
    demand1.step(climate)
    demand2.step(climate)
    
    # Calculate constraints
    constraints = {
        "link1": link1.calculate_constraints(),
        "link2": link2.calculate_constraints(),
        "link3": link3.calculate_constraints(),
    }
    
    # Solve
    solver = LinearProgrammingSolver()
    flows = solver.solve([source, junction, demand1, demand2], 
                        [link1, link2, link3], constraints)
    
    # Verify solution
    assert flows["link1"] == pytest.approx(70.0)  # Total demand
    assert flows["link2"] == pytest.approx(30.0)  # Demand1
    assert flows["link3"] == pytest.approx(40.0)  # Demand2


def test_solver_respects_capacity_constraints():
    """Test solver respects link capacity constraints."""
    # Create nodes with demand that can be met within capacity
    source = SourceNode("source1", MockGeneratorStrategy(100.0))
    demand = DemandNode("demand1", MockDemandModel(40.0))  # Demand within capacity
    
    # Create link with limited capacity
    link = Link("link1", source, demand, physical_capacity=50.0, cost=1.0)
    source.outflows.append(link)
    demand.inflows.append(link)
    
    # Run node steps
    climate = create_test_climate()
    source.step(climate)
    demand.step(climate)
    
    # Calculate constraints
    constraints = {
        "link1": link.calculate_constraints()
    }
    
    # Solve
    solver = LinearProgrammingSolver()
    flows = solver.solve([source, demand], [link], constraints)
    
    # Verify solution respects capacity and meets demand
    assert flows["link1"] == pytest.approx(40.0)  # Meets demand within capacity


def test_solver_minimizes_cost():
    """Test solver minimizes cost when multiple paths exist."""
    # Create nodes
    source = SourceNode("source1", MockGeneratorStrategy(100.0))
    demand = DemandNode("demand1", MockDemandModel(50.0))
    
    # Create two parallel links with different costs
    link1 = Link("link1", source, demand, physical_capacity=100.0, cost=1.0)
    link2 = Link("link2", source, demand, physical_capacity=100.0, cost=2.0)
    source.outflows.extend([link1, link2])
    demand.inflows.extend([link1, link2])
    
    # Run node steps
    climate = create_test_climate()
    source.step(climate)
    demand.step(climate)
    
    # Calculate constraints
    constraints = {
        "link1": link1.calculate_constraints(),
        "link2": link2.calculate_constraints(),
    }
    
    # Solve
    solver = LinearProgrammingSolver()
    flows = solver.solve([source, demand], [link1, link2], constraints)
    
    # Verify solution uses cheaper link
    assert flows["link1"] == pytest.approx(50.0)  # All flow through cheaper link
    assert flows["link2"] == pytest.approx(0.0)   # No flow through expensive link


def test_solver_with_storage_node():
    """Test solver with storage node using virtual network architecture.
    
    With the virtual network architecture, storage nodes:
    1. Provide their available mass (storage - evaporation) as a source
    2. Create a carryover link representing final storage
    3. Can draw down to meet demand or refill from excess inflow
    
    This test verifies the solver correctly handles storage with upstream inflow.
    """
    # Create EAV table with very small surface area to minimize evaporation
    elevations = [100.0, 110.0, 120.0]
    areas = [0.01, 0.02, 0.03]  # Very small areas (minimal evaporation)
    volumes = [0.0, 10000.0, 30000.0]
    eav = ElevationAreaVolume(elevations, areas, volumes)
    
    # Create nodes
    source = SourceNode("source1", MockGeneratorStrategy(100.0))
    storage = StorageNode("storage1", initial_storage=10000.0, eav_table=eav, 
                         max_storage=50000.0, min_storage=0.0)
    demand = DemandNode("demand1", MockDemandModel(50.0))
    
    # Create links
    link1 = Link("link1", source, storage, physical_capacity=200.0, cost=1.0)
    link2 = Link("link2", storage, demand, physical_capacity=200.0, cost=-1000.0)  # Demand link
    
    source.outflows.append(link1)
    storage.inflows.append(link1)
    storage.outflows.append(link2)
    demand.inflows.append(link2)
    
    # Run node steps
    climate = create_test_climate()
    source.step(climate)
    storage.step(climate)  # Calculates evaporation (should be minimal)
    demand.step(climate)
    
    # Calculate constraints
    constraints = {
        "link1": link1.calculate_constraints(),
        "link2": link2.calculate_constraints(),
    }
    
    # Solve
    solver = LinearProgrammingSolver()
    flows = solver.solve([source, storage, demand], [link1, link2], constraints)
    
    # Verify solution
    # With virtual network architecture:
    # - Storage provides ~10000 as available mass (minus minimal evaporation)
    # - Source provides 100
    # - Demand requests 50
    # - Solver should meet demand (50) and store the rest
    assert "link1" in flows
    assert "link2" in flows
    assert flows["link2"] == pytest.approx(50.0)  # Demand is met
    
    # Verify storage was updated via carryover link
    # Final storage should be: initial + inflow - outflow - evaporation
    # = 10000 + 100 - 50 - evap ≈ 10050 (minus small evaporation)
    expected_final = 10000.0 + 100.0 - 50.0 - storage.evap_loss
    assert storage.storage == pytest.approx(expected_final, abs=1.0)


def test_solver_empty_network():
    """Test solver with empty network."""
    solver = LinearProgrammingSolver()
    flows = solver.solve([], [], {})
    
    assert flows == {}


def test_solver_infeasible_network():
    """Test solver raises error for infeasible network."""
    # Create nodes with demand exceeding supply
    source = SourceNode("source1", MockGeneratorStrategy(50.0))
    demand = DemandNode("demand1", MockDemandModel(100.0))
    
    # Create link with limited capacity
    link = Link("link1", source, demand, physical_capacity=30.0, cost=1.0)
    source.outflows.append(link)
    demand.inflows.append(link)
    
    # Run node steps
    climate = create_test_climate()
    source.step(climate)
    demand.step(climate)
    
    # Calculate constraints
    constraints = {
        "link1": link.calculate_constraints()
    }
    
    # Solve - should raise error
    solver = LinearProgrammingSolver()
    from hydrosim.exceptions import InfeasibleNetworkError
    with pytest.raises(InfeasibleNetworkError, match="Network flow optimization is infeasible"):
        solver.solve([source, demand], [link], constraints)
