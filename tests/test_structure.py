"""
Basic tests to verify project structure and imports.
"""

import pytest


def test_imports():
    """Test that all core modules can be imported."""
    import hydrosim
    from hydrosim import nodes
    from hydrosim import links
    from hydrosim import solver
    from hydrosim import climate
    from hydrosim import config
    from hydrosim import strategies
    from hydrosim import controls
    from hydrosim import hydraulics
    
    assert hydrosim.__version__ == "0.1.0"


def test_abstract_classes_exist():
    """Test that all abstract base classes are defined."""
    from hydrosim.nodes import Node
    from hydrosim.strategies import GeneratorStrategy, DemandModel
    from hydrosim.controls import Control
    from hydrosim.hydraulics import HydraulicModel
    from hydrosim.solver import NetworkSolver
    
    # Verify they are abstract
    from abc import ABC
    assert issubclass(Node, ABC)
    assert issubclass(GeneratorStrategy, ABC)
    assert issubclass(DemandModel, ABC)
    assert issubclass(Control, ABC)
    assert issubclass(HydraulicModel, ABC)
    assert issubclass(NetworkSolver, ABC)


def test_data_classes_exist():
    """Test that data classes are defined."""
    from hydrosim.climate import ClimateState, SiteConfig
    from dataclasses import is_dataclass
    
    assert is_dataclass(ClimateState)
    assert is_dataclass(SiteConfig)


def test_concrete_classes_exist():
    """Test that concrete classes are defined."""
    from hydrosim.links import Link
    from hydrosim.config import NetworkGraph
    from hydrosim.simulation import SimulationEngine
    
    # These should be instantiable (though we won't instantiate them here)
    assert Link is not None
    assert NetworkGraph is not None
    assert SimulationEngine is not None
