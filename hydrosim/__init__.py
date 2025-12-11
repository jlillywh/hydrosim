"""
HydroSim: A Python-based water resources planning framework.

This package provides tools for daily timestep simulation of complex,
interconnected water systems.
"""

__version__ = "0.4.0"

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

__all__ = [
    'ClimateState',
    'SiteConfig',
    'ElevationAreaVolume',
    'NetworkGraph',
    'YAMLParser',
    'Node',
    'StorageNode',
    'JunctionNode',
    'SourceNode',
    'DemandNode',
    'Link',
    'ClimateEngine',
    'ClimateSource',
    'TimeSeriesClimateSource',
    'WGENClimateSource',
    'WGENParams',
    'WGENState',
    'WGENOutputs',
    'wgen_step',
    'GeneratorStrategy',
    'DemandModel',
    'TimeSeriesStrategy',
    'HydrologyStrategy',
    'Snow17Model',
    'AWBMModel',
    'MunicipalDemand',
    'AgricultureDemand',
    'Control',
    'FractionalControl',
    'AbsoluteControl',
    'SwitchControl',
    'HydraulicModel',
    'WeirModel',
    'PipeModel',
    'NetworkSolver',
    'LinearProgrammingSolver',
    'SimulationEngine',
    'ResultsWriter',
    'visualize_network',
    'save_network_visualization',
    'ResultsVisualizer',
    'visualize_results',
    'HydroSimError',
    'NegativeStorageError',
    'InfeasibleNetworkError',
    'ClimateDataError',
    'EAVInterpolationError',
    'COST_DEMAND',
    'COST_STORAGE',
    'COST_SPILL',
]
