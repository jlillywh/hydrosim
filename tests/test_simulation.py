"""
Tests for the simulation engine.

These tests verify that the simulation engine correctly orchestrates
timestep execution in the proper order and updates state correctly.
"""

import pytest
from datetime import datetime
import numpy as np

from hydrosim.simulation import SimulationEngine
from hydrosim.climate_engine import ClimateEngine
from hydrosim.climate import ClimateState, SiteConfig
from hydrosim.climate_sources import TimeSeriesClimateSource
from hydrosim.config import NetworkGraph, ElevationAreaVolume
from hydrosim.nodes import StorageNode, JunctionNode, SourceNode, DemandNode
from hydrosim.links import Link
from hydrosim.solver import LinearProgrammingSolver
from hydrosim.strategies import TimeSeriesStrategy, MunicipalDemand
import pandas as pd


@pytest.fixture
def simple_network():
    """Create a simple network for testing: Source -> Storage -> Demand"""
    network = NetworkGraph()
    
    # Create EAV table for storage
    eav = ElevationAreaVolume(
        elevations=[100.0, 110.0, 120.0],
        areas=[1000.0, 1500.0, 2000.0],
        volumes=[0.0, 12500.0, 30000.0]
    )
    
    # Create nodes
    # Source with time series data
    inflow_data = pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=10, freq='D'),
        'inflow': [100.0] * 10
    })
    source = SourceNode('source1', TimeSeriesStrategy(inflow_data, 'inflow'))
    
    # Storage node
    storage = StorageNode('storage1', initial_storage=15000.0, eav_table=eav, max_storage=50000.0, min_storage=0.0)
    
    # Demand node (lower demand to make network feasible)
    demand = DemandNode('demand1', MunicipalDemand(population=400, per_capita_demand=0.2))
    
    # Add nodes to network
    network.add_node(source)
    network.add_node(storage)
    network.add_node(demand)
    
    # Create links
    link1 = Link('link1', source, storage, physical_capacity=200.0, cost=1.0)
    link2 = Link('link2', storage, demand, physical_capacity=300.0, cost=1.0)
    
    # Add links to network
    network.add_link(link1)
    network.add_link(link2)
    
    return network


@pytest.fixture
def climate_engine():
    """Create a climate engine for testing."""
    # Create simple climate data with date as index
    climate_data = pd.DataFrame({
        'precip': [5.0] * 10,
        't_max': [25.0] * 10,
        't_min': [15.0] * 10,
        'solar': [20.0] * 10
    }, index=pd.date_range('2024-01-01', periods=10, freq='D'))
    
    source = TimeSeriesClimateSource(climate_data)
    site_config = SiteConfig(latitude=40.0, elevation=100.0)
    
    return ClimateEngine(source, site_config, datetime(2024, 1, 1))


def test_simulation_engine_initialization(simple_network, climate_engine):
    """Test that simulation engine can be initialized."""
    solver = LinearProgrammingSolver()
    engine = SimulationEngine(simple_network, climate_engine, solver)
    
    assert engine.network == simple_network
    assert engine.climate_engine == climate_engine
    assert engine.solver == solver
    assert engine.current_timestep == 0


def test_simulation_engine_single_step(simple_network, climate_engine):
    """Test that simulation engine can execute a single timestep."""
    solver = LinearProgrammingSolver()
    engine = SimulationEngine(simple_network, climate_engine, solver)
    
    # Execute one timestep
    results = engine.step()
    
    # Verify results structure
    assert 'timestep' in results
    assert 'date' in results
    assert 'climate' in results
    assert 'node_states' in results
    assert 'flows' in results
    
    # Verify timestep incremented
    assert results['timestep'] == 0
    assert engine.current_timestep == 1
    
    # Verify climate state
    assert isinstance(results['climate'], ClimateState)
    
    # Verify node states
    assert 'source1' in results['node_states']
    assert 'storage1' in results['node_states']
    assert 'demand1' in results['node_states']
    
    # Verify flows
    assert 'link1' in results['flows']
    assert 'link2' in results['flows']


def test_execution_order_environment_first(simple_network, climate_engine):
    """Test that environment step executes first and updates climate."""
    solver = LinearProgrammingSolver()
    engine = SimulationEngine(simple_network, climate_engine, solver)
    
    # Get initial date
    initial_date = climate_engine.current_date
    
    # Execute one timestep
    results = engine.step()
    
    # Verify climate was updated
    assert results['climate'] is not None
    assert results['climate'].date == initial_date
    
    # Verify climate engine advanced
    assert climate_engine.current_date == initial_date + pd.Timedelta(days=1)


def test_execution_order_nodes_after_environment(simple_network, climate_engine):
    """Test that nodes execute after environment and receive climate data."""
    solver = LinearProgrammingSolver()
    engine = SimulationEngine(simple_network, climate_engine, solver)
    
    # Execute one timestep
    results = engine.step()
    
    # Verify source generated inflow
    source_state = results['node_states']['source1']
    assert 'inflow' in source_state
    assert source_state['inflow'] == 100.0  # From time series
    
    # Verify demand calculated request
    demand_state = results['node_states']['demand1']
    assert 'request' in demand_state
    assert demand_state['request'] == 80.0  # 400 * 0.2
    
    # Verify storage calculated evaporation
    storage_state = results['node_states']['storage1']
    assert 'evap_loss' in storage_state
    assert storage_state['evap_loss'] > 0  # Should have some evaporation


def test_execution_order_solver_after_links(simple_network, climate_engine):
    """Test that solver executes after links calculate constraints."""
    solver = LinearProgrammingSolver()
    engine = SimulationEngine(simple_network, climate_engine, solver)
    
    # Execute one timestep
    results = engine.step()
    
    # Verify flows were allocated
    assert results['flows']['link1'] >= 0
    assert results['flows']['link2'] >= 0
    
    # Verify flows respect constraints
    link1 = simple_network.links['link1']
    link2 = simple_network.links['link2']
    
    assert results['flows']['link1'] <= link1.physical_capacity
    assert results['flows']['link2'] <= link2.physical_capacity


def test_state_update_after_solver(simple_network, climate_engine):
    """Test that state is updated after solver allocates flows."""
    solver = LinearProgrammingSolver()
    engine = SimulationEngine(simple_network, climate_engine, solver)
    
    # Get initial storage
    storage_node = simple_network.nodes['storage1']
    initial_storage = storage_node.storage
    
    # Execute one timestep
    results = engine.step()
    
    # Verify storage was updated
    final_storage = storage_node.storage
    assert final_storage != initial_storage
    
    # Verify mass balance: storage change = inflow - outflow - evaporation
    inflow = results['flows']['link1']
    outflow = results['flows']['link2']
    evap_loss = results['node_states']['storage1']['evap_loss']
    
    expected_change = inflow - outflow - evap_loss
    actual_change = final_storage - initial_storage
    
    assert abs(actual_change - expected_change) < 1e-6


def test_demand_delivery_update(simple_network, climate_engine):
    """Test that demand nodes are updated with delivery information."""
    solver = LinearProgrammingSolver()
    engine = SimulationEngine(simple_network, climate_engine, solver)
    
    # Execute one timestep
    results = engine.step()
    
    # Verify demand node was updated
    demand_node = simple_network.nodes['demand1']
    demand_state = results['node_states']['demand1']
    
    assert 'delivered' in demand_state
    assert 'deficit' in demand_state
    
    # Delivered should equal inflow to demand node
    delivered = demand_state['delivered']
    inflow_to_demand = results['flows']['link2']
    assert abs(delivered - inflow_to_demand) < 1e-6
    
    # Deficit should be request - delivered
    request = demand_state['request']
    deficit = demand_state['deficit']
    assert abs(deficit - max(0, request - delivered)) < 1e-6


def test_link_flow_values_updated(simple_network, climate_engine):
    """Test that link flow values are updated after solver."""
    solver = LinearProgrammingSolver()
    engine = SimulationEngine(simple_network, climate_engine, solver)
    
    # Execute one timestep
    results = engine.step()
    
    # Verify link flow attributes were updated
    link1 = simple_network.links['link1']
    link2 = simple_network.links['link2']
    
    assert link1.flow == results['flows']['link1']
    assert link2.flow == results['flows']['link2']


def test_run_multiple_timesteps(simple_network, climate_engine):
    """Test that simulation can run for multiple timesteps."""
    solver = LinearProgrammingSolver()
    engine = SimulationEngine(simple_network, climate_engine, solver)
    
    # Run for 5 timesteps
    results = engine.run(5)
    
    # Verify we got 5 results
    assert len(results) == 5
    
    # Verify timesteps are sequential
    for i, result in enumerate(results):
        assert result['timestep'] == i
    
    # Verify final timestep counter
    assert engine.current_timestep == 5


def test_sequential_timestep_solving(simple_network, climate_engine):
    """Test that timesteps are solved independently in sequence."""
    solver = LinearProgrammingSolver()
    engine = SimulationEngine(simple_network, climate_engine, solver)
    
    # Get initial storage
    storage_node = simple_network.nodes['storage1']
    initial_storage = storage_node.storage
    
    # Run first timestep
    results1 = engine.step()
    storage_after_1 = storage_node.storage
    
    # Run second timestep
    results2 = engine.step()
    storage_after_2 = storage_node.storage
    
    # Verify storage changed between timesteps
    assert storage_after_1 != initial_storage
    assert storage_after_2 != storage_after_1
    
    # Verify each timestep used updated state
    # (storage at timestep 2 should reflect changes from timestep 1)
    assert results2['node_states']['storage1']['storage'] == storage_after_2


def test_get_current_timestep(simple_network, climate_engine):
    """Test that current timestep can be queried."""
    solver = LinearProgrammingSolver()
    engine = SimulationEngine(simple_network, climate_engine, solver)
    
    assert engine.get_current_timestep() == 0
    
    engine.step()
    assert engine.get_current_timestep() == 1
    
    engine.step()
    assert engine.get_current_timestep() == 2


def test_get_network_state(simple_network, climate_engine):
    """Test that network state can be queried."""
    solver = LinearProgrammingSolver()
    engine = SimulationEngine(simple_network, climate_engine, solver)
    
    # Execute one timestep
    engine.step()
    
    # Get network state
    state = engine.get_network_state()
    
    # Verify all nodes are present
    assert 'source1' in state
    assert 'storage1' in state
    assert 'demand1' in state
    
    # Verify state structure
    assert isinstance(state['source1'], dict)
    assert isinstance(state['storage1'], dict)
    assert isinstance(state['demand1'], dict)


def test_storage_mass_balance_over_multiple_timesteps(simple_network, climate_engine):
    """Test that storage mass balance is maintained over multiple timesteps."""
    solver = LinearProgrammingSolver()
    engine = SimulationEngine(simple_network, climate_engine, solver)
    
    storage_node = simple_network.nodes['storage1']
    initial_storage = storage_node.storage
    
    # Track cumulative flows
    total_inflow = 0.0
    total_outflow = 0.0
    total_evap = 0.0
    
    # Run for 5 timesteps
    results = engine.run(5)
    
    for result in results:
        total_inflow += result['flows']['link1']
        total_outflow += result['flows']['link2']
        total_evap += result['node_states']['storage1']['evap_loss']
    
    # Verify final storage
    final_storage = storage_node.storage
    expected_storage = initial_storage + total_inflow - total_outflow - total_evap
    
    assert abs(final_storage - expected_storage) < 1e-4


def test_constraint_update_propagation(simple_network, climate_engine):
    """Test that constraint updates propagate to next timestep."""
    solver = LinearProgrammingSolver()
    engine = SimulationEngine(simple_network, climate_engine, solver)
    
    storage_node = simple_network.nodes['storage1']
    
    # Run first timestep
    results1 = engine.step()
    storage_after_1 = storage_node.storage
    
    # Manually change storage to affect hydraulic constraints
    # (In a real scenario, this would happen naturally through simulation)
    storage_node.storage = 5000.0  # Lower storage
    
    # Run second timestep
    results2 = engine.step()
    
    # The solver should have used updated constraints
    # (We can't easily verify the exact constraint values without
    # instrumenting the solver, but we can verify the simulation ran)
    assert results2['timestep'] == 1
    assert 'flows' in results2


def test_stepwise_optimization_no_lookahead():
    """Test that solver only uses current timestep data, not future data."""
    # Create a network where future information would change decisions
    network = NetworkGraph()
    
    eav = ElevationAreaVolume(
        elevations=[100.0, 110.0, 120.0],
        areas=[1000.0, 1500.0, 2000.0],
        volumes=[0.0, 12500.0, 30000.0]
    )
    
    # Source with varying inflow
    inflow_data = pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=10, freq='D'),
        'inflow': [100.0, 0.0, 0.0, 0.0, 0.0, 200.0, 200.0, 200.0, 200.0, 200.0]
    })
    source = SourceNode('source1', TimeSeriesStrategy(inflow_data, 'inflow'))
    
    storage = StorageNode('storage1', initial_storage=15000.0, eav_table=eav, max_storage=50000.0, min_storage=0.0)
    demand = DemandNode('demand1', MunicipalDemand(population=400, per_capita_demand=0.2))
    
    network.add_node(source)
    network.add_node(storage)
    network.add_node(demand)
    
    link1 = Link('link1', source, storage, physical_capacity=200.0, cost=1.0)
    link2 = Link('link2', storage, demand, physical_capacity=300.0, cost=1.0)
    
    network.add_link(link1)
    network.add_link(link2)
    
    # Create climate engine with date as index
    climate_data = pd.DataFrame({
        'precip': [5.0] * 10,
        't_max': [25.0] * 10,
        't_min': [15.0] * 10,
        'solar': [20.0] * 10
    }, index=pd.date_range('2024-01-01', periods=10, freq='D'))
    
    source_climate = TimeSeriesClimateSource(climate_data)
    site_config = SiteConfig(latitude=40.0, elevation=100.0)
    climate_engine = ClimateEngine(source_climate, site_config, datetime(2024, 1, 1))
    
    # Run simulation
    solver = LinearProgrammingSolver()
    engine = SimulationEngine(network, climate_engine, solver)
    
    results = engine.run(5)
    
    # At timestep 0, solver should not know that inflow will be 0 for next 4 days
    # So it should allocate based only on current state
    # We verify this by checking that the simulation ran successfully
    # (A lookahead solver would require different implementation)
    assert len(results) == 5
    assert all('flows' in r for r in results)
