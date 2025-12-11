#!/usr/bin/env python3
"""
Debug script to verify axis label formatting is being applied.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from hydrosim.config import YAMLParser
from hydrosim import (
    SimulationEngine, LinearProgrammingSolver, ResultsWriter, ClimateEngine,
    visualize_results
)
from datetime import datetime


def debug_axis_labels():
    """Debug axis label formatting in quick_start workflow."""
    
    print("🔍 Debugging Axis Label Formatting")
    print("=" * 50)
    
    # Use the same workflow as quick_start.py
    print("\n[1] Loading simple network configuration...")
    parser = YAMLParser('examples/simple_network.yaml')
    network, climate_source, site_config = parser.parse()
    
    print("\n[2] Running short simulation...")
    climate_engine = ClimateEngine(climate_source, site_config, datetime(2024, 1, 1))
    solver = LinearProgrammingSolver()
    engine = SimulationEngine(network, climate_engine, solver)
    writer = ResultsWriter(output_dir="output", format="csv")
    
    # Run just 5 days for quick test
    for day in range(5):
        result = engine.step()
        writer.add_timestep(result)
    
    print("\n[3] Checking visualization configuration...")
    viz_config = network.viz_config or {}
    print(f"   Viz config found: {bool(viz_config)}")
    
    if viz_config and 'plots' in viz_config:
        for i, plot in enumerate(viz_config['plots']):
            print(f"   Plot {i+1}: {plot.get('type', 'unknown')}")
            if 'y1_axis' in plot:
                label = plot['y1_axis'].get('label', '')
                print(f"      Y1 label: '{label}'")
            if 'y2_axis' in plot:
                label = plot['y2_axis'].get('label', '')
                print(f"      Y2 label: '{label}'")
    
    print("\n[4] Testing our _format_axis_label method directly...")
    from hydrosim.results_viz import ResultsVisualizer
    visualizer = ResultsVisualizer(writer, network, viz_config)
    
    test_labels = [
        'Temperature (°C)',
        'Flow (m³/day)',
        'Storage (m³)',
        'Precipitation (mm/day)'
    ]
    
    for label in test_labels:
        formatted = visualizer._format_axis_label(label)
        print(f"   '{label}' → '{formatted}'")
    
    print("\n[5] Generating visualization...")
    fig = visualize_results(
        results_writer=writer,
        network=network,
        viz_config=viz_config,
        output_file='output/debug_axis_test.html'
    )
    
    print("   ✓ Visualization saved to: output/debug_axis_test.html")
    
    print("\n[6] Checking if labels were applied...")
    # Check the figure's axis titles
    for i, subplot in enumerate(fig._get_subplot_rows_columns()):
        row, col = subplot
        try:
            # Get y-axis title for this subplot
            yaxis_key = f'yaxis{i+1}' if i > 0 else 'yaxis'
            if yaxis_key in fig.layout:
                yaxis_title = fig.layout[yaxis_key].title.text
                print(f"   Subplot {i+1} Y-axis: '{yaxis_title}'")
            
            # Check secondary y-axis
            yaxis2_key = f'yaxis{i+1}' if i > 0 else 'yaxis2'
            if yaxis2_key in fig.layout:
                yaxis2_title = fig.layout[yaxis2_key].title.text
                print(f"   Subplot {i+1} Y2-axis: '{yaxis2_title}'")
                
        except Exception as e:
            print(f"   Subplot {i+1}: Could not read axis title ({e})")
    
    print("\n" + "=" * 50)
    print("🎯 Check the HTML file to see if axis labels display correctly!")
    print("=" * 50)


if __name__ == "__main__":
    debug_axis_labels()