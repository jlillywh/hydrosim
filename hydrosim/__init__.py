"""
HydroSim: A Python-based water resources planning framework.

This package provides tools for daily timestep simulation of complex,
interconnected water systems including:

• Network-based modeling with nodes (storage, demand, source, junction) and links
• Climate data integration with time series and weather generator support  
• Optimization-based water allocation using linear programming
• Comprehensive results analysis and visualization tools
• YAML-based configuration for easy model setup

Quick Start:
    >>> import hydrosim as hs
    >>> hs.help()  # Display comprehensive help
    >>> hs.quick_start()  # Interactive tutorial for beginners
    >>> hs.examples()  # Show working code examples
    >>> hs.docs()  # Open documentation

Main Components:
    - Nodes & Links: StorageNode, DemandNode, SourceNode, JunctionNode, Link
    - Climate: ClimateEngine, WGENClimateSource, TimeSeriesClimateSource  
    - Strategies: HydrologyStrategy, DemandModel, GeneratorStrategy
    - Simulation: SimulationEngine, NetworkSolver
    - Results: ResultsWriter, ResultsVisualizer
    - Configuration: YAMLParser, NetworkGraph
"""

__version__ = "0.4.3"

from hydrosim.climate import ClimateState, SiteConfig
from hydrosim.config import ElevationAreaVolume, NetworkGraph, YAMLParser
from hydrosim.nodes import Node, StorageNode, JunctionNode, SourceNode, DemandNode
from hydrosim.links import Link
from hydrosim.climate_engine import ClimateEngine
from hydrosim.climate_sources import ClimateSource, TimeSeriesClimateSource, WGENClimateSource
from hydrosim.wgen import WGENParams, WGENState, WGENOutputs, wgen_step
from hydrosim.strategies import (
    GeneratorStrategy, 
    DemandModel,
    TimeSeriesStrategy,
    HydrologyStrategy,
    Snow17Model,
    AWBMModel,
    MunicipalDemand,
    AgricultureDemand,
)
from hydrosim.controls import Control, FractionalControl, AbsoluteControl, SwitchControl
from hydrosim.hydraulics import HydraulicModel, WeirModel, PipeModel
from hydrosim.solver import NetworkSolver, LinearProgrammingSolver, COST_DEMAND, COST_STORAGE, COST_SPILL
from hydrosim.simulation import SimulationEngine
from hydrosim.results import ResultsWriter
from hydrosim.visualization import visualize_network, save_network_visualization
from hydrosim.results_viz import ResultsVisualizer, visualize_results
from hydrosim.exceptions import (
    HydroSimError,
    NegativeStorageError,
    InfeasibleNetworkError,
    ClimateDataError,
    EAVInterpolationError,
)
from hydrosim.help import help, about, docs, examples, quick_start, download_examples

__all__ = [
    # Help and documentation functions
    'help',
    'about', 
    'docs',
    'examples',
    'quick_start',
    'download_examples',

    # Examples management
    'get_examples',
    'create_starter_project',
    # Core data structures
    'ClimateState',
    'SiteConfig',
    'ElevationAreaVolume',
    'NetworkGraph',
    'YAMLParser',
    # Network components
    'Node',
    'StorageNode',
    'JunctionNode',
    'SourceNode',
    'DemandNode',
    'Link',
    # Climate system
    'ClimateEngine',
    'ClimateSource',
    'TimeSeriesClimateSource',
    'WGENClimateSource',
    'WGENParams',
    'WGENState',
    'WGENOutputs',
    'wgen_step',
    # Strategies and models
    'GeneratorStrategy',
    'DemandModel',
    'TimeSeriesStrategy',
    'HydrologyStrategy',
    'Snow17Model',
    'AWBMModel',
    'MunicipalDemand',
    'AgricultureDemand',
    # Controls and hydraulics
    'Control',
    'FractionalControl',
    'AbsoluteControl',
    'SwitchControl',
    'HydraulicModel',
    'WeirModel',
    'PipeModel',
    # Simulation and solving
    'NetworkSolver',
    'LinearProgrammingSolver',
    'SimulationEngine',
    # Results and visualization
    'ResultsWriter',
    'visualize_network',
    'save_network_visualization',
    'ResultsVisualizer',
    'visualize_results',
    # Exceptions
    'HydroSimError',
    'NegativeStorageError',
    'InfeasibleNetworkError',
    'ClimateDataError',
    'EAVInterpolationError',
    # Cost constants
    'COST_DEMAND',
    'COST_STORAGE',
    'COST_SPILL',
]
