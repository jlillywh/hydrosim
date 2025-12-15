"""
Configuration parsing and network construction.

This module handles YAML configuration parsing and network graph construction,
providing a declarative way to define complex water networks. It supports
all node types, link configurations, climate sources, and control strategies.

Example:
    >>> import hydrosim as hs
    >>> 
    >>> # Load network from YAML configuration
    >>> network = hs.YAMLParser.load_network('my_network.yaml')
    >>> 
    >>> # Inspect loaded network
    >>> print(f"Nodes: {len(network.nodes)}")
    >>> print(f"Links: {len(network.links)}")
    >>> 
    >>> # Access specific nodes
    >>> reservoir = network.get_node('reservoir')
    >>> print(f"Capacity: {reservoir.capacity}")

YAML Configuration Structure:
    nodes:
      - id: reservoir
        type: storage
        capacity: 1000
        initial_storage: 500
      - id: city
        type: demand
        demand_strategy:
          type: municipal
          base_demand: 50
    
    links:
      - id: pipeline
        source: reservoir
        target: city
        capacity: 100
        cost: 0.01

The YAMLParser automatically creates appropriate node and link objects
with all specified parameters and strategies.
"""

from typing import Dict, List, Any, Optional
import numpy as np
import yaml
import pandas as pd
import logging
from pathlib import Path
from hydrosim.nodes import Node, StorageNode, JunctionNode, SourceNode, DemandNode
from hydrosim.links import Link
from hydrosim.climate import SiteConfig
from hydrosim.solver import COST_DEMAND, COST_STORAGE, COST_SPILL
from hydrosim.climate_sources import ClimateSource, TimeSeriesClimateSource, WGENClimateSource
from hydrosim.strategies import (
    TimeSeriesStrategy, HydrologyStrategy, AWBMGeneratorStrategy,
    MunicipalDemand, AgricultureDemand
)
from hydrosim.controls import FractionalControl, AbsoluteControl, SwitchControl
from hydrosim.hydraulics import WeirModel, PipeModel
from hydrosim.wgen import WGENParams
from hydrosim.exceptions import EAVInterpolationError
from datetime import datetime

# Configure logger
logger = logging.getLogger(__name__)


class ElevationAreaVolume:
    """Interpolation table for storage properties."""
    
    def __init__(self, elevations: List[float], areas: List[float], 
                 volumes: List[float], node_id: str = None,
                 extrapolate: bool = True, warn_threshold: float = 0.95):
        """
        Initialize elevation-area-volume table.
        
        Args:
            elevations: List of elevation values (must be monotonic)
            areas: List of surface area values corresponding to elevations
            volumes: List of storage volume values corresponding to elevations
            node_id: Optional node identifier for error messages
            extrapolate: If True, extrapolate beyond table bounds; if False, raise error
            warn_threshold: Fraction of table range at which to issue warnings (0.0-1.0)
        """
        self.elevations = np.array(elevations)
        self.areas = np.array(areas)
        self.volumes = np.array(volumes)
        self.node_id = node_id or "unknown"
        self.extrapolate = extrapolate
        self.warn_threshold = warn_threshold
        
        # Store bounds for checking
        self.min_volume = float(np.min(self.volumes))
        self.max_volume = float(np.max(self.volumes))
        
        # Calculate warning thresholds
        volume_range = self.max_volume - self.min_volume
        self.lower_warn_threshold = self.min_volume + (1 - warn_threshold) * volume_range
        self.upper_warn_threshold = self.max_volume - (1 - warn_threshold) * volume_range
    
    def _check_bounds(self, storage: float, interpolation_type: str) -> None:
        """
        Check if storage is within or near table bounds and issue warnings/errors.
        
        Args:
            storage: Storage volume to check
            interpolation_type: Type of interpolation for error messages
            
        Raises:
            EAVInterpolationError: If storage is out of bounds and extrapolate=False
        """
        # Check if out of bounds
        if storage < self.min_volume or storage > self.max_volume:
            if not self.extrapolate:
                raise EAVInterpolationError(
                    self.node_id, storage, 
                    self.min_volume, self.max_volume,
                    interpolation_type
                )
            else:
                # Log warning about extrapolation
                if storage < self.min_volume:
                    distance = self.min_volume - storage
                    logger.warning(
                        f"Storage node '{self.node_id}': Extrapolating {interpolation_type} "
                        f"below table minimum. Storage: {storage:.2f}, "
                        f"Table min: {self.min_volume:.2f}, Distance: {distance:.2f}"
                    )
                else:
                    distance = storage - self.max_volume
                    logger.warning(
                        f"Storage node '{self.node_id}': Extrapolating {interpolation_type} "
                        f"above table maximum. Storage: {storage:.2f}, "
                        f"Table max: {self.max_volume:.2f}, Distance: {distance:.2f}"
                    )
        
        # Check if approaching bounds (within warning threshold)
        elif storage < self.lower_warn_threshold:
            distance = storage - self.min_volume
            logger.info(
                f"Storage node '{self.node_id}': Approaching lower table boundary. "
                f"Storage: {storage:.2f}, Table min: {self.min_volume:.2f}, "
                f"Distance from minimum: {distance:.2f}"
            )
        elif storage > self.upper_warn_threshold:
            distance = self.max_volume - storage
            logger.info(
                f"Storage node '{self.node_id}': Approaching upper table boundary. "
                f"Storage: {storage:.2f}, Table max: {self.max_volume:.2f}, "
                f"Distance from maximum: {distance:.2f}"
            )
    
    def storage_to_elevation(self, storage: float) -> float:
        """
        Interpolate elevation from storage volume.
        
        Args:
            storage: Storage volume
            
        Returns:
            Interpolated elevation
            
        Raises:
            EAVInterpolationError: If storage is out of bounds and extrapolate=False
        """
        self._check_bounds(storage, "elevation")
        return float(np.interp(storage, self.volumes, self.elevations))
    
    def storage_to_area(self, storage: float) -> float:
        """
        Interpolate surface area from storage volume.
        
        Args:
            storage: Storage volume
            
        Returns:
            Interpolated surface area
            
        Raises:
            EAVInterpolationError: If storage is out of bounds and extrapolate=False
        """
        self._check_bounds(storage, "area")
        return float(np.interp(storage, self.volumes, self.areas))


class NetworkGraph:
    """Directed graph representation of the water network."""
    
    def __init__(self, model_name: Optional[str] = None, author: Optional[str] = None):
        """
        Initialize an empty network graph.
        
        Args:
            model_name: Optional name/title for the model
            author: Optional author name
        """
        self.nodes: Dict[str, Node] = {}
        self.links: Dict[str, Link] = {}
        self.model_name = model_name
        self.author = author
    
    def add_node(self, node: Node) -> None:
        """
        Add a node to the network.
        
        Args:
            node: Node to add
        """
        self.nodes[node.node_id] = node
    
    def add_link(self, link: Link) -> None:
        """
        Add a link to the network and update node connections.
        
        Args:
            link: Link to add
        """
        self.links[link.link_id] = link
        link.source.outflows.append(link)
        link.target.inflows.append(link)
    
    def validate(self) -> List[str]:
        """
        Validate network topology.
        
        Virtual components (virtual_sink nodes and carryover links) are excluded
        from validation as they are temporary constructs used only during solver
        execution.
        
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        # Check all links reference existing nodes (skip virtual carryover links)
        for link_id, link in self.links.items():
            # Skip virtual carryover links
            if link_id.endswith("_carryover"):
                continue
            
            if link.source.node_id not in self.nodes:
                errors.append(
                    f"Link '{link_id}' references non-existent source node '{link.source.node_id}'"
                )
            if link.target.node_id not in self.nodes:
                errors.append(
                    f"Link '{link_id}' references non-existent target node '{link.target.node_id}'"
                )
        
        # Check for orphaned nodes (nodes with no connections)
        for node_id, node in self.nodes.items():
            # Skip virtual sink nodes
            if hasattr(node, 'node_type') and node.node_type == "virtual_sink":
                continue
            
            if len(node.inflows) == 0 and len(node.outflows) == 0:
                # Source and demand nodes can be orphaned (terminal nodes)
                if node.node_type not in ["source", "demand"]:
                    errors.append(
                        f"Node '{node_id}' (type: {node.node_type}) has no connections. "
                        f"All junction and storage nodes must have at least one connection."
                    )
        
        # Validate control parameters on links (skip virtual carryover links)
        for link_id, link in self.links.items():
            # Skip virtual carryover links
            if link_id.endswith("_carryover"):
                continue
            
            if link.control is not None:
                control_errors = self._validate_control(link_id, link.control)
                errors.extend(control_errors)
        
        return errors
    
    def _validate_control(self, link_id: str, control) -> List[str]:
        """
        Validate control parameters.
        
        Args:
            link_id: Link identifier for error messages
            control: Control object to validate
            
        Returns:
            List of validation error messages
        """
        from hydrosim.controls import FractionalControl, AbsoluteControl
        
        errors = []
        
        if isinstance(control, FractionalControl):
            if not (0.0 <= control.fraction <= 1.0):
                errors.append(
                    f"Link '{link_id}' has invalid fractional control: "
                    f"fraction must be between 0.0 and 1.0, got {control.fraction}"
                )
        
        elif isinstance(control, AbsoluteControl):
            if control.max_flow < 0.0:
                errors.append(
                    f"Link '{link_id}' has invalid absolute control: "
                    f"max_flow must be non-negative, got {control.max_flow}"
                )
        
        return errors
    
    def export_graphml(self, filepath: str) -> None:
        """
        Export network graph to GraphML format.
        
        GraphML is an XML-based format for graphs that can be read by
        visualization tools like Gephi, yEd, and Cytoscape.
        
        Args:
            filepath: Path to output GraphML file
        """
        from xml.etree import ElementTree as ET
        from xml.dom import minidom
        
        # Create root element
        graphml = ET.Element('graphml', {
            'xmlns': 'http://graphml.graphdrawing.org/xmlns',
            'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
            'xsi:schemaLocation': 'http://graphml.graphdrawing.org/xmlns '
                                 'http://graphml.graphdrawing.org/xmlns/1.0/graphml.xsd'
        })
        
        # Define node attributes
        ET.SubElement(graphml, 'key', {
            'id': 'd0',
            'for': 'node',
            'attr.name': 'node_type',
            'attr.type': 'string'
        })
        
        ET.SubElement(graphml, 'key', {
            'id': 'd1',
            'for': 'node',
            'attr.name': 'initial_storage',
            'attr.type': 'double'
        })
        
        # Define edge attributes
        ET.SubElement(graphml, 'key', {
            'id': 'd2',
            'for': 'edge',
            'attr.name': 'capacity',
            'attr.type': 'double'
        })
        
        ET.SubElement(graphml, 'key', {
            'id': 'd3',
            'for': 'edge',
            'attr.name': 'cost',
            'attr.type': 'double'
        })
        
        ET.SubElement(graphml, 'key', {
            'id': 'd4',
            'for': 'edge',
            'attr.name': 'control_type',
            'attr.type': 'string'
        })
        
        ET.SubElement(graphml, 'key', {
            'id': 'd5',
            'for': 'edge',
            'attr.name': 'hydraulic_type',
            'attr.type': 'string'
        })
        
        # Create graph element
        graph = ET.SubElement(graphml, 'graph', {
            'id': 'G',
            'edgedefault': 'directed'
        })
        
        # Add nodes
        for node_id, node in self.nodes.items():
            node_elem = ET.SubElement(graph, 'node', {'id': node_id})
            
            # Add node type
            data_type = ET.SubElement(node_elem, 'data', {'key': 'd0'})
            data_type.text = node.node_type
            
            # Add storage-specific attributes
            if hasattr(node, 'initial_storage'):
                data_storage = ET.SubElement(node_elem, 'data', {'key': 'd1'})
                data_storage.text = str(node.initial_storage)
        
        # Add edges (links)
        for link_id, link in self.links.items():
            edge_elem = ET.SubElement(graph, 'edge', {
                'id': link_id,
                'source': link.source.node_id,
                'target': link.target.node_id
            })
            
            # Add capacity
            data_capacity = ET.SubElement(edge_elem, 'data', {'key': 'd2'})
            data_capacity.text = str(link.physical_capacity)
            
            # Add cost
            data_cost = ET.SubElement(edge_elem, 'data', {'key': 'd3'})
            data_cost.text = str(link.cost)
            
            # Add control type if present
            if link.control is not None:
                data_control = ET.SubElement(edge_elem, 'data', {'key': 'd4'})
                data_control.text = type(link.control).__name__
            
            # Add hydraulic type if present
            if link.hydraulic_model is not None:
                data_hydraulic = ET.SubElement(edge_elem, 'data', {'key': 'd5'})
                data_hydraulic.text = type(link.hydraulic_model).__name__
        
        # Pretty print and write to file
        xml_str = minidom.parseString(
            ET.tostring(graphml, encoding='unicode')
        ).toprettyxml(indent='  ')
        
        with open(filepath, 'w') as f:
            f.write(xml_str)
    
    def export_dot(self, filepath: str) -> None:
        """
        Export network graph to DOT format.
        
        DOT is a graph description language used by Graphviz for
        graph visualization and layout.
        
        Args:
            filepath: Path to output DOT file
        """
        lines = ['digraph HydroSim {']
        lines.append('  rankdir=LR;')  # Left to right layout
        lines.append('  node [shape=box];')
        lines.append('')
        
        # Add nodes with attributes
        for node_id, node in self.nodes.items():
            # Escape node_id for DOT format
            safe_id = node_id.replace('-', '_').replace(' ', '_')
            
            # Build label with node type and properties
            label_parts = [f"{node_id}"]
            label_parts.append(f"Type: {node.node_type}")
            
            # Add type-specific properties
            if node.node_type == 'storage' and hasattr(node, 'initial_storage'):
                label_parts.append(f"Storage: {node.initial_storage:.2f}")
            
            label = '\\n'.join(label_parts)
            
            # Set node color based on type
            color_map = {
                'storage': 'lightblue',
                'junction': 'lightgray',
                'source': 'lightgreen',
                'demand': 'lightyellow'
            }
            color = color_map.get(node.node_type, 'white')
            
            lines.append(
                f'  "{safe_id}" [label="{label}", style=filled, fillcolor={color}];'
            )
        
        lines.append('')
        
        # Add edges (links) with attributes
        for link_id, link in self.links.items():
            source_id = link.source.node_id.replace('-', '_').replace(' ', '_')
            target_id = link.target.node_id.replace('-', '_').replace(' ', '_')
            
            # Build label with link properties
            label_parts = [link_id]
            
            if link.physical_capacity != float('inf'):
                label_parts.append(f"Cap: {link.physical_capacity:.2f}")
            
            label_parts.append(f"Cost: {link.cost:.2f}")
            
            if link.control is not None:
                label_parts.append(f"Ctrl: {type(link.control).__name__}")
            
            if link.hydraulic_model is not None:
                label_parts.append(f"Hyd: {type(link.hydraulic_model).__name__}")
            
            label = '\\n'.join(label_parts)
            
            lines.append(
                f'  "{source_id}" -> "{target_id}" [label="{label}"];'
            )
        
        lines.append('}')
        
        with open(filepath, 'w') as f:
            f.write('\n'.join(lines))


class YAMLParser:
    """Parser for YAML configuration files."""
    
    def __init__(self, config_path: str):
        """
        Initialize YAML parser.
        
        Args:
            config_path: Path to YAML configuration file
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If YAML syntax is invalid
        """
        self.config_path = Path(config_path)
        self.config_dir = self.config_path.parent
        
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Invalid YAML syntax in {config_path}: {e}")
        
        if self.config is None:
            raise ValueError(f"Empty configuration file: {config_path}")
    
    def parse(self) -> tuple[NetworkGraph, ClimateSource, SiteConfig]:
        """
        Parse the complete configuration and construct network.
        
        Returns:
            Tuple of (NetworkGraph, ClimateSource, SiteConfig)
            
        Raises:
            ValueError: If configuration is invalid
        """
        # Validate configuration structure
        self._validate_configuration()
        
        # Parse climate configuration first (needed for some strategies)
        climate_source, site_config = self._parse_climate_config()
        
        # Parse optional metadata
        model_name = self.config.get('model_name')
        author = self.config.get('author')
        viz_config = self.config.get('visualization')
        
        # Parse simulation configuration
        sim_config = self._parse_simulation_config()
        
        # Parse optimization configuration
        opt_config = self._parse_optimization_config()
        
        # Create network graph
        network = NetworkGraph(model_name=model_name, author=author)
        network.viz_config = viz_config
        network.sim_config = sim_config
        network.opt_config = opt_config
        
        # Parse and add nodes
        nodes_config = self.config.get('nodes', {})
        if not nodes_config:
            raise ValueError("Configuration must include 'nodes' section")
        
        for node_id, node_params in nodes_config.items():
            node = self._parse_node(node_id, node_params)
            network.add_node(node)
        
        # Parse and add links
        links_config = self.config.get('links', {})
        if not links_config:
            raise ValueError("Configuration must include 'links' section")
        
        for link_id, link_params in links_config.items():
            link = self._parse_link(link_id, link_params, network.nodes)
            network.add_link(link)
        
        # Validate network topology
        errors = network.validate()
        if errors:
            raise ValueError(f"Network validation failed:\n" + "\n".join(errors))
        
        return network, climate_source, site_config
    
    def _validate_configuration(self) -> None:
        """
        Validate configuration structure and parameters.
        
        Raises:
            ValueError: If configuration contains invalid parameters
        """
        errors = []
        
        # Check for sub-daily timestep configuration (not supported)
        if 'timestep' in self.config:
            timestep_config = self.config['timestep']
            
            # Check if timestep is specified
            if isinstance(timestep_config, dict):
                unit = timestep_config.get('unit', 'day')
                if unit != 'day':
                    errors.append(
                        f"Invalid timestep configuration: HydroSim only supports daily timesteps. "
                        f"Found timestep unit '{unit}'. Please remove the timestep configuration "
                        f"or set unit to 'day'."
                    )
                
                # Check for duration/interval that's not 1 day
                duration = timestep_config.get('duration', 1)
                if duration != 1:
                    errors.append(
                        f"Invalid timestep configuration: HydroSim only supports 1-day timesteps. "
                        f"Found duration {duration}. Please set duration to 1 or remove the timestep configuration."
                    )
            
            elif isinstance(timestep_config, str):
                # If timestep is a string like "1h", "6h", etc.
                if timestep_config not in ['1d', '1day', 'day', 'daily']:
                    errors.append(
                        f"Invalid timestep configuration: HydroSim only supports daily timesteps. "
                        f"Found timestep '{timestep_config}'. Please use '1d', 'day', or 'daily', "
                        f"or remove the timestep configuration."
                    )
        
        if errors:
            raise ValueError("Configuration validation failed:\n" + "\n".join(errors))
    
    def _parse_climate_config(self) -> tuple[ClimateSource, SiteConfig]:
        """
        Parse climate configuration section.
        
        Returns:
            Tuple of (ClimateSource, SiteConfig)
            
        Raises:
            ValueError: If climate configuration is invalid
        """
        climate_config = self.config.get('climate', {})
        if not climate_config:
            raise ValueError("Configuration must include 'climate' section")
        
        # Parse site configuration
        site_params = climate_config.get('site', {})
        if not site_params:
            raise ValueError("Climate configuration must include 'site' parameters")
        
        try:
            site_config = SiteConfig(
                latitude=float(site_params['latitude']),
                elevation=float(site_params['elevation'])
            )
        except KeyError as e:
            raise ValueError(f"Missing required site parameter: {e}")
        
        # Parse climate source
        source_type = climate_config.get('source_type')
        if not source_type:
            raise ValueError("Climate configuration must include 'source_type'")
        
        if source_type == 'timeseries':
            climate_source = self._parse_timeseries_climate(climate_config)
        elif source_type == 'wgen':
            climate_source = self._parse_wgen_climate(climate_config)
        else:
            raise ValueError(f"Unknown climate source type: {source_type}")
        
        return climate_source, site_config
    
    def _parse_timeseries_climate(self, climate_config: Dict[str, Any]) -> TimeSeriesClimateSource:
        """
        Parse time series climate source configuration.
        
        Args:
            climate_config: Climate configuration dictionary
            
        Returns:
            TimeSeriesClimateSource instance
        """
        filepath = climate_config.get('filepath')
        if not filepath:
            raise ValueError("Time series climate source requires 'filepath'")
        
        # Resolve relative paths
        if not Path(filepath).is_absolute():
            filepath = self.config_dir / filepath
        
        # Get column names (with defaults)
        date_col = climate_config.get('date_col', 'date')
        precip_col = climate_config.get('precip_col', 'precip')
        tmax_col = climate_config.get('tmax_col', 't_max')
        tmin_col = climate_config.get('tmin_col', 't_min')
        solar_col = climate_config.get('solar_col', 'solar')
        
        try:
            return TimeSeriesClimateSource.from_csv(
                str(filepath),
                date_col=date_col,
                precip_col=precip_col,
                tmax_col=tmax_col,
                tmin_col=tmin_col,
                solar_col=solar_col
            )
        except Exception as e:
            raise ValueError(f"Failed to load climate time series from {filepath}: {e}")
    
    def _parse_wgen_climate(self, climate_config: Dict[str, Any]) -> WGENClimateSource:
        """
        Parse WGEN climate source configuration.
        
        Supports two parameter specification methods:
        1. Inline YAML: wgen_params dictionary with all 62 parameters
        2. CSV file: wgen_params_file string pointing to CSV parameter file
        
        The CSV method is recommended for managing the 62 WGEN parameters more easily.
        CSV files can be created using CSVWGENParamsParser.create_template().
        
        Example YAML (CSV method):
            climate:
              source_type: wgen
              start_date: "2024-01-01"
              wgen_params_file: wgen_params.csv  # Relative to YAML file
              site:
                latitude: 45.0
                elevation: 1000.0
        
        Example YAML (inline method):
            climate:
              source_type: wgen
              start_date: "2024-01-01"
              wgen_params:
                pww: [0.45, 0.42, ..., 0.48]  # 12 monthly values
                pwd: [0.25, 0.23, ..., 0.27]  # 12 monthly values
                alpha: [1.2, 1.1, ..., 1.3]   # 12 monthly values
                beta: [8.5, 7.8, ..., 9.2]    # 12 monthly values
                txmd: 20.0
                atx: 10.0
                # ... (9 temperature parameters)
                rmd: 15.0
                ar: 5.0
                rmw: 12.0
                latitude: 45.0
                random_seed: 42
              site:
                latitude: 45.0
                elevation: 1000.0
        
        Args:
            climate_config: Climate configuration dictionary from YAML
            
        Returns:
            WGENClimateSource instance with validated parameters
            
        Raises:
            ValueError: If configuration is invalid (missing parameters, both methods
                       specified, neither method specified, invalid parameter values)
            FileNotFoundError: If CSV file doesn't exist (via CSVWGENParamsParser)
        
        See Also:
            hydrosim.wgen_params.CSVWGENParamsParser: CSV parameter loading
            hydrosim.wgen.WGENParams: Parameter validation and structure
            examples/wgen_params_template.csv: Template CSV file
            README.md: Complete WGEN parameter documentation
        """
        # Check for parameter specification
        has_inline = 'wgen_params' in climate_config
        has_csv = 'wgen_params_file' in climate_config
        
        # Validate mutually exclusive options
        if has_inline and has_csv:
            raise ValueError(
                "Cannot specify both 'wgen_params' and 'wgen_params_file'. "
                "Use one method to provide WGEN parameters."
            )
        
        if not has_inline and not has_csv:
            raise ValueError(
                "WGEN climate source requires either 'wgen_params' (inline) "
                "or 'wgen_params_file' (CSV file path)."
            )
        
        # Load parameters from appropriate source
        if has_inline:
            # Existing inline parsing logic
            wgen_params = climate_config['wgen_params']
            try:
                params = WGENParams(**wgen_params)
            except TypeError as e:
                raise ValueError(f"Invalid WGEN parameters: {e}")
        else:
            # New CSV file parsing logic
            csv_path = climate_config['wgen_params_file']
            
            # Resolve relative paths
            if not Path(csv_path).is_absolute():
                csv_path = self.config_dir / csv_path
            
            # Parse CSV file
            from hydrosim.wgen_params import CSVWGENParamsParser
            params = CSVWGENParamsParser.parse(str(csv_path))
        
        # Parse start_date (common to both methods)
        start_date_str = climate_config.get('start_date')
        if not start_date_str:
            raise ValueError("WGEN climate source requires 'start_date'")
        
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        except ValueError:
            raise ValueError(f"Invalid start_date format: {start_date_str}. Expected YYYY-MM-DD")
        
        return WGENClimateSource(params, start_date)
    
    def _parse_node(self, node_id: str, node_params: Dict[str, Any]) -> Node:
        """
        Parse a node definition.
        
        Args:
            node_id: Node identifier
            node_params: Node parameters dictionary
            
        Returns:
            Node instance
            
        Raises:
            ValueError: If node configuration is invalid
        """
        node_type = node_params.get('type')
        if not node_type:
            raise ValueError(f"Node {node_id} must specify 'type'")
        
        if node_type == 'storage':
            return self._parse_storage_node(node_id, node_params)
        elif node_type == 'junction':
            return self._parse_junction_node(node_id, node_params)
        elif node_type == 'source':
            return self._parse_source_node(node_id, node_params)
        elif node_type == 'demand':
            return self._parse_demand_node(node_id, node_params)
        else:
            raise ValueError(f"Unknown node type for {node_id}: {node_type}")
    
    def _parse_storage_node(self, node_id: str, node_params: Dict[str, Any]) -> StorageNode:
        """Parse storage node configuration."""
        try:
            initial_storage = float(node_params['initial_storage'])
        except KeyError:
            raise ValueError(f"StorageNode {node_id} requires 'initial_storage'")
        
        try:
            max_storage = float(node_params['max_storage'])
        except KeyError:
            raise ValueError(f"StorageNode {node_id} requires 'max_storage'")
        
        eav_params = node_params.get('eav_table')
        if not eav_params:
            raise ValueError(f"StorageNode {node_id} requires 'eav_table'")
        
        try:
            # Get optional EAV configuration
            extrapolate = eav_params.get('extrapolate', True)
            warn_threshold = eav_params.get('warn_threshold', 0.95)
            
            eav_table = ElevationAreaVolume(
                elevations=eav_params['elevations'],
                areas=eav_params['areas'],
                volumes=eav_params['volumes'],
                node_id=node_id,
                extrapolate=extrapolate,
                warn_threshold=warn_threshold
            )
        except KeyError as e:
            raise ValueError(f"StorageNode {node_id} EAV table missing parameter: {e}")
        
        # Get optional storage node configuration
        min_storage = float(node_params.get('min_storage', 0.0))
        allow_negative = node_params.get('allow_negative', False)
        low_storage_threshold = node_params.get('low_storage_threshold', 0.1)
        
        return StorageNode(
            node_id, 
            initial_storage, 
            eav_table,
            max_storage=max_storage,
            min_storage=min_storage,
            allow_negative=allow_negative,
            low_storage_threshold=low_storage_threshold
        )
    
    def _parse_junction_node(self, node_id: str, node_params: Dict[str, Any]) -> JunctionNode:
        """Parse junction node configuration."""
        return JunctionNode(node_id)
    
    def _parse_source_node(self, node_id: str, node_params: Dict[str, Any]) -> SourceNode:
        """Parse source node configuration."""
        strategy_type = node_params.get('strategy')
        if not strategy_type:
            raise ValueError(f"SourceNode {node_id} requires 'strategy'")
        
        if strategy_type == 'timeseries':
            strategy = self._parse_timeseries_strategy(node_id, node_params)
        elif strategy_type == 'hydrology':
            strategy = self._parse_hydrology_strategy(node_id, node_params)
        elif strategy_type == 'awbm':
            strategy = self._parse_awbm_strategy(node_id, node_params)
        else:
            raise ValueError(f"Unknown generator strategy for {node_id}: {strategy_type}")
        
        return SourceNode(node_id, strategy)
    
    def _parse_timeseries_strategy(self, node_id: str, node_params: Dict[str, Any]) -> TimeSeriesStrategy:
        """Parse time series generator strategy."""
        filepath = node_params.get('filepath')
        if not filepath:
            raise ValueError(f"TimeSeriesStrategy for {node_id} requires 'filepath'")
        
        # Resolve relative paths
        if not Path(filepath).is_absolute():
            filepath = self.config_dir / filepath
        
        column = node_params.get('column', 'inflow')
        
        try:
            data = pd.read_csv(filepath)
            if column not in data.columns:
                raise ValueError(f"Column '{column}' not found in {filepath}")
            return TimeSeriesStrategy(data, column)
        except Exception as e:
            raise ValueError(f"Failed to load time series for {node_id} from {filepath}: {e}")
    
    def _parse_hydrology_strategy(self, node_id: str, node_params: Dict[str, Any]) -> HydrologyStrategy:
        """Parse hydrology generator strategy."""
        snow17_params = node_params.get('snow17_params', {})
        awbm_params = node_params.get('awbm_params', {})
        
        try:
            area = float(node_params['area'])
        except KeyError:
            raise ValueError(f"HydrologyStrategy for {node_id} requires 'area'")
        
        return HydrologyStrategy(snow17_params, awbm_params, area)
    
    def _parse_awbm_strategy(self, node_id: str, node_params: Dict[str, Any]) -> AWBMGeneratorStrategy:
        """
        Parse AWBM generator strategy configuration.
        
        Args:
            node_id: Node identifier for error messages
            node_params: Node parameters dictionary from YAML
            
        Returns:
            AWBMGeneratorStrategy instance
            
        Raises:
            ValueError: If required parameters are missing or invalid
        """
        # Extract required catchment area
        try:
            area = float(node_params['area'])
            if area <= 0:
                raise ValueError(f"AWBM strategy for {node_id}: area must be positive, got {area}")
        except KeyError:
            raise ValueError(f"AWBM strategy for {node_id} requires 'area' parameter")
        except (TypeError, ValueError) as e:
            raise ValueError(f"AWBM strategy for {node_id}: invalid area value - {e}")
        
        # Extract parameters dictionary
        parameters = node_params.get('parameters', {})
        if not parameters:
            raise ValueError(f"AWBM strategy for {node_id} requires 'parameters' section")
        
        # Extract required AWBM parameters with validation
        try:
            # Surface store capacities (mm)
            a1 = float(parameters['A1'])
            a2 = float(parameters['A2']) 
            a3 = float(parameters['A3'])
            
            # Partial area fractions (must sum to 1.0)
            f1 = float(parameters['f1'])
            f2 = float(parameters['f2'])
            f3 = float(parameters['f3'])
            
            # Flow partitioning parameters
            bfi = float(parameters['BFI'])
            k_base = float(parameters['K_base'])
            
        except KeyError as e:
            raise ValueError(f"AWBM strategy for {node_id} missing required parameter: {e}")
        except (TypeError, ValueError) as e:
            raise ValueError(f"AWBM strategy for {node_id} has invalid parameter value: {e}")
        
        # Extract optional initial_storage parameter (handled separately from AWBMParameters)
        initial_storage = parameters.get('initial_storage', 0.5)
        try:
            initial_storage = float(initial_storage)
            if not (0.0 <= initial_storage <= 1.0):
                raise ValueError(f"initial_storage must be between 0.0 and 1.0, got {initial_storage}")
        except (TypeError, ValueError) as e:
            raise ValueError(f"AWBM strategy for {node_id}: invalid initial_storage - {e}")
        
        # Validate parameter ranges before creating strategy
        try:
            # Validate positive capacities
            if any(x <= 0 for x in [a1, a2, a3]):
                raise ValueError("Store capacities (A1, A2, A3) must be positive")
            
            # Validate partial area fractions
            if not (0 <= f1 <= 1 and 0 <= f2 <= 1 and 0 <= f3 <= 1):
                raise ValueError("Partial area fractions (f1, f2, f3) must be between 0 and 1")
            
            if abs(f1 + f2 + f3 - 1.0) > 1e-6:
                raise ValueError(f"Partial area fractions must sum to 1.0, got {f1 + f2 + f3:.6f}")
            
            # Validate BFI and recession constant
            if not (0 <= bfi <= 1):
                raise ValueError(f"Baseflow Index (BFI) must be between 0 and 1, got {bfi}")
            
            if not (0 <= k_base <= 1):
                raise ValueError(f"Recession constant (K_base) must be between 0 and 1, got {k_base}")
                
        except ValueError as e:
            raise ValueError(f"AWBM strategy for {node_id}: {e}")
        
        # Create and return AWBMGeneratorStrategy instance
        try:
            return AWBMGeneratorStrategy(
                catchment_area=area,
                a1=a1, a2=a2, a3=a3,
                f1=f1, f2=f2, f3=f3,
                bfi=bfi, k_base=k_base,
                initial_storage=initial_storage
            )
        except Exception as e:
            raise ValueError(f"Failed to create AWBM strategy for {node_id}: {e}")
    
    def _parse_demand_node(self, node_id: str, node_params: Dict[str, Any]) -> DemandNode:
        """Parse demand node configuration."""
        demand_type = node_params.get('demand_type')
        if not demand_type:
            raise ValueError(f"DemandNode {node_id} requires 'demand_type'")
        
        if demand_type == 'municipal':
            demand_model = self._parse_municipal_demand(node_id, node_params)
        elif demand_type == 'agriculture':
            demand_model = self._parse_agriculture_demand(node_id, node_params)
        else:
            raise ValueError(f"Unknown demand type for {node_id}: {demand_type}")
        
        return DemandNode(node_id, demand_model)
    
    def _parse_municipal_demand(self, node_id: str, node_params: Dict[str, Any]) -> MunicipalDemand:
        """Parse municipal demand model."""
        try:
            population = float(node_params['population'])
            per_capita_demand = float(node_params['per_capita_demand'])
        except KeyError as e:
            raise ValueError(f"MunicipalDemand for {node_id} missing parameter: {e}")
        
        return MunicipalDemand(population, per_capita_demand)
    
    def _parse_agriculture_demand(self, node_id: str, node_params: Dict[str, Any]) -> AgricultureDemand:
        """Parse agriculture demand model."""
        try:
            area = float(node_params['area'])
            crop_coefficient = float(node_params['crop_coefficient'])
        except KeyError as e:
            raise ValueError(f"AgricultureDemand for {node_id} missing parameter: {e}")
        
        return AgricultureDemand(area, crop_coefficient)
    
    def _parse_link(self, link_id: str, link_params: Dict[str, Any], 
                   nodes: Dict[str, Node]) -> Link:
        """
        Parse a link definition.
        
        Args:
            link_id: Link identifier
            link_params: Link parameters dictionary
            nodes: Dictionary of all nodes in the network
            
        Returns:
            Link instance
            
        Raises:
            ValueError: If link configuration is invalid
        """
        # Get source and target nodes
        source_id = link_params.get('source')
        target_id = link_params.get('target')
        
        if not source_id:
            raise ValueError(f"Link '{link_id}' requires 'source'")
        if not target_id:
            raise ValueError(f"Link '{link_id}' requires 'target'")
        
        # Check if nodes exist - but don't raise yet, let validation catch it
        if source_id not in nodes:
            raise ValueError(f"Link '{link_id}' references non-existent source node '{source_id}'")
        if target_id not in nodes:
            raise ValueError(f"Link '{link_id}' references non-existent target node '{target_id}'")
        
        source = nodes[source_id]
        target = nodes[target_id]
        
        # Get capacity and cost
        try:
            capacity = float(link_params.get('capacity', float('inf')))
            
            # Determine cost based on link type if not explicitly specified
            if 'cost' in link_params:
                cost = float(link_params['cost'])
            else:
                # Auto-assign cost based on target node type
                if target.node_type == 'demand':
                    cost = COST_DEMAND  # High priority for demand links
                else:
                    cost = 1.0  # Default cost for other links
        except (TypeError, ValueError) as e:
            raise ValueError(f"Link '{link_id}' has invalid capacity or cost: {e}")
        
        # Create link
        link = Link(link_id, source, target, capacity, cost)
        
        # Parse optional control
        if 'control' in link_params:
            link.control = self._parse_control(link_id, link_params['control'])
        
        # Parse optional hydraulic model
        if 'hydraulic' in link_params:
            link.hydraulic_model = self._parse_hydraulic(link_id, link_params['hydraulic'])
        
        return link
    
    def _parse_control(self, link_id: str, control_params: Dict[str, Any]):
        """Parse control configuration for a link."""
        control_type = control_params.get('type')
        if not control_type:
            raise ValueError(f"Control for link {link_id} requires 'type'")
        
        if control_type == 'fractional':
            try:
                fraction = float(control_params['fraction'])
            except KeyError:
                raise ValueError(f"FractionalControl for link {link_id} requires 'fraction'")
            return FractionalControl(fraction)
        
        elif control_type == 'absolute':
            try:
                max_flow = float(control_params['max_flow'])
            except KeyError:
                raise ValueError(f"AbsoluteControl for link {link_id} requires 'max_flow'")
            return AbsoluteControl(max_flow)
        
        elif control_type == 'switch':
            is_on = control_params.get('is_on', True)
            if not isinstance(is_on, bool):
                raise ValueError(f"SwitchControl for link {link_id} 'is_on' must be boolean")
            return SwitchControl(is_on)
        
        else:
            raise ValueError(f"Unknown control type for link {link_id}: {control_type}")
    
    def _parse_hydraulic(self, link_id: str, hydraulic_params: Dict[str, Any]):
        """Parse hydraulic model configuration for a link."""
        hydraulic_type = hydraulic_params.get('type')
        if not hydraulic_type:
            raise ValueError(f"Hydraulic model for link {link_id} requires 'type'")
        
        if hydraulic_type == 'weir':
            try:
                coefficient = float(hydraulic_params['coefficient'])
                length = float(hydraulic_params['length'])
                crest_elevation = float(hydraulic_params['crest_elevation'])
            except KeyError as e:
                raise ValueError(f"WeirModel for link {link_id} missing parameter: {e}")
            return WeirModel(coefficient, length, crest_elevation)
        
        elif hydraulic_type == 'pipe':
            try:
                capacity = float(hydraulic_params['capacity'])
            except KeyError:
                raise ValueError(f"PipeModel for link {link_id} requires 'capacity'")
            return PipeModel(capacity)
        
        else:
            raise ValueError(f"Unknown hydraulic type for link {link_id}: {hydraulic_type}")
    
    def _parse_simulation_config(self) -> Dict[str, Any]:
        """
        Parse simulation configuration section.
        
        Returns:
            Dictionary with simulation parameters (start_date, num_timesteps, end_date)
        """
        sim_config = self.config.get('simulation', {})
        
        # Default values
        result = {
            'start_date': '2024-01-01',
            'num_timesteps': 30
        }
        
        # Parse start_date
        if 'start_date' in sim_config:
            start_date_str = sim_config['start_date']
            try:
                # Validate date format
                datetime.strptime(start_date_str, '%Y-%m-%d')
                result['start_date'] = start_date_str
            except ValueError:
                raise ValueError(f"Invalid start_date format: {start_date_str}. Expected YYYY-MM-DD")
        
        # Parse duration - either num_timesteps or end_date
        if 'num_timesteps' in sim_config and 'end_date' in sim_config:
            raise ValueError("Cannot specify both 'num_timesteps' and 'end_date' in simulation config")
        
        if 'num_timesteps' in sim_config:
            try:
                num_timesteps = int(sim_config['num_timesteps'])
                if num_timesteps <= 0:
                    raise ValueError("num_timesteps must be positive")
                result['num_timesteps'] = num_timesteps
            except (ValueError, TypeError):
                raise ValueError(f"Invalid num_timesteps: {sim_config['num_timesteps']}. Must be a positive integer")
        
        elif 'end_date' in sim_config:
            end_date_str = sim_config['end_date']
            try:
                # Validate date format
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
                start_date = datetime.strptime(result['start_date'], '%Y-%m-%d')
                
                # Calculate number of days
                num_days = (end_date - start_date).days
                if num_days <= 0:
                    raise ValueError("end_date must be after start_date")
                
                result['end_date'] = end_date_str
                result['num_timesteps'] = num_days
            except ValueError as e:
                if "time data" in str(e):
                    raise ValueError(f"Invalid end_date format: {end_date_str}. Expected YYYY-MM-DD")
                else:
                    raise e
        
        return result
    
    def _parse_optimization_config(self) -> Dict[str, Any]:
        """
        Parse optimization configuration section for look-ahead optimization.
        
        Returns:
            Dictionary with optimization parameters (lookahead_days, solver_type, etc.)
        """
        opt_config = self.config.get('optimization', {})
        
        # Default values
        result = {
            'lookahead_days': 1,  # Default to current myopic behavior
            'solver_type': 'linear_programming',  # Default solver
            'perfect_foresight': True,  # Assume perfect foresight for V1
            'carryover_cost': -1.0,  # Cost for storing water (hedging penalty)
            'rolling_horizon': True  # Use rolling horizon approach
        }
        
        # Parse lookahead_days
        if 'lookahead_days' in opt_config:
            try:
                lookahead_days = int(opt_config['lookahead_days'])
                if lookahead_days < 1:
                    raise ValueError("lookahead_days must be at least 1")
                if lookahead_days > 365:
                    raise ValueError("lookahead_days cannot exceed 365 (performance limitation)")
                result['lookahead_days'] = lookahead_days
            except (ValueError, TypeError):
                raise ValueError(f"Invalid lookahead_days: {opt_config['lookahead_days']}. Must be a positive integer between 1 and 365")
        
        # Parse solver_type
        if 'solver_type' in opt_config:
            solver_type = opt_config['solver_type']
            if solver_type not in ['linear_programming', 'network_simplex']:
                raise ValueError(f"Invalid solver_type: {solver_type}. Must be 'linear_programming' or 'network_simplex'")
            result['solver_type'] = solver_type
        
        # Parse perfect_foresight
        if 'perfect_foresight' in opt_config:
            perfect_foresight = opt_config['perfect_foresight']
            if not isinstance(perfect_foresight, bool):
                raise ValueError("perfect_foresight must be a boolean (true/false)")
            result['perfect_foresight'] = perfect_foresight
        
        # Parse carryover_cost (hedging penalty)
        if 'carryover_cost' in opt_config:
            try:
                carryover_cost = float(opt_config['carryover_cost'])
                result['carryover_cost'] = carryover_cost
            except (ValueError, TypeError):
                raise ValueError(f"Invalid carryover_cost: {opt_config['carryover_cost']}. Must be a number")
        
        # Parse rolling_horizon
        if 'rolling_horizon' in opt_config:
            rolling_horizon = opt_config['rolling_horizon']
            if not isinstance(rolling_horizon, bool):
                raise ValueError("rolling_horizon must be a boolean (true/false)")
            result['rolling_horizon'] = rolling_horizon
        
        return result
