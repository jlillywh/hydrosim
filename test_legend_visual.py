#!/usr/bin/env python3
"""
Visual test for subplot legends implementation.
Creates a simple plot to verify legend positioning and styling.
"""

import pandas as pd
from datetime import datetime, timedelta
from hydrosim.results_viz import ResultsVisualizer
from hydrosim.results import ResultsWriter
from hydrosim.config import NetworkGraph
from hydrosim.nodes import StorageNode, SourceNode, DemandNode
from hydrosim.links import Link
from hydrosim.strategies import TimeSeriesStrategy, MunicipalDemand
from hydrosim.config import ElevationAreaVolume
from hydrosim.climate import ClimateState


def create_test_data():
    """Create test data for visualization."""
    # Create network
    network = NetworkGraph()
    
    # Create EAV table
    eav = ElevationAreaVolume([100, 110, 120], [1000, 2000, 3000], [0, 10000, 30000])
    
    # Add nodes
    source = SourceNode("catchment", TimeSeriesStrategy(pd.DataFrame({'flow': [100, 120, 80, 90, 110]}), 'flow'))
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
    
    # Create results
    results_writer = ResultsWriter("test", "csv")
    
    # Add sample timesteps
    for i in range(5):
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
    
    return network, results_writer


def test_legend_implementation():
    """Test the legend implementation."""
    print("Creating test data...")
    network, results_writer = create_test_data()
    
    # Test configuration with multiple plots
    viz_config = {
        'plots': [
            {
                'type': 'climate',
                'title': 'Climate Conditions',
                'y1_axis': {'label': 'Precipitation (mm/day)', 'variables': ['precip']},
                'y2_axis': {'label': 'Temperature (degC)', 'variables': ['tmax', 'tmin']}
            },
            {
                'type': 'reservoir',
                'node_id': 'reservoir',
                'title': 'Reservoir Operations',
                'y1_axis': {'label': 'Storage (m^3)', 'variables': ['storage']},
                'y2_axis': {'label': 'Flow (m^3/day)', 'variables': ['inflow', 'outflow', 'evap_loss']}
            },
            {
                'type': 'demand',
                'node_id': 'city',
                'title': 'City Supply vs Demand',
                'y1_axis': {'label': 'Flow (m^3/day)', 'variables': ['request', 'delivered', 'deficit']}
            }
        ],
        'layout': {
            'width': 1000,
            'height': 300
        }
    }
    
    print("Creating visualizer...")
    visualizer = ResultsVisualizer(results_writer, network, viz_config)
    
    print("Generating plots...")
    fig = visualizer.generate_all_plots()
    
    print("Checking implementation...")
    print(f"Number of traces: {len(fig.data)}")
    print(f"Number of annotations: {len(fig.layout.annotations)}")
    print(f"Show legend: {fig.layout.showlegend}")
    
    # Check for custom legend annotations
    legend_annotations = [ann for ann in fig.layout.annotations if ann.x > 1.0]
    print(f"Custom legend annotations: {len(legend_annotations)}")
    
    for i, ann in enumerate(legend_annotations):
        print(f"  Legend {i+1}: x={ann.x}, y={ann.y}, text preview: {ann.text[:50]}...")
    
    print("Saving test output...")
    fig.write_html("test_legend_output.html")
    print("✓ Test complete! Check 'test_legend_output.html' to see the results.")


if __name__ == "__main__":
    test_legend_implementation()