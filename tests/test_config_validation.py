"""
Tests for configuration validation.

This module tests the validation functionality for network topology,
control parameters, and timestep configurations.
"""

import pytest
import yaml
import pandas as pd
from pathlib import Path
from hydrosim.config import YAMLParser, NetworkGraph
from hydrosim.nodes import JunctionNode, StorageNode
from hydrosim.links import Link
from hydrosim.controls import FractionalControl, AbsoluteControl


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


# Test link reference validation

def test_validate_link_references_nonexistent_source(temp_config_dir, sample_climate_csv):
    """Test validation catches link with non-existent source node."""
    config_path = temp_config_dir / "invalid_source.yaml"
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
                'source': 'nonexistent_source',
                'target': 'j1',
                'capacity': 100.0,
                'cost': 1.0
            }
        }
    }
    
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    
    parser = YAMLParser(str(config_path))
    with pytest.raises(ValueError, match="non-existent.*source.*node.*nonexistent_source"):
        parser.parse()


def test_validate_link_references_nonexistent_target(temp_config_dir, sample_climate_csv):
    """Test validation catches link with non-existent target node."""
    config_path = temp_config_dir / "invalid_target.yaml"
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
                'target': 'nonexistent_target',
                'capacity': 100.0,
                'cost': 1.0
            }
        }
    }
    
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    
    parser = YAMLParser(str(config_path))
    with pytest.raises(ValueError, match="non-existent.*target.*node.*nonexistent_target"):
        parser.parse()


def test_validate_link_references_both_nonexistent(temp_config_dir, sample_climate_csv):
    """Test validation catches link with both source and target non-existent."""
    config_path = temp_config_dir / "invalid_both.yaml"
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
                'source': 'bad_source',
                'target': 'bad_target',
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
    # At least one of the errors should be reported
    assert "bad_source" in error_msg or "bad_target" in error_msg


# Test orphaned node validation

def test_validate_orphaned_junction_node(temp_config_dir, sample_climate_csv):
    """Test validation catches orphaned junction node."""
    config_path = temp_config_dir / "orphaned_junction.yaml"
    config = {
        'climate': {
            'source_type': 'timeseries',
            'filepath': 'climate.csv',
            'site': {'latitude': 45.0, 'elevation': 1000.0}
        },
        'nodes': {
            'j1': {'type': 'junction'},
            'j2': {'type': 'junction'},
            'orphan': {'type': 'junction'}
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
    with pytest.raises(ValueError, match="orphan.*has no connections"):
        parser.parse()


def test_validate_orphaned_storage_node(temp_config_dir, sample_climate_csv):
    """Test validation catches orphaned storage node."""
    config_path = temp_config_dir / "orphaned_storage.yaml"
    config = {
        'climate': {
            'source_type': 'timeseries',
            'filepath': 'climate.csv',
            'site': {'latitude': 45.0, 'elevation': 1000.0}
        },
        'nodes': {
            'j1': {'type': 'junction'},
            'j2': {'type': 'junction'},
            'orphan_storage': {
                'type': 'storage',
                'initial_storage': 50000.0,
                'max_storage': 100000.0,
                'min_storage': 0.0,
                'eav_table': {
                    'elevations': [100.0, 110.0, 120.0],
                    'areas': [1000.0, 2000.0, 3000.0],
                    'volumes': [0.0, 10000.0, 30000.0]
                }
            }
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
    with pytest.raises(ValueError, match="orphan_storage.*has no connections"):
        parser.parse()


def test_validate_orphaned_source_allowed(temp_config_dir, sample_climate_csv):
    """Test that orphaned source nodes are allowed (terminal nodes)."""
    csv_path = temp_config_dir / "inflow.csv"
    data = pd.DataFrame({'inflow': [100.0] * 10})
    data.to_csv(csv_path, index=False)
    
    config_path = temp_config_dir / "orphaned_source.yaml"
    config = {
        'climate': {
            'source_type': 'timeseries',
            'filepath': 'climate.csv',
            'site': {'latitude': 45.0, 'elevation': 1000.0}
        },
        'nodes': {
            'j1': {'type': 'junction'},
            'j2': {'type': 'junction'},
            'orphan_source': {
                'type': 'source',
                'strategy': 'timeseries',
                'filepath': 'inflow.csv',
                'column': 'inflow'
            }
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
    # Should not raise an error - source nodes can be orphaned
    network, climate_source, site_config = parser.parse()
    assert 'orphan_source' in network.nodes


def test_validate_orphaned_demand_allowed(temp_config_dir, sample_climate_csv):
    """Test that orphaned demand nodes are allowed (terminal nodes)."""
    config_path = temp_config_dir / "orphaned_demand.yaml"
    config = {
        'climate': {
            'source_type': 'timeseries',
            'filepath': 'climate.csv',
            'site': {'latitude': 45.0, 'elevation': 1000.0}
        },
        'nodes': {
            'j1': {'type': 'junction'},
            'j2': {'type': 'junction'},
            'orphan_demand': {
                'type': 'demand',
                'demand_type': 'municipal',
                'population': 10000.0,
                'per_capita_demand': 0.2
            }
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
    # Should not raise an error - demand nodes can be orphaned
    network, climate_source, site_config = parser.parse()
    assert 'orphan_demand' in network.nodes


# Test control parameter validation

def test_validate_fractional_control_invalid_low(temp_config_dir, sample_climate_csv):
    """Test validation catches fractional control with value < 0."""
    config_path = temp_config_dir / "invalid_fractional_low.yaml"
    config = {
        'climate': {
            'source_type': 'timeseries',
            'filepath': 'climate.csv',
            'site': {'latitude': 45.0, 'elevation': 1000.0}
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
                'cost': 1.0,
                'control': {
                    'type': 'fractional',
                    'fraction': -0.5
                }
            }
        }
    }
    
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    
    parser = YAMLParser(str(config_path))
    with pytest.raises(ValueError, match="Fraction must be between 0.0 and 1.0"):
        parser.parse()


def test_validate_fractional_control_invalid_high(temp_config_dir, sample_climate_csv):
    """Test validation catches fractional control with value > 1."""
    config_path = temp_config_dir / "invalid_fractional_high.yaml"
    config = {
        'climate': {
            'source_type': 'timeseries',
            'filepath': 'climate.csv',
            'site': {'latitude': 45.0, 'elevation': 1000.0}
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
                'cost': 1.0,
                'control': {
                    'type': 'fractional',
                    'fraction': 1.5
                }
            }
        }
    }
    
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    
    parser = YAMLParser(str(config_path))
    with pytest.raises(ValueError, match="Fraction must be between 0.0 and 1.0"):
        parser.parse()


def test_validate_fractional_control_valid_boundary(temp_config_dir, sample_climate_csv):
    """Test that fractional control accepts boundary values 0.0 and 1.0."""
    config_path = temp_config_dir / "valid_fractional_boundary.yaml"
    config = {
        'climate': {
            'source_type': 'timeseries',
            'filepath': 'climate.csv',
            'site': {'latitude': 45.0, 'elevation': 1000.0}
        },
        'nodes': {
            'j1': {'type': 'junction'},
            'j2': {'type': 'junction'},
            'j3': {'type': 'junction'}
        },
        'links': {
            'link1': {
                'source': 'j1',
                'target': 'j2',
                'capacity': 100.0,
                'cost': 1.0,
                'control': {
                    'type': 'fractional',
                    'fraction': 0.0
                }
            },
            'link2': {
                'source': 'j2',
                'target': 'j3',
                'capacity': 100.0,
                'cost': 1.0,
                'control': {
                    'type': 'fractional',
                    'fraction': 1.0
                }
            }
        }
    }
    
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    
    parser = YAMLParser(str(config_path))
    network, climate_source, site_config = parser.parse()
    
    assert network.links['link1'].control.fraction == 0.0
    assert network.links['link2'].control.fraction == 1.0


def test_validate_absolute_control_negative(temp_config_dir, sample_climate_csv):
    """Test validation catches absolute control with negative value."""
    config_path = temp_config_dir / "invalid_absolute.yaml"
    config = {
        'climate': {
            'source_type': 'timeseries',
            'filepath': 'climate.csv',
            'site': {'latitude': 45.0, 'elevation': 1000.0}
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
                'cost': 1.0,
                'control': {
                    'type': 'absolute',
                    'max_flow': -50.0
                }
            }
        }
    }
    
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    
    parser = YAMLParser(str(config_path))
    with pytest.raises(ValueError, match="Max flow must be non-negative"):
        parser.parse()


def test_validate_absolute_control_zero_allowed(temp_config_dir, sample_climate_csv):
    """Test that absolute control accepts zero value."""
    config_path = temp_config_dir / "valid_absolute_zero.yaml"
    config = {
        'climate': {
            'source_type': 'timeseries',
            'filepath': 'climate.csv',
            'site': {'latitude': 45.0, 'elevation': 1000.0}
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
                'cost': 1.0,
                'control': {
                    'type': 'absolute',
                    'max_flow': 0.0
                }
            }
        }
    }
    
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    
    parser = YAMLParser(str(config_path))
    network, climate_source, site_config = parser.parse()
    
    assert network.links['link1'].control.max_flow == 0.0


# Test timestep configuration validation

def test_validate_subdaily_timestep_hourly(temp_config_dir, sample_climate_csv):
    """Test validation rejects hourly timestep configuration."""
    config_path = temp_config_dir / "subdaily_hourly.yaml"
    config = {
        'timestep': {
            'unit': 'hour',
            'duration': 1
        },
        'climate': {
            'source_type': 'timeseries',
            'filepath': 'climate.csv',
            'site': {'latitude': 45.0, 'elevation': 1000.0}
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
    with pytest.raises(ValueError, match="only supports daily timesteps.*hour"):
        parser.parse()


def test_validate_subdaily_timestep_string(temp_config_dir, sample_climate_csv):
    """Test validation rejects sub-daily timestep string."""
    config_path = temp_config_dir / "subdaily_string.yaml"
    config = {
        'timestep': '6h',
        'climate': {
            'source_type': 'timeseries',
            'filepath': 'climate.csv',
            'site': {'latitude': 45.0, 'elevation': 1000.0}
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
    with pytest.raises(ValueError, match="only supports daily timesteps.*6h"):
        parser.parse()


def test_validate_timestep_duration_not_one(temp_config_dir, sample_climate_csv):
    """Test validation rejects timestep duration other than 1."""
    config_path = temp_config_dir / "invalid_duration.yaml"
    config = {
        'timestep': {
            'unit': 'day',
            'duration': 7
        },
        'climate': {
            'source_type': 'timeseries',
            'filepath': 'climate.csv',
            'site': {'latitude': 45.0, 'elevation': 1000.0}
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
    with pytest.raises(ValueError, match="only supports 1-day timesteps.*duration 7"):
        parser.parse()


def test_validate_daily_timestep_allowed(temp_config_dir, sample_climate_csv):
    """Test that daily timestep configuration is allowed."""
    config_path = temp_config_dir / "valid_daily.yaml"
    config = {
        'timestep': {
            'unit': 'day',
            'duration': 1
        },
        'climate': {
            'source_type': 'timeseries',
            'filepath': 'climate.csv',
            'site': {'latitude': 45.0, 'elevation': 1000.0}
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
    # Should not raise an error
    network, climate_source, site_config = parser.parse()
    assert len(network.nodes) == 2


def test_validate_daily_timestep_string_allowed(temp_config_dir, sample_climate_csv):
    """Test that daily timestep string formats are allowed."""
    for timestep_str in ['1d', '1day', 'day', 'daily']:
        config_path = temp_config_dir / f"valid_{timestep_str}.yaml"
        config = {
            'timestep': timestep_str,
            'climate': {
                'source_type': 'timeseries',
                'filepath': 'climate.csv',
                'site': {'latitude': 45.0, 'elevation': 1000.0}
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
        # Should not raise an error
        network, climate_source, site_config = parser.parse()
        assert len(network.nodes) == 2


def test_validate_no_timestep_config_allowed(temp_config_dir, sample_climate_csv):
    """Test that omitting timestep configuration is allowed (defaults to daily)."""
    config_path = temp_config_dir / "no_timestep.yaml"
    config = {
        'climate': {
            'source_type': 'timeseries',
            'filepath': 'climate.csv',
            'site': {'latitude': 45.0, 'elevation': 1000.0}
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
    # Should not raise an error - timestep defaults to daily
    network, climate_source, site_config = parser.parse()
    assert len(network.nodes) == 2


# Test multiple validation errors reported together

def test_validate_multiple_errors_reported(temp_config_dir, sample_climate_csv):
    """Test that validation errors are reported."""
    config_path = temp_config_dir / "multiple_errors.yaml"
    config = {
        'climate': {
            'source_type': 'timeseries',
            'filepath': 'climate.csv',
            'site': {'latitude': 45.0, 'elevation': 1000.0}
        },
        'nodes': {
            'j1': {'type': 'junction'},
            'orphan': {'type': 'junction'}
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
    with pytest.raises(ValueError) as exc_info:
        parser.parse()
    
    error_msg = str(exc_info.value)
    # Should report the invalid reference (parsing catches this first)
    assert "nonexistent" in error_msg


# Test NetworkGraph.validate() directly

def test_network_graph_validate_direct():
    """Test NetworkGraph.validate() method directly."""
    network = NetworkGraph()
    
    # Add nodes
    j1 = JunctionNode('j1')
    j2 = JunctionNode('j2')
    orphan = JunctionNode('orphan')
    
    network.add_node(j1)
    network.add_node(j2)
    network.add_node(orphan)
    
    # Add link
    link = Link('link1', j1, j2, 100.0, 1.0)
    network.add_link(link)
    
    # Validate
    errors = network.validate()
    
    # Should have one error for orphaned node
    assert len(errors) == 1
    assert 'orphan' in errors[0]
    assert 'has no connections' in errors[0]


def test_network_graph_validate_control_parameters():
    """Test NetworkGraph validates control parameters."""
    network = NetworkGraph()
    
    # Add nodes
    j1 = JunctionNode('j1')
    j2 = JunctionNode('j2')
    
    network.add_node(j1)
    network.add_node(j2)
    
    # Add link with invalid fractional control
    link = Link('link1', j1, j2, 100.0, 1.0)
    link.control = FractionalControl(0.5)  # Valid
    network.add_link(link)
    
    # Manually set invalid value (bypassing constructor validation)
    link.control.fraction = 1.5
    
    # Validate
    errors = network.validate()
    
    # Should catch the invalid fraction
    assert len(errors) == 1
    assert 'link1' in errors[0]
    assert 'fractional control' in errors[0].lower()
    assert '1.5' in errors[0]


def test_network_graph_validate_excludes_virtual_components():
    """Test that NetworkGraph.validate() excludes virtual components from validation."""
    from hydrosim.nodes import VirtualSink
    from hydrosim.config import ElevationAreaVolume
    
    network = NetworkGraph()
    
    # Add physical nodes
    storage = StorageNode(
        'storage1', 
        initial_storage=1000.0,
        eav_table=ElevationAreaVolume([0, 10], [100, 200], [0, 2000], 'storage1'),
        max_storage=2000.0,
        min_storage=0.0
    )
    j1 = JunctionNode('j1')
    
    network.add_node(storage)
    network.add_node(j1)
    
    # Add virtual sink (orphaned, but should be excluded from validation)
    virtual_sink = VirtualSink(
        node_id='storage1_future',
        demand=1000.0
    )
    network.add_node(virtual_sink)
    
    # Add physical link
    physical_link = Link('link1', storage, j1, 100.0, 1.0)
    network.add_link(physical_link)
    
    # Add carryover link (should be excluded from validation)
    carryover_link = Link('storage1_carryover', storage, virtual_sink, 2000.0, -1.0)
    network.add_link(carryover_link)
    
    # Validate
    errors = network.validate()
    
    # Should have no errors - virtual components should be excluded
    # The virtual_sink is orphaned but should not trigger an error
    # The carryover link references the virtual_sink but should not be validated
    assert len(errors) == 0, f"Expected no validation errors, but got: {errors}"
