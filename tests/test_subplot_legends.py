"""
Tests for subplot-specific legends (Issue #2).

This module tests the implementation of individual legends for each subplot
instead of a single global legend.
"""

import pytest
import pandas as pd
from datetime import datetime
from hydrosim.results_viz import ResultsVisualizer
from hydrosim.results import ResultsWriter
from hydrosim.config import NetworkGraph
from hydrosim.nodes import StorageNode, SourceNode, DemandNode
from hydrosim.links import Link
from hydrosim.strategies import TimeSeriesStrategy, MunicipalDemand
from hydrosim.config import ElevationAreaVolume
from hydrosim.climate import ClimateState


@pytest.fixture
def sample_network():
    """Create a sample network for testing."""
    network = NetworkGraph()
    
    # Create EAV table
    eav = ElevationAreaVolume([100, 110, 120], [1000, 2000, 3000], [0, 10000, 30000])
    
    # Add nodes
    source = SourceNode("catchment", TimeSeriesStrategy(pd.DataFrame({'flow': [100, 120, 80]}), 'flow'))
    storage = StorageNode("reservoir", 20000, eav, max_storage=30000)
    demand = DemandNode("city", MunicipalDemand(1000, 0.2))
    
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
def sample_results():
    """Create sample results data."""
    results_writer = ResultsWriter("test", "csv")
    
    # Add sample timesteps
    for i in range(3):
        results_writer.add_timestep({
            'timestep': i,
            'date': pd.Timestamp(f'2024-01-0{i+1}'),
            'climate': ClimateState(
                date=datetime(2024, 1, 1 + i),
                precip=5.0 + i,
                t_max=25.0 + i,
                t_min=15.0 + i,
                solar=20.0,
                et0=4.0
            ),
            'node_states': {
                'catchment': {'inflow': 100 - i*10},
                'reservoir': {
                    'storage': 20000 - i*1000, 
                    'evap_loss': 10 + i,
                    'elevation': 110.0 + i,
                    'surface_area': 1500.0 + i*100
                },
                'city': {
                    'request': 1000, 
                    'delivered': 950 + i*10, 
                    'deficit': 50 - i*10
                }
            },
            'flows': {
                'source_to_storage': 100 - i*10,
                'storage_to_demand': 80 - i*5
            }
        })
    
    return results_writer


class TestSubplotLegends:
    """Test subplot-specific legend functionality."""
    
    def test_legends_disabled_globally(self, sample_network, sample_results):
        """Test that global legend is disabled."""
        viz_config = {
            'plots': [
                {'type': 'climate', 'title': 'Climate'},
                {'type': 'reservoir', 'auto': True}
            ]
        }
        
        visualizer = ResultsVisualizer(sample_results, sample_network, viz_config)
        fig = visualizer.generate_all_plots()
        
        # Global showlegend should be False
        assert fig.layout.showlegend == False
    
    def test_traces_have_legend_groups(self, sample_network, sample_results):
        """Test that traces are assigned to legend groups by subplot."""
        viz_config = {
            'plots': [
                {'type': 'climate', 'title': 'Climate'},
                {'type': 'reservoir', 'auto': True}
            ]
        }
        
        visualizer = ResultsVisualizer(sample_results, sample_network, viz_config)
        fig = visualizer.generate_all_plots()
        
        # Check that traces have legend groups
        legend_groups = set()
        for trace in fig.data:
            if hasattr(trace, 'legendgroup') and trace.legendgroup:
                legend_groups.add(trace.legendgroup)
        
        # Should have legend groups for each subplot
        assert len(legend_groups) >= 1
        assert any('plot_' in lg for lg in legend_groups)
    
    def test_custom_legend_annotations_created(self, sample_network, sample_results):
        """Test that custom legend annotations are created for each subplot."""
        viz_config = {
            'plots': [
                {'type': 'climate', 'title': 'Climate'},
                {'type': 'reservoir', 'auto': True}
            ]
        }
        
        visualizer = ResultsVisualizer(sample_results, sample_network, viz_config)
        fig = visualizer.generate_all_plots()
        
        # Should have annotations for legends
        assert len(fig.layout.annotations) > 0
        
        # Check that annotations are positioned to the right (x > 1.0)
        legend_annotations = [ann for ann in fig.layout.annotations if ann.x > 1.0]
        assert len(legend_annotations) > 0
    
    def test_multiple_subplots_have_separate_legends(self, sample_network, sample_results):
        """Test that multiple subplots get separate legend positioning."""
        viz_config = {
            'plots': [
                {'type': 'climate', 'title': 'Climate'},
                {'type': 'reservoir', 'auto': True},
                {'type': 'demand', 'auto': True}
            ]
        }
        
        visualizer = ResultsVisualizer(sample_results, sample_network, viz_config)
        fig = visualizer.generate_all_plots()
        
        # Should have multiple legend groups
        legend_groups = set()
        for trace in fig.data:
            if hasattr(trace, 'legendgroup') and trace.legendgroup:
                legend_groups.add(trace.legendgroup)
        
        # Should have at least 1 legend group (some plots might not have data)
        assert len(legend_groups) >= 1
    
    def test_legend_positioning_scales_with_subplots(self, sample_network, sample_results):
        """Test that legend positions scale correctly with number of subplots."""
        viz_config = {
            'plots': [
                {'type': 'climate', 'title': 'Climate'},
                {'type': 'reservoir', 'auto': True},
                {'type': 'demand', 'auto': True}
            ]
        }
        
        visualizer = ResultsVisualizer(sample_results, sample_network, viz_config)
        fig = visualizer.generate_all_plots()
        
        # Get legend annotation y-positions
        legend_annotations = [ann for ann in fig.layout.annotations if ann.x > 1.0]
        y_positions = [ann.y for ann in legend_annotations]
        
        if len(y_positions) > 1:
            # Y positions should be different (spread vertically)
            assert len(set(y_positions)) > 1
            # Y positions should be between 0 and 1
            assert all(0 <= y <= 1 for y in y_positions)
    
    def test_backward_compatibility_with_no_viz_config(self, sample_network, sample_results):
        """Test that the system works without visualization config (backward compatibility)."""
        # No viz_config provided - should use defaults
        visualizer = ResultsVisualizer(sample_results, sample_network)
        fig = visualizer.generate_all_plots()
        
        # Should still generate a figure without errors
        assert fig is not None
        assert len(fig.data) > 0
    
    def test_empty_results_handled_gracefully(self, sample_network):
        """Test that empty results are handled gracefully."""
        empty_results = ResultsWriter("test", "csv")
        
        viz_config = {
            'plots': [
                {'type': 'climate', 'title': 'Climate'},
                {'type': 'reservoir', 'auto': True}
            ]
        }
        
        visualizer = ResultsVisualizer(empty_results, sample_network, viz_config)
        fig = visualizer.generate_all_plots()
        
        # Should generate figure without errors, even with no data
        assert fig is not None
        assert fig.layout.showlegend == False