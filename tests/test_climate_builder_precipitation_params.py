"""
Tests for Precipitation Parameter Calculator.

This module tests the PrecipitationParameterCalculator class functionality including:
- Wet/dry day classification
- Markov chain transition probability calculation
- Gamma distribution parameter fitting
- Handling of insufficient data
"""

import datetime
import warnings
import pandas as pd
import numpy as np
import pytest

from hydrosim.climate_builder.precipitation_params import PrecipitationParameterCalculator


class TestPrecipitationParameterCalculator:
    """Test suite for PrecipitationParameterCalculator class."""
    
    def test_initialization(self):
        """Test calculator initialization with valid parameters."""
        calc = PrecipitationParameterCalculator(wet_day_threshold=0.1, min_wet_days=10)
        assert calc.wet_day_threshold == 0.1
        assert calc.min_wet_days == 10
    
    def test_initialization_invalid_threshold(self):
        """Test that negative threshold raises error."""
        with pytest.raises(ValueError, match="wet_day_threshold must be non-negative"):
            PrecipitationParameterCalculator(wet_day_threshold=-0.1)
    
    def test_initialization_invalid_min_wet_days(self):
        """Test that non-positive min_wet_days raises error."""
        with pytest.raises(ValueError, match="min_wet_days must be positive"):
            PrecipitationParameterCalculator(min_wet_days=0)
    
    def test_classify_wet_dry_basic(self):
        """Test wet/dry classification with threshold of 0.1 mm."""
        calc = PrecipitationParameterCalculator(wet_day_threshold=0.1)
        
        # Test various precipitation values
        precip = pd.Series([0.0, 0.05, 0.1, 0.15, 1.0, 10.0, np.nan])
        result = calc._classify_wet_dry(precip)
        
        # Expected: False, False, True, True, True, True, False (NaN comparison returns False)
        assert result.iloc[0] == False  # 0.0 < 0.1
        assert result.iloc[1] == False  # 0.05 < 0.1
        assert result.iloc[2] == True   # 0.1 >= 0.1
        assert result.iloc[3] == True   # 0.15 >= 0.1
        assert result.iloc[4] == True   # 1.0 >= 0.1
        assert result.iloc[5] == True   # 10.0 >= 0.1
        assert result.iloc[6] == False  # NaN comparison returns False
    
    def test_markov_chain_simple_sequence(self):
        """Test Markov chain calculation with a simple known sequence."""
        calc = PrecipitationParameterCalculator()
        
        # Create a simple sequence: W W D W D D W W W D
        # Transitions: W->W, W->D, D->W, W->D, D->D, D->W, W->W, W->W, W->D
        # NWW=3, NDW=3, NWD=2, NDD=1
        # PWW = 3/(3+3) = 0.5
        # PWD = 2/(2+1) = 0.667
        dates = pd.date_range('2020-01-01', periods=10, freq='D')
        df = pd.DataFrame({
            'date': dates,
            'is_wet': [True, True, False, True, False, False, True, True, True, False]
        })
        
        pww, pwd = calc._calculate_markov_params(df, month=1)
        
        assert abs(pww - 0.5) < 0.01
        assert abs(pwd - 0.667) < 0.01
    
    def test_markov_chain_all_wet(self):
        """Test Markov chain with all wet days."""
        calc = PrecipitationParameterCalculator()
        
        dates = pd.date_range('2020-01-01', periods=10, freq='D')
        df = pd.DataFrame({
            'date': dates,
            'is_wet': [True] * 10
        })
        
        pww, pwd = calc._calculate_markov_params(df, month=1)
        
        # All transitions are W->W, so PWW should be 1.0
        # No dry days, so PWD uses default
        assert pww == 1.0
        assert pwd == 0.3  # default value
    
    def test_markov_chain_all_dry(self):
        """Test Markov chain with all dry days."""
        calc = PrecipitationParameterCalculator()
        
        dates = pd.date_range('2020-01-01', periods=10, freq='D')
        df = pd.DataFrame({
            'date': dates,
            'is_wet': [False] * 10
        })
        
        pww, pwd = calc._calculate_markov_params(df, month=1)
        
        # All transitions are D->D, so PWD should be 0.0
        # No wet days, so PWW uses default
        assert pwd == 0.0
        assert pww == 0.5  # default value
    
    def test_gamma_fitting_known_distribution(self):
        """Test Gamma parameter fitting with known distribution."""
        calc = PrecipitationParameterCalculator()
        
        # Generate data from known Gamma distribution
        np.random.seed(42)
        true_alpha = 2.0
        true_beta = 5.0
        wet_amounts = np.random.gamma(true_alpha, true_beta, size=100)
        
        dates = pd.date_range('2020-01-01', periods=100, freq='D')
        df = pd.DataFrame({
            'date': dates,
            'precipitation_mm': wet_amounts,
            'is_wet': [True] * 100
        })
        
        alpha, beta = calc._calculate_gamma_params(df, month=1)
        
        # Parameters should be close to true values (within ~20% due to sampling)
        assert abs(alpha - true_alpha) / true_alpha < 0.3
        assert abs(beta - true_beta) / true_beta < 0.3
    
    def test_gamma_fitting_insufficient_data(self):
        """Test Gamma fitting with insufficient wet days."""
        calc = PrecipitationParameterCalculator(min_wet_days=10)
        
        # Only 5 wet days
        dates = pd.date_range('2020-01-01', periods=5, freq='D')
        df = pd.DataFrame({
            'date': dates,
            'precipitation_mm': [1.0, 2.0, 3.0, 4.0, 5.0],
            'is_wet': [True] * 5
        })
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            alpha, beta = calc._calculate_gamma_params(df, month=1)
            
            # Should issue warning
            assert len(w) > 0
            assert "Insufficient wet days" in str(w[0].message)
        
        # Should return default values
        assert alpha == 1.5
        assert beta == 5.0
    
    def test_calculate_parameters_full_year(self):
        """Test full parameter calculation with a year of data."""
        calc = PrecipitationParameterCalculator()
        
        # Create synthetic data for a full year
        dates = pd.date_range('2020-01-01', '2020-12-31', freq='D')
        np.random.seed(42)
        
        # Generate precipitation with seasonal pattern
        precip = []
        for date in dates:
            # Higher precipitation in winter months
            if date.month in [11, 12, 1, 2]:
                p = np.random.gamma(2.0, 5.0) if np.random.random() > 0.3 else 0.0
            else:
                p = np.random.gamma(1.5, 3.0) if np.random.random() > 0.6 else 0.0
            precip.append(p)
        
        df = pd.DataFrame({
            'date': dates,
            'precipitation_mm': precip
        })
        
        params = calc.calculate_parameters(df)
        
        # Check structure
        assert 'pww' in params
        assert 'pwd' in params
        assert 'alpha' in params
        assert 'beta' in params
        
        # Check all have 12 values
        assert len(params['pww']) == 12
        assert len(params['pwd']) == 12
        assert len(params['alpha']) == 12
        assert len(params['beta']) == 12
        
        # Check all probabilities are in [0, 1]
        for pww in params['pww']:
            assert 0 <= pww <= 1
        for pwd in params['pwd']:
            assert 0 <= pwd <= 1
        
        # Check all Gamma parameters are positive
        for alpha in params['alpha']:
            assert alpha > 0
        for beta in params['beta']:
            assert beta > 0
    
    def test_calculate_parameters_missing_column(self):
        """Test that missing required columns raise error."""
        calc = PrecipitationParameterCalculator()
        
        # Missing precipitation_mm column
        df = pd.DataFrame({
            'date': pd.date_range('2020-01-01', periods=10, freq='D')
        })
        
        with pytest.raises(ValueError, match="must have 'precipitation_mm' column"):
            calc.calculate_parameters(df)
        
        # Missing date column
        df = pd.DataFrame({
            'precipitation_mm': [1.0] * 10
        })
        
        with pytest.raises(ValueError, match="must have 'date' column"):
            calc.calculate_parameters(df)
    
    def test_wet_day_threshold_property(self):
        """Test that wet day classification respects the threshold."""
        # Test with different thresholds
        calc_01 = PrecipitationParameterCalculator(wet_day_threshold=0.1)
        calc_05 = PrecipitationParameterCalculator(wet_day_threshold=0.5)
        
        precip = pd.Series([0.0, 0.2, 0.4, 0.6, 1.0])
        
        result_01 = calc_01._classify_wet_dry(precip)
        result_05 = calc_05._classify_wet_dry(precip)
        
        # With threshold 0.1: [F, T, T, T, T]
        assert result_01.tolist() == [False, True, True, True, True]
        
        # With threshold 0.5: [F, F, F, T, T]
        assert result_05.tolist() == [False, False, False, True, True]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
