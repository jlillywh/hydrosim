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


def create_wgen_csv_new_format(csv_path, pww_val=0.6, pwd_val=0.3, alpha_val=0.5, beta_val=2.0,
                                txmd=25.0, atx=5.0, txmw=23.0, tn=15.0, atn=3.0,
                                cvtx=0.1, acvtx=0.05, cvtn=0.1, acvtn=0.05,
                                rmd=20.0, ar=5.0, rmw=15.0, latitude=45.0, random_seed=None):
    """Helper function to create WGEN CSV files in the new format."""
    lines = []
    
    # Monthly parameters section
    lines.append("month,pww,pwd,alpha,beta")
    months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
    for month in months:
        lines.append(f"{month},{pww_val},{pwd_val},{alpha_val},{beta_val}")
    
    lines.append("")  # Blank line
    
    # Temperature parameters section
    lines.append("parameter,value")
    lines.append(f"txmd,{txmd}")
    lines.append(f"atx,{atx}")
    lines.append(f"txmw,{txmw}")
    lines.append(f"tn,{tn}")
    lines.append(f"atn,{atn}")
    lines.append(f"cvtx,{cvtx}")
    lines.append(f"acvtx,{acvtx}")
    lines.append(f"cvtn,{cvtn}")
    lines.append(f"acvtn,{acvtn}")
    
    lines.append("")  # Blank line
    
    # Radiation parameters section
    lines.append("parameter,value")
    lines.append(f"rmd,{rmd}")
    lines.append(f"ar,{ar}")
    lines.append(f"rmw,{rmw}")
    
    lines.append("")  # Blank line
    
    # Location parameters section
    lines.append("parameter,value")
    lines.append(f"latitude,{latitude}")
    if random_seed is not None:
        lines.append(f"random_seed,{random_seed}")
    
    # Write CSV file
    with open(csv_path, 'w', newline='') as f:
        f.write('\n'.join(lines) + '\n')


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


# ============================================================================
# WGEN CSV Configuration Validation Tests (Task 4)
# ============================================================================

def test_wgen_conflicting_configuration_both_inline_and_csv(temp_config_dir):
    """Test that parser raises error when both inline params and CSV file are specified."""
    # Create a dummy CSV file
    csv_path = temp_config_dir / "wgen_params.csv"
    create_wgen_csv_new_format(csv_path)
    
    config_path = temp_config_dir / "conflicting_wgen.yaml"
    config = {
        'climate': {
            'source_type': 'wgen',
            'start_date': '2024-01-01',
            # Both inline params AND CSV file specified - should raise error
            'wgen_params': {
                'pww': [0.6] * 12,
                'pwd': [0.3] * 12,
                'alpha': [0.5] * 12,
                'beta': [2.0] * 12,
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
            'wgen_params_file': 'wgen_params.csv',
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
    with pytest.raises(ValueError) as exc_info:
        parser.parse()
    
    error_msg = str(exc_info.value)
    assert "cannot specify both" in error_msg.lower()
    assert "wgen_params" in error_msg
    assert "wgen_params_file" in error_msg


def test_wgen_missing_configuration_neither_inline_nor_csv(temp_config_dir):
    """Test that parser raises error when neither inline params nor CSV file are specified."""
    config_path = temp_config_dir / "missing_wgen.yaml"
    config = {
        'climate': {
            'source_type': 'wgen',
            'start_date': '2024-01-01',
            # Neither wgen_params nor wgen_params_file specified - should raise error
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
    with pytest.raises(ValueError) as exc_info:
        parser.parse()
    
    error_msg = str(exc_info.value)
    assert "requires either" in error_msg.lower()
    assert "wgen_params" in error_msg
    assert "wgen_params_file" in error_msg


def test_wgen_csv_relative_path_resolution(temp_config_dir):
    """Test that parser correctly resolves relative CSV file paths."""
    # Create a valid CSV file in the temp directory
    csv_path = temp_config_dir / "wgen_params.csv"
    create_wgen_csv_new_format(csv_path)
    
    config_path = temp_config_dir / "wgen_relative.yaml"
    config = {
        'climate': {
            'source_type': 'wgen',
            'start_date': '2024-01-01',
            # Use relative path (relative to YAML file location)
            'wgen_params_file': 'wgen_params.csv',
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
    # Should successfully parse and resolve the relative path
    network, climate_source, site_config = parser.parse()
    
    assert isinstance(climate_source, WGENClimateSource)
    assert climate_source.params.pww[0] == 0.6
    assert climate_source.params.latitude == 45.0


def test_wgen_csv_relative_path_subdirectory(temp_config_dir):
    """Test that parser correctly resolves relative CSV file paths in subdirectories."""
    # Create a subdirectory
    subdir = temp_config_dir / "params"
    subdir.mkdir()
    
    # Create a valid CSV file in the subdirectory
    csv_path = subdir / "wgen_params.csv"
    create_wgen_csv_new_format(csv_path, pww_val=0.5, pwd_val=0.25, alpha_val=1.0, beta_val=5.0,
                               txmd=22.0, atx=8.0, txmw=20.0, tn=12.0, atn=6.0,
                               cvtx=0.15, acvtx=0.08, cvtn=0.12, acvtn=0.06,
                               rmd=18.0, ar=6.0, rmw=14.0, latitude=40.0)
    
    config_path = temp_config_dir / "wgen_subdir.yaml"
    config = {
        'climate': {
            'source_type': 'wgen',
            'start_date': '2024-01-01',
            # Use relative path with subdirectory
            'wgen_params_file': 'params/wgen_params.csv',
            'site': {
                'latitude': 40.0,
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
    # Should successfully parse and resolve the relative path with subdirectory
    network, climate_source, site_config = parser.parse()
    
    assert isinstance(climate_source, WGENClimateSource)
    assert climate_source.params.pww[0] == 0.5
    assert climate_source.params.latitude == 40.0


def test_wgen_csv_absolute_path_handling(temp_config_dir):
    """Test that parser correctly handles absolute CSV file paths."""
    # Create a valid CSV file
    csv_path = temp_config_dir / "wgen_params_absolute.csv"
    create_wgen_csv_new_format(csv_path, pww_val=0.7, pwd_val=0.35, alpha_val=1.5, beta_val=6.0,
                               txmd=28.0, atx=12.0, txmw=26.0, tn=18.0, atn=10.0,
                               cvtx=0.2, acvtx=0.1, cvtn=0.15, acvtn=0.08,
                               rmd=22.0, ar=8.0, rmw=18.0, latitude=50.0)
    
    config_path = temp_config_dir / "wgen_absolute.yaml"
    config = {
        'climate': {
            'source_type': 'wgen',
            'start_date': '2024-01-01',
            # Use absolute path
            'wgen_params_file': str(csv_path.absolute()),
            'site': {
                'latitude': 50.0,
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
    # Should successfully parse using the absolute path
    network, climate_source, site_config = parser.parse()
    
    assert isinstance(climate_source, WGENClimateSource)
    assert climate_source.params.pww[0] == 0.7
    assert climate_source.params.latitude == 50.0


def test_wgen_csv_file_not_found_relative_path(temp_config_dir):
    """Test that parser raises FileNotFoundError for missing CSV file with relative path."""
    config_path = temp_config_dir / "wgen_missing_csv.yaml"
    config = {
        'climate': {
            'source_type': 'wgen',
            'start_date': '2024-01-01',
            # Reference non-existent CSV file
            'wgen_params_file': 'nonexistent_params.csv',
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
    with pytest.raises(FileNotFoundError):
        parser.parse()


def test_wgen_csv_file_not_found_absolute_path(temp_config_dir):
    """Test that parser raises FileNotFoundError for missing CSV file with absolute path."""
    config_path = temp_config_dir / "wgen_missing_csv_abs.yaml"
    # Create an absolute path to a non-existent file
    nonexistent_csv = temp_config_dir / "definitely_does_not_exist.csv"
    
    config = {
        'climate': {
            'source_type': 'wgen',
            'start_date': '2024-01-01',
            # Reference non-existent CSV file with absolute path
            'wgen_params_file': str(nonexistent_csv.absolute()),
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
    with pytest.raises(FileNotFoundError):
        parser.parse()


def test_awbm_strategy_parsing(temp_config_dir, sample_climate_csv):
    """Test parsing of AWBM strategy configuration."""
    config_path = temp_config_dir / "awbm_config.yaml"
    
    config = {
        'climate': {
            'source_type': 'timeseries',
            'filepath': str(sample_climate_csv),
            'site': {
                'latitude': 45.0,
                'elevation': 1000.0
            }
        },
        'nodes': {
            'awbm_source': {
                'type': 'source',
                'strategy': 'awbm',
                'area': 5.0e7,  # 50 km² in m²
                'parameters': {
                    'A1': 134.0,
                    'A2': 433.0,
                    'A3': 433.0,
                    'f1': 0.3,
                    'f2': 0.3,
                    'f3': 0.4,
                    'BFI': 0.35,
                    'K_base': 0.95,
                    'initial_storage': 0.5
                }
            },
            'junction': {
                'type': 'junction'
            }
        },
        'links': {
            'link1': {
                'source': 'awbm_source',
                'target': 'junction',
                'capacity': 1000.0,
                'cost': 1.0
            }
        }
    }
    
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    
    parser = YAMLParser(str(config_path))
    network, climate_source, site_config = parser.parse()
    
    # Verify network structure
    assert len(network.nodes) == 2
    assert len(network.links) == 1
    
    # Verify AWBM source node
    awbm_node = network.nodes['awbm_source']
    assert isinstance(awbm_node, SourceNode)
    
    # Import AWBMGeneratorStrategy for type checking
    from hydrosim.strategies import AWBMGeneratorStrategy
    assert isinstance(awbm_node.generator, AWBMGeneratorStrategy)
    
    # Verify AWBM parameters
    strategy = awbm_node.generator
    assert strategy.catchment_area == 5.0e7
    assert strategy.parameters.a1 == 134.0
    assert strategy.parameters.a2 == 433.0
    assert strategy.parameters.a3 == 433.0
    assert strategy.parameters.f1 == 0.3
    assert strategy.parameters.f2 == 0.3
    assert strategy.parameters.f3 == 0.4
    assert strategy.parameters.bfi == 0.35
    assert strategy.parameters.k_base == 0.95
    assert strategy.initial_storage == 0.5


def test_awbm_strategy_missing_area(temp_config_dir, sample_climate_csv):
    """Test AWBM strategy parsing with missing area parameter."""
    config_path = temp_config_dir / "awbm_missing_area.yaml"
    
    config = {
        'climate': {
            'source_type': 'timeseries',
            'filepath': str(sample_climate_csv),
            'site': {
                'latitude': 45.0,
                'elevation': 1000.0
            }
        },
        'nodes': {
            'awbm_source': {
                'type': 'source',
                'strategy': 'awbm',
                # Missing 'area' parameter
                'parameters': {
                    'A1': 134.0,
                    'A2': 433.0,
                    'A3': 433.0,
                    'f1': 0.3,
                    'f2': 0.3,
                    'f3': 0.4,
                    'BFI': 0.35,
                    'K_base': 0.95
                }
            }
        },
        'links': {}
    }
    
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    
    parser = YAMLParser(str(config_path))
    with pytest.raises(ValueError, match="requires 'area' parameter"):
        parser.parse()


def test_awbm_strategy_missing_parameters(temp_config_dir, sample_climate_csv):
    """Test AWBM strategy parsing with missing parameters section."""
    config_path = temp_config_dir / "awbm_missing_params.yaml"
    
    config = {
        'climate': {
            'source_type': 'timeseries',
            'filepath': str(sample_climate_csv),
            'site': {
                'latitude': 45.0,
                'elevation': 1000.0
            }
        },
        'nodes': {
            'awbm_source': {
                'type': 'source',
                'strategy': 'awbm',
                'area': 5.0e7
                # Missing 'parameters' section
            }
        },
        'links': {}
    }
    
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    
    parser = YAMLParser(str(config_path))
    with pytest.raises(ValueError, match="requires 'parameters' section"):
        parser.parse()


def test_awbm_strategy_invalid_partial_areas(temp_config_dir, sample_climate_csv):
    """Test AWBM strategy parsing with invalid partial area fractions."""
    config_path = temp_config_dir / "awbm_invalid_areas.yaml"
    
    config = {
        'climate': {
            'source_type': 'timeseries',
            'filepath': str(sample_climate_csv),
            'site': {
                'latitude': 45.0,
                'elevation': 1000.0
            }
        },
        'nodes': {
            'awbm_source': {
                'type': 'source',
                'strategy': 'awbm',
                'area': 5.0e7,
                'parameters': {
                    'A1': 134.0,
                    'A2': 433.0,
                    'A3': 433.0,
                    'f1': 0.3,
                    'f2': 0.3,
                    'f3': 0.5,  # Sum = 1.1, should be 1.0
                    'BFI': 0.35,
                    'K_base': 0.95
                }
            }
        },
        'links': {}
    }
    
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    
    parser = YAMLParser(str(config_path))
    with pytest.raises(ValueError, match="must sum to 1.0"):
        parser.parse()


def test_awbm_strategy_invalid_bfi(temp_config_dir, sample_climate_csv):
    """Test AWBM strategy parsing with invalid BFI value."""
    config_path = temp_config_dir / "awbm_invalid_bfi.yaml"
    
    config = {
        'climate': {
            'source_type': 'timeseries',
            'filepath': str(sample_climate_csv),
            'site': {
                'latitude': 45.0,
                'elevation': 1000.0
            }
        },
        'nodes': {
            'awbm_source': {
                'type': 'source',
                'strategy': 'awbm',
                'area': 5.0e7,
                'parameters': {
                    'A1': 134.0,
                    'A2': 433.0,
                    'A3': 433.0,
                    'f1': 0.3,
                    'f2': 0.3,
                    'f3': 0.4,
                    'BFI': 1.5,  # Invalid: > 1.0
                    'K_base': 0.95
                }
            }
        },
        'links': {}
    }
    
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    
    parser = YAMLParser(str(config_path))
    with pytest.raises(ValueError, match="Baseflow Index.*must be between 0 and 1"):
        parser.parse()


def test_awbm_strategy_missing_required_parameter(temp_config_dir, sample_climate_csv):
    """Test AWBM strategy parsing with missing required parameter."""
    config_path = temp_config_dir / "awbm_missing_param.yaml"
    
    config = {
        'climate': {
            'source_type': 'timeseries',
            'filepath': str(sample_climate_csv),
            'site': {
                'latitude': 45.0,
                'elevation': 1000.0
            }
        },
        'nodes': {
            'awbm_source': {
                'type': 'source',
                'strategy': 'awbm',
                'area': 5.0e7,
                'parameters': {
                    'A1': 134.0,
                    'A2': 433.0,
                    # Missing 'A3'
                    'f1': 0.3,
                    'f2': 0.3,
                    'f3': 0.4,
                    'BFI': 0.35,
                    'K_base': 0.95
                }
            }
        },
        'links': {}
    }
    
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    
    parser = YAMLParser(str(config_path))
    with pytest.raises(ValueError, match="missing required parameter.*A3"):
        parser.parse()


def test_awbm_strategy_default_initial_storage(temp_config_dir, sample_climate_csv):
    """Test AWBM strategy parsing with default initial_storage value."""
    config_path = temp_config_dir / "awbm_default_storage.yaml"
    
    config = {
        'climate': {
            'source_type': 'timeseries',
            'filepath': str(sample_climate_csv),
            'site': {
                'latitude': 45.0,
                'elevation': 1000.0
            }
        },
        'nodes': {
            'awbm_source': {
                'type': 'source',
                'strategy': 'awbm',
                'area': 5.0e7,
                'parameters': {
                    'A1': 134.0,
                    'A2': 433.0,
                    'A3': 433.0,
                    'f1': 0.3,
                    'f2': 0.3,
                    'f3': 0.4,
                    'BFI': 0.35,
                    'K_base': 0.95
                    # No initial_storage specified - should default to 0.5
                }
            },
            'junction': {
                'type': 'junction'
            }
        },
        'links': {
            'link1': {
                'source': 'awbm_source',
                'target': 'junction',
                'capacity': 1000.0,
                'cost': 1.0
            }
        }
    }
    
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    
    parser = YAMLParser(str(config_path))
    network, climate_source, site_config = parser.parse()
    
    # Verify default initial_storage value
    awbm_node = network.nodes['awbm_source']
    assert awbm_node.generator.initial_storage == 0.5


def test_awbm_strategy_invalid_initial_storage(temp_config_dir, sample_climate_csv):
    """Test AWBM strategy parsing with invalid initial_storage value."""
    config_path = temp_config_dir / "awbm_invalid_storage.yaml"
    
    config = {
        'climate': {
            'source_type': 'timeseries',
            'filepath': str(sample_climate_csv),
            'site': {
                'latitude': 45.0,
                'elevation': 1000.0
            }
        },
        'nodes': {
            'awbm_source': {
                'type': 'source',
                'strategy': 'awbm',
                'area': 5.0e7,
                'parameters': {
                    'A1': 134.0,
                    'A2': 433.0,
                    'A3': 433.0,
                    'f1': 0.3,
                    'f2': 0.3,
                    'f3': 0.4,
                    'BFI': 0.35,
                    'K_base': 0.95,
                    'initial_storage': 1.5  # Invalid: > 1.0
                }
            }
        },
        'links': {}
    }
    
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    
    parser = YAMLParser(str(config_path))
    with pytest.raises(ValueError, match="initial_storage must be between 0.0 and 1.0"):
        parser.parse()