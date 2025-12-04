"""
Tests for generator and demand strategies.

This module tests the concrete strategy implementations:
TimeSeriesStrategy, HydrologyStrategy, Snow17Model, and AWBMModel.
"""

import pytest
import pandas as pd
from datetime import datetime
from hydrosim.climate import ClimateState
from hydrosim.strategies import (
    TimeSeriesStrategy,
    HydrologyStrategy,
    Snow17Model,
    AWBMModel,
    MunicipalDemand,
    AgricultureDemand,
)


def create_test_climate(precip: float = 10.0, t_max: float = 25.0, 
                       t_min: float = 15.0, et0: float = 5.0) -> ClimateState:
    """Create a test climate state."""
    return ClimateState(
        date=datetime(2024, 1, 1),
        precip=precip,
        t_max=t_max,
        t_min=t_min,
        solar=20.0,
        et0=et0
    )


# TimeSeriesStrategy Tests

def test_timeseries_strategy_creation():
    """Test TimeSeriesStrategy initialization."""
    data = pd.DataFrame({'inflow': [10.0, 20.0, 30.0]})
    strategy = TimeSeriesStrategy(data, 'inflow')
    
    assert strategy.column == 'inflow'
    assert strategy.current_index == 0


def test_timeseries_strategy_generate():
    """Test TimeSeriesStrategy generates values from data."""
    data = pd.DataFrame({'inflow': [10.0, 20.0, 30.0]})
    strategy = TimeSeriesStrategy(data, 'inflow')
    climate = create_test_climate()
    
    assert strategy.generate(climate) == 10.0
    assert strategy.generate(climate) == 20.0
    assert strategy.generate(climate) == 30.0


def test_timeseries_strategy_exhausted():
    """Test TimeSeriesStrategy raises error when data exhausted."""
    data = pd.DataFrame({'inflow': [10.0, 20.0]})
    strategy = TimeSeriesStrategy(data, 'inflow')
    climate = create_test_climate()
    
    strategy.generate(climate)
    strategy.generate(climate)
    
    with pytest.raises(IndexError):
        strategy.generate(climate)


# Snow17Model Tests

def test_snow17_creation():
    """Test Snow17Model initialization."""
    model = Snow17Model(melt_factor=2.5, rain_temp=2.0, snow_temp=0.0)
    
    assert model.melt_factor == 2.5
    assert model.rain_temp == 2.0
    assert model.snow_temp == 0.0
    assert model.snowpack == 0.0


def test_snow17_all_rain():
    """Test Snow17Model with warm temperatures (all rain)."""
    model = Snow17Model()
    
    rain, melt = model.step(precip=10.0, t_max=15.0, t_min=5.0)
    
    # t_avg = 10.0, above rain_temp (2.0), so all rain
    assert rain == 10.0
    assert melt == 0.0
    assert model.snowpack == 0.0


def test_snow17_all_snow():
    """Test Snow17Model with cold temperatures (all snow)."""
    model = Snow17Model()
    
    rain, melt = model.step(precip=10.0, t_max=-5.0, t_min=-10.0)
    
    # t_avg = -7.5, below snow_temp (0.0), so all snow
    assert rain == 0.0
    assert melt == 0.0
    assert model.snowpack == 10.0


def test_snow17_mixed_precipitation():
    """Test Snow17Model with mixed rain/snow."""
    model = Snow17Model(rain_temp=2.0, snow_temp=0.0)
    
    rain, melt = model.step(precip=10.0, t_max=2.0, t_min=0.0)
    
    # t_avg = 1.0, between snow_temp and rain_temp
    # rain_fraction = (1.0 - 0.0) / (2.0 - 0.0) = 0.5
    assert rain == pytest.approx(5.0)
    # t_avg = 1.0 > 0, so potential_melt = 2.5 * 1.0 = 2.5
    # Snow added = 5.0, actual_melt = min(2.5, 5.0) = 2.5
    assert melt == pytest.approx(2.5)
    assert model.snowpack == pytest.approx(2.5)  # 5.0 snow - 2.5 melt


def test_snow17_snowmelt():
    """Test Snow17Model snowmelt calculation."""
    model = Snow17Model(melt_factor=2.5)
    
    # First accumulate snow
    model.step(precip=10.0, t_max=-5.0, t_min=-10.0)
    assert model.snowpack == 10.0
    
    # Then melt with warm temperatures
    rain, melt = model.step(precip=0.0, t_max=10.0, t_min=2.0)
    
    # t_avg = 6.0, potential_melt = 2.5 * 6.0 = 15.0
    # actual_melt = min(15.0, 10.0) = 10.0
    assert melt == 10.0
    assert model.snowpack == 0.0


def test_snow17_partial_melt():
    """Test Snow17Model partial snowmelt."""
    model = Snow17Model(melt_factor=2.5)
    
    # Accumulate snow
    model.step(precip=20.0, t_max=-5.0, t_min=-10.0)
    assert model.snowpack == 20.0
    
    # Partial melt
    rain, melt = model.step(precip=0.0, t_max=4.0, t_min=0.0)
    
    # t_avg = 2.0, potential_melt = 2.5 * 2.0 = 5.0
    assert melt == 5.0
    assert model.snowpack == 15.0


# AWBMModel Tests

def test_awbm_creation():
    """Test AWBMModel initialization."""
    model = AWBMModel(c1=0.134, c2=0.433, c3=0.433)
    
    assert model.c1 == 0.134
    assert model.c2 == 0.433
    assert model.c3 == 0.433
    assert model.s1 == 0.0
    assert model.s2 == 0.0
    assert model.s3 == 0.0


def test_awbm_no_runoff_dry():
    """Test AWBMModel with no precipitation."""
    model = AWBMModel()
    
    runoff = model.step(precip=0.0, et0=5.0)
    
    # No precip, so no runoff
    assert runoff == 0.0


def test_awbm_generates_runoff():
    """Test AWBMModel generates runoff with precipitation."""
    model = AWBMModel(c1=10.0, c2=20.0, c3=30.0)
    
    # Large precipitation to generate runoff
    runoff = model.step(precip=50.0, et0=2.0)
    
    # Should generate some runoff
    assert runoff > 0.0


def test_awbm_stores_update():
    """Test AWBMModel updates store levels."""
    model = AWBMModel(c1=10.0, c2=20.0, c3=30.0)
    
    # Add precipitation
    model.step(precip=5.0, et0=1.0)
    
    # Stores should have increased
    assert model.s1 > 0.0
    assert model.s2 > 0.0
    assert model.s3 > 0.0


# HydrologyStrategy Tests

def test_hydrology_strategy_creation():
    """Test HydrologyStrategy initialization."""
    snow17_params = {'melt_factor': 2.5, 'rain_temp': 2.0, 'snow_temp': 0.0}
    awbm_params = {'c1': 0.134, 'c2': 0.433, 'c3': 0.433}
    area = 1000000.0  # 1 km² in m²
    
    strategy = HydrologyStrategy(snow17_params, awbm_params, area)
    
    assert strategy.area == area
    assert isinstance(strategy.snow17, Snow17Model)
    assert isinstance(strategy.awbm, AWBMModel)


def test_hydrology_strategy_generate_warm():
    """Test HydrologyStrategy with warm weather (rain only)."""
    snow17_params = {'melt_factor': 2.5, 'rain_temp': 2.0, 'snow_temp': 0.0}
    awbm_params = {'c1': 10.0, 'c2': 20.0, 'c3': 30.0}
    area = 1000000.0  # 1 km² in m²
    
    strategy = HydrologyStrategy(snow17_params, awbm_params, area)
    climate = create_test_climate(precip=50.0, t_max=20.0, t_min=10.0, et0=5.0)
    
    inflow = strategy.generate(climate)
    
    # Should generate some inflow
    assert inflow > 0.0


def test_hydrology_strategy_generate_cold():
    """Test HydrologyStrategy with cold weather (snow accumulation)."""
    snow17_params = {'melt_factor': 2.5, 'rain_temp': 2.0, 'snow_temp': 0.0}
    awbm_params = {'c1': 10.0, 'c2': 20.0, 'c3': 30.0}
    area = 1000000.0  # 1 km² in m²
    
    strategy = HydrologyStrategy(snow17_params, awbm_params, area)
    climate = create_test_climate(precip=10.0, t_max=-5.0, t_min=-10.0, et0=0.0)
    
    inflow = strategy.generate(climate)
    
    # Cold weather, snow accumulates, minimal runoff
    assert inflow >= 0.0
    assert strategy.snow17.snowpack > 0.0


def test_hydrology_strategy_volume_conversion():
    """Test HydrologyStrategy converts depth to volume correctly."""
    snow17_params = {'melt_factor': 2.5, 'rain_temp': 2.0, 'snow_temp': 0.0}
    awbm_params = {'c1': 10.0, 'c2': 20.0, 'c3': 30.0}
    area = 1000000.0  # 1 km² in m²
    
    strategy = HydrologyStrategy(snow17_params, awbm_params, area)
    
    # Mock the AWBM to return a known runoff depth
    strategy.awbm.step = lambda p, e: 10.0  # 10 mm runoff
    
    climate = create_test_climate(precip=50.0, t_max=20.0, t_min=10.0, et0=5.0)
    inflow = strategy.generate(climate)
    
    # 10 mm over 1,000,000 m² = 10,000 m³
    assert inflow == pytest.approx(10000.0)


# MunicipalDemand Tests

def test_municipal_demand_creation():
    """Test MunicipalDemand initialization."""
    demand = MunicipalDemand(population=10000.0, per_capita_demand=0.2)
    
    assert demand.population == 10000.0
    assert demand.per_capita_demand == 0.2


def test_municipal_demand_calculate():
    """Test MunicipalDemand calculates demand correctly."""
    demand = MunicipalDemand(population=10000.0, per_capita_demand=0.2)
    climate = create_test_climate()
    
    result = demand.calculate(climate)
    
    # 10000 people * 0.2 m³/person/day = 2000 m³/day
    assert result == 2000.0


def test_municipal_demand_independent_of_climate():
    """Test MunicipalDemand is independent of climate conditions."""
    demand = MunicipalDemand(population=5000.0, per_capita_demand=0.15)
    
    climate1 = create_test_climate(et0=5.0)
    climate2 = create_test_climate(et0=10.0)
    
    # Should be the same regardless of climate
    assert demand.calculate(climate1) == demand.calculate(climate2)
    assert demand.calculate(climate1) == 750.0  # 5000 * 0.15


# AgricultureDemand Tests

def test_agriculture_demand_creation():
    """Test AgricultureDemand initialization."""
    demand = AgricultureDemand(area=100000.0, crop_coefficient=0.8)
    
    assert demand.area == 100000.0
    assert demand.kc == 0.8


def test_agriculture_demand_calculate():
    """Test AgricultureDemand calculates demand correctly."""
    demand = AgricultureDemand(area=100000.0, crop_coefficient=0.8)
    climate = create_test_climate(et0=5.0)
    
    result = demand.calculate(climate)
    
    # ET_crop = 0.8 * 5.0 = 4.0 mm
    # Volume = 4.0 mm * 100000 m² / 1000 = 400 m³
    assert result == pytest.approx(400.0)


def test_agriculture_demand_varies_with_et0():
    """Test AgricultureDemand varies with ET0."""
    demand = AgricultureDemand(area=100000.0, crop_coefficient=0.8)
    
    climate1 = create_test_climate(et0=5.0)
    climate2 = create_test_climate(et0=10.0)
    
    result1 = demand.calculate(climate1)
    result2 = demand.calculate(climate2)
    
    # Higher ET0 should result in higher demand
    assert result2 > result1
    assert result2 == pytest.approx(2.0 * result1)  # ET0 doubled, so demand doubles


def test_agriculture_demand_zero_et0():
    """Test AgricultureDemand with zero ET0."""
    demand = AgricultureDemand(area=100000.0, crop_coefficient=0.8)
    climate = create_test_climate(et0=0.0)
    
    result = demand.calculate(climate)
    
    # Zero ET0 means zero demand
    assert result == 0.0


def test_agriculture_demand_different_crop_coefficients():
    """Test AgricultureDemand with different crop coefficients."""
    area = 100000.0
    climate = create_test_climate(et0=5.0)
    
    demand_low = AgricultureDemand(area=area, crop_coefficient=0.5)
    demand_high = AgricultureDemand(area=area, crop_coefficient=1.2)
    
    result_low = demand_low.calculate(climate)
    result_high = demand_high.calculate(climate)
    
    # Higher Kc should result in higher demand
    assert result_high > result_low
    assert result_low == pytest.approx(250.0)  # 0.5 * 5.0 * 100000 / 1000
    assert result_high == pytest.approx(600.0)  # 1.2 * 5.0 * 100000 / 1000
