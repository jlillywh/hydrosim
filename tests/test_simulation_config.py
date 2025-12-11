"""
Tests for simulation configuration parsing in YAML files.

This module tests the simulation configuration section parsing
and validation in the YAMLParser class.
"""

import pytest
import yaml
import tempfile
from pathlib import Path
from datetime import datetime
from hydrosim.config import YAMLParser


class TestSimulationConfig:
    """Test simulation configuration parsing."""
    
    def create_minimal_config(self, simulation_config=None):
        """Create a minimal valid configuration with optional simulation section."""
        config = {
            'model_name': 'Test Model',
            'climate': {
                'source_type': 'timeseries',
                'filepath': 'climate_data.csv',
                'site': {
                    'latitude': 45.0,
                    'elevation': 1000.0
                }
            },
            'nodes': {
                'test_source': {
                    'type': 'source',
                    'strategy': 'timeseries',
                    'filepath': 'inflow_data.csv',
                    'column': 'inflow'
                },
                'test_demand': {
                    'type': 'demand',
                    'demand_type': 'municipal',
                    'population': 1000.0,
                    'per_capita_demand': 0.2
                }
            },
            'links': {
                'source_to_demand': {
                    'source': 'test_source',
                    'target': 'test_demand',
                    'capacity': 1000.0
                }
            }
        }
        
        if simulation_config:
            config['simulation'] = simulation_config
        
        return config
    
    def create_test_files(self, temp_dir):
        """Create dummy CSV files for testing."""
        # Create climate CSV
        climate_path = temp_dir / 'climate_data.csv'
        with open(climate_path, 'w') as f:
            f.write("date,precip,t_max,t_min,solar\n")
            f.write("2024-01-01,0.0,25.0,15.0,20.0\n")
            f.write("2024-01-02,5.0,22.0,12.0,18.0\n")
        
        # Create inflow CSV
        inflow_path = temp_dir / 'inflow_data.csv'
        with open(inflow_path, 'w') as f:
            f.write("date,inflow\n")
            f.write("2024-01-01,100.0\n")
            f.write("2024-01-02,150.0\n")
    
    def test_simulation_config_with_end_date(self):
        """Test simulation configuration with start_date and end_date."""
        simulation_config = {
            'start_date': '2024-06-01',
            'end_date': '2024-06-15'
        }
        
        config = self.create_minimal_config(simulation_config)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self.create_test_files(temp_path)
            
            config_path = temp_path / 'test_config.yaml'
            with open(config_path, 'w') as f:
                yaml.dump(config, f)
            
            parser = YAMLParser(str(config_path))
            network, climate_source, site_config = parser.parse()
            
            sim_config = network.simulation_config
            assert sim_config['start_date'] == datetime(2024, 6, 1)
            assert sim_config['end_date'] == datetime(2024, 6, 15)
            assert sim_config['num_timesteps'] == 14  # 15 - 1 = 14 days
    
    def test_simulation_config_with_num_timesteps(self):
        """Test simulation configuration with start_date and num_timesteps."""
        simulation_config = {
            'start_date': '2024-01-01',
            'num_timesteps': 45
        }
        
        config = self.create_minimal_config(simulation_config)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self.create_test_files(temp_path)
            
            config_path = temp_path / 'test_config.yaml'
            with open(config_path, 'w') as f:
                yaml.dump(config, f)
            
            parser = YAMLParser(str(config_path))
            network, climate_source, site_config = parser.parse()
            
            sim_config = network.simulation_config
            assert sim_config['start_date'] == datetime(2024, 1, 1)
            assert sim_config['end_date'] is None
            assert sim_config['num_timesteps'] == 45
    
    def test_simulation_config_defaults(self):
        """Test simulation configuration with default values."""
        config = self.create_minimal_config()  # No simulation section
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self.create_test_files(temp_path)
            
            config_path = temp_path / 'test_config.yaml'
            with open(config_path, 'w') as f:
                yaml.dump(config, f)
            
            parser = YAMLParser(str(config_path))
            network, climate_source, site_config = parser.parse()
            
            sim_config = network.simulation_config
            assert sim_config['start_date'] == datetime(2024, 1, 1)  # Default
            assert sim_config['end_date'] is None
            assert sim_config['num_timesteps'] == 30  # Default
    
    def test_simulation_config_invalid_date_format(self):
        """Test that invalid date formats raise ValueError."""
        simulation_config = {
            'start_date': '2024/01/01',  # Wrong format
            'num_timesteps': 30
        }
        
        config = self.create_minimal_config(simulation_config)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self.create_test_files(temp_path)
            
            config_path = temp_path / 'test_config.yaml'
            with open(config_path, 'w') as f:
                yaml.dump(config, f)
            
            parser = YAMLParser(str(config_path))
            
            with pytest.raises(ValueError, match="Invalid start_date format"):
                parser.parse()
    
    def test_simulation_config_end_before_start(self):
        """Test that end_date before start_date raises ValueError."""
        simulation_config = {
            'start_date': '2024-06-15',
            'end_date': '2024-06-01'  # Before start_date
        }
        
        config = self.create_minimal_config(simulation_config)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self.create_test_files(temp_path)
            
            config_path = temp_path / 'test_config.yaml'
            with open(config_path, 'w') as f:
                yaml.dump(config, f)
            
            parser = YAMLParser(str(config_path))
            
            with pytest.raises(ValueError, match="end_date.*must be after start_date"):
                parser.parse()
    
    def test_simulation_config_both_end_date_and_num_timesteps(self):
        """Test that specifying both end_date and num_timesteps raises ValueError."""
        simulation_config = {
            'start_date': '2024-01-01',
            'end_date': '2024-01-31',
            'num_timesteps': 30  # Conflicting with end_date
        }
        
        config = self.create_minimal_config(simulation_config)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self.create_test_files(temp_path)
            
            config_path = temp_path / 'test_config.yaml'
            with open(config_path, 'w') as f:
                yaml.dump(config, f)
            
            parser = YAMLParser(str(config_path))
            
            with pytest.raises(ValueError, match="Cannot specify both 'end_date' and 'num_timesteps'"):
                parser.parse()
    
    def test_simulation_config_invalid_num_timesteps(self):
        """Test that invalid num_timesteps values raise ValueError."""
        simulation_config = {
            'start_date': '2024-01-01',
            'num_timesteps': -5  # Negative value
        }
        
        config = self.create_minimal_config(simulation_config)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self.create_test_files(temp_path)
            
            config_path = temp_path / 'test_config.yaml'
            with open(config_path, 'w') as f:
                yaml.dump(config, f)
            
            parser = YAMLParser(str(config_path))
            
            with pytest.raises(ValueError, match="Must be a positive integer"):
                parser.parse()
    
    def test_simulation_config_zero_day_period(self):
        """Test that same start and end dates raise ValueError."""
        simulation_config = {
            'start_date': '2024-01-01',
            'end_date': '2024-01-01'  # Same as start_date
        }
        
        config = self.create_minimal_config(simulation_config)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self.create_test_files(temp_path)
            
            config_path = temp_path / 'test_config.yaml'
            with open(config_path, 'w') as f:
                yaml.dump(config, f)
            
            parser = YAMLParser(str(config_path))
            
            with pytest.raises(ValueError, match="end_date.*must be after start_date"):
                parser.parse()
    
    def test_simulation_config_custom_start_date_only(self):
        """Test simulation configuration with only custom start_date."""
        simulation_config = {
            'start_date': '2024-12-01'
            # No end_date or num_timesteps - should default to 30 days
        }
        
        config = self.create_minimal_config(simulation_config)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self.create_test_files(temp_path)
            
            config_path = temp_path / 'test_config.yaml'
            with open(config_path, 'w') as f:
                yaml.dump(config, f)
            
            parser = YAMLParser(str(config_path))
            network, climate_source, site_config = parser.parse()
            
            sim_config = network.simulation_config
            assert sim_config['start_date'] == datetime(2024, 12, 1)
            assert sim_config['end_date'] is None
            assert sim_config['num_timesteps'] == 30  # Default