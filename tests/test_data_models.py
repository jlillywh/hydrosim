"""
Tests for data models and network graph.

This module tests the core data structures including ClimateState, SiteConfig,
ElevationAreaVolume, and NetworkGraph.
"""

import pytest
from datetime import datetime
from hydrosim.climate import ClimateState, SiteConfig
from hydrosim.config import ElevationAreaVolume, NetworkGraph
from hydrosim.nodes import Node
from hydrosim.links import Link


class MockNode(Node):
    """Mock node for testing."""
    
    def step(self, climate):
        pass
    
    def get_state(self):
        return {}


def test_climate_state_creation():
    """Test ClimateState dataclass creation."""
    climate = ClimateState(
        date=datetime(2024, 1, 1),
        precip=10.0,
        t_max=25.0,
        t_min=15.0,
        solar=20.0,
        et0=5.0
    )
    
    assert climate.date == datetime(2024, 1, 1)
    assert climate.precip == 10.0
    assert climate.t_max == 25.0
    assert climate.t_min == 15.0
    assert climate.solar == 20.0
    assert climate.et0 == 5.0


def test_site_config_creation():
    """Test SiteConfig dataclass creation."""
    site = SiteConfig(latitude=45.0, elevation=1000.0)
    
    assert site.latitude == 45.0
    assert site.elevation == 1000.0


def test_eav_interpolation():
    """Test ElevationAreaVolume interpolation methods."""
    # Create a simple EAV table
    elevations = [100.0, 110.0, 120.0]
    areas = [1000.0, 2000.0, 3000.0]
    volumes = [0.0, 10000.0, 30000.0]
    
    eav = ElevationAreaVolume(elevations, areas, volumes)
    
    # Test exact values
    assert eav.storage_to_elevation(0.0) == 100.0
    assert eav.storage_to_elevation(10000.0) == 110.0
    assert eav.storage_to_elevation(30000.0) == 120.0
    
    assert eav.storage_to_area(0.0) == 1000.0
    assert eav.storage_to_area(10000.0) == 2000.0
    assert eav.storage_to_area(30000.0) == 3000.0
    
    # Test interpolated values
    mid_storage = 5000.0
    mid_elevation = eav.storage_to_elevation(mid_storage)
    assert 100.0 < mid_elevation < 110.0
    
    mid_area = eav.storage_to_area(mid_storage)
    assert 1000.0 < mid_area < 2000.0


def test_network_graph_add_node():
    """Test adding nodes to network graph."""
    graph = NetworkGraph()
    node1 = MockNode("node1", "junction")
    node2 = MockNode("node2", "storage")
    
    graph.add_node(node1)
    graph.add_node(node2)
    
    assert "node1" in graph.nodes
    assert "node2" in graph.nodes
    assert graph.nodes["node1"] == node1
    assert graph.nodes["node2"] == node2


def test_network_graph_add_link():
    """Test adding links to network graph."""
    graph = NetworkGraph()
    node1 = MockNode("node1", "junction")
    node2 = MockNode("node2", "storage")
    
    graph.add_node(node1)
    graph.add_node(node2)
    
    link = Link("link1", node1, node2, physical_capacity=100.0, cost=1.0)
    graph.add_link(link)
    
    assert "link1" in graph.links
    assert graph.links["link1"] == link
    assert link in node1.outflows
    assert link in node2.inflows


def test_network_graph_validation_valid():
    """Test network validation with valid topology."""
    graph = NetworkGraph()
    node1 = MockNode("node1", "source")
    node2 = MockNode("node2", "demand")
    
    graph.add_node(node1)
    graph.add_node(node2)
    
    link = Link("link1", node1, node2, physical_capacity=100.0, cost=1.0)
    graph.add_link(link)
    
    errors = graph.validate()
    assert len(errors) == 0


def test_network_graph_validation_orphaned_node():
    """Test network validation detects orphaned nodes."""
    graph = NetworkGraph()
    node1 = MockNode("node1", "junction")  # Not source or demand
    node2 = MockNode("node2", "source")
    node3 = MockNode("node3", "demand")
    
    graph.add_node(node1)
    graph.add_node(node2)
    graph.add_node(node3)
    
    # Connect node2 and node3, but leave node1 orphaned
    link = Link("link1", node2, node3, physical_capacity=100.0, cost=1.0)
    graph.add_link(link)
    
    errors = graph.validate()
    assert len(errors) == 1
    assert "node1" in errors[0]
    assert "no connections" in errors[0]


def test_network_graph_validation_missing_source():
    """Test network validation detects missing source node."""
    graph = NetworkGraph()
    node1 = MockNode("node1", "junction")
    node2 = MockNode("node2", "storage")
    
    # Only add node2 to graph
    graph.add_node(node2)
    
    # Create link with node1 as source (not in graph)
    link = Link("link1", node1, node2, physical_capacity=100.0, cost=1.0)
    graph.add_link(link)
    
    errors = graph.validate()
    assert len(errors) > 0
    assert any("node1" in error and "source" in error for error in errors)


def test_network_graph_validation_missing_target():
    """Test network validation detects missing target node."""
    graph = NetworkGraph()
    node1 = MockNode("node1", "junction")
    node2 = MockNode("node2", "storage")
    
    # Only add node1 to graph
    graph.add_node(node1)
    
    # Create link with node2 as target (not in graph)
    link = Link("link1", node1, node2, physical_capacity=100.0, cost=1.0)
    graph.add_link(link)
    
    errors = graph.validate()
    assert len(errors) > 0
    assert any("node2" in error and "target" in error for error in errors)
