"""
Climate data sources for the HydroSim framework.

This module provides different sources of climate data including time series
from CSV files and stochastic generation using WGEN.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Tuple, Optional
import pandas as pd
import logging
from hydrosim.wgen import WGENParams, WGENState, wgen_step
from hydrosim.exceptions import ClimateDataError

# Configure logger
logger = logging.getLogger(__name__)


class ClimateSource(ABC):
    """Abstract base class for climate data sources."""
    
    @abstractmethod
    def get_climate_data(self, date: datetime) -> Tuple[float, float, float, float]:
        """Get climate data for a specific date.
        
        Args:
            date: Date to get climate data for
            
        Returns:
            Tuple of (precip, t_max, t_min, solar) in mm, °C, °C, MJ/m²/day
        """
        pass


class TimeSeriesClimateSource(ClimateSource):
    """Climate source that reads from time series data (CSV).
    
    Attributes:
        data: DataFrame with columns for date, precip, t_max, t_min, solar
        precip_col: Name of precipitation column
        tmax_col: Name of maximum temperature column
        tmin_col: Name of minimum temperature column
        solar_col: Name of solar radiation column
        start_date: First date in the time series
        end_date: Last date in the time series
    """
    
    def __init__(self, 
                 data: pd.DataFrame,
                 precip_col: str = 'precip',
                 tmax_col: str = 't_max',
                 tmin_col: str = 't_min',
                 solar_col: str = 'solar'):
        """Initialize time series climate source.
        
        Args:
            data: DataFrame with climate data indexed by date
            precip_col: Name of precipitation column (mm)
            tmax_col: Name of maximum temperature column (°C)
            tmin_col: Name of minimum temperature column (°C)
            solar_col: Name of solar radiation column (MJ/m²/day)
        """
        self.data = data
        self.precip_col = precip_col
        self.tmax_col = tmax_col
        self.tmin_col = tmin_col
        self.solar_col = solar_col
        
        # Validate required columns exist
        required_cols = [precip_col, tmax_col, tmin_col, solar_col]
        missing_cols = [col for col in required_cols if col not in data.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        # Store date range for error messages
        if len(data) > 0:
            self.start_date = data.index.min()
            self.end_date = data.index.max()
        else:
            self.start_date = None
            self.end_date = None
    
    @classmethod
    def from_csv(cls, 
                 filepath: str,
                 date_col: str = 'date',
                 precip_col: str = 'precip',
                 tmax_col: str = 't_max',
                 tmin_col: str = 't_min',
                 solar_col: str = 'solar') -> 'TimeSeriesClimateSource':
        """Create climate source from CSV file.
        
        Args:
            filepath: Path to CSV file
            date_col: Name of date column
            precip_col: Name of precipitation column
            tmax_col: Name of maximum temperature column
            tmin_col: Name of minimum temperature column
            solar_col: Name of solar radiation column
            
        Returns:
            TimeSeriesClimateSource instance
        """
        data = pd.read_csv(filepath, parse_dates=[date_col])
        data = data.set_index(date_col)
        return cls(data, precip_col, tmax_col, tmin_col, solar_col)
    
    def validate_date_range(self, start_date: datetime, end_date: datetime) -> None:
        """
        Validate that climate data is available for the entire simulation period.
        
        Args:
            start_date: Start date of simulation
            end_date: End date of simulation
            
        Raises:
            ClimateDataError: If any part of the simulation period is outside available data
        """
        if self.start_date is None or self.end_date is None:
            raise ClimateDataError(
                start_date,
                available_range=None,
                source_type="timeseries"
            )
        
        if start_date < self.start_date:
            raise ClimateDataError(
                start_date,
                available_range=(self.start_date, self.end_date),
                source_type="timeseries"
            )
        
        if end_date > self.end_date:
            raise ClimateDataError(
                end_date,
                available_range=(self.start_date, self.end_date),
                source_type="timeseries"
            )
    
    def get_climate_data(self, date: datetime) -> Tuple[float, float, float, float]:
        """Get climate data for a specific date.
        
        Args:
            date: Date to get climate data for
            
        Returns:
            Tuple of (precip, t_max, t_min, solar)
            
        Raises:
            ClimateDataError: If date is not in the time series
        """
        try:
            row = self.data.loc[date]
            return (
                float(row[self.precip_col]),
                float(row[self.tmax_col]),
                float(row[self.tmin_col]),
                float(row[self.solar_col])
            )
        except KeyError:
            # Provide helpful error message with available date range
            available_range = None
            if self.start_date is not None and self.end_date is not None:
                available_range = (self.start_date, self.end_date)
            
            raise ClimateDataError(
                date,
                available_range=available_range,
                source_type="timeseries"
            )


class WGENClimateSource(ClimateSource):
    """Climate source that generates stochastic weather using WGEN.
    
    Attributes:
        params: WGEN parameters
        state: Current WGEN state
    """
    
    def __init__(self, params: WGENParams, initial_date: datetime):
        """Initialize WGEN climate source.
        
        Args:
            params: WGEN parameters
            initial_date: Starting date for generation
        """
        self.params = params
        self.state = WGENState(
            is_wet=False,
            random_state=None,
            current_date=initial_date.date() if isinstance(initial_date, datetime) else initial_date
        )
    
    def get_climate_data(self, date: datetime) -> Tuple[float, float, float, float]:
        """Get climate data for a specific date.
        
        Note: WGEN generates data sequentially, so dates must be requested
        in order. The date parameter is used for validation but the actual
        date comes from the internal state.
        
        Args:
            date: Date to get climate data for (must match internal state)
            
        Returns:
            Tuple of (precip, t_max, t_min, solar)
            
        Raises:
            ValueError: If requested date doesn't match internal state
        """
        # Validate date matches internal state
        expected_date = self.state.current_date
        request_date = date.date() if isinstance(date, datetime) else date
        
        if request_date != expected_date:
            raise ValueError(
                f"WGEN must generate dates sequentially. "
                f"Expected {expected_date}, got {request_date}"
            )
        
        # Generate next day's weather
        self.state, outputs = wgen_step(self.params, self.state)
        
        return (
            outputs.precip_mm,
            outputs.tmax_c,
            outputs.tmin_c,
            outputs.solar_mjm2
        )
