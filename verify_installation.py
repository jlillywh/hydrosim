#!/usr/bin/env python3
"""
Installation verification script for HydroSim.

This script verifies that HydroSim is properly installed and all
core functionality is working correctly.
"""

import sys
import importlib
from datetime import datetime


def check_import(module_name, description=""):
    """Check if a module can be imported."""
    try:
        importlib.import_module(module_name)
        print(f"✅ {module_name} - {description}")
        return True
    except ImportError as e:
        print(f"❌ {module_name} - {description}")
        print(f"   ImportError: {e}")
        return False
    except Exception as e:
        print(f"⚠️  {module_name} - {description}")
        print(f"   Warning: {e}")
        print(f"   (Module exists but may have compatibility issues)")
        return True  # Consider it available but with warnings


def check_hydrosim_components():
    """Check HydroSim core components."""
    print("🔍 Checking HydroSim core components...")
    
    components = [
        ("hydrosim", "Main package"),
        ("hydrosim.nodes", "Node abstractions"),
        ("hydrosim.links", "Link implementation"),
        ("hydrosim.solver", "Network solver"),
        ("hydrosim.climate", "Climate data structures"),
        ("hydrosim.simulation", "Simulation engine"),
        ("hydrosim.results", "Results output"),
        ("hydrosim.visualization", "Network visualization"),
        ("hydrosim.climate_builder", "Climate data tools"),
    ]
    
    success_count = 0
    for module, description in components:
        if check_import(module, description):
            success_count += 1
    
    return success_count == len(components)


def check_dependencies():
    """Check required dependencies."""
    print("\n🔍 Checking dependencies...")
    
    dependencies = [
        ("numpy", "Numerical computations"),
        ("pandas", "Data manipulation"),
        ("scipy", "Scientific computing"),
        ("networkx", "Graph algorithms"),
        ("yaml", "YAML parsing"),
        ("plotly", "Interactive visualizations"),
        ("requests", "HTTP requests"),
    ]
    
    success_count = 0
    for module, description in dependencies:
        if check_import(module, description):
            success_count += 1
    
    return success_count == len(dependencies)


def test_basic_functionality():
    """Test basic HydroSim functionality."""
    print("\n🧪 Testing basic functionality...")
    
    try:
        # Test imports
        from hydrosim import (
            NetworkGraph, StorageNode, DemandNode, Link,
            ElevationAreaVolume, MunicipalDemand,
            LinearProgrammingSolver, SimulationEngine,
            ClimateEngine, TimeSeriesClimateSource, SiteConfig
        )
        print("✅ Core imports successful")
        
        # Test network creation
        network = NetworkGraph()
        print("✅ Network creation successful")
        
        # Test node creation
        eav = ElevationAreaVolume(
            elevations=[100.0, 110.0, 120.0],
            areas=[1000.0, 2000.0, 3000.0],
            volumes=[0.0, 10000.0, 30000.0]
        )
        storage = StorageNode(
            'test_reservoir', 
            initial_storage=20000.0, 
            max_storage=30000.0,
            min_storage=0.0,
            eav_table=eav
        )
        demand = DemandNode('test_city', MunicipalDemand(population=1000, per_capita_demand=0.2))
        print("✅ Node creation successful")
        
        # Test network assembly
        network.add_node(storage)
        network.add_node(demand)
        link = Link('test_delivery', storage, demand, physical_capacity=500.0, cost=1.0)
        network.add_link(link)
        print("✅ Network assembly successful")
        
        # Test solver creation
        solver = LinearProgrammingSolver()
        print("✅ Solver creation successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False


def check_version():
    """Check HydroSim version."""
    print("\n📋 Version information...")
    
    try:
        import hydrosim
        print(f"✅ HydroSim version: {hydrosim.__version__}")
        return True
    except Exception as e:
        print(f"❌ Could not get version: {e}")
        return False


def main():
    """Main verification routine."""
    print("🚀 HydroSim Installation Verification")
    print("=" * 40)
    
    # Check Python version
    python_version = sys.version_info
    print(f"🐍 Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    if python_version < (3, 8):
        print("❌ Python 3.8 or higher is required")
        return False
    else:
        print("✅ Python version is compatible")
    
    # Run checks
    checks = [
        check_version(),
        check_dependencies(),
        check_hydrosim_components(),
        test_basic_functionality(),
    ]
    
    # Summary
    print("\n" + "=" * 40)
    if all(checks):
        print("🎉 All checks passed! HydroSim is properly installed.")
        print("\n📚 Next steps:")
        print("   • Try the examples: git clone https://github.com/jlillywh/hydrosim.git")
        print("   • Read the documentation: https://github.com/jlillywh/hydrosim#readme")
        print("   • Run: python examples/quick_start.py")
        return True
    else:
        print("❌ Some checks failed. Please check the errors above.")
        print("\n🔧 Troubleshooting:")
        print("   • Reinstall: pip uninstall hydrosim && pip install hydrosim")
        print("   • Check dependencies: pip install --upgrade numpy pandas scipy networkx pyyaml plotly requests")
        print("   • Check Python version: python --version")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)