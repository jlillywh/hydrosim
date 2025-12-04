"""
Tests for Control system implementations.

Validates Requirements: 7.3, 8.1, 8.2, 8.3, 8.4, 8.5
"""

import pytest
from hydrosim.controls import Control, FractionalControl, AbsoluteControl, SwitchControl
from hydrosim.nodes import JunctionNode


def test_fractional_control_initialization():
    """
    Test FractionalControl initialization with valid fraction.
    Validates Requirement 8.1: Throttle capacity using value between 0.0 and 1.0.
    """
    control = FractionalControl(0.5)
    assert control.fraction == 0.5


def test_fractional_control_invalid_fraction_too_high():
    """
    Test that FractionalControl rejects fractions > 1.0.
    Validates configuration validation for control parameters.
    """
    with pytest.raises(ValueError, match="Fraction must be between 0.0 and 1.0"):
        FractionalControl(1.5)


def test_fractional_control_invalid_fraction_negative():
    """
    Test that FractionalControl rejects negative fractions.
    Validates configuration validation for control parameters.
    """
    with pytest.raises(ValueError, match="Fraction must be between 0.0 and 1.0"):
        FractionalControl(-0.1)


def test_fractional_control_boundary_values():
    """Test FractionalControl accepts boundary values 0.0 and 1.0."""
    control_zero = FractionalControl(0.0)
    assert control_zero.fraction == 0.0
    
    control_one = FractionalControl(1.0)
    assert control_one.fraction == 1.0


def test_fractional_control_calculate_limit():
    """
    Test FractionalControl throttles capacity correctly.
    Validates Requirement 8.1: Throttle capacity using fraction.
    """
    node1 = JunctionNode("node1")
    node2 = JunctionNode("node2")
    
    control = FractionalControl(0.75)
    
    # Test with various base capacities
    assert control.calculate_limit(100.0, node1, node2) == 75.0
    assert control.calculate_limit(200.0, node1, node2) == 150.0
    assert control.calculate_limit(50.0, node1, node2) == 37.5


def test_fractional_control_zero_fraction():
    """Test FractionalControl with 0.0 fraction blocks all flow."""
    node1 = JunctionNode("node1")
    node2 = JunctionNode("node2")
    
    control = FractionalControl(0.0)
    
    assert control.calculate_limit(100.0, node1, node2) == 0.0


def test_fractional_control_full_fraction():
    """Test FractionalControl with 1.0 fraction allows full capacity."""
    node1 = JunctionNode("node1")
    node2 = JunctionNode("node2")
    
    control = FractionalControl(1.0)
    
    assert control.calculate_limit(100.0, node1, node2) == 100.0


def test_absolute_control_initialization():
    """
    Test AbsoluteControl initialization with valid max_flow.
    Validates Requirement 8.2: Set hard flow cap in absolute units.
    """
    control = AbsoluteControl(50.0)
    assert control.max_flow == 50.0


def test_absolute_control_invalid_negative():
    """
    Test that AbsoluteControl rejects negative max_flow.
    Validates configuration validation for control parameters.
    """
    with pytest.raises(ValueError, match="Max flow must be non-negative"):
        AbsoluteControl(-10.0)


def test_absolute_control_zero_allowed():
    """Test that AbsoluteControl accepts zero max_flow."""
    control = AbsoluteControl(0.0)
    assert control.max_flow == 0.0


def test_absolute_control_calculate_limit_below_capacity():
    """
    Test AbsoluteControl caps flow when below base capacity.
    Validates Requirement 8.2: Set hard flow cap.
    """
    node1 = JunctionNode("node1")
    node2 = JunctionNode("node2")
    
    control = AbsoluteControl(60.0)
    
    # When base capacity is higher, absolute control limits it
    assert control.calculate_limit(100.0, node1, node2) == 60.0


def test_absolute_control_calculate_limit_above_capacity():
    """
    Test AbsoluteControl doesn't increase flow when above base capacity.
    Validates Requirement 8.2: Absolute control respects base capacity.
    """
    node1 = JunctionNode("node1")
    node2 = JunctionNode("node2")
    
    control = AbsoluteControl(150.0)
    
    # When base capacity is lower, it remains the limit
    assert control.calculate_limit(100.0, node1, node2) == 100.0


def test_absolute_control_various_capacities():
    """Test AbsoluteControl with various base capacities."""
    node1 = JunctionNode("node1")
    node2 = JunctionNode("node2")
    
    control = AbsoluteControl(75.0)
    
    # Test multiple scenarios
    assert control.calculate_limit(50.0, node1, node2) == 50.0   # Base is limiting
    assert control.calculate_limit(75.0, node1, node2) == 75.0   # Equal
    assert control.calculate_limit(100.0, node1, node2) == 75.0  # Control is limiting
    assert control.calculate_limit(200.0, node1, node2) == 75.0  # Control is limiting


def test_switch_control_initialization_on():
    """
    Test SwitchControl initialization in on state.
    Validates Requirement 8.3: Binary on/off logic.
    """
    control = SwitchControl(True)
    assert control.is_on is True


def test_switch_control_initialization_off():
    """
    Test SwitchControl initialization in off state.
    Validates Requirement 8.3: Binary on/off logic.
    """
    control = SwitchControl(False)
    assert control.is_on is False


def test_switch_control_on_allows_full_capacity():
    """
    Test SwitchControl allows full capacity when on.
    Validates Requirement 8.3: Enable flow when on.
    """
    node1 = JunctionNode("node1")
    node2 = JunctionNode("node2")
    
    control = SwitchControl(True)
    
    # When on, should return full base capacity
    assert control.calculate_limit(100.0, node1, node2) == 100.0
    assert control.calculate_limit(50.0, node1, node2) == 50.0
    assert control.calculate_limit(200.0, node1, node2) == 200.0


def test_switch_control_off_blocks_flow():
    """
    Test SwitchControl blocks all flow when off.
    Validates Requirement 8.3: Disable flow when off.
    """
    node1 = JunctionNode("node1")
    node2 = JunctionNode("node2")
    
    control = SwitchControl(False)
    
    # When off, should return 0.0 regardless of base capacity
    assert control.calculate_limit(100.0, node1, node2) == 0.0
    assert control.calculate_limit(50.0, node1, node2) == 0.0
    assert control.calculate_limit(200.0, node1, node2) == 0.0


def test_switch_control_toggle():
    """Test that SwitchControl state can be toggled."""
    node1 = JunctionNode("node1")
    node2 = JunctionNode("node2")
    
    control = SwitchControl(True)
    assert control.calculate_limit(100.0, node1, node2) == 100.0
    
    # Toggle to off
    control.is_on = False
    assert control.calculate_limit(100.0, node1, node2) == 0.0
    
    # Toggle back to on
    control.is_on = True
    assert control.calculate_limit(100.0, node1, node2) == 100.0


def test_all_controls_inherit_from_control():
    """Test that all control implementations inherit from Control base class."""
    assert issubclass(FractionalControl, Control)
    assert issubclass(AbsoluteControl, Control)
    assert issubclass(SwitchControl, Control)


def test_control_integration_with_link():
    """
    Test that controls integrate correctly with Link constraint calculation.
    Validates Requirements 7.3, 8.1, 8.2, 8.3.
    """
    from hydrosim.links import Link
    
    node1 = JunctionNode("node1")
    node2 = JunctionNode("node2")
    
    # Test FractionalControl integration
    link1 = Link("link1", node1, node2, physical_capacity=100.0, cost=1.0)
    link1.control = FractionalControl(0.6)
    q_min1, q_max1, cost1 = link1.calculate_constraints()
    assert q_max1 == 60.0
    
    # Test AbsoluteControl integration
    link2 = Link("link2", node1, node2, physical_capacity=100.0, cost=1.0)
    link2.control = AbsoluteControl(45.0)
    q_min2, q_max2, cost2 = link2.calculate_constraints()
    assert q_max2 == 45.0
    
    # Test SwitchControl integration (on)
    link3 = Link("link3", node1, node2, physical_capacity=100.0, cost=1.0)
    link3.control = SwitchControl(True)
    q_min3, q_max3, cost3 = link3.calculate_constraints()
    assert q_max3 == 100.0
    
    # Test SwitchControl integration (off)
    link4 = Link("link4", node1, node2, physical_capacity=100.0, cost=1.0)
    link4.control = SwitchControl(False)
    q_min4, q_max4, cost4 = link4.calculate_constraints()
    assert q_max4 == 0.0
