"""
Integration tests for generator strategies with SourceNode.

This module tests the complete integration of generator strategies
with SourceNode to verify Requirements 5.1-5.5.
"""

import pandas as pd
from datetime import datetime
from hydrosim.climate import ClimateState
from hydrosim.nodes import SourceNode
from hydrosim.strategies import TimeSeriesStrategy, HydrologyStrategy


def create_test_climate(precip: float = 10.0, t_max: float = 25.0, 
                       t_min: float = 15.0, et0: float = 5.0) -> ClimateState:
    """Create a test climate state."""
    return ClimateState(
        date=datetime(2024, 1, 1),
        precip=precip,
        t_max=t_max,
        t_min=t_min,
        solar=20.0,
        et0=et0
    )


def test_source_node_with_timeseries_strategy():
    """
    Test SourceNode with TimeSeriesStrategy.
    Validates Requirement 5.1: TimeSeriesStrategy reads inflow values.
    """
    # Create time series data
    data = pd.DataFrame({'inflow': [100.0, 150.0, 200.0]})
    strategy = TimeSeriesStrategy(data, 'inflow')
    
    # Create source node
    node = SourceNode("source1", generator=strategy)
    climate = create_test_climate()
    
    # Step through multiple timesteps
    node.step(climate)
    assert node.inflow == 100.0
    
    node.step(climate)
    assert node.inflow == 150.0
    
    node.step(climate)
    assert node.inflow == 200.0


def test_source_node_with_hydrology_strategy():
    """
    Test SourceNode with HydrologyStrategy.
    Validates Requirement 5.2: HydrologyStrategy simulates runoff using Snow17 and AWBM.
    """
    # Create hydrology strategy
    snow17_params = {'melt_factor': 2.5, 'rain_temp': 2.0, 'snow_temp': 0.0}
    awbm_params = {'c1': 10.0, 'c2': 20.0, 'c3': 30.0}
    area = 1000000.0  # 1 km²
    
    strategy = HydrologyStrategy(snow17_params, awbm_params, area)
    
    # Create source node
    node = SourceNode("source1", generator=strategy)
    
    # Test with warm weather (rain)
    climate = create_test_climate(precip=50.0, t_max=20.0, t_min=10.0, et0=5.0)
    node.step(climate)
    
    # Should generate some inflow
    assert node.inflow > 0.0


def test_hydrology_strategy_uses_climate_drivers():
    """
    Test HydrologyStrategy uses climate drivers.
    Validates Requirement 5.3: HydrologyStrategy uses climate drivers to calculate runoff.
    """
    snow17_params = {'melt_factor': 2.5, 'rain_temp': 2.0, 'snow_temp': 0.0}
    awbm_params = {'c1': 10.0, 'c2': 20.0, 'c3': 30.0}
    area = 1000000.0
    
    strategy = HydrologyStrategy(snow17_params, awbm_params, area)
    node = SourceNode("source1", generator=strategy)
    
    # Cold weather - snow accumulation
    cold_climate = create_test_climate(precip=20.0, t_max=-5.0, t_min=-10.0, et0=0.0)
    node.step(cold_climate)
    inflow_cold = node.inflow
    
    # Warm weather - rain and melt
    warm_climate = create_test_climate(precip=20.0, t_max=20.0, t_min=10.0, et0=5.0)
    node.step(warm_climate)
    inflow_warm = node.inflow
    
    # Different climate conditions should produce different inflows
    # (warm should produce more runoff due to rain + snowmelt)
    assert inflow_warm > inflow_cold


def test_strategy_switching():
    """
    Test switching between different generator strategies.
    Validates Requirement 5.4: Strategy switching without modifying other node properties.
    """
    # Create two different strategies
    data = pd.DataFrame({'inflow': [100.0, 200.0]})
    ts_strategy = TimeSeriesStrategy(data, 'inflow')
    
    snow17_params = {'melt_factor': 2.5, 'rain_temp': 2.0, 'snow_temp': 0.0}
    awbm_params = {'c1': 10.0, 'c2': 20.0, 'c3': 30.0}
    hydro_strategy = HydrologyStrategy(snow17_params, awbm_params, 1000000.0)
    
    # Create node with first strategy
    node = SourceNode("source1", generator=ts_strategy)
    original_id = node.node_id
    original_type = node.node_type
    
    climate = create_test_climate()
    
    # Use first strategy
    node.step(climate)
    inflow1 = node.inflow
    assert inflow1 == 100.0
    
    # Switch to second strategy
    node.generator = hydro_strategy
    
    # Verify node properties unchanged
    assert node.node_id == original_id
    assert node.node_type == original_type
    
    # Use second strategy
    node.step(climate)
    inflow2 = node.inflow
    
    # Should produce different result
    assert inflow2 != inflow1


def test_inflow_available_for_solver():
    """
    Test that generated inflow is available for solver.
    Validates Requirement 5.5: Generated inflow is available for solver allocation.
    """
    data = pd.DataFrame({'inflow': [250.0]})
    strategy = TimeSeriesStrategy(data, 'inflow')
    node = SourceNode("source1", generator=strategy)
    
    climate = create_test_climate()
    
    # Before step, inflow should be 0
    assert node.inflow == 0.0
    
    # After step, inflow should be available
    node.step(climate)
    assert node.inflow == 250.0
    
    # Inflow is accessible via get_state() for solver
    state = node.get_state()
    assert state['inflow'] == 250.0
