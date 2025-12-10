#!/usr/bin/env python3
"""
Visual test for axis label character encoding fix.

This script creates a simple plot with special characters to verify
they display correctly in the HTML output.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from hydrosim.results_viz import ResultsVisualizer
from hydrosim import ResultsWriter, NetworkGraph
import webbrowser


def create_test_plot():
    """Create a test plot with special characters in axis labels."""
    
    print("🧪 Creating visual test for axis label character encoding...")
    
    # Create a simple test plot
    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=[
            "Before Fix: Raw Unicode Characters",
            "After Fix: HTML Entities", 
            "Comprehensive Character Test"
        ],
        vertical_spacing=0.1
    )
    
    # Sample data
    x_data = [1, 2, 3, 4, 5]
    y_data = [10, 15, 13, 17, 20]
    
    # Plot 1: Raw Unicode (what it looked like before)
    fig.add_trace(
        go.Scatter(x=x_data, y=y_data, name="Temperature", mode='lines+markers'),
        row=1, col=1
    )
    
    # Plot 2: HTML entities (our fix)
    fig.add_trace(
        go.Scatter(x=x_data, y=[v*2 for v in y_data], name="Flow", mode='lines+markers'),
        row=2, col=1
    )
    
    # Plot 3: Comprehensive test
    fig.add_trace(
        go.Scatter(x=x_data, y=[v*3 for v in y_data], name="Pressure", mode='lines+markers'),
        row=3, col=1
    )
    
    # Test our formatting function
    visualizer = ResultsVisualizer(ResultsWriter("temp", "csv"), NetworkGraph())
    
    # Apply labels - Plot 1: Raw Unicode
    fig.update_yaxes(title_text="Temperature (°C)", row=1, col=1)  # Raw Unicode
    fig.update_xaxes(title_text="Time (days)", row=1, col=1)
    
    # Apply labels - Plot 2: Our formatted version
    temp_label = visualizer._format_axis_label("Temperature (°C)")
    flow_label = visualizer._format_axis_label("Flow (m³/day)")
    fig.update_yaxes(title_text=temp_label, row=2, col=1)
    fig.update_xaxes(title_text="Time (days)", row=2, col=1)
    
    # Apply labels - Plot 3: Comprehensive test
    pressure_label = visualizer._format_axis_label("Pressure (μPa ± 5%)")
    area_label = visualizer._format_axis_label("Area (m² × 10³)")
    fig.update_yaxes(title_text=pressure_label, row=3, col=1)
    fig.update_xaxes(title_text=area_label, row=3, col=1)
    
    # Update layout
    fig.update_layout(
        title="HydroSim Axis Label Character Encoding Test",
        height=800,
        showlegend=True
    )
    
    return fig


def main():
    """Run the visual test."""
    print("🚀 HydroSim Axis Label Visual Test")
    print("=" * 50)
    
    # Create test plot
    fig = create_test_plot()
    
    # Save to HTML
    output_file = "output/axis_label_test.html"
    fig.write_html(output_file)
    
    print(f"✅ Test plot saved to: {output_file}")
    print()
    print("🔍 What to look for:")
    print("  Row 1: May show strange characters (°, ³) if browser doesn't handle Unicode well")
    print("  Row 2: Should show proper degree symbol (°) and superscript (³)")
    print("  Row 3: Should show micro (μ), plus-minus (±), superscript (²), multiplication (×)")
    print()
    print("✅ Expected results:")
    print("  - Temperature (°C) → Temperature (degC)")
    print("  - Flow (m³/day) → Flow (m^3/day)")
    print("  - Pressure (μPa ± 5%) → Pressure (uPa +/- 5%)")
    print("  - Area (m² × 10³) → Area (m^2 x 10^3)")
    print()
    
    # Open in browser
    print("🌐 Opening test plot in browser...")
    webbrowser.open(f'file://{os.path.abspath(output_file)}')
    
    print("=" * 50)
    print("🎯 Visual Verification Steps:")
    print("1. Check that degree symbols (°) display correctly")
    print("2. Check that superscripts (³, ²) display correctly") 
    print("3. Check that Greek letters (μ) display correctly")
    print("4. Check that math symbols (±, ×) display correctly")
    print("5. Compare with any old plots to see the improvement")
    print("=" * 50)


if __name__ == "__main__":
    main()