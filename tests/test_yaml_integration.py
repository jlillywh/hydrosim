"""
Integration tests for YAML parser with real configuration files.

This module tests the YAMLParser with realistic configuration scenarios
to ensure end-to-end functionality.
"""

import pytest
import pandas as pd
from pathlib import Path
from hydrosim.config import YAMLParser
from hydrosim.nodes import StorageNode, JunctionNode, SourceNode, DemandNode
from hydrosim.links import Link
from hydrosim.climate_sources import TimeSeriesClimateSource


@pytest.fixture
def integration_test_dir(tmp_path):
    """Create a temporary directory with test data files."""
    # Create climate data CSV
    climate_data = pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=365, freq='D'),
        'precip': [5.0] * 365,
        't_max': [25.0] * 365,
        't_min': [15.0] * 365,
        'solar': [20.0] * 365
    })
    climate_path = tmp_path / "climate.csv"
    climate_data.to_csv(climate_path, index=False)
    
    # Create inflow data CSV
    inflow_data = pd.DataFrame({
        'inflow': [100.0] * 365
    })
    inflow_path = tmp_path / "inflow.csv"
    inflow_data.to_csv(inflow_path, index=False)
    
    return tmp_path


def test_parse_complete_network(integration_test_dir):
    """Test parsing a complete network configuration."""
    config_path = integration_test_dir / "network.yaml"
    
    # Write a complete configuration
    config_content = """
climate:
  source_type: timeseries
  filepath: climate.csv
  site:
    latitude: 45.0
    elevation: 1000.0

nodes:
  reservoir:
    type: storage
    initial_storage: 50000.0
    max_storage: 100000.0
    min_storage: 0.0
    eav_table:
      elevations: [100.0, 110.0, 120.0]
      areas: [1000.0, 2000.0, 3000.0]
      volumes: [0.0, 10000.0, 30000.0]
  
  catchment:
    type: source
    strategy: timeseries
    filepath: inflow.csv
    column: inflow
  
  junction1:
    type: junction
  
  city:
    type: demand
    demand_type: municipal
    population: 10000.0
    per_capita_demand: 0.2
  
  farm:
    type: demand
    demand_type: agriculture
    area: 50000.0
    crop_coefficient: 0.8

links:
  catchment_to_reservoir:
    source: catchment
    target: reservoir
    capacity: 5000.0
    cost: 0.0
  
  reservoir_to_junction:
    source: reservoir
    target: junction1
    capacity: 3000.0
    cost: 1.0
    hydraulic:
      type: weir
      coefficient: 1.5
      length: 10.0
      crest_elevation: 105.0
  
  junction_to_city:
    source: junction1
    target: city
    capacity: 2000.0
    cost: 2.0
    control:
      type: fractional
      fraction: 0.8
  
  junction_to_farm:
    source: junction1
    target: farm
    capacity: 3000.0
    cost: 3.0
"""
    
    with open(config_path, 'w') as f:
        f.write(config_content)
    
    # Parse the configuration
    parser = YAMLParser(str(config_path))
    network, climate_source, site_config = parser.parse()
    
    # Verify network structure
    assert len(network.nodes) == 5
    assert len(network.links) == 4
    
    # Verify node types
    assert isinstance(network.nodes['reservoir'], StorageNode)
    assert isinstance(network.nodes['catchment'], SourceNode)
    assert isinstance(network.nodes['junction1'], JunctionNode)
    assert isinstance(network.nodes['city'], DemandNode)
    assert isinstance(network.nodes['farm'], DemandNode)
    
    # Verify links exist and are connected
    assert 'catchment_to_reservoir' in network.links
    assert 'reservoir_to_junction' in network.links
    assert 'junction_to_city' in network.links
    assert 'junction_to_farm' in network.links
    
    # Verify link connections
    catchment_link = network.links['catchment_to_reservoir']
    assert catchment_link.source == network.nodes['catchment']
    assert catchment_link.target == network.nodes['reservoir']
    
    # Verify climate source
    assert isinstance(climate_source, TimeSeriesClimateSource)
    
    # Verify site config
    assert site_config.latitude == 45.0
    assert site_config.elevation == 1000.0
    
    # Verify network validation passes
    errors = network.validate()
    assert len(errors) == 0


def test_parse_network_with_all_control_types(integration_test_dir):
    """Test parsing a network with all control types."""
    config_path = integration_test_dir / "controls.yaml"
    
    config_content = """
climate:
  source_type: timeseries
  filepath: climate.csv
  site:
    latitude: 45.0
    elevation: 1000.0

nodes:
  j1:
    type: junction
  j2:
    type: junction
  j3:
    type: junction
  j4:
    type: junction

links:
  link_frac:
    source: j1
    target: j2
    capacity: 100.0
    cost: 1.0
    control:
      type: fractional
      fraction: 0.5
  
  link_abs:
    source: j2
    target: j3
    capacity: 100.0
    cost: 1.0
    control:
      type: absolute
      max_flow: 50.0
  
  link_switch:
    source: j3
    target: j4
    capacity: 100.0
    cost: 1.0
    control:
      type: switch
      is_on: false
"""
    
    with open(config_path, 'w') as f:
        f.write(config_content)
    
    parser = YAMLParser(str(config_path))
    network, climate_source, site_config = parser.parse()
    
    # Verify all control types are present
    assert network.links['link_frac'].control is not None
    assert network.links['link_abs'].control is not None
    assert network.links['link_switch'].control is not None
    
    # Verify control parameters
    assert network.links['link_frac'].control.fraction == 0.5
    assert network.links['link_abs'].control.max_flow == 50.0
    assert network.links['link_switch'].control.is_on == False


def test_parse_network_with_relative_paths(integration_test_dir):
    """Test that relative paths in configuration are resolved correctly."""
    # Create a subdirectory for config
    config_dir = integration_test_dir / "configs"
    config_dir.mkdir()
    
    config_path = config_dir / "network.yaml"
    
    config_content = """
climate:
  source_type: timeseries
  filepath: ../climate.csv
  site:
    latitude: 45.0
    elevation: 1000.0

nodes:
  source1:
    type: source
    strategy: timeseries
    filepath: ../inflow.csv
    column: inflow
  
  demand1:
    type: demand
    demand_type: municipal
    population: 1000.0
    per_capita_demand: 0.2

links:
  link1:
    source: source1
    target: demand1
    capacity: 500.0
    cost: 1.0
"""
    
    with open(config_path, 'w') as f:
        f.write(config_content)
    
    # Parse should resolve relative paths correctly
    parser = YAMLParser(str(config_path))
    network, climate_source, site_config = parser.parse()
    
    # If parsing succeeds, relative paths were resolved correctly
    assert len(network.nodes) == 2
    assert len(network.links) == 1


def test_validation_error_reported_clearly(integration_test_dir):
    """Test that validation errors are reported with clear messages."""
    config_path = integration_test_dir / "invalid.yaml"
    
    config_content = """
climate:
  source_type: timeseries
  filepath: climate.csv
  site:
    latitude: 45.0
    elevation: 1000.0

nodes:
  node1:
    type: junction

links:
  bad_link:
    source: node1
    target: nonexistent_node
    capacity: 100.0
    cost: 1.0
"""
    
    with open(config_path, 'w') as f:
        f.write(config_content)
    
    parser = YAMLParser(str(config_path))
    
    # Should raise ValueError with clear message about missing node
    with pytest.raises(ValueError) as exc_info:
        parser.parse()
    
    assert "non-existent" in str(exc_info.value).lower()
    assert "nonexistent_node" in str(exc_info.value)
