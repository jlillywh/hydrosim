"""
Climate Data Acquisition & Parameterization Module for HydroSim.

This module provides tools for:
1. Fetching observed climate data from NOAA GHCN stations
2. Generating WGEN statistical parameters from observed data
3. Running simulations with observed or synthetic climate data

The module enforces rigid consistency rules:
- Precipitation and Temperature must both be observed OR both be synthetic
- Solar Radiation is always generated synthetically using WGEN algorithms

Example Usage:
    # Fetch data and generate parameters
    from hydrosim.climate_builder import GHCNDataFetcher, WGENParameterGenerator
    
    fetcher = GHCNDataFetcher("USW00024233", output_dir="./my_project")
    dly_path = fetcher.download_dly_file()
    observed_df = fetcher.parse_dly_file(dly_path)
    fetcher.save_processed_data(observed_df)
    
    generator = WGENParameterGenerator(
        observed_data_path="./my_project/data/processed/observed_climate.csv",
        latitude=47.45,
        output_dir="./my_project"
    )
    params = generator.generate_all_parameters()
    generator.save_parameters_to_csv(params)
    
    # Run simulation with climate driver
    from hydrosim.climate_builder import HistoricalClimateDriver
    
    driver = HistoricalClimateDriver(config={
        'mode': 'historical',
        'observed_data_file': 'data/processed/observed_climate.csv',
        'wgen_params_file': 'data/processed/wgen_params.csv',
        'latitude': 47.45
    })
    
    climate_data = driver.get_climate_for_date(datetime.date(2020, 1, 15))
"""

from hydrosim.climate_builder.data_models import (
    ObservedClimateData,
    ClimateData,
    DataQualityReport,
)
from hydrosim.climate_builder.project_structure import (
    ProjectStructure,
)
from hydrosim.climate_builder.ghcn_fetcher import (
    GHCNDataFetcher,
)
from hydrosim.climate_builder.dly_parser import (
    DLYParser,
)
from hydrosim.climate_builder.data_quality import (
    DataQualityValidator,
)
from hydrosim.climate_builder.precipitation_params import (
    PrecipitationParameterCalculator,
)
from hydrosim.climate_builder.temperature_params import (
    TemperatureParameterCalculator,
)
from hydrosim.climate_builder.solar_params import (
    SolarParameterCalculator,
)
from hydrosim.climate_builder.parameter_generator import (
    WGENParameterGenerator,
)
from hydrosim.climate_builder.parameter_csv import (
    ParameterCSVWriter,
)

__all__ = [
    'ObservedClimateData',
    'ClimateData',
    'DataQualityReport',
    'ProjectStructure',
    'GHCNDataFetcher',
    'DLYParser',
    'DataQualityValidator',
    'PrecipitationParameterCalculator',
    'TemperatureParameterCalculator',
    'SolarParameterCalculator',
    'WGENParameterGenerator',
    'ParameterCSVWriter',
]

__version__ = "0.1.0"
