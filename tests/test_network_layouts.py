"""
Tests for network layout improvements (Issue #4).

This module tests the improved network layout algorithms that make
network graphs more compact and less spread out.
"""

import pytest
import math
from hydrosim.config import NetworkGraph
from hydrosim.nodes import StorageNode, SourceNode, DemandNode, JunctionNode
from hydrosim.links import Link
from hydrosim.visualization import _calculate_layout, visualize_network
from hydrosim.strategies import MunicipalDemand, TimeSeriesStrategy
from hydrosim.config import ElevationAreaVolume
import pandas as pd


@pytest.fixture
def small_network():
    """Create a small network (3 nodes) for testing compact layouts."""
    network = NetworkGraph()
    
    # Create EAV table
    eav = ElevationAreaVolume([100, 110, 120], [1000, 2000, 3000], [0, 10000, 30000])
    
    # Add nodes
    source = SourceNode("source", TimeSeriesStrategy(pd.DataFrame({'flow': [100]}), 'flow'))
    storage = StorageNode("storage", 20000, eav, max_storage=30000)
    demand = DemandNode("demand", MunicipalDemand(1000, 0.2))
    
    network.add_node(source)
    network.add_node(storage)
    network.add_node(demand)
    
    # Add links
    link1 = Link("source_to_storage", source, storage, 1000, 0)
    link2 = Link("storage_to_demand", storage, demand, 500, -1000)
    
    network.add_link(link1)
    network.add_link(link2)
    
    return network


@pytest.fixture
def medium_network():
    """Create a medium network (6 nodes) for testing layouts."""
    network = NetworkGraph()
    
    # Create EAV table
    eav = ElevationAreaVolume([100, 110, 120], [1000, 2000, 3000], [0, 10000, 30000])
    
    # Add nodes
    source1 = SourceNode("source1", TimeSeriesStrategy(pd.DataFrame({'flow': [100]}), 'flow'))
    source2 = SourceNode("source2", TimeSeriesStrategy(pd.DataFrame({'flow': [150]}), 'flow'))
    storage = StorageNode("storage", 20000, eav, max_storage=30000)
    junction = JunctionNode("junction")
    demand1 = DemandNode("demand1", MunicipalDemand(1000, 0.2))
    demand2 = DemandNode("demand2", MunicipalDemand(500, 0.15))
    
    for node in [source1, source2, storage, junction, demand1, demand2]:
        network.add_node(node)
    
    # Add links
    links = [
        Link("source1_to_storage", source1, storage, 1000, 0),
        Link("source2_to_junction", source2, junction, 800, 0),
        Link("storage_to_junction", storage, junction, 500, 1),
        Link("junction_to_demand1", junction, demand1, 400, -1000),
        Link("junction_to_demand2", junction, demand2, 300, -1000)
    ]
    
    for link in links:
        network.add_link(link)
    
    return network


class TestNetworkLayouts:
    """Test network layout algorithms."""
    
    def test_hierarchical_layout_compact(self, small_network):
        """Test that hierarchical layout is more compact than before."""
        pos = _calculate_layout(small_network, 'hierarchical')
        
        # Check that all positions are within a reasonable range
        x_coords = [x for x, y in pos.values()]
        y_coords = [y for x, y in pos.values()]
        
        x_range = max(x_coords) - min(x_coords)
        y_range = max(y_coords) - min(y_coords)
        
        # Should be much more compact than the old 1.0 unit spacing
        assert x_range <= 0.8, f"X range too large: {x_range}"
        assert y_range <= 0.8, f"Y range too large: {y_range}"
        
        # Check hierarchical ordering (sources at top, demands at bottom)
        source_y = pos['source'][1]
        storage_y = pos['storage'][1]
        demand_y = pos['demand'][1]
        
        assert source_y > storage_y, "Source should be above storage"
        assert storage_y > demand_y, "Storage should be above demand"
    
    def test_circular_layout_compact(self, small_network):
        """Test that circular layout uses appropriate radius."""
        pos = _calculate_layout(small_network, 'circular')
        
        # Calculate actual radius used
        distances = [math.sqrt(x*x + y*y) for x, y in pos.values()]
        actual_radius = max(distances)
        
        # Should use a very compact radius
        assert actual_radius <= 0.3, f"Radius too large: {actual_radius}"
        assert actual_radius >= 0.1, f"Radius too small: {actual_radius}"
    
    def test_compact_layout_very_tight(self, small_network):
        """Test that compact layout is very tight for small networks."""
        pos = _calculate_layout(small_network, 'compact')
        
        # For 3 nodes, should use single row layout
        x_coords = [x for x, y in pos.values()]
        y_coords = [y for x, y in pos.values()]
        
        x_range = max(x_coords) - min(x_coords)
        y_range = max(y_coords) - min(y_coords)
        
        # Should be very compact
        assert x_range <= 0.5, f"X range too large for compact layout: {x_range}"
        assert y_range <= 0.1, f"Y range should be minimal for single row: {y_range}"
    
    def test_compact_layout_grid(self, medium_network):
        """Test that compact layout uses grid for larger networks."""
        pos = _calculate_layout(medium_network, 'compact')
        
        # Should arrange in a compact grid
        x_coords = [x for x, y in pos.values()]
        y_coords = [y for x, y in pos.values()]
        
        x_range = max(x_coords) - min(x_coords)
        y_range = max(y_coords) - min(y_coords)
        
        # Should be compact but allow for grid arrangement
        assert x_range <= 1.0, f"X range too large for compact grid: {x_range}"
        assert y_range <= 0.8, f"Y range too large for compact grid: {y_range}"
    
    def test_layout_scaling_with_network_size(self):
        """Test that layouts scale appropriately with network size."""
        # Test different network sizes
        for n_nodes in [2, 5, 10]:
            network = NetworkGraph()
            
            # Add nodes
            for i in range(n_nodes):
                if i == 0:
                    node = SourceNode(f"node_{i}", TimeSeriesStrategy(pd.DataFrame({'flow': [100]}), 'flow'))
                else:
                    node = DemandNode(f"node_{i}", MunicipalDemand(100, 0.1))
                network.add_node(node)
            
            # Test circular layout scaling
            pos = _calculate_layout(network, 'circular')
            distances = [math.sqrt(x*x + y*y) for x, y in pos.values()]
            max_radius = max(distances)
            
            # Radius should scale with network size but stay compact
            expected_radius = max(0.1, min(0.3, 0.05 * math.sqrt(n_nodes)))
            assert abs(max_radius - expected_radius) < 0.05, \
                f"Radius {max_radius} not close to expected {expected_radius} for {n_nodes} nodes"
    
    def test_visualize_network_with_layouts(self, small_network):
        """Test that visualize_network works with all layout options."""
        layouts = ['hierarchical', 'circular', 'compact']
        
        for layout in layouts:
            # Should not raise any exceptions
            fig = visualize_network(small_network, width=400, height=300, layout=layout)
            
            # Check that figure was created
            assert fig is not None
            assert len(fig.data) > 0  # Should have traces for nodes and edges
    
    def test_invalid_layout_defaults_to_circular(self, small_network):
        """Test that invalid layout names default to circular."""
        pos = _calculate_layout(small_network, 'invalid_layout')
        
        # Should behave like circular layout
        distances = [math.sqrt(x*x + y*y) for x, y in pos.values()]
        max_radius = max(distances)
        
        # Should use ultra-compact circular layout
        assert max_radius <= 0.3
        assert max_radius >= 0.1
    
    def test_empty_network_handling(self):
        """Test that empty networks are handled gracefully."""
        network = NetworkGraph()
        
        for layout in ['hierarchical', 'circular', 'compact']:
            pos = _calculate_layout(network, layout)
            assert pos == {}, f"Empty network should return empty positions for {layout}"
    
    def test_single_node_network(self):
        """Test layouts with single node networks."""
        network = NetworkGraph()
        source = SourceNode("source", TimeSeriesStrategy(pd.DataFrame({'flow': [100]}), 'flow'))
        network.add_node(source)
        
        for layout in ['hierarchical', 'circular', 'compact']:
            pos = _calculate_layout(network, layout)
            assert len(pos) == 1
            
            # Single node should be near origin
            x, y = pos['source']
            distance = math.sqrt(x*x + y*y)
            assert distance <= 0.5, f"Single node too far from origin in {layout} layout"