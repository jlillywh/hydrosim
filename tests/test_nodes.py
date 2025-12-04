"""
Tests for node implementations.

This module tests the concrete node types: StorageNode, JunctionNode,
SourceNode, and DemandNode.
"""

import pytest
from datetime import datetime
from hydrosim.climate import ClimateState
from hydrosim.config import ElevationAreaVolume
from hydrosim.nodes import StorageNode, JunctionNode, SourceNode, DemandNode
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


def create_test_eav() -> ElevationAreaVolume:
    """Create a test EAV table."""
    elevations = [100.0, 110.0, 120.0]
    areas = [1000.0, 2000.0, 3000.0]
    volumes = [0.0, 10000.0, 30000.0]
    return ElevationAreaVolume(elevations, areas, volumes)


# StorageNode Tests

def test_storage_node_creation():
    """Test StorageNode initialization."""
    eav = create_test_eav()
    node = StorageNode("reservoir1", initial_storage=10000.0, eav_table=eav, max_storage=50000.0, min_storage=0.0)
    
    assert node.node_id == "reservoir1"
    assert node.node_type == "storage"
    assert node.storage == 10000.0
    assert node.eav_table == eav
    assert node.evap_loss == 0.0
    assert node.max_storage == 50000.0
    assert node.min_storage == 0.0


def test_storage_node_get_elevation():
    """Test StorageNode elevation interpolation."""
    eav = create_test_eav()
    node = StorageNode("reservoir1", initial_storage=10000.0, eav_table=eav, max_storage=50000.0, min_storage=0.0)
    
    elevation = node.get_elevation()
    assert elevation == 110.0


def test_storage_node_get_surface_area():
    """Test StorageNode surface area interpolation."""
    eav = create_test_eav()
    node = StorageNode("reservoir1", initial_storage=10000.0, eav_table=eav, max_storage=50000.0, min_storage=0.0)
    
    area = node.get_surface_area()
    assert area == 2000.0


def test_storage_node_step_calculates_evaporation():
    """Test StorageNode calculates evaporation during step."""
    eav = create_test_eav()
    node = StorageNode("reservoir1", initial_storage=10000.0, eav_table=eav, max_storage=50000.0, min_storage=0.0)
    climate = create_test_climate()
    
    node.step(climate)
    
    # Evaporation = surface_area * et0 / 1000 = 2000.0 * 5.0 / 1000 = 10.0 m³/day
    # (ET0 is in mm/day, area is in m², result is in m³/day)
    assert node.evap_loss == 10.0


def test_storage_node_update_storage():
    """Test StorageNode storage update with mass balance."""
    eav = create_test_eav()
    node = StorageNode("reservoir1", initial_storage=10000.0, eav_table=eav, max_storage=50000.0, min_storage=0.0)
    climate = create_test_climate()
    
    # Calculate evaporation first
    node.step(climate)
    
    # Update storage: new = old + inflow - outflow - evap
    # new = 10000 + 5000 - 2000 - 10.0 = 12990.0
    node.update_storage(inflow=5000.0, outflow=2000.0)
    
    assert node.storage == 12990.0


def test_storage_node_get_state():
    """Test StorageNode state reporting."""
    eav = create_test_eav()
    node = StorageNode("reservoir1", initial_storage=10000.0, eav_table=eav, max_storage=50000.0, min_storage=0.0)
    climate = create_test_climate()
    
    node.step(climate)
    state = node.get_state()
    
    assert "storage" in state
    assert "elevation" in state
    assert "surface_area" in state
    assert "evap_loss" in state
    assert state["storage"] == 10000.0
    assert state["elevation"] == 110.0
    assert state["surface_area"] == 2000.0
    assert state["evap_loss"] == 10.0


# JunctionNode Tests

def test_junction_node_creation():
    """Test JunctionNode initialization."""
    node = JunctionNode("junction1")
    
    assert node.node_id == "junction1"
    assert node.node_type == "junction"


def test_junction_node_step_does_nothing():
    """Test JunctionNode step does not modify state."""
    node = JunctionNode("junction1")
    climate = create_test_climate()
    
    # Should not raise any errors
    node.step(climate)


def test_junction_node_get_state_empty():
    """Test JunctionNode returns empty state."""
    node = JunctionNode("junction1")
    
    state = node.get_state()
    assert state == {}


# SourceNode Tests

def test_source_node_creation():
    """Test SourceNode initialization."""
    generator = MockGeneratorStrategy(100.0)
    node = SourceNode("source1", generator=generator)
    
    assert node.node_id == "source1"
    assert node.node_type == "source"
    assert node.generator == generator
    assert node.inflow == 0.0


def test_source_node_step_generates_inflow():
    """Test SourceNode generates inflow during step."""
    generator = MockGeneratorStrategy(100.0)
    node = SourceNode("source1", generator=generator)
    climate = create_test_climate()
    
    node.step(climate)
    
    assert node.inflow == 100.0


def test_source_node_get_state():
    """Test SourceNode state reporting."""
    generator = MockGeneratorStrategy(100.0)
    node = SourceNode("source1", generator=generator)
    climate = create_test_climate()
    
    node.step(climate)
    state = node.get_state()
    
    assert "inflow" in state
    assert state["inflow"] == 100.0


def test_source_node_strategy_pluggability():
    """Test SourceNode can use different strategies."""
    generator1 = MockGeneratorStrategy(100.0)
    generator2 = MockGeneratorStrategy(200.0)
    
    node = SourceNode("source1", generator=generator1)
    climate = create_test_climate()
    
    node.step(climate)
    assert node.inflow == 100.0
    
    # Switch strategy
    node.generator = generator2
    node.step(climate)
    assert node.inflow == 200.0


# DemandNode Tests

def test_demand_node_creation():
    """Test DemandNode initialization."""
    demand_model = MockDemandModel(50.0)
    node = DemandNode("demand1", demand_model=demand_model)
    
    assert node.node_id == "demand1"
    assert node.node_type == "demand"
    assert node.demand_model == demand_model
    assert node.request == 0.0
    assert node.delivered == 0.0
    assert node.deficit == 0.0


def test_demand_node_step_calculates_request():
    """Test DemandNode calculates request during step."""
    demand_model = MockDemandModel(50.0)
    node = DemandNode("demand1", demand_model=demand_model)
    climate = create_test_climate()
    
    node.step(climate)
    
    assert node.request == 50.0


def test_demand_node_update_delivery_no_deficit():
    """Test DemandNode update when demand is fully met."""
    demand_model = MockDemandModel(50.0)
    node = DemandNode("demand1", demand_model=demand_model)
    climate = create_test_climate()
    
    node.step(climate)
    node.update_delivery(50.0)
    
    assert node.delivered == 50.0
    assert node.deficit == 0.0


def test_demand_node_update_delivery_with_deficit():
    """Test DemandNode update when demand is not fully met."""
    demand_model = MockDemandModel(50.0)
    node = DemandNode("demand1", demand_model=demand_model)
    climate = create_test_climate()
    
    node.step(climate)
    node.update_delivery(30.0)
    
    assert node.delivered == 30.0
    assert node.deficit == 20.0


def test_demand_node_update_delivery_over_delivery():
    """Test DemandNode update when delivery exceeds request."""
    demand_model = MockDemandModel(50.0)
    node = DemandNode("demand1", demand_model=demand_model)
    climate = create_test_climate()
    
    node.step(climate)
    node.update_delivery(70.0)
    
    assert node.delivered == 70.0
    assert node.deficit == 0.0  # Deficit should not be negative


def test_demand_node_get_state():
    """Test DemandNode state reporting."""
    demand_model = MockDemandModel(50.0)
    node = DemandNode("demand1", demand_model=demand_model)
    climate = create_test_climate()
    
    node.step(climate)
    node.update_delivery(30.0)
    state = node.get_state()
    
    assert "request" in state
    assert "delivered" in state
    assert "deficit" in state
    assert state["request"] == 50.0
    assert state["delivered"] == 30.0
    assert state["deficit"] == 20.0


def test_demand_node_strategy_pluggability():
    """Test DemandNode can use different strategies."""
    demand_model1 = MockDemandModel(50.0)
    demand_model2 = MockDemandModel(100.0)
    
    node = DemandNode("demand1", demand_model=demand_model1)
    climate = create_test_climate()
    
    node.step(climate)
    assert node.request == 50.0
    
    # Switch strategy
    node.demand_model = demand_model2
    node.step(climate)
    assert node.request == 100.0



# Integration tests with real demand models

def test_demand_node_with_municipal_demand():
    """Test DemandNode with MunicipalDemand strategy."""
    from hydrosim.strategies import MunicipalDemand
    
    demand_model = MunicipalDemand(population=10000.0, per_capita_demand=0.2)
    node = DemandNode("city1", demand_model=demand_model)
    climate = create_test_climate()
    
    node.step(climate)
    
    # 10000 * 0.2 = 2000 m³/day
    assert node.request == 2000.0


def test_demand_node_with_agriculture_demand():
    """Test DemandNode with AgricultureDemand strategy."""
    from hydrosim.strategies import AgricultureDemand
    
    demand_model = AgricultureDemand(area=100000.0, crop_coefficient=0.8)
    node = DemandNode("farm1", demand_model=demand_model)
    climate = create_test_climate(et0=5.0)
    
    node.step(climate)
    
    # ET_crop = 0.8 * 5.0 = 4.0 mm
    # Volume = 4.0 * 100000 / 1000 = 400 m³
    assert node.request == pytest.approx(400.0)


def test_demand_node_switch_between_demand_models():
    """Test DemandNode can switch between different demand model types."""
    from hydrosim.strategies import MunicipalDemand, AgricultureDemand
    
    municipal = MunicipalDemand(population=5000.0, per_capita_demand=0.15)
    agriculture = AgricultureDemand(area=50000.0, crop_coefficient=1.0)
    
    node = DemandNode("demand1", demand_model=municipal)
    climate = create_test_climate(et0=6.0)
    
    # Test with municipal demand
    node.step(climate)
    assert node.request == 750.0  # 5000 * 0.15
    
    # Switch to agriculture demand
    node.demand_model = agriculture
    node.step(climate)
    assert node.request == pytest.approx(300.0)  # 1.0 * 6.0 * 50000 / 1000
