"""
Climate engine for managing temporal and climatic context.

The climate engine manages timestep progression and calculates derived
climate variables like reference evapotranspiration (ET0).
"""

from datetime import datetime, timedelta
import numpy as np
from hydrosim.climate import ClimateState, SiteConfig
from hydrosim.climate_sources import ClimateSource


class ClimateEngine:
    """Manages climate data and timestep progression.
    
    The climate engine coordinates climate data sources, calculates ET0,
    and broadcasts climate state to the simulation.
    
    Attributes:
        source: Climate data source (TimeSeriesClimateSource or WGENClimateSource)
        site_config: Site configuration for ET0 calculation
        current_date: Current simulation date
        current_state: Current climate state
    """
    
    def __init__(self, 
                 source: ClimateSource,
                 site_config: SiteConfig,
                 start_date: datetime):
        """Initialize climate engine.
        
        Args:
            source: Climate data source
            site_config: Site configuration (latitude, elevation)
            start_date: Starting date for simulation
        """
        self.source = source
        self.site_config = site_config
        self.current_date = start_date
        self.current_state = None
    
    def step(self) -> ClimateState:
        """Advance one timestep and update climate state.
        
        Returns:
            Updated climate state with calculated ET0
        """
        # Get climate data from source
        precip, t_max, t_min, solar = self.source.get_climate_data(self.current_date)
        
        # Calculate ET0 using Hargreaves method
        et0 = self.calculate_et0_hargreaves(
            t_max, t_min, solar, 
            self.site_config.latitude,
            self.current_date
        )
        
        # Create climate state
        self.current_state = ClimateState(
            date=self.current_date,
            precip=precip,
            t_max=t_max,
            t_min=t_min,
            solar=solar,
            et0=et0
        )
        
        # Advance date by one day
        self.current_date += timedelta(days=1)
        
        return self.current_state
    
    def get_current_state(self) -> ClimateState:
        """Get current climate state without advancing timestep.
        
        Returns:
            Current climate state
            
        Raises:
            RuntimeError: If step() has not been called yet
        """
        if self.current_state is None:
            raise RuntimeError("Climate engine has not been stepped yet")
        return self.current_state
    
    @staticmethod
    def calculate_et0_hargreaves(t_max: float,
                                 t_min: float,
                                 solar: float,
                                 latitude: float,
                                 date: datetime) -> float:
        """Calculate reference evapotranspiration using Hargreaves method.
        
        Formula: ET0 = 0.0023 × (T_mean + 17.8) × (T_max - T_min)^0.5 × R_a
        
        Where:
            - T_mean = (T_max + T_min) / 2
            - R_a = extraterrestrial radiation (calculated from latitude and day of year)
        
        Args:
            t_max: Maximum temperature (°C)
            t_min: Minimum temperature (°C)
            solar: Solar radiation (MJ/m²/day) - used as proxy for R_a if available
            latitude: Site latitude (degrees)
            date: Date for calculation
            
        Returns:
            Reference evapotranspiration (mm/day)
        """
        # Calculate mean temperature
        t_mean = (t_max + t_min) / 2.0
        
        # Calculate temperature range
        temp_range = t_max - t_min
        
        # Ensure non-negative temperature range
        if temp_range < 0:
            temp_range = 0
        
        # Calculate extraterrestrial radiation if not using solar directly
        # For simplicity, we use the provided solar radiation as R_a
        # In a more complete implementation, this would be calculated from
        # latitude, day of year, and solar declination
        r_a = solar
        
        # Hargreaves formula
        et0 = 0.0023 * (t_mean + 17.8) * np.sqrt(temp_range) * r_a
        
        # Ensure non-negative ET0
        return max(0.0, et0)
    
    @staticmethod
    def calculate_extraterrestrial_radiation(latitude: float,
                                            day_of_year: int) -> float:
        """Calculate extraterrestrial radiation.
        
        This is a simplified calculation. A complete implementation would
        use the FAO-56 method with solar declination, sunset hour angle, etc.
        
        Args:
            latitude: Site latitude (degrees)
            day_of_year: Day of year (1-365/366)
            
        Returns:
            Extraterrestrial radiation (MJ/m²/day)
        """
        # Convert latitude to radians
        lat_rad = np.radians(latitude)
        
        # Solar declination (simplified)
        declination = 0.409 * np.sin(2 * np.pi * day_of_year / 365 - 1.39)
        
        # Sunset hour angle
        sunset_angle = np.arccos(-np.tan(lat_rad) * np.tan(declination))
        
        # Inverse relative distance Earth-Sun
        dr = 1 + 0.033 * np.cos(2 * np.pi * day_of_year / 365)
        
        # Solar constant
        gsc = 0.0820  # MJ/m²/min
        
        # Extraterrestrial radiation
        r_a = (24 * 60 / np.pi) * gsc * dr * (
            sunset_angle * np.sin(lat_rad) * np.sin(declination) +
            np.cos(lat_rad) * np.cos(declination) * np.sin(sunset_angle)
        )
        
        return max(0.0, r_a)
