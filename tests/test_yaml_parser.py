"""
Tests for YAML configuration parser.

This module tests the YAMLParser class and its ability to parse
configuration files and construct network graphs.
"""

import pytest
import yaml
import pandas as pd
from pathlib import Path
from datetime import datetime
from hydrosim.config import YAMLParser, NetworkGraph
from hydrosim.nodes import StorageNode, JunctionNode, SourceNode, DemandNode
from hydrosim.links import Link
from hydrosim.climate import SiteConfig
from hydrosim.climate_sources import TimeSeriesClimateSource, WGENClimateSource
from hydrosim.strategies import TimeSeriesStrategy, MunicipalDemand, AgricultureDemand
from hydrosim.controls import FractionalControl, AbsoluteControl, SwitchControl
from hydrosim.hydraulics import WeirModel, PipeModel


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create a temporary directory for test configuration files."""
    return tmp_path


@pytest.fixture
def sample_climate_csv(temp_config_dir):
    """Create a sample climate CSV file."""
    csv_path = temp_config_dir / "climate.csv"
    data = pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=10, freq='D'),
        'precip': [0.0, 5.0, 10.0, 0.0, 0.0, 2.0, 8.0, 0.0, 0.0, 1.0],
        't_max': [25.0, 24.0, 23.0, 26.0, 27.0, 25.0, 24.0, 26.0, 28.0, 27.0],
        't_min': [15.0, 14.0, 13.0, 16.0, 17.0, 15.0, 14.0, 16.0, 18.0, 17.0],
        'solar': [20.0, 18.0, 15.0, 22.0, 23.0, 20.0, 18.0, 22.0, 24.0, 23.0]
    })
    data.to_csv(csv_path, index=False)
    return csv_path


@pytest.fixture
def sample_inflow_csv(temp_config_dir):
    """Create a sample inflow CSV file."""
    csv_path = temp_config_dir / "inflow.csv"
    data = pd.DataFrame({
        'inflow': [100.0, 120.0, 150.0, 130.0, 110.0, 140.0, 160.0, 145.0, 125.0, 115.0]
    })
    data.to_csv(csv_path, index=False)
    return csv_path


def test_yaml_parser_file_not_found():
    """Test that parser raises error for non-existent file."""
    with pytest.raises(FileNotFoundError):
        YAMLParser("nonexistent.yaml")


def test_yaml_parser_invalid_syntax(temp_config_dir):
    """Test that parser raises error for invalid YAML syntax."""
    config_path = temp_config_dir / "invalid.yaml"
    with open(config_path, 'w') as f:
        f.write("invalid: yaml: syntax:\n  - broken")
    
    with pytest.raises(yaml.YAMLError):
        YAMLParser(str(config_path))


def test_yaml_parser_empty_file(temp_config_dir):
    """Test that parser raises error for empty configuration."""
    config_path = temp_config_dir / "empty.yaml"
    with open(config_path, 'w') as f:
        f.write("")
    
    with pytest.raises(ValueError, match="Empty configuration"):
        YAMLParser(str(config_path))


def test_yaml_parser_simple_network(temp_config_dir, sample_climate_csv):
    """Test parsing a simple network configuration."""
    config_path = temp_config_dir / "simple.yaml"
    config = {
        'climate': {
            'source_type': 'timeseries',
            'filepath': 'climate.csv',
            'site': {
                'latitude': 45.0,
                'elevation': 1000.0
            }
        },
        'nodes': {
            'reservoir': {
                'type': 'storage',
                'initial_storage': 50000.0,
                'max_storage': 100000.0,
                'min_storage': 0.0,
                'eav_table': {
                    'elevations': [100.0, 110.0, 120.0],
                    'areas': [1000.0, 2000.0, 3000.0],
                    'volumes': [0.0, 10000.0, 30000.0]
                }
            },
            'junction1': {
                'type': 'junction'
            }
        },
        'links': {
            'link1': {
                'source': 'reservoir',
                'target': 'junction1',
                'capacity': 100.0,
                'cost': 1.0
            }
        }
    }
    
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    
    parser = YAMLParser(str(config_path))
    network, climate_source, site_config = parser.parse()
    
    # Check network structure
    assert isinstance(network, NetworkGraph)
    assert len(network.nodes) == 2
    assert len(network.links) == 1
    
    # Check nodes
    assert 'reservoir' in network.nodes
    assert 'junction1' in network.nodes
    assert isinstance(network.nodes['reservoir'], StorageNode)
    assert isinstance(network.nodes['junction1'], JunctionNode)
    
    # Check links
    assert 'link1' in network.links
    link = network.links['link1']
    assert link.source == network.nodes['reservoir']
    assert link.target == network.nodes['junction1']
    assert link.physical_capacity == 100.0
    assert link.cost == 1.0
    
    # Check climate source
    assert isinstance(climate_source, TimeSeriesClimateSource)
    
    # Check site config
    assert isinstance(site_config, SiteConfig)
    assert site_config.latitude == 45.0
    assert site_config.elevation == 1000.0


def test_yaml_parser_source_node_timeseries(temp_config_dir, sample_climate_csv, sample_inflow_csv):
    """Test parsing source node with time series strategy."""
    config_path = temp_config_dir / "source.yaml"
    config = {
        'climate': {
            'source_type': 'timeseries',
            'filepath': 'climate.csv',
            'site': {'latitude': 45.0, 'elevation': 1000.0}
        },
        'nodes': {
            'source1': {
                'type': 'source',
                'strategy': 'timeseries',
                'filepath': 'inflow.csv',
                'column': 'inflow'
            },
            'demand1': {
                'type': 'demand',
                'demand_type': 'municipal',
                'population': 10000.0,
                'per_capita_demand': 0.2
            }
        },
        'links': {
            'link1': {
                'source': 'source1',
                'target': 'demand1',
                'capacity': 5000.0,
                'cost': 1.0
            }
        }
    }
    
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    
    parser = YAMLParser(str(config_path))
    network, climate_source, site_config = parser.parse()
    
    # Check source node
    assert 'source1' in network.nodes
    source_node = network.nodes['source1']
    assert isinstance(source_node, SourceNode)
    assert isinstance(source_node.generator, TimeSeriesStrategy)


def test_yaml_parser_demand_nodes(temp_config_dir, sample_climate_csv):
    """Test parsing different demand node types."""
    config_path = temp_config_dir / "demand.yaml"
    config = {
        'climate': {
            'source_type': 'timeseries',
            'filepath': 'climate.csv',
            'site': {'latitude': 45.0, 'elevation': 1000.0}
        },
        'nodes': {
            'municipal': {
                'type': 'demand',
                'demand_type': 'municipal',
                'population': 10000.0,
                'per_capita_demand': 0.2
            },
            'agriculture': {
                'type': 'demand',
                'demand_type': 'agriculture',
                'area': 50000.0,
                'crop_coefficient': 0.8
            },
            'junction1': {
                'type': 'junction'
            }
        },
        'links': {
            'link1': {
                'source': 'junction1',
                'target': 'municipal',
                'capacity': 5000.0,
                'cost': 1.0
            },
            'link2': {
                'source': 'junction1',
                'target': 'agriculture',
                'capacity': 10000.0,
                'cost': 2.0
            }
        }
    }
    
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    
    parser = YAMLParser(str(config_path))
    network, climate_source, site_config = parser.parse()
    
    # Check municipal demand
    assert 'municipal' in network.nodes
    municipal = network.nodes['municipal']
    assert isinstance(municipal, DemandNode)
    assert isinstance(municipal.demand_model, MunicipalDemand)
    
    # Check agriculture demand
    assert 'agriculture' in network.nodes
    agriculture = network.nodes['agriculture']
    assert isinstance(agriculture, DemandNode)
    assert isinstance(agriculture.demand_model, AgricultureDemand)


def test_yaml_parser_controls(temp_config_dir, sample_climate_csv):
    """Test parsing links with different control types."""
    config_path = temp_config_dir / "controls.yaml"
    config = {
        'climate': {
            'source_type': 'timeseries',
            'filepath': 'climate.csv',
            'site': {'latitude': 45.0, 'elevation': 1000.0}
        },
        'nodes': {
            'j1': {'type': 'junction'},
            'j2': {'type': 'junction'},
            'j3': {'type': 'junction'},
            'j4': {'type': 'junction'}
        },
        'links': {
            'link_fractional': {
                'source': 'j1',
                'target': 'j2',
                'capacity': 100.0,
                'cost': 1.0,
                'control': {
                    'type': 'fractional',
                    'fraction': 0.5
                }
            },
            'link_absolute': {
                'source': 'j2',
                'target': 'j3',
                'capacity': 100.0,
                'cost': 1.0,
                'control': {
                    'type': 'absolute',
                    'max_flow': 50.0
                }
            },
            'link_switch': {
                'source': 'j3',
                'target': 'j4',
                'capacity': 100.0,
                'cost': 1.0,
                'control': {
                    'type': 'switch',
                    'is_on': False
                }
            }
        }
    }
    
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    
    parser = YAMLParser(str(config_path))
    network, climate_source, site_config = parser.parse()
    
    # Check fractional control
    link_frac = network.links['link_fractional']
    assert isinstance(link_frac.control, FractionalControl)
    assert link_frac.control.fraction == 0.5
    
    # Check absolute control
    link_abs = network.links['link_absolute']
    assert isinstance(link_abs.control, AbsoluteControl)
    assert link_abs.control.max_flow == 50.0
    
    # Check switch control
    link_switch = network.links['link_switch']
    assert isinstance(link_switch.control, SwitchControl)
    assert link_switch.control.is_on == False


def test_yaml_parser_hydraulics(temp_config_dir, sample_climate_csv):
    """Test parsing links with hydraulic models."""
    config_path = temp_config_dir / "hydraulics.yaml"
    config = {
        'climate': {
            'source_type': 'timeseries',
            'filepath': 'climate.csv',
            'site': {'latitude': 45.0, 'elevation': 1000.0}
        },
        'nodes': {
            'reservoir': {
                'type': 'storage',
                'initial_storage': 50000.0,
                'max_storage': 100000.0,
                'min_storage': 0.0,
                'eav_table': {
                    'elevations': [100.0, 110.0, 120.0],
                    'areas': [1000.0, 2000.0, 3000.0],
                    'volumes': [0.0, 10000.0, 30000.0]
                }
            },
            'j1': {'type': 'junction'},
            'j2': {'type': 'junction'}
        },
        'links': {
            'weir_link': {
                'source': 'reservoir',
                'target': 'j1',
                'capacity': 1000.0,
                'cost': 1.0,
                'hydraulic': {
                    'type': 'weir',
                    'coefficient': 1.5,
                    'length': 10.0,
                    'crest_elevation': 105.0
                }
            },
            'pipe_link': {
                'source': 'j1',
                'target': 'j2',
                'capacity': 500.0,
                'cost': 1.0,
                'hydraulic': {
                    'type': 'pipe',
                    'capacity': 300.0
                }
            }
        }
    }
    
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    
    parser = YAMLParser(str(config_path))
    network, climate_source, site_config = parser.parse()
    
    # Check weir model
    weir_link = network.links['weir_link']
    assert isinstance(weir_link.hydraulic_model, WeirModel)
    assert weir_link.hydraulic_model.C == 1.5
    assert weir_link.hydraulic_model.L == 10.0
    assert weir_link.hydraulic_model.crest_elev == 105.0
    
    # Check pipe model
    pipe_link = network.links['pipe_link']
    assert isinstance(pipe_link.hydraulic_model, PipeModel)
    assert pipe_link.hydraulic_model.capacity == 300.0


def test_yaml_parser_missing_nodes_section(temp_config_dir, sample_climate_csv):
    """Test that parser raises error when nodes section is missing."""
    config_path = temp_config_dir / "missing_nodes.yaml"
    config = {
        'climate': {
            'source_type': 'timeseries',
            'filepath': 'climate.csv',
            'site': {'latitude': 45.0, 'elevation': 1000.0}
        },
        'links': {}
    }
    
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    
    parser = YAMLParser(str(config_path))
    with pytest.raises(ValueError, match="must include 'nodes'"):
        parser.parse()


def test_yaml_parser_missing_links_section(temp_config_dir, sample_climate_csv):
    """Test that parser raises error when links section is missing."""
    config_path = temp_config_dir / "missing_links.yaml"
    config = {
        'climate': {
            'source_type': 'timeseries',
            'filepath': 'climate.csv',
            'site': {'latitude': 45.0, 'elevation': 1000.0}
        },
        'nodes': {
            'j1': {'type': 'junction'}
        }
    }
    
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    
    parser = YAMLParser(str(config_path))
    with pytest.raises(ValueError, match="must include 'links'"):
        parser.parse()


def test_yaml_parser_invalid_node_reference(temp_config_dir, sample_climate_csv):
    """Test that parser raises error for invalid node references in links."""
    config_path = temp_config_dir / "invalid_ref.yaml"
    config = {
        'climate': {
            'source_type': 'timeseries',
            'filepath': 'climate.csv',
            'site': {'latitude': 45.0, 'elevation': 1000.0}
        },
        'nodes': {
            'j1': {'type': 'junction'}
        },
        'links': {
            'link1': {
                'source': 'j1',
                'target': 'nonexistent',
                'capacity': 100.0,
                'cost': 1.0
            }
        }
    }
    
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    
    parser = YAMLParser(str(config_path))
    with pytest.raises(ValueError, match="non-existent.*node"):
        parser.parse()


def test_yaml_parser_missing_climate_section(temp_config_dir):
    """Test that parser raises error when climate section is missing."""
    config_path = temp_config_dir / "missing_climate.yaml"
    config = {
        'nodes': {
            'j1': {'type': 'junction'}
        },
        'links': {}
    }
    
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    
    parser = YAMLParser(str(config_path))
    with pytest.raises(ValueError, match="must include 'climate'"):
        parser.parse()


def test_yaml_parser_wgen_climate_source(temp_config_dir):
    """Test parsing WGEN climate source configuration."""
    config_path = temp_config_dir / "wgen.yaml"
    config = {
        'climate': {
            'source_type': 'wgen',
            'start_date': '2024-01-01',
            'wgen_params': {
                'pww': [0.6] * 12,  # 12 monthly values
                'pwd': [0.3] * 12,  # 12 monthly values
                'alpha': [0.5] * 12,  # 12 monthly values
                'beta': [2.0] * 12,  # 12 monthly values
                'txmd': 25.0,
                'atx': 5.0,
                'txmw': 23.0,
                'tn': 15.0,
                'atn': 3.0,
                'cvtx': 0.1,
                'acvtx': 0.05,
                'cvtn': 0.1,
                'acvtn': 0.05,
                'rmd': 20.0,
                'ar': 5.0,
                'rmw': 15.0,
                'latitude': 45.0
            },
            'site': {
                'latitude': 45.0,
                'elevation': 1000.0
            }
        },
        'nodes': {
            'j1': {'type': 'junction'},
            'j2': {'type': 'junction'}
        },
        'links': {
            'link1': {
                'source': 'j1',
                'target': 'j2',
                'capacity': 100.0,
                'cost': 1.0
            }
        }
    }
    
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    
    parser = YAMLParser(str(config_path))
    network, climate_source, site_config = parser.parse()
    
    assert isinstance(climate_source, WGENClimateSource)
    assert climate_source.params.pww[0] == 0.6
    assert climate_source.params.pwd[0] == 0.3
