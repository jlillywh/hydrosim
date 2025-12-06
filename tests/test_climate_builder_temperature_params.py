"""
Tests for temperature parameter calculator.

This module tests the TemperatureParameterCalculator class, which calculates
WGEN temperature parameters from observed data.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from hydrosim.climate_builder.temperature_params import TemperatureParameterCalculator


class TestTemperatureParameterCalculator:
    """Test suite for TemperatureParameterCalculator."""
    
    def test_initialization(self):
        """Test calculator initialization with valid parameters."""
        calc = TemperatureParameterCalculator(wet_day_threshold=0.1, num_periods=13)
        assert calc.wet_day_threshold == 0.1
        assert calc.num_periods == 13
        assert calc.days_per_period == 28
    
    def test_initialization_invalid_threshold(self):
        """Test that negative threshold raises error."""
        with pytest.raises(ValueError, match="wet_day_threshold must be non-negative"):
            TemperatureParameterCalculator(wet_day_threshold=-0.1)
    
    def test_initialization_invalid_periods(self):
        """Test that invalid num_periods raises error."""
        with pytest.raises(ValueError, match="num_periods must be positive"):
            TemperatureParameterCalculator(num_periods=0)
    
    def test_assign_periods(self):
        """Test period assignment for dates."""
        calc = TemperatureParameterCalculator()
        
        # Create dates spanning the year
        dates = pd.date_range('2020-01-01', '2020-12-31', freq='D')
        df = pd.DataFrame({'date': dates})
        
        periods = calc._assign_periods(df['date'])
        
        # Check period 1 (days 1-28)
        assert periods.iloc[0] == 1  # Jan 1
        assert periods.iloc[27] == 1  # Jan 28
        
        # Check period 2 (days 29-56)
        assert periods.iloc[28] == 2  # Jan 29
        
        # Check period 13 (days 337-365)
        assert periods.iloc[336] == 13  # Dec 3
        assert periods.iloc[364] == 13  # Dec 31 (day 365 in non-leap year)
        
        # All periods should be in range 1-13
        assert periods.min() == 1
        assert periods.max() == 13
    
    def test_calculate_parameters_with_synthetic_data(self):
        """Test parameter calculation with synthetic seasonal data."""
        calc = TemperatureParameterCalculator()
        
        # Create synthetic data with clear seasonal pattern
        dates = pd.date_range('2015-01-01', '2019-12-31', freq='D')
        n_days = len(dates)
        
        # Create seasonal temperature pattern
        day_of_year = np.array([d.timetuple().tm_yday for d in dates])
        
        # Tmax: warm in summer (day 180), cold in winter
        tmax_base = 20 + 15 * np.cos(2 * np.pi * (day_of_year - 180) / 365)
        tmax = tmax_base + np.random.normal(0, 2, n_days)
        
        # Tmin: follows similar pattern but lower
        tmin_base = 10 + 10 * np.cos(2 * np.pi * (day_of_year - 180) / 365)
        tmin = tmin_base + np.random.normal(0, 2, n_days)
        
        # Precipitation: random with some wet days
        precip = np.random.exponential(5, n_days) * (np.random.random(n_days) > 0.7)
        
        df = pd.DataFrame({
            'date': dates,
            'precipitation_mm': precip,
            'tmax_c': tmax,
            'tmin_c': tmin
        })
        
        # Calculate parameters
        params = calc.calculate_parameters(df)
        
        # Check that all required parameters are present
        required_keys = ['txmd', 'atx', 'txmw', 'tn', 'atn', 'cvtx', 'acvtx', 'cvtn', 'acvtn']
        for key in required_keys:
            assert key in params, f"Missing parameter: {key}"
            assert isinstance(params[key], (int, float)), f"Parameter {key} is not numeric"
        
        # Check reasonable ranges
        # Mean temperatures should be around 20°C for tmax, 10°C for tmin
        assert 15 <= params['txmd'] <= 25, f"txmd out of range: {params['txmd']}"
        assert 15 <= params['txmw'] <= 25, f"txmw out of range: {params['txmw']}"
        assert 5 <= params['tn'] <= 15, f"tn out of range: {params['tn']}"
        
        # Amplitudes should be positive and reasonable (5-20°C)
        assert 5 <= params['atx'] <= 20, f"atx out of range: {params['atx']}"
        assert 5 <= params['atn'] <= 20, f"atn out of range: {params['atn']}"
        
        # CV should be positive values (can vary widely depending on data)
        assert params['cvtx'] >= 0, f"cvtx should be non-negative: {params['cvtx']}"
        assert params['cvtn'] >= 0, f"cvtn should be non-negative: {params['cvtn']}"
        assert params['acvtx'] >= 0, f"acvtx should be non-negative: {params['acvtx']}"
        assert params['acvtn'] >= 0, f"acvtn should be non-negative: {params['acvtn']}"
    
    def test_calculate_parameters_missing_columns(self):
        """Test that missing columns raise appropriate errors."""
        calc = TemperatureParameterCalculator()
        
        # Missing precipitation_mm
        dates = pd.date_range('2020-01-01', '2020-12-31')
        df = pd.DataFrame({
            'date': dates,
            'tmax_c': np.random.normal(20, 5, len(dates)),
            'tmin_c': np.random.normal(10, 5, len(dates))
        })
        
        with pytest.raises(ValueError, match="DataFrame must have columns"):
            calc.calculate_parameters(df)
    
    def test_calculate_period_stats_all_days(self):
        """Test period statistics calculation for all days."""
        calc = TemperatureParameterCalculator()
        
        # Create simple test data
        dates = pd.date_range('2020-01-01', '2020-12-31', freq='D')
        df = pd.DataFrame({
            'date': dates,
            'precipitation_mm': np.random.exponential(5, len(dates)),
            'tmax_c': np.random.normal(20, 5, len(dates)),
            'tmin_c': np.random.normal(10, 5, len(dates))
        })
        
        df['period'] = calc._assign_periods(df['date'])
        df['is_wet'] = df['precipitation_mm'] >= 0.1
        
        # Calculate stats for all days
        stats = calc._calculate_period_stats(df, 'tmax_c', wet_status=None)
        
        # Should have 13 periods
        assert len(stats['means']) == 13
        assert len(stats['stds']) == 13
        assert len(stats['counts']) == 13
        
        # All periods should have some data
        assert np.all(stats['counts'] > 0)
        
        # Means should be reasonable
        assert np.all(stats['means'] > 0)
        assert np.all(stats['means'] < 40)
    
    def test_calculate_period_stats_wet_dry_separation(self):
        """Test that wet and dry day statistics are calculated separately."""
        calc = TemperatureParameterCalculator()
        
        # Create data where wet days are systematically cooler
        dates = pd.date_range('2020-01-01', '2020-12-31', freq='D')
        n_days = len(dates)
        
        # Random precipitation
        precip = np.random.exponential(5, n_days) * (np.random.random(n_days) > 0.7)
        is_wet = precip >= 0.1
        
        # Tmax: cooler on wet days
        tmax = np.where(is_wet, 
                       np.random.normal(18, 3, n_days),  # Wet days: 18°C
                       np.random.normal(25, 3, n_days))  # Dry days: 25°C
        
        df = pd.DataFrame({
            'date': dates,
            'precipitation_mm': precip,
            'tmax_c': tmax,
            'tmin_c': np.random.normal(10, 3, n_days)
        })
        
        df['period'] = calc._assign_periods(df['date'])
        df['is_wet'] = is_wet
        
        # Calculate stats for wet and dry days
        wet_stats = calc._calculate_period_stats(df, 'tmax_c', wet_status=True)
        dry_stats = calc._calculate_period_stats(df, 'tmax_c', wet_status=False)
        
        # Dry day means should generally be higher than wet day means
        # (at least for most periods)
        higher_count = np.sum(dry_stats['means'] > wet_stats['means'])
        assert higher_count >= 8, "Dry days should be warmer than wet days in most periods"
    
    def test_interpolate_missing(self):
        """Test interpolation of missing values."""
        calc = TemperatureParameterCalculator()
        
        # Create array with some missing values
        values = np.array([10.0, 12.0, np.nan, 16.0, 18.0, np.nan, np.nan, 14.0, 12.0, 10.0, np.nan, 9.0, 10.0])
        
        result = calc._interpolate_missing(values)
        
        # Should have no NaN values
        assert not np.any(np.isnan(result))
        
        # Known values should be unchanged
        assert result[0] == 10.0
        assert result[1] == 12.0
        assert result[3] == 16.0
    
    def test_fit_fourier_series(self):
        """Test Fourier series fitting."""
        calc = TemperatureParameterCalculator()
        
        # Create synthetic seasonal pattern
        periods = np.arange(1, 14)
        true_mean = 20.0
        true_amplitude = 10.0
        true_phase = 7.0  # Peak in middle of year
        
        # Generate data from known Fourier series
        period_means = true_mean + true_amplitude * np.cos(2 * np.pi * (periods - true_phase) / 13)
        
        # Fit the series
        fitted_mean, fitted_amplitude = calc._fit_fourier_series(period_means)
        
        # Should recover approximately the true parameters
        assert abs(fitted_mean - true_mean) < 1.0, f"Mean mismatch: {fitted_mean} vs {true_mean}"
        assert abs(fitted_amplitude - true_amplitude) < 1.0, f"Amplitude mismatch: {fitted_amplitude} vs {true_amplitude}"
    
    def test_calculate_cv_params(self):
        """Test coefficient of variation parameter calculation."""
        calc = TemperatureParameterCalculator()
        
        # Create stats with known CV pattern
        means = np.array([20.0, 22.0, 24.0, 26.0, 28.0, 30.0, 28.0, 26.0, 24.0, 22.0, 20.0, 18.0, 19.0])
        stds = np.array([2.0, 2.2, 2.4, 2.6, 2.8, 3.0, 2.8, 2.6, 2.4, 2.2, 2.0, 1.8, 1.9])
        
        stats = {
            'means': means,
            'stds': stds,
            'counts': np.ones(13, dtype=int) * 28
        }
        
        cv_mean, cv_amplitude = calc._calculate_cv_params(stats)
        
        # CV is calculated in Kelvin to avoid near-zero division issues
        # For temps around 20°C (293.15K), CV ≈ std/293.15 ≈ 2.4/293.15 ≈ 0.008
        assert 0.005 <= cv_mean <= 0.015, f"CV mean out of range: {cv_mean}"
        
        # Amplitude should be positive
        assert cv_amplitude >= 0, f"CV amplitude should be non-negative: {cv_amplitude}"
    
    def test_with_missing_data(self):
        """Test parameter calculation with some missing data."""
        calc = TemperatureParameterCalculator()
        
        # Create data with some missing values
        dates = pd.date_range('2015-01-01', '2019-12-31', freq='D')
        n_days = len(dates)
        
        tmax = np.random.normal(20, 5, n_days)
        tmin = np.random.normal(10, 5, n_days)
        precip = np.random.exponential(5, n_days) * (np.random.random(n_days) > 0.7)
        
        # Introduce some missing values (10%)
        missing_mask = np.random.random(n_days) < 0.1
        tmax[missing_mask] = np.nan
        tmin[missing_mask] = np.nan
        
        df = pd.DataFrame({
            'date': dates,
            'precipitation_mm': precip,
            'tmax_c': tmax,
            'tmin_c': tmin
        })
        
        # Should still calculate parameters
        params = calc.calculate_parameters(df)
        
        # All parameters should be present and finite
        for key, value in params.items():
            assert np.isfinite(value), f"Parameter {key} is not finite: {value}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
