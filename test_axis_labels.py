#!/usr/bin/env python3
"""
Test script for axis label character encoding fix.

This script tests that special characters in axis labels are properly
converted to HTML entities for correct display in Plotly HTML output.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from hydrosim.results_viz import ResultsVisualizer
from hydrosim import ResultsWriter, NetworkGraph


def test_axis_label_formatting():
    """Test that special characters are properly formatted."""
    
    # Create a dummy visualizer to test the method
    writer = ResultsWriter(output_dir="temp", format="csv")
    network = NetworkGraph()
    visualizer = ResultsVisualizer(writer, network)
    
    # Test cases
    test_cases = [
        # (input, expected_output)
        ("Temperature (°C)", "Temperature (&deg;C)"),
        ("Flow (m³/day)", "Flow (m&sup3;/day)"),
        ("Area (m²)", "Area (m&sup2;)"),
        ("Pressure (μPa)", "Pressure (&micro;Pa)"),
        ("Change (±5%)", "Change (&plusmn;5%)"),
        ("Normal text", "Normal text"),  # Should remain unchanged
        ("", ""),  # Empty string
        ("Multiple °C and m³", "Multiple &deg;C and m&sup3;"),
    ]
    
    print("🧪 Testing axis label formatting...")
    print("=" * 60)
    
    all_passed = True
    
    for i, (input_label, expected) in enumerate(test_cases, 1):
        result = visualizer._format_axis_label(input_label)
        passed = result == expected
        all_passed = all_passed and passed
        
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"Test {i}: {status}")
        print(f"  Input:    '{input_label}'")
        print(f"  Expected: '{expected}'")
        print(f"  Got:      '{result}'")
        print()
    
    print("=" * 60)
    if all_passed:
        print("🎉 All tests passed! Axis label formatting is working correctly.")
        return True
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return False


def test_real_labels():
    """Test with actual labels used in HydroSim."""
    
    writer = ResultsWriter(output_dir="temp", format="csv")
    network = NetworkGraph()
    visualizer = ResultsVisualizer(writer, network)
    
    # Real labels from the codebase
    real_labels = [
        'Temperature (°C)',
        'Precipitation (mm/day)',
        'Runoff (m³/day)',
        'Storage (m³)',
        'Flow (m³/day)',
    ]
    
    print("🔍 Testing real HydroSim axis labels...")
    print("=" * 60)
    
    for label in real_labels:
        formatted = visualizer._format_axis_label(label)
        print(f"Original: '{label}'")
        print(f"Formatted: '{formatted}'")
        print()
    
    print("=" * 60)
    print("✅ Real label formatting complete!")


if __name__ == "__main__":
    print("🚀 Axis Label Character Encoding Test")
    print("=" * 60)
    print()
    
    # Run tests
    success = test_axis_label_formatting()
    print()
    test_real_labels()
    
    if success:
        print("\n🎉 Issue #3 fix is working correctly!")
        print("Special characters in axis labels will now display properly in HTML plots.")
    else:
        print("\n❌ Tests failed. The fix needs more work.")
        sys.exit(1)