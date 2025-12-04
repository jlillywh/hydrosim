"""
Tests for Link class and constraint funnel logic.

Validates Requirements: 7.1, 7.4, 7.5, 11.1, 11.3, 11.4
"""

import pytest
from hydrosim.links import Link
from hydrosim.nodes import Node, StorageNode, JunctionNode
from hydrosim.controls import Control
from hydrosim.hydraulics import HydraulicModel
from hydrosim.config import ElevationAreaVolume
from hydrosim.climate import ClimateState
from datetime import datetime


class MockControl(Control):
    """Mock control for testing."""
    
    def __init__(self, limit_factor: float):
        self.limit_factor = limit_factor
    
    def calculate_limit(self, base_capacity: float, source: Node, target: Node) -> float:
        return base_capacity * self.limit_factor


class MockHydraulicModel(HydraulicModel):
    """Mock hydraulic model for testing."""
    
    def __init__(self, capacity: float):
        self.capacity = capacity
    
    def calculate_capacity(self, source_node: Node) -> float:
        return self.capacity


def test_link_initialization():
    """Test that Link can be initialized with required parameters."""
    node1 = JunctionNode("node1")
    node2 = JunctionNode("node2")
    
    link = Link("link1", node1, node2, physical_capacity=100.0, cost=1.5)
    
    assert link.link_id == "link1"
    assert link.source == node1
    assert link.target == node2
    assert link.physical_capacity == 100.0
    assert link.cost == 1.5
    assert link.control is None
    assert link.hydraulic_model is None
    assert link.flow == 0.0


def test_link_physical_capacity_constraint():
    """
    Test that physical capacity constraint is applied.
    Validates Requirement 7.1: Physical limits based on static capacity values.
    """
    node1 = JunctionNode("node1")
    node2 = JunctionNode("node2")
    
    link = Link("link1", node1, node2, physical_capacity=100.0, cost=1.0)
    
    q_min, q_max, cost = link.calculate_constraints()
    
    assert q_min == 0.0
    assert q_max == 100.0
    assert cost == 1.0


def test_link_constraint_output_completeness():
    """
    Test that constraint calculation returns all required parameters.
    Validates Requirement 7.5: Include q_min, q_max, and cost parameters.
    """
    node1 = JunctionNode("node1")
    node2 = JunctionNode("node2")
    
    link = Link("link1", node1, node2, physical_capacity=100.0, cost=2.5)
    
    result = link.calculate_constraints()
    
    # Should return a tuple with exactly 3 elements
    assert isinstance(result, tuple)
    assert len(result) == 3
    
    q_min, q_max, cost = result
    assert isinstance(q_min, (int, float))
    assert isinstance(q_max, (int, float))
    assert isinstance(cost, (int, float))


def test_link_hydraulic_constraint_funnel():
    """
    Test that hydraulic constraints are applied through the constraint funnel.
    Validates Requirement 7.2: Apply hydraulic limits based on current system state.
    """
    node1 = JunctionNode("node1")
    node2 = JunctionNode("node2")
    
    link = Link("link1", node1, node2, physical_capacity=100.0, cost=1.0)
    
    # Add hydraulic model that limits flow to 60
    link.hydraulic_model = MockHydraulicModel(60.0)
    
    q_min, q_max, cost = link.calculate_constraints()
    
    # Hydraulic limit should reduce the max flow
    assert q_max == 60.0


def test_link_control_constraint_funnel():
    """
    Test that control constraints are applied through the constraint funnel.
    Validates Requirement 7.3: Apply control limits based on logic rules.
    """
    node1 = JunctionNode("node1")
    node2 = JunctionNode("node2")
    
    link = Link("link1", node1, node2, physical_capacity=100.0, cost=1.0)
    
    # Add control that throttles to 50% capacity
    link.control = MockControl(0.5)
    
    q_min, q_max, cost = link.calculate_constraints()
    
    # Control should reduce the max flow
    assert q_max == 50.0


def test_link_constraint_funnel_minimum():
    """
    Test that the constraint funnel applies constraints sequentially.
    Validates Requirement 7.4: Final limit is minimum of physical, hydraulic, and control.
    
    The constraint funnel applies constraints in sequence:
    1. Start with physical capacity (100)
    2. Apply hydraulic constraint: min(100, 80) = 80
    3. Apply control constraint: min(80, 0.5 * 80) = min(80, 40) = 40
    """
    node1 = JunctionNode("node1")
    node2 = JunctionNode("node2")
    
    link = Link("link1", node1, node2, physical_capacity=100.0, cost=1.0)
    
    # Add hydraulic model (limits to 80)
    link.hydraulic_model = MockHydraulicModel(80.0)
    
    # Add control (limits to 50% of current capacity)
    link.control = MockControl(0.5)
    
    q_min, q_max, cost = link.calculate_constraints()
    
    # Sequential application: min(100, 80) = 80, then min(80, 0.5*80) = 40
    assert q_max == 40.0


def test_link_constraint_funnel_sequential_application():
    """
    Test that constraint funnel applies constraints sequentially.
    
    The funnel applies: physical -> hydraulic -> control
    Each layer receives the output of the previous layer.
    """
    node1 = JunctionNode("node1")
    node2 = JunctionNode("node2")
    
    # Case 1: Physical is most limiting initially, then control reduces further
    link1 = Link("link1", node1, node2, physical_capacity=30.0, cost=1.0)
    link1.hydraulic_model = MockHydraulicModel(80.0)
    link1.control = MockControl(0.9)  # 90% of min(30, 80) = 90% of 30 = 27
    
    q_min1, q_max1, cost1 = link1.calculate_constraints()
    assert q_max1 == 27.0  # min(30, 80) = 30, then 30 * 0.9 = 27
    
    # Case 2: Hydraulic is most limiting, then control reduces further
    link2 = Link("link2", node1, node2, physical_capacity=100.0, cost=1.0)
    link2.hydraulic_model = MockHydraulicModel(25.0)
    link2.control = MockControl(0.9)  # 90% of min(100, 25) = 90% of 25 = 22.5
    
    q_min2, q_max2, cost2 = link2.calculate_constraints()
    assert q_max2 == 22.5  # min(100, 25) = 25, then 25 * 0.9 = 22.5
    
    # Case 3: Control significantly reduces the capacity
    link3 = Link("link3", node1, node2, physical_capacity=100.0, cost=1.0)
    link3.hydraulic_model = MockHydraulicModel(80.0)
    link3.control = MockControl(0.2)  # 20% of min(100, 80) = 20% of 80 = 16
    
    q_min3, q_max3, cost3 = link3.calculate_constraints()
    assert q_max3 == 16.0  # min(100, 80) = 80, then 80 * 0.2 = 16


def test_link_explicit_connection():
    """
    Test that Link explicitly connects source and target nodes.
    Validates Requirement 11.1: Water moves via explicit Link objects.
    """
    node1 = JunctionNode("node1")
    node2 = JunctionNode("node2")
    
    link = Link("link1", node1, node2, physical_capacity=100.0, cost=1.0)
    
    # Link should have explicit references to both nodes
    assert link.source is node1
    assert link.target is node2
    assert link.source is not None
    assert link.target is not None


def test_link_cost_preserved():
    """Test that link cost is preserved through constraint calculation."""
    node1 = JunctionNode("node1")
    node2 = JunctionNode("node2")
    
    link = Link("link1", node1, node2, physical_capacity=100.0, cost=3.7)
    
    q_min, q_max, cost = link.calculate_constraints()
    
    assert cost == 3.7


def test_link_minimum_flow_is_zero():
    """Test that minimum flow is always zero (no negative flows)."""
    node1 = JunctionNode("node1")
    node2 = JunctionNode("node2")
    
    link = Link("link1", node1, node2, physical_capacity=100.0, cost=1.0)
    
    q_min, q_max, cost = link.calculate_constraints()
    
    assert q_min == 0.0


def test_link_with_no_constraints():
    """Test link behavior when no hydraulic or control constraints are present."""
    node1 = JunctionNode("node1")
    node2 = JunctionNode("node2")
    
    link = Link("link1", node1, node2, physical_capacity=150.0, cost=0.5)
    
    q_min, q_max, cost = link.calculate_constraints()
    
    # Should only have physical capacity constraint
    assert q_min == 0.0
    assert q_max == 150.0
    assert cost == 0.5


def test_link_flow_tracking():
    """Test that link can track allocated flow."""
    node1 = JunctionNode("node1")
    node2 = JunctionNode("node2")
    
    link = Link("link1", node1, node2, physical_capacity=100.0, cost=1.0)
    
    # Initially zero
    assert link.flow == 0.0
    
    # Can be updated
    link.flow = 45.5
    assert link.flow == 45.5


def test_weir_model_with_storage_node():
    """
    Test WeirModel calculates capacity using weir equation Q = C * L * H^1.5.
    Validates Requirements 13.1, 13.2, 13.3.
    """
    from hydrosim.hydraulics import WeirModel
    
    # Create a storage node with EAV table
    elevations = [100.0, 110.0, 120.0]
    areas = [1000.0, 1500.0, 2000.0]
    volumes = [0.0, 10000.0, 25000.0]
    eav = ElevationAreaVolume(elevations, areas, volumes)
    
    storage_node = StorageNode("storage1", initial_storage=15000.0, eav_table=eav, max_storage=50000.0, min_storage=0.0)
    junction_node = JunctionNode("junction1")
    
    # Create weir model with crest at elevation 105
    weir = WeirModel(coefficient=1.5, length=10.0, crest_elevation=105.0)
    
    # Storage at 15000 should give elevation around 113.33
    # Head = 113.33 - 105 = 8.33
    # Q = 1.5 * 10.0 * 8.33^1.5 = 15 * 24.04 ≈ 360.6
    elevation = storage_node.get_elevation()
    head = elevation - 105.0
    expected_capacity = 1.5 * 10.0 * (head ** 1.5)
    
    capacity = weir.calculate_capacity(storage_node)
    
    assert abs(capacity - expected_capacity) < 0.1


def test_weir_model_with_zero_head():
    """
    Test WeirModel returns zero capacity when head is zero or negative.
    Validates Requirement 13.5: Set max flow to zero when head is insufficient.
    """
    from hydrosim.hydraulics import WeirModel
    
    # Create a storage node with low storage
    elevations = [100.0, 110.0, 120.0]
    areas = [1000.0, 1500.0, 2000.0]
    volumes = [0.0, 10000.0, 25000.0]
    eav = ElevationAreaVolume(elevations, areas, volumes)
    
    storage_node = StorageNode("storage1", initial_storage=0.0, eav_table=eav, max_storage=50000.0, min_storage=0.0)
    
    # Create weir model with crest at elevation 105 (above current water level)
    weir = WeirModel(coefficient=1.5, length=10.0, crest_elevation=105.0)
    
    capacity = weir.calculate_capacity(storage_node)
    
    # Head is negative, so capacity should be zero
    assert capacity == 0.0


def test_weir_model_with_non_storage_node():
    """
    Test WeirModel returns infinity for non-storage nodes.
    Validates that weir equations only apply to storage nodes.
    """
    from hydrosim.hydraulics import WeirModel
    
    junction_node = JunctionNode("junction1")
    
    weir = WeirModel(coefficient=1.5, length=10.0, crest_elevation=105.0)
    
    capacity = weir.calculate_capacity(junction_node)
    
    # Non-storage nodes should return infinity (no hydraulic limit)
    assert capacity == float('inf')


def test_pipe_model_fixed_capacity():
    """
    Test PipeModel returns fixed capacity regardless of node state.
    Validates Requirements 13.2, 13.3.
    """
    from hydrosim.hydraulics import PipeModel
    
    # Create various node types
    junction_node = JunctionNode("junction1")
    
    elevations = [100.0, 110.0, 120.0]
    areas = [1000.0, 1500.0, 2000.0]
    volumes = [0.0, 10000.0, 25000.0]
    eav = ElevationAreaVolume(elevations, areas, volumes)
    storage_node = StorageNode("storage1", initial_storage=15000.0, eav_table=eav, max_storage=50000.0, min_storage=0.0)
    
    # Create pipe model with fixed capacity
    pipe = PipeModel(capacity=50.0)
    
    # Should return same capacity for any node
    assert pipe.calculate_capacity(junction_node) == 50.0
    assert pipe.calculate_capacity(storage_node) == 50.0


def test_link_with_weir_model():
    """
    Test Link integration with WeirModel.
    Validates Requirement 7.2, 13.4: Hydraulic limits recalculated based on state.
    """
    from hydrosim.hydraulics import WeirModel
    
    # Create storage node
    elevations = [100.0, 110.0, 120.0]
    areas = [1000.0, 1500.0, 2000.0]
    volumes = [0.0, 10000.0, 25000.0]
    eav = ElevationAreaVolume(elevations, areas, volumes)
    
    storage_node = StorageNode("storage1", initial_storage=15000.0, eav_table=eav, max_storage=50000.0, min_storage=0.0)
    junction_node = JunctionNode("junction1")
    
    # Create link with weir model
    link = Link("link1", storage_node, junction_node, physical_capacity=1000.0, cost=1.0)
    weir = WeirModel(coefficient=1.5, length=10.0, crest_elevation=105.0)
    link.hydraulic_model = weir
    
    # Calculate constraints
    q_min, q_max, cost = link.calculate_constraints()
    
    # Max flow should be limited by weir equation, not physical capacity
    elevation = storage_node.get_elevation()
    head = max(0.0, elevation - 105.0)
    expected_weir_capacity = 1.5 * 10.0 * (head ** 1.5)
    
    assert q_max == min(1000.0, expected_weir_capacity)
    assert q_max < 1000.0  # Weir should be limiting


def test_link_with_pipe_model():
    """
    Test Link integration with PipeModel.
    Validates Requirement 7.2: Hydraulic limits applied to link constraints.
    """
    from hydrosim.hydraulics import PipeModel
    
    node1 = JunctionNode("node1")
    node2 = JunctionNode("node2")
    
    # Create link with pipe model
    link = Link("link1", node1, node2, physical_capacity=1000.0, cost=1.0)
    pipe = PipeModel(capacity=75.0)
    link.hydraulic_model = pipe
    
    # Calculate constraints
    q_min, q_max, cost = link.calculate_constraints()
    
    # Max flow should be limited by pipe capacity
    assert q_max == 75.0


def test_hydraulic_model_recalculation():
    """
    Test that hydraulic limits are recalculated when node state changes.
    Validates Requirement 13.4: Recalculate flow limits before each solver execution.
    """
    from hydrosim.hydraulics import WeirModel
    
    # Create storage node
    elevations = [100.0, 110.0, 120.0]
    areas = [1000.0, 1500.0, 2000.0]
    volumes = [0.0, 10000.0, 25000.0]
    eav = ElevationAreaVolume(elevations, areas, volumes)
    
    storage_node = StorageNode("storage1", initial_storage=20000.0, eav_table=eav, max_storage=50000.0, min_storage=0.0)
    junction_node = JunctionNode("junction1")
    
    # Create link with weir model
    link = Link("link1", storage_node, junction_node, physical_capacity=1000.0, cost=1.0)
    weir = WeirModel(coefficient=1.5, length=10.0, crest_elevation=105.0)
    link.hydraulic_model = weir
    
    # Calculate constraints at high storage
    q_min1, q_max1, cost1 = link.calculate_constraints()
    
    # Reduce storage
    storage_node.storage = 5000.0
    
    # Recalculate constraints at low storage
    q_min2, q_max2, cost2 = link.calculate_constraints()
    
    # Capacity should be lower with reduced storage (lower head)
    assert q_max2 < q_max1
