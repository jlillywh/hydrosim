"""
Tests for the ParameterCSVWriter class.

This module tests the CSV writing functionality for WGEN parameters,
ensuring compatibility with the existing CSVWGENParamsParser.
"""

import pytest
import tempfile
from pathlib import Path
import pandas as pd
from io import StringIO

from hydrosim.climate_builder.parameter_csv import ParameterCSVWriter
from hydrosim.wgen_params import CSVWGENParamsParser


class TestParameterCSVWriter:
    """Test suite for ParameterCSVWriter class."""
    
    @pytest.fixture
    def sample_params(self):
        """Create sample WGEN parameters for testing."""
        return {
            # Monthly precipitation parameters (12 values each)
            'pww': [0.45, 0.42, 0.40, 0.38, 0.35, 0.30, 0.25, 0.28, 0.32, 0.38, 0.42, 0.48],
            'pwd': [0.25, 0.23, 0.22, 0.20, 0.18, 0.15, 0.12, 0.15, 0.18, 0.22, 0.25, 0.27],
            'alpha': [1.2, 1.1, 1.0, 0.9, 0.8, 0.7, 0.6, 0.7, 0.8, 1.0, 1.1, 1.3],
            'beta': [8.5, 7.8, 7.2, 6.5, 5.8, 5.0, 4.5, 5.2, 6.0, 7.0, 7.8, 9.2],
            
            # Temperature parameters (single values)
            'txmd': 20.0,
            'atx': 10.0,
            'txmw': 18.0,
            'tn': 10.0,
            'atn': 8.0,
            'cvtx': 0.1,
            'acvtx': 0.05,
            'cvtn': 0.1,
            'acvtn': 0.05,
            
            # Solar radiation parameters
            'rmd': 15.0,  # Single value
            'rmw': 12.0,  # Single value
            'ar': 5.0,
            
            # Location parameters
            'latitude': 47.45
        }
    
    @pytest.fixture
    def sample_params_with_monthly_solar(self):
        """Create sample WGEN parameters with monthly solar values."""
        params = {
            # Monthly precipitation parameters (12 values each)
            'pww': [0.45, 0.42, 0.40, 0.38, 0.35, 0.30, 0.25, 0.28, 0.32, 0.38, 0.42, 0.48],
            'pwd': [0.25, 0.23, 0.22, 0.20, 0.18, 0.15, 0.12, 0.15, 0.18, 0.22, 0.25, 0.27],
            'alpha': [1.2, 1.1, 1.0, 0.9, 0.8, 0.7, 0.6, 0.7, 0.8, 1.0, 1.1, 1.3],
            'beta': [8.5, 7.8, 7.2, 6.5, 5.8, 5.0, 4.5, 5.2, 6.0, 7.0, 7.8, 9.2],
            
            # Temperature parameters (single values)
            'txmd': 20.0,
            'atx': 10.0,
            'txmw': 18.0,
            'tn': 10.0,
            'atn': 8.0,
            'cvtx': 0.1,
            'acvtx': 0.05,
            'cvtn': 0.1,
            'acvtn': 0.05,
            
            # Solar radiation parameters (monthly values)
            'rmd': [10.0, 12.0, 15.0, 18.0, 20.0, 22.0, 23.0, 21.0, 18.0, 15.0, 12.0, 10.0],
            'rmw': [8.0, 10.0, 12.0, 14.0, 16.0, 18.0, 19.0, 17.0, 14.0, 12.0, 10.0, 8.0],
            'ar': 5.0,
            
            # Location parameters
            'latitude': 47.45
        }
        return params
    
    def test_write_creates_file(self, sample_params):
        """Test that write() creates a CSV file."""
        writer = ParameterCSVWriter()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "wgen_params.csv"
            result_path = writer.write(sample_params, output_path)
            
            assert result_path.exists()
            assert result_path == output_path
    
    def test_write_creates_parent_directories(self, sample_params):
        """Test that write() creates parent directories if they don't exist."""
        writer = ParameterCSVWriter()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "data" / "processed" / "wgen_params.csv"
            result_path = writer.write(sample_params, output_path)
            
            assert result_path.exists()
            assert result_path.parent.exists()
    
    def test_csv_has_correct_structure(self, sample_params):
        """Test that the CSV file has the correct structure."""
        writer = ParameterCSVWriter()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "wgen_params.csv"
            writer.write(sample_params, output_path)
            
            # Read the file and check structure
            with open(output_path, 'r') as f:
                content = f.read()
            
            # Check for section headers
            assert "month,pww,pwd,alpha,beta" in content
            assert "parameter,value" in content
            
            # Check for month names
            for month in ['jan', 'feb', 'mar', 'apr', 'may', 'jun',
                         'jul', 'aug', 'sep', 'oct', 'nov', 'dec']:
                assert month in content
            
            # Check for temperature parameters
            for param in ['txmd', 'atx', 'txmw', 'tn', 'atn',
                         'cvtx', 'acvtx', 'cvtn', 'acvtn']:
                assert param in content
            
            # Check for radiation parameters
            for param in ['rmd', 'ar', 'rmw']:
                assert param in content
            
            # Check for location parameters
            assert 'latitude' in content
            assert 'random_seed' in content
    
    def test_csv_compatible_with_parser(self, sample_params):
        """Test that the CSV file can be parsed by CSVWGENParamsParser."""
        writer = ParameterCSVWriter()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "wgen_params.csv"
            writer.write(sample_params, output_path)
            
            # Try to parse the file
            parsed_params = CSVWGENParamsParser.parse(str(output_path))
            
            # Verify parsed parameters match original
            assert len(parsed_params.pww) == 12
            assert len(parsed_params.pwd) == 12
            assert len(parsed_params.alpha) == 12
            assert len(parsed_params.beta) == 12
            
            # Check a few specific values
            assert abs(parsed_params.pww[0] - sample_params['pww'][0]) < 1e-5
            assert abs(parsed_params.txmd - sample_params['txmd']) < 1e-5
            assert abs(parsed_params.latitude - sample_params['latitude']) < 1e-5
    
    def test_monthly_solar_converted_to_annual(self, sample_params_with_monthly_solar):
        """Test that monthly solar values are converted to annual averages."""
        writer = ParameterCSVWriter()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "wgen_params.csv"
            writer.write(sample_params_with_monthly_solar, output_path)
            
            # Parse the file
            parsed_params = CSVWGENParamsParser.parse(str(output_path))
            
            # Check that rmd and rmw are single values (annual averages)
            import numpy as np
            expected_rmd = np.mean(sample_params_with_monthly_solar['rmd'])
            expected_rmw = np.mean(sample_params_with_monthly_solar['rmw'])
            
            assert abs(parsed_params.rmd - expected_rmd) < 1e-5
            assert abs(parsed_params.rmw - expected_rmw) < 1e-5
    
    def test_missing_monthly_parameter_raises_error(self, sample_params):
        """Test that missing monthly parameters raise ValueError."""
        writer = ParameterCSVWriter()
        
        # Remove a required monthly parameter
        incomplete_params = sample_params.copy()
        del incomplete_params['pww']
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "wgen_params.csv"
            
            with pytest.raises(ValueError, match="Missing required monthly parameter"):
                writer.write(incomplete_params, output_path)
    
    def test_missing_temperature_parameter_raises_error(self, sample_params):
        """Test that missing temperature parameters raise ValueError."""
        writer = ParameterCSVWriter()
        
        # Remove a required temperature parameter
        incomplete_params = sample_params.copy()
        del incomplete_params['txmd']
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "wgen_params.csv"
            
            with pytest.raises(ValueError, match="Missing required temperature parameter"):
                writer.write(incomplete_params, output_path)
    
    def test_missing_radiation_parameter_raises_error(self, sample_params):
        """Test that missing radiation parameters raise ValueError."""
        writer = ParameterCSVWriter()
        
        # Remove a required radiation parameter
        incomplete_params = sample_params.copy()
        del incomplete_params['rmd']
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "wgen_params.csv"
            
            with pytest.raises(ValueError, match="Missing required radiation parameter"):
                writer.write(incomplete_params, output_path)
    
    def test_missing_latitude_raises_error(self, sample_params):
        """Test that missing latitude raises ValueError."""
        writer = ParameterCSVWriter()
        
        # Remove latitude
        incomplete_params = sample_params.copy()
        del incomplete_params['latitude']
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "wgen_params.csv"
            
            with pytest.raises(ValueError, match="Missing required location parameter"):
                writer.write(incomplete_params, output_path)
    
    def test_wrong_number_of_monthly_values_raises_error(self, sample_params):
        """Test that wrong number of monthly values raises ValueError."""
        writer = ParameterCSVWriter()
        
        # Provide only 11 monthly values instead of 12
        incomplete_params = sample_params.copy()
        incomplete_params['pww'] = [0.45, 0.42, 0.40, 0.38, 0.35, 0.30, 0.25, 0.28, 0.32, 0.38, 0.42]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "wgen_params.csv"
            
            with pytest.raises(ValueError, match="must have 12 values"):
                writer.write(incomplete_params, output_path)
    
    def test_custom_random_seed(self, sample_params):
        """Test that custom random seed is written correctly."""
        writer = ParameterCSVWriter()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "wgen_params.csv"
            writer.write(sample_params, output_path, random_seed=12345)
            
            # Parse the file
            parsed_params = CSVWGENParamsParser.parse(str(output_path))
            
            # Check random seed
            assert parsed_params.random_seed == 12345
    
    def test_round_trip_preserves_values(self, sample_params):
        """Test that writing and parsing preserves parameter values."""
        writer = ParameterCSVWriter()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "wgen_params.csv"
            writer.write(sample_params, output_path)
            
            # Parse the file
            parsed_params = CSVWGENParamsParser.parse(str(output_path))
            
            # Check all monthly parameters
            for i in range(12):
                assert abs(parsed_params.pww[i] - sample_params['pww'][i]) < 1e-5
                assert abs(parsed_params.pwd[i] - sample_params['pwd'][i]) < 1e-5
                assert abs(parsed_params.alpha[i] - sample_params['alpha'][i]) < 1e-5
                assert abs(parsed_params.beta[i] - sample_params['beta'][i]) < 1e-5
            
            # Check temperature parameters
            assert abs(parsed_params.txmd - sample_params['txmd']) < 1e-5
            assert abs(parsed_params.atx - sample_params['atx']) < 1e-5
            assert abs(parsed_params.txmw - sample_params['txmw']) < 1e-5
            assert abs(parsed_params.tn - sample_params['tn']) < 1e-5
            assert abs(parsed_params.atn - sample_params['atn']) < 1e-5
            assert abs(parsed_params.cvtx - sample_params['cvtx']) < 1e-5
            assert abs(parsed_params.acvtx - sample_params['acvtx']) < 1e-5
            assert abs(parsed_params.cvtn - sample_params['cvtn']) < 1e-5
            assert abs(parsed_params.acvtn - sample_params['acvtn']) < 1e-5
            
            # Check radiation parameters
            assert abs(parsed_params.rmd - sample_params['rmd']) < 1e-5
            assert abs(parsed_params.rmw - sample_params['rmw']) < 1e-5
            assert abs(parsed_params.ar - sample_params['ar']) < 1e-5
            
            # Check location parameters
            assert abs(parsed_params.latitude - sample_params['latitude']) < 1e-5
