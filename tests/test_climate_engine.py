"""
Tests for climate engine and climate sources.

This module tests the ClimateEngine, TimeSeriesClimateSource, WGENClimateSource,
and ET0 calculation.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from hydrosim.climate import ClimateState, SiteConfig
from hydrosim.climate_engine import ClimateEngine
from hydrosim.climate_sources import TimeSeriesClimateSource, WGENClimateSource
from hydrosim.wgen import WGENParams, WGENState


def test_time_series_climate_source_creation():
    """Test creating TimeSeriesClimateSource from DataFrame."""
    dates = pd.date_range('2024-01-01', periods=10, freq='D')
    data = pd.DataFrame({
        'precip': np.random.rand(10) * 10,
        't_max': np.random.rand(10) * 10 + 20,
        't_min': np.random.rand(10) * 10 + 10,
        'solar': np.random.rand(10) * 10 + 15
    }, index=dates)
    
    source = TimeSeriesClimateSource(data)
    
    assert source.precip_col == 'precip'
    assert source.tmax_col == 't_max'
    assert source.tmin_col == 't_min'
    assert source.solar_col == 'solar'


def test_time_series_climate_source_get_data():
    """Test getting climate data from TimeSeriesClimateSource."""
    dates = pd.date_range('2024-01-01', periods=5, freq='D')
    data = pd.DataFrame({
        'precip': [5.0, 10.0, 0.0, 2.5, 7.5],
        't_max': [25.0, 26.0, 27.0, 24.0, 23.0],
        't_min': [15.0, 16.0, 17.0, 14.0, 13.0],
        'solar': [20.0, 21.0, 22.0, 19.0, 18.0]
    }, index=dates)
    
    source = TimeSeriesClimateSource(data)
    
    # Test getting data for specific date
    precip, t_max, t_min, solar = source.get_climate_data(datetime(2024, 1, 2))
    assert precip == 10.0
    assert t_max == 26.0
    assert t_min == 16.0
    assert solar == 21.0


def test_time_series_climate_source_missing_date():
    """Test error handling for missing date."""
    dates = pd.date_range('2024-01-01', periods=5, freq='D')
    data = pd.DataFrame({
        'precip': [5.0, 10.0, 0.0, 2.5, 7.5],
        't_max': [25.0, 26.0, 27.0, 24.0, 23.0],
        't_min': [15.0, 16.0, 17.0, 14.0, 13.0],
        'solar': [20.0, 21.0, 22.0, 19.0, 18.0]
    }, index=dates)
    
    source = TimeSeriesClimateSource(data)
    
    from hydrosim.exceptions import ClimateDataError
    with pytest.raises(ClimateDataError):
        source.get_climate_data(datetime(2024, 2, 1))


def test_wgen_climate_source_creation():
    """Test creating WGENClimateSource."""
    params = WGENParams(
        pww=[0.5] * 12,
        pwd=[0.3] * 12,
        alpha=[1.0] * 12,
        beta=[10.0] * 12,
        txmd=20.0,
        atx=10.0,
        txmw=18.0,
        tn=10.0,
        atn=8.0,
        cvtx=0.1,
        acvtx=0.05,
        cvtn=0.1,
        acvtn=0.05,
        rmd=15.0,
        ar=5.0,
        rmw=12.0,
        latitude=40.0,
        random_seed=42
    )
    
    source = WGENClimateSource(params, datetime(2024, 1, 1))
    
    assert source.params == params
    assert source.state.current_date == datetime(2024, 1, 1).date()


def test_wgen_climate_source_get_data():
    """Test getting climate data from WGENClimateSource."""
    params = WGENParams(
        pww=[0.5] * 12,
        pwd=[0.3] * 12,
        alpha=[1.0] * 12,
        beta=[10.0] * 12,
        txmd=20.0,
        atx=10.0,
        txmw=18.0,
        tn=10.0,
        atn=8.0,
        cvtx=0.1,
        acvtx=0.05,
        cvtn=0.1,
        acvtn=0.05,
        rmd=15.0,
        ar=5.0,
        rmw=12.0,
        latitude=40.0,
        random_seed=42
    )
    
    source = WGENClimateSource(params, datetime(2024, 1, 1))
    
    # Get data for first day
    precip, t_max, t_min, solar = source.get_climate_data(datetime(2024, 1, 1))
    
    # Check that values are reasonable
    assert precip >= 0
    assert -50 < t_max < 50  # Reasonable temperature range
    assert -50 < t_min < 50
    assert solar >= 0


def test_wgen_climate_source_sequential():
    """Test that WGEN generates data sequentially."""
    params = WGENParams(
        pww=[0.5] * 12,
        pwd=[0.3] * 12,
        alpha=[1.0] * 12,
        beta=[10.0] * 12,
        txmd=20.0,
        atx=10.0,
        txmw=18.0,
        tn=10.0,
        atn=8.0,
        cvtx=0.1,
        acvtx=0.05,
        cvtn=0.1,
        acvtn=0.05,
        rmd=15.0,
        ar=5.0,
        rmw=12.0,
        latitude=40.0,
        random_seed=42
    )
    
    source = WGENClimateSource(params, datetime(2024, 1, 1))
    
    # Get data for first day
    source.get_climate_data(datetime(2024, 1, 1))
    
    # Try to get data for non-sequential date
    with pytest.raises(ValueError):
        source.get_climate_data(datetime(2024, 1, 3))


def test_climate_engine_with_time_series():
    """Test ClimateEngine with TimeSeriesClimateSource."""
    dates = pd.date_range('2024-01-01', periods=5, freq='D')
    data = pd.DataFrame({
        'precip': [5.0, 10.0, 0.0, 2.5, 7.5],
        't_max': [25.0, 26.0, 27.0, 24.0, 23.0],
        't_min': [15.0, 16.0, 17.0, 14.0, 13.0],
        'solar': [20.0, 21.0, 22.0, 19.0, 18.0]
    }, index=dates)
    
    source = TimeSeriesClimateSource(data)
    site_config = SiteConfig(latitude=40.0, elevation=1000.0)
    
    engine = ClimateEngine(source, site_config, datetime(2024, 1, 1))
    
    # Step through first day
    state = engine.step()
    
    assert state.date == datetime(2024, 1, 1)
    assert state.precip == 5.0
    assert state.t_max == 25.0
    assert state.t_min == 15.0
    assert state.solar == 20.0
    assert state.et0 > 0  # ET0 should be calculated


def test_climate_engine_with_wgen():
    """Test ClimateEngine with WGENClimateSource."""
    params = WGENParams(
        pww=[0.5] * 12,
        pwd=[0.3] * 12,
        alpha=[1.0] * 12,
        beta=[10.0] * 12,
        txmd=20.0,
        atx=10.0,
        txmw=18.0,
        tn=10.0,
        atn=8.0,
        cvtx=0.1,
        acvtx=0.05,
        cvtn=0.1,
        acvtn=0.05,
        rmd=15.0,
        ar=5.0,
        rmw=12.0,
        latitude=40.0,
        random_seed=42
    )
    
    source = WGENClimateSource(params, datetime(2024, 1, 1))
    site_config = SiteConfig(latitude=40.0, elevation=1000.0)
    
    engine = ClimateEngine(source, site_config, datetime(2024, 1, 1))
    
    # Step through first day
    state = engine.step()
    
    assert state.date == datetime(2024, 1, 1)
    assert state.precip >= 0
    assert state.et0 >= 0  # ET0 should be non-negative (can be 0 if temp range is negative)


def test_climate_engine_timestep_progression():
    """Test that ClimateEngine advances timesteps correctly."""
    dates = pd.date_range('2024-01-01', periods=5, freq='D')
    data = pd.DataFrame({
        'precip': [5.0, 10.0, 0.0, 2.5, 7.5],
        't_max': [25.0, 26.0, 27.0, 24.0, 23.0],
        't_min': [15.0, 16.0, 17.0, 14.0, 13.0],
        'solar': [20.0, 21.0, 22.0, 19.0, 18.0]
    }, index=dates)
    
    source = TimeSeriesClimateSource(data)
    site_config = SiteConfig(latitude=40.0, elevation=1000.0)
    
    engine = ClimateEngine(source, site_config, datetime(2024, 1, 1))
    
    # Step through multiple days
    state1 = engine.step()
    assert state1.date == datetime(2024, 1, 1)
    
    state2 = engine.step()
    assert state2.date == datetime(2024, 1, 2)
    
    state3 = engine.step()
    assert state3.date == datetime(2024, 1, 3)


def test_hargreaves_et0_calculation():
    """Test Hargreaves ET0 calculation."""
    et0 = ClimateEngine.calculate_et0_hargreaves(
        t_max=30.0,
        t_min=20.0,
        solar=25.0,
        latitude=40.0,
        date=datetime(2024, 6, 15)
    )
    
    # ET0 should be positive
    assert et0 > 0
    
    # ET0 should be reasonable (typically 2-8 mm/day)
    assert 0 < et0 < 20


def test_hargreaves_et0_zero_temp_range():
    """Test ET0 calculation with zero temperature range."""
    et0 = ClimateEngine.calculate_et0_hargreaves(
        t_max=25.0,
        t_min=25.0,
        solar=20.0,
        latitude=40.0,
        date=datetime(2024, 6, 15)
    )
    
    # ET0 should still be non-negative
    assert et0 >= 0


def test_hargreaves_et0_negative_temp_range():
    """Test ET0 calculation with negative temperature range (error case)."""
    et0 = ClimateEngine.calculate_et0_hargreaves(
        t_max=20.0,
        t_min=25.0,  # Min > Max (error in data)
        solar=20.0,
        latitude=40.0,
        date=datetime(2024, 6, 15)
    )
    
    # ET0 should handle this gracefully and return non-negative
    assert et0 >= 0


def test_extraterrestrial_radiation_calculation():
    """Test extraterrestrial radiation calculation."""
    # Summer solstice in Northern Hemisphere
    r_a_summer = ClimateEngine.calculate_extraterrestrial_radiation(
        latitude=40.0,
        day_of_year=172
    )
    
    # Winter solstice in Northern Hemisphere
    r_a_winter = ClimateEngine.calculate_extraterrestrial_radiation(
        latitude=40.0,
        day_of_year=355
    )
    
    # Summer should have more radiation than winter
    assert r_a_summer > r_a_winter
    
    # Both should be positive
    assert r_a_summer > 0
    assert r_a_winter > 0
