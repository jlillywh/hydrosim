"""
Tests for error handling in the HydroSim framework.

This module tests all error handling scenarios including:
- Negative storage errors
- Infeasible network errors
- Missing climate data errors
- EAV interpolation out of bounds errors
- Warning logging for low storage and approaching table boundaries
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

from hydrosim.nodes import StorageNode, SourceNode, DemandNode
from hydrosim.links import Link
from hydrosim.config import ElevationAreaVolume
from hydrosim.climate import ClimateState
from hydrosim.climate_sources import TimeSeriesClimateSource
from hydrosim.strategies import TimeSeriesStrategy, MunicipalDemand
from hydrosim.solver import LinearProgrammingSolver
from hydrosim.exceptions import (
    NegativeStorageError,
    InfeasibleNetworkError,
    ClimateDataError,
    EAVInterpolationError
)


def create_test_climate():
    """Helper to create a test climate state."""
    return ClimateState(
        date=datetime(2024, 1, 1),
        precip=5.0,
        t_max=25.0,
        t_min=15.0,
        solar=20.0,
        et0=5.0
    )


def create_test_eav(node_id="test", extrapolate=True):
    """Helper to create a test EAV table."""
    return ElevationAreaVolume(
        elevations=[100.0, 110.0, 120.0],
        areas=[1000.0, 2000.0, 3000.0],
        volumes=[10000.0, 30000.0, 60000.0],
        node_id=node_id,
        extrapolate=extrapolate
    )


# ============================================================================
# Negative Storage Error Tests
# ============================================================================

def test_negative_storage_error_raised():
    """Test that NegativeStorageError is raised when storage would go negative."""
    eav = create_test_eav()
    storage = StorageNode("storage1", initial_storage=100.0, eav_table=eav, max_storage=50000.0, min_storage=0.0, allow_negative=False)
    
    climate = create_test_climate()
    storage.step(climate)
    
    # Try to remove more water than available
    with pytest.raises(NegativeStorageError) as exc_info:
        storage.update_storage(inflow=0.0, outflow=200.0)
    
    # Check error message contains relevant information
    assert "storage1" in str(exc_info.value)
    assert "negative storage" in str(exc_info.value).lower()


def test_negative_storage_constrained_to_zero():
    """Test that negative storage is constrained to zero when allow_negative=True."""
    eav = create_test_eav()
    storage = StorageNode("storage1", initial_storage=100.0, eav_table=eav, max_storage=50000.0, min_storage=0.0, allow_negative=True)
    
    climate = create_test_climate()
    storage.step(climate)
    
    # Try to remove more water than available - should constrain to zero
    storage.update_storage(inflow=0.0, outflow=200.0)
    
    assert storage.storage == 0.0


def test_negative_storage_error_details():
    """Test that NegativeStorageError contains detailed information."""
    eav = create_test_eav()
    storage = StorageNode("storage1", initial_storage=100.0, eav_table=eav, max_storage=50000.0, min_storage=0.0, allow_negative=False)
    
    climate = create_test_climate()
    storage.step(climate)
    
    try:
        storage.update_storage(inflow=0.0, outflow=200.0)
        pytest.fail("Expected NegativeStorageError")
    except NegativeStorageError as e:
        assert e.node_id == "storage1"
        assert e.current_storage == 100.0
        assert e.attempted_outflow == 200.0
        assert e.evaporation > 0.0


def test_low_storage_warning(caplog):
    """Test that low storage triggers a warning."""
    eav = create_test_eav()
    # Set initial storage just above low threshold
    storage = StorageNode(
        "storage1", 
        initial_storage=1500.0,  # Just above 10% of min volume (10000)
        eav_table=eav,
        max_storage=50000.0,
        min_storage=0.0,
        low_storage_threshold=0.1
    )
    
    climate = create_test_climate()
    storage.step(climate)
    
    # Reduce storage to trigger warning
    with caplog.at_level(logging.WARNING):
        storage.update_storage(inflow=0.0, outflow=500.0)
    
    # Check that warning was logged
    assert any("low storage" in record.message.lower() for record in caplog.records)


# ============================================================================
# Infeasible Network Error Tests
# ============================================================================

def test_infeasible_network_demand_exceeds_supply():
    """Test that InfeasibleNetworkError is raised when demand exceeds supply."""
    # Create nodes
    data = pd.DataFrame({'inflow': [50.0]})
    source = SourceNode("source1", TimeSeriesStrategy(data, 'inflow'))
    demand = DemandNode("demand1", MunicipalDemand(population=1000, per_capita_demand=0.1))
    
    # Create link with limited capacity
    link = Link("link1", source, demand, physical_capacity=30.0, cost=1.0)
    source.outflows.append(link)
    demand.inflows.append(link)
    
    # Run node steps
    climate = create_test_climate()
    source.step(climate)
    demand.step(climate)
    
    # Calculate constraints
    constraints = {"link1": link.calculate_constraints()}
    
    # Solve - should raise error with diagnostics
    solver = LinearProgrammingSolver()
    with pytest.raises(InfeasibleNetworkError) as exc_info:
        solver.solve([source, demand], [link], constraints)
    
    # Check error contains diagnostic information
    error_msg = str(exc_info.value)
    assert "infeasible" in error_msg.lower()
    assert "demand exceeds supply" in error_msg.lower() or "conflicting" in error_msg.lower()


def test_infeasible_network_error_diagnostics():
    """Test that InfeasibleNetworkError provides detailed diagnostics."""
    # Create nodes with impossible constraints
    data = pd.DataFrame({'inflow': [50.0]})
    source = SourceNode("source1", TimeSeriesStrategy(data, 'inflow'))
    demand = DemandNode("demand1", MunicipalDemand(population=2000, per_capita_demand=0.1))
    
    # Create link with very limited capacity
    link = Link("link1", source, demand, physical_capacity=10.0, cost=1.0)
    source.outflows.append(link)
    demand.inflows.append(link)
    
    # Run node steps
    climate = create_test_climate()
    source.step(climate)
    demand.step(climate)
    
    # Calculate constraints
    constraints = {"link1": link.calculate_constraints()}
    
    # Solve - should raise error
    solver = LinearProgrammingSolver()
    try:
        solver.solve([source, demand], [link], constraints)
        pytest.fail("Expected InfeasibleNetworkError")
    except InfeasibleNetworkError as e:
        # Check that diagnostics are provided
        assert len(e.conflicting_constraints) > 0
        assert any("demand" in str(c).lower() for c in e.conflicting_constraints)


# ============================================================================
# Climate Data Error Tests
# ============================================================================

def test_climate_data_error_missing_date():
    """Test that ClimateDataError is raised for missing dates."""
    dates = pd.date_range('2024-01-01', periods=5, freq='D')
    data = pd.DataFrame({
        'precip': [5.0, 10.0, 0.0, 2.5, 7.5],
        't_max': [25.0, 26.0, 27.0, 24.0, 23.0],
        't_min': [15.0, 16.0, 17.0, 14.0, 13.0],
        'solar': [20.0, 21.0, 22.0, 19.0, 18.0]
    }, index=dates)
    
    source = TimeSeriesClimateSource(data)
    
    # Try to get data for a date outside the range
    with pytest.raises(ClimateDataError) as exc_info:
        source.get_climate_data(datetime(2024, 2, 1))
    
    # Check error message
    error_msg = str(exc_info.value)
    assert "2024-02-01" in error_msg
    assert "timeseries" in error_msg.lower()


def test_climate_data_error_includes_available_range():
    """Test that ClimateDataError includes available date range."""
    dates = pd.date_range('2024-01-01', periods=5, freq='D')
    data = pd.DataFrame({
        'precip': [5.0, 10.0, 0.0, 2.5, 7.5],
        't_max': [25.0, 26.0, 27.0, 24.0, 23.0],
        't_min': [15.0, 16.0, 17.0, 14.0, 13.0],
        'solar': [20.0, 21.0, 22.0, 19.0, 18.0]
    }, index=dates)
    
    source = TimeSeriesClimateSource(data)
    
    try:
        source.get_climate_data(datetime(2024, 2, 1))
        pytest.fail("Expected ClimateDataError")
    except ClimateDataError as e:
        assert e.available_range is not None
        assert e.source_type == "timeseries"
        # Check that error message includes range
        error_msg = str(e)
        assert "2024-01-01" in error_msg
        assert "2024-01-05" in error_msg


def test_climate_data_validate_date_range():
    """Test validation of simulation period against available data."""
    dates = pd.date_range('2024-01-01', periods=10, freq='D')
    data = pd.DataFrame({
        'precip': [5.0] * 10,
        't_max': [25.0] * 10,
        't_min': [15.0] * 10,
        'solar': [20.0] * 10
    }, index=dates)
    
    source = TimeSeriesClimateSource(data)
    
    # Valid range should not raise error
    source.validate_date_range(datetime(2024, 1, 1), datetime(2024, 1, 10))
    
    # Start date before available data should raise error
    with pytest.raises(ClimateDataError):
        source.validate_date_range(datetime(2023, 12, 31), datetime(2024, 1, 5))
    
    # End date after available data should raise error
    with pytest.raises(ClimateDataError):
        source.validate_date_range(datetime(2024, 1, 5), datetime(2024, 1, 15))


# ============================================================================
# EAV Interpolation Error Tests
# ============================================================================

def test_eav_interpolation_error_below_minimum():
    """Test that EAVInterpolationError is raised for storage below table minimum."""
    eav = ElevationAreaVolume(
        elevations=[100.0, 110.0, 120.0],
        areas=[1000.0, 2000.0, 3000.0],
        volumes=[10000.0, 30000.0, 60000.0],
        node_id="storage1",
        extrapolate=False  # Don't allow extrapolation
    )
    
    # Try to interpolate below minimum
    with pytest.raises(EAVInterpolationError) as exc_info:
        eav.storage_to_elevation(5000.0)
    
    # Check error details
    error_msg = str(exc_info.value)
    assert "storage1" in error_msg
    assert "below minimum" in error_msg.lower()
    assert "5000" in error_msg


def test_eav_interpolation_error_above_maximum():
    """Test that EAVInterpolationError is raised for storage above table maximum."""
    eav = ElevationAreaVolume(
        elevations=[100.0, 110.0, 120.0],
        areas=[1000.0, 2000.0, 3000.0],
        volumes=[10000.0, 30000.0, 60000.0],
        node_id="storage1",
        extrapolate=False
    )
    
    # Try to interpolate above maximum
    with pytest.raises(EAVInterpolationError) as exc_info:
        eav.storage_to_area(70000.0)
    
    # Check error details
    error_msg = str(exc_info.value)
    assert "storage1" in error_msg
    assert "above maximum" in error_msg.lower()
    assert "70000" in error_msg


def test_eav_extrapolation_allowed():
    """Test that extrapolation works when enabled."""
    eav = ElevationAreaVolume(
        elevations=[100.0, 110.0, 120.0],
        areas=[1000.0, 2000.0, 3000.0],
        volumes=[10000.0, 30000.0, 60000.0],
        node_id="storage1",
        extrapolate=True  # Allow extrapolation
    )
    
    # Should not raise error when extrapolate=True
    # numpy.interp clamps to boundary values by default
    elevation_below = eav.storage_to_elevation(5000.0)
    elevation_above = eav.storage_to_elevation(70000.0)
    
    # Check that values are at boundaries (numpy.interp behavior)
    assert elevation_below == 100.0  # Clamped to minimum elevation
    assert elevation_above == 120.0  # Clamped to maximum elevation


def test_eav_approaching_bounds_warning(caplog):
    """Test that approaching table boundaries triggers warnings."""
    eav = ElevationAreaVolume(
        elevations=[100.0, 110.0, 120.0],
        areas=[1000.0, 2000.0, 3000.0],
        volumes=[10000.0, 30000.0, 60000.0],
        node_id="storage1",
        extrapolate=True,
        warn_threshold=0.95  # Warn when within 5% of bounds
    )
    
    # Interpolate near lower bound (should trigger warning)
    with caplog.at_level(logging.INFO):
        eav.storage_to_elevation(11000.0)  # Just above minimum
    
    # Check that warning was logged
    assert any("approaching" in record.message.lower() for record in caplog.records)


def test_eav_extrapolation_warning(caplog):
    """Test that extrapolation triggers warnings."""
    eav = ElevationAreaVolume(
        elevations=[100.0, 110.0, 120.0],
        areas=[1000.0, 2000.0, 3000.0],
        volumes=[10000.0, 30000.0, 60000.0],
        node_id="storage1",
        extrapolate=True
    )
    
    # Extrapolate below minimum (should trigger warning)
    with caplog.at_level(logging.WARNING):
        eav.storage_to_elevation(5000.0)
    
    # Check that warning was logged
    assert any("extrapolating" in record.message.lower() for record in caplog.records)


# ============================================================================
# Integration Tests
# ============================================================================

def test_error_handling_integration():
    """Test that errors propagate correctly through the simulation."""
    # This test verifies that errors from components are properly
    # caught and re-raised by the simulation engine
    
    # Create a storage node that will go negative
    eav = create_test_eav()
    storage = StorageNode(
        "storage1", 
        initial_storage=100.0, 
        eav_table=eav,
        max_storage=50000.0,
        min_storage=0.0,
        allow_negative=False
    )
    
    climate = create_test_climate()
    storage.step(climate)
    
    # Verify that the error is raised
    with pytest.raises(NegativeStorageError):
        storage.update_storage(inflow=0.0, outflow=200.0)


def test_multiple_error_types():
    """Test that different error types can be distinguished."""
    # Test that we can catch specific error types
    
    # NegativeStorageError
    eav = create_test_eav()
    storage = StorageNode("storage1", initial_storage=100.0, eav_table=eav, max_storage=50000.0, min_storage=0.0, allow_negative=False)
    climate = create_test_climate()
    storage.step(climate)
    
    with pytest.raises(NegativeStorageError):
        storage.update_storage(inflow=0.0, outflow=200.0)
    
    # ClimateDataError
    dates = pd.date_range('2024-01-01', periods=5, freq='D')
    data = pd.DataFrame({
        'precip': [5.0] * 5,
        't_max': [25.0] * 5,
        't_min': [15.0] * 5,
        'solar': [20.0] * 5
    }, index=dates)
    source = TimeSeriesClimateSource(data)
    
    with pytest.raises(ClimateDataError):
        source.get_climate_data(datetime(2024, 2, 1))
    
    # EAVInterpolationError
    eav_no_extrap = ElevationAreaVolume(
        elevations=[100.0, 110.0, 120.0],
        areas=[1000.0, 2000.0, 3000.0],
        volumes=[10000.0, 30000.0, 60000.0],
        node_id="storage1",
        extrapolate=False
    )
    
    with pytest.raises(EAVInterpolationError):
        eav_no_extrap.storage_to_elevation(5000.0)


# ============================================================================
# Configuration Error Tests (Task 19)
# ============================================================================

def test_storage_node_min_exceeds_max():
    """Test that ConfigurationError is raised when min_storage > max_storage."""
    from hydrosim.exceptions import ConfigurationError
    
    eav = create_test_eav()
    
    with pytest.raises(ConfigurationError) as exc_info:
        StorageNode(
            "storage1",
            initial_storage=5000.0,
            eav_table=eav,
            max_storage=10000.0,
            min_storage=15000.0  # Invalid: min > max
        )
    
    error_msg = str(exc_info.value)
    assert "min_storage" in error_msg
    assert "max_storage" in error_msg
    assert "15000" in error_msg
    assert "10000" in error_msg


def test_storage_node_initial_below_min():
    """Test that ConfigurationError is raised when initial_storage < min_storage."""
    from hydrosim.exceptions import ConfigurationError
    
    eav = create_test_eav()
    
    with pytest.raises(ConfigurationError) as exc_info:
        StorageNode(
            "storage1",
            initial_storage=5000.0,  # Invalid: below min
            eav_table=eav,
            max_storage=50000.0,
            min_storage=10000.0
        )
    
    error_msg = str(exc_info.value)
    assert "initial_storage" in error_msg
    assert "min_storage" in error_msg
    assert "5000" in error_msg
    assert "10000" in error_msg


def test_storage_node_initial_above_max():
    """Test that ConfigurationError is raised when initial_storage > max_storage."""
    from hydrosim.exceptions import ConfigurationError
    
    eav = create_test_eav()
    
    with pytest.raises(ConfigurationError) as exc_info:
        StorageNode(
            "storage1",
            initial_storage=60000.0,  # Invalid: above max
            eav_table=eav,
            max_storage=50000.0,
            min_storage=0.0
        )
    
    error_msg = str(exc_info.value)
    assert "initial_storage" in error_msg
    assert "max_storage" in error_msg
    assert "60000" in error_msg
    assert "50000" in error_msg


def test_storage_node_valid_configuration():
    """Test that valid storage configuration does not raise errors."""
    eav = create_test_eav()
    
    # Should not raise any errors
    storage = StorageNode(
        "storage1",
        initial_storage=25000.0,
        eav_table=eav,
        max_storage=50000.0,
        min_storage=10000.0
    )
    
    assert storage.storage == 25000.0
    assert storage.max_storage == 50000.0
    assert storage.min_storage == 10000.0


def test_cost_hierarchy_validation():
    """Test that cost hierarchy is validated on solver initialization."""
    from hydrosim.solver import LinearProgrammingSolver
    
    # Valid hierarchy should not raise error
    solver = LinearProgrammingSolver()
    assert solver is not None


def test_cost_hierarchy_constants():
    """Test that cost constants maintain correct hierarchy."""
    from hydrosim.solver import COST_DEMAND, COST_STORAGE, COST_SPILL
    
    # Verify the hierarchy
    assert COST_DEMAND < COST_STORAGE, "COST_DEMAND must be less than COST_STORAGE"
    assert COST_STORAGE < COST_SPILL, "COST_STORAGE must be less than COST_SPILL"
    assert COST_DEMAND < COST_SPILL, "COST_DEMAND must be less than COST_SPILL"
    
    # Verify specific values match design
    assert COST_DEMAND == -1000.0
    assert COST_STORAGE == -1.0
    assert COST_SPILL == 0.0
