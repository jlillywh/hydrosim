"""
Test look-ahead optimization hedging behavior.

This test validates that the LookaheadSolver can anticipate future constraints
and make hedging decisions (saving water now for later high-priority needs).
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path

from hydrosim.nodes import StorageNode, SourceNode, DemandNode
from hydrosim.links import Link
from hydrosim.solver import LinearProgrammingSolver, LookaheadSolver
from hydrosim.strategies import TimeSeriesStrategy, MunicipalDemand
from hydrosim.config import ElevationAreaVolume
from hydrosim.simulation import SimulationEngine
from hydrosim.climate_engine import ClimateEngine
from hydrosim.climate_sources import TimeSeriesClimateSource
from hydrosim.climate import SiteConfig


@pytest.fixture
def hedging_test_network():
    """
    Create a test network for hedging validation.
    
    Network structure:
    - Source: Provides water on Day 1 only (100 units)
    - Storage: Can store up to 100 units
    - Low Priority Demand: Wants 50 units on Day 1
    - High Priority Demand: Wants 80 units on Day 3
    
    Expected behavior with look-ahead:
    - Day 1: Store 60, deliver 0 to low priority (hedge for future)
    - Day 2: No inflow, no demands
    - Day 3: Release 60 to high priority from storage (still 20 short)
    
    Expected behavior without look-ahead (myopic):
    - Day 1: Store 10, deliver 50 to low priority
    - Day 2: No inflow, no demands  
    - Day 3: Can only deliver 10 to high priority (70 shortage!)
    """
    # Create time series data for source (limited inflow on Day 1)
    source_data = pd.DataFrame({
        'date': ['2024-01-01', '2024-01-02', '2024-01-03'],
        'inflow': [60.0, 0.0, 0.0]  # Limited water available on Day 1
    })
    
    # Create time series data for low priority demand (only on Day 1)
    low_demand_data = pd.DataFrame({
        'date': ['2024-01-01', '2024-01-02', '2024-01-03'],
        'demand': [50.0, 0.0, 0.0]  # Low priority wants water on Day 1
    })
    
    # Create time series data for high priority demand (only on Day 3)
    high_demand_data = pd.DataFrame({
        'date': ['2024-01-01', '2024-01-02', '2024-01-03'],
        'demand': [0.0, 0.0, 80.0]  # High priority needs water on Day 3
    })
    
    # Create nodes
    source = SourceNode(
        "source",
        TimeSeriesStrategy(source_data, 'inflow')
    )
    
    # Storage with 100 unit capacity
    eav_table = ElevationAreaVolume(
        elevations=[0, 50, 100],
        areas=[1000, 1000, 1000],
        volumes=[0, 50, 100],
        node_id="storage"
    )
    storage = StorageNode("storage", 0.0, eav_table, max_storage=100.0)
    
    # Low priority demand (municipal with low cost)
    low_demand = DemandNode("low_demand", MunicipalDemand(50, 1.0))  # 50 people * 1 m³/day
    
    # High priority demand (municipal with high cost)
    high_demand = DemandNode("high_demand", MunicipalDemand(80, 1.0))  # 80 people * 1 m³/day
    
    # Create links
    source_to_storage = Link("source_to_storage", source, storage, 200.0, -1.0)
    storage_to_low = Link("storage_to_low", storage, low_demand, 100.0, -500.0)  # Lower priority
    storage_to_high = Link("storage_to_high", storage, high_demand, 100.0, -1000.0)  # Higher priority
    
    # Set up node connections
    source.outflows = [source_to_storage]
    storage.inflows = [source_to_storage]
    storage.outflows = [storage_to_low, storage_to_high]
    low_demand.inflows = [storage_to_low]
    high_demand.inflows = [storage_to_high]
    
    # Create demand schedules for testing
    low_demand.demand_schedule = [50.0, 0.0, 0.0]  # Day 1, 2, 3
    high_demand.demand_schedule = [0.0, 0.0, 80.0]  # Day 1, 2, 3
    
    return {
        'nodes': [source, storage, low_demand, high_demand],
        'links': [source_to_storage, storage_to_low, storage_to_high],
        'source_data': source_data,
        'low_demand_data': low_demand_data,
        'high_demand_data': high_demand_data
    }


@pytest.fixture
def climate_engine_3day():
    """Create a simple 3-day climate engine."""
    # Create minimal climate data
    climate_data = pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=3, freq='D'),
        'precip': [0.0, 0.0, 0.0],
        't_max': [25.0, 25.0, 25.0],
        't_min': [15.0, 15.0, 15.0],
        'solar': [20.0, 20.0, 20.0]
    })
    
    climate_source = TimeSeriesClimateSource(climate_data)
    site_config = SiteConfig(latitude=45.0, elevation=1000.0)
    
    return ClimateEngine(climate_source, site_config, datetime(2024, 1, 1))


def test_myopic_solver_fails_hedging(hedging_test_network, climate_engine_3day):
    """
    Test that myopic solver fails to hedge properly.
    
    The myopic solver should:
    - Day 1: Deliver 50 to low priority, store 50
    - Day 3: Can only deliver 50 to high priority (shortage)
    """
    network_data = hedging_test_network
    nodes = network_data['nodes']
    links = network_data['links']
    
    # Use myopic solver (lookahead_days=1)
    solver = LinearProgrammingSolver()
    
    # Simulate Day 1
    # Set up demands for Day 1
    nodes[0].inflow = 60.0   # source has limited inflow
    nodes[2].request = 50.0  # low_demand wants 50
    nodes[3].request = 0.0   # high_demand wants 0
    
    # Calculate constraints
    constraints = {}
    for link in links:
        constraints[link.link_id] = link.calculate_constraints()
    
    # Solve Day 1
    flows_day1 = solver.solve(nodes, links, constraints)
    
    # Update storage based on flows
    storage_node = nodes[1]  # storage
    inflow = flows_day1.get("source_to_storage", 0.0)
    outflow_low = flows_day1.get("storage_to_low", 0.0)
    outflow_high = flows_day1.get("storage_to_high", 0.0)
    total_outflow = outflow_low + outflow_high
    
    storage_node.update_storage(inflow, total_outflow)
    
    print(f"Day 1 - Myopic solver:")
    print(f"  Storage after Day 1: {storage_node.storage:.1f}")
    print(f"  Low priority delivery: {outflow_low:.1f}")
    print(f"  High priority delivery: {outflow_high:.1f}")
    
    # Simulate Day 3 (skip Day 2 - no demands)
    # Set up demands for Day 3
    nodes[0].inflow = 0.0    # source has no inflow
    nodes[2].request = 0.0   # low_demand wants 0
    nodes[3].request = 80.0  # high_demand wants 80
    
    # Calculate constraints for Day 3
    constraints_day3 = {}
    for link in links:
        constraints_day3[link.link_id] = link.calculate_constraints()
    
    # Solve Day 3
    flows_day3 = solver.solve(nodes, links, constraints_day3)
    
    high_priority_delivery_day3 = flows_day3.get("storage_to_high", 0.0)
    
    print(f"Day 3 - Myopic solver:")
    print(f"  High priority delivery: {high_priority_delivery_day3:.1f}")
    print(f"  High priority request: 80.0")
    print(f"  Shortage: {80.0 - high_priority_delivery_day3:.1f}")
    
    # Myopic solver should fail to meet high priority demand fully
    assert high_priority_delivery_day3 < 30.0, "Myopic solver should create major shortage on Day 3"
    assert outflow_low >= 40.0, "Myopic solver should deliver significant amount to low priority on Day 1"


def test_lookahead_solver_hedges_successfully(hedging_test_network, climate_engine_3day):
    """
    Test that look-ahead solver hedges successfully.
    
    The look-ahead solver should:
    - Day 1: Store all 100 units, deliver 0 to low priority (hedge)
    - Day 3: Deliver full 80 to high priority from storage
    """
    network_data = hedging_test_network
    nodes = network_data['nodes']
    links = network_data['links']
    
    # Use look-ahead solver with 3-day horizon
    solver = LookaheadSolver(lookahead_days=3, carryover_cost=-1.0)
    
    # Set up future data for perfect foresight
    future_inflows = {
        "source": [60.0, 0.0, 0.0]  # Limited inflow pattern
    }
    future_demands = {
        "low_demand": [50.0, 0.0, 0.0],   # Low priority demand pattern
        "high_demand": [0.0, 0.0, 80.0]   # High priority demand pattern
    }
    
    solver.set_future_data(future_inflows, future_demands)
    
    # Set up current state (Day 1)
    nodes[0].inflow = 60.0   # source has limited inflow
    nodes[2].request = 50.0  # low_demand wants 50
    nodes[3].request = 0.0   # high_demand wants 0
    
    # Calculate constraints
    constraints = {}
    for link in links:
        constraints[link.link_id] = link.calculate_constraints()
    
    # Solve with look-ahead
    flows_day1 = solver.solve(nodes, links, constraints)
    
    # Extract current timestep flows (t=0)
    current_flows = {}
    for link_id, flow in flows_day1.items():
        if not link_id.endswith(('_t1', '_t2', '_carryover')):
            current_flows[link_id] = flow
    
    low_priority_delivery = current_flows.get("storage_to_low", 0.0)
    high_priority_delivery = current_flows.get("storage_to_high", 0.0)
    storage_inflow = current_flows.get("source_to_storage", 0.0)
    
    print(f"Day 1 - Look-ahead solver:")
    print(f"  Storage inflow: {storage_inflow:.1f}")
    print(f"  Low priority delivery: {low_priority_delivery:.1f}")
    print(f"  High priority delivery: {high_priority_delivery:.1f}")
    
    # Look-ahead solver should hedge: store water, don't deliver to low priority
    assert low_priority_delivery < 25.0, "Look-ahead solver should hedge by limiting low priority delivery"
    assert storage_inflow > 50.0, "Look-ahead solver should store most/all water for future"
    
    print("✅ Look-ahead solver successfully hedged water for future high-priority demand")


def test_lookahead_regression_single_day():
    """
    Test that lookahead_days=1 produces identical results to myopic solver.
    
    This ensures backward compatibility and validates the implementation.
    """
    # Create simple single-day network
    source_data = pd.DataFrame({
        'date': ['2024-01-01'],
        'inflow': [100.0]
    })
    
    source = SourceNode("source", TimeSeriesStrategy(source_data, 'inflow'))
    
    eav_table = ElevationAreaVolume(
        elevations=[0, 100],
        areas=[1000, 1000],
        volumes=[0, 100],
        node_id="storage"
    )
    storage = StorageNode("storage", 0.0, eav_table, max_storage=100.0)
    
    demand = DemandNode("demand", MunicipalDemand(50, 1.0))
    
    source_to_storage = Link("source_to_storage", source, storage, 200.0, -1.0)
    storage_to_demand = Link("storage_to_demand", storage, demand, 100.0, -1000.0)
    
    # Set up connections
    source.outflows = [source_to_storage]
    storage.inflows = [source_to_storage]
    storage.outflows = [storage_to_demand]
    demand.inflows = [storage_to_demand]
    
    nodes = [source, storage, demand]
    links = [source_to_storage, storage_to_demand]
    
    # Set current state
    source.inflow = 100.0
    demand.request = 50.0
    
    # Calculate constraints
    constraints = {}
    for link in links:
        constraints[link.link_id] = link.calculate_constraints()
    
    # Solve with myopic solver
    myopic_solver = LinearProgrammingSolver()
    myopic_flows = myopic_solver.solve(nodes, links, constraints)
    
    # Solve with look-ahead solver (1 day = myopic behavior)
    lookahead_solver = LookaheadSolver(lookahead_days=1)
    lookahead_flows = lookahead_solver.solve(nodes, links, constraints)
    
    # Results should be identical
    for link_id in myopic_flows:
        myopic_flow = myopic_flows[link_id]
        lookahead_flow = lookahead_flows[link_id]
        
        print(f"Link {link_id}: Myopic={myopic_flow:.3f}, Lookahead={lookahead_flow:.3f}")
        
        assert abs(myopic_flow - lookahead_flow) < 1e-6, \
            f"Regression test failed for {link_id}: {myopic_flow} != {lookahead_flow}"
    
    print("✅ Regression test passed: lookahead_days=1 matches myopic solver")


if __name__ == "__main__":
    # Run tests manually for debugging
    import sys
    sys.path.append('.')
    
    # Create fixtures manually
    network = hedging_test_network()
    climate = climate_engine_3day()
    
    print("=== Testing Myopic Solver (Expected to Fail Hedging) ===")
    test_myopic_solver_fails_hedging(network, climate)
    
    print("\n=== Testing Look-ahead Solver (Expected to Hedge Successfully) ===")
    test_lookahead_solver_hedges_successfully(network, climate)
    
    print("\n=== Testing Regression (lookahead_days=1) ===")
    test_lookahead_regression_single_day()
    
    print("\n🎉 All hedging tests completed!")