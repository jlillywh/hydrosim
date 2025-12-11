"""
Strategy pattern implementations for generation and demand calculation.

Strategies allow pluggable algorithms for inflow generation and demand modeling.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Dict, Any
import pandas as pd

if TYPE_CHECKING:
    from hydrosim.climate import ClimateState


class GeneratorStrategy(ABC):
    """Abstract base for inflow generation strategies."""
    
    @abstractmethod
    def generate(self, climate: 'ClimateState') -> float:
        """
        Generate inflow volume for current timestep.
        
        Args:
            climate: Current climate state
            
        Returns:
            Inflow volume
        """
        pass


class TimeSeriesStrategy(GeneratorStrategy):
    """Read inflows from time series data."""
    
    def __init__(self, data: pd.DataFrame, column: str):
        """
        Initialize time series strategy.
        
        Args:
            data: DataFrame containing time series data
            column: Column name containing inflow values
        """
        self.data = data
        self.column = column
        self.current_index = 0
    
    def generate(self, climate: 'ClimateState') -> float:
        """
        Generate inflow by reading from time series.
        
        Args:
            climate: Current climate state (unused for time series)
            
        Returns:
            Inflow volume from time series
        """
        if self.current_index >= len(self.data):
            raise IndexError(f"Time series data exhausted at index {self.current_index}")
        
        value = self.data.iloc[self.current_index][self.column]
        self.current_index += 1
        return float(value)
    
    def get_future_values(self, num_timesteps: int) -> List[float]:
        """
        Get future values for look-ahead optimization.
        
        Args:
            num_timesteps: Number of future timesteps to extract
            
        Returns:
            List of future inflow values
        """
        future_values = []
        start_index = self.current_index
        
        for i in range(num_timesteps):
            index = start_index + i
            if index < len(self.data):
                value = self.data.iloc[index][self.column]
                future_values.append(float(value))
            else:
                # If we run out of data, repeat the last available value
                if len(self.data) > 0:
                    last_value = self.data.iloc[-1][self.column]
                    future_values.append(float(last_value))
                else:
                    future_values.append(0.0)
        
        return future_values


class HydrologyStrategy(GeneratorStrategy):
    """Simulate runoff using Snow17 and AWBM models."""
    
    def __init__(self, snow17_params: Dict[str, Any], awbm_params: Dict[str, Any], area: float):
        """
        Initialize hydrology strategy.
        
        Args:
            snow17_params: Parameters for Snow17 snow model
            awbm_params: Parameters for AWBM rainfall-runoff model
            area: Catchment area in square meters
        """
        self.snow17 = Snow17Model(**snow17_params)
        self.awbm = AWBMModel(**awbm_params)
        self.area = area
    
    def generate(self, climate: 'ClimateState') -> float:
        """
        Generate inflow by simulating hydrology.
        
        Args:
            climate: Current climate state
            
        Returns:
            Inflow volume from hydrologic simulation
        """
        # Snow17: Partition precip into rain and snow, track snowpack
        rain, snow_melt = self.snow17.step(
            climate.precip, climate.t_max, climate.t_min
        )
        
        # AWBM: Convert effective precip to runoff
        runoff_depth = self.awbm.step(rain + snow_melt, climate.et0)
        
        # Convert depth (mm) to volume (m³)
        # area is in m², runoff_depth is in mm, so divide by 1000 to get m³
        return runoff_depth * self.area / 1000.0


class Snow17Model:
    """
    Simplified Snow17 snow accumulation and melt model.
    
    This is a basic implementation that partitions precipitation into
    rain and snow based on temperature, and simulates snowmelt.
    """
    
    def __init__(self, melt_factor: float = 2.5, rain_temp: float = 2.0, 
                 snow_temp: float = 0.0):
        """
        Initialize Snow17 model.
        
        Args:
            melt_factor: Degree-day melt factor (mm/°C/day)
            rain_temp: Temperature threshold for rain (°C)
            snow_temp: Temperature threshold for snow (°C)
        """
        self.melt_factor = melt_factor
        self.rain_temp = rain_temp
        self.snow_temp = snow_temp
        self.snowpack = 0.0  # Current snowpack water equivalent (mm)
    
    def step(self, precip: float, t_max: float, t_min: float) -> tuple[float, float]:
        """
        Execute one timestep of snow model.
        
        Args:
            precip: Precipitation (mm)
            t_max: Maximum temperature (°C)
            t_min: Minimum temperature (°C)
            
        Returns:
            Tuple of (rain, snow_melt) in mm
        """
        t_avg = (t_max + t_min) / 2.0
        
        # Partition precipitation
        if t_avg <= self.snow_temp:
            # All snow
            snow = precip
            rain = 0.0
        elif t_avg >= self.rain_temp:
            # All rain
            rain = precip
            snow = 0.0
        else:
            # Mixed - linear interpolation
            rain_fraction = (t_avg - self.snow_temp) / (self.rain_temp - self.snow_temp)
            rain = precip * rain_fraction
            snow = precip * (1.0 - rain_fraction)
        
        # Add snow to snowpack
        self.snowpack += snow
        
        # Calculate melt
        if t_avg > 0.0:
            potential_melt = self.melt_factor * t_avg
            actual_melt = min(potential_melt, self.snowpack)
        else:
            actual_melt = 0.0
        
        # Remove melt from snowpack
        self.snowpack -= actual_melt
        
        return rain, actual_melt


class AWBMModel:
    """
    Simplified AWBM (Australian Water Balance Model) rainfall-runoff model.
    
    This is a basic implementation using three surface stores with
    different capacities to simulate partial area runoff generation.
    """
    
    def __init__(self, c1: float = 0.134, c2: float = 0.433, c3: float = 0.433,
                 a1: float = 0.3, a2: float = 0.3, a3: float = 0.4,
                 baseflow_coeff: float = 0.35, surface_coeff: float = 0.1):
        """
        Initialize AWBM model.
        
        Args:
            c1, c2, c3: Capacities of the three surface stores (mm)
            a1, a2, a3: Partial areas for the three stores (fractions, must sum to 1.0)
            baseflow_coeff: Baseflow recession coefficient
            surface_coeff: Surface flow recession coefficient
        """
        self.c1 = c1
        self.c2 = c2
        self.c3 = c3
        self.a1 = a1
        self.a2 = a2
        self.a3 = a3
        self.baseflow_coeff = baseflow_coeff
        self.surface_coeff = surface_coeff
        
        # State variables
        self.s1 = 0.0  # Store 1 level (mm)
        self.s2 = 0.0  # Store 2 level (mm)
        self.s3 = 0.0  # Store 3 level (mm)
        self.baseflow_store = 0.0  # Baseflow store (mm)
        self.surface_store = 0.0   # Surface store (mm)
    
    def step(self, precip: float, et0: float) -> float:
        """
        Execute one timestep of AWBM model.
        
        Args:
            precip: Effective precipitation (rain + snowmelt) (mm)
            et0: Reference evapotranspiration (mm)
            
        Returns:
            Total runoff (mm)
        """
        # Calculate excess from each store
        excess1 = self._store_excess(precip, et0, self.s1, self.c1, self.a1)
        excess2 = self._store_excess(precip, et0, self.s2, self.c2, self.a2)
        excess3 = self._store_excess(precip, et0, self.s3, self.c3, self.a3)
        
        # Update store levels
        self.s1 = min(self.c1, max(0.0, self.s1 + precip - et0))
        self.s2 = min(self.c2, max(0.0, self.s2 + precip - et0))
        self.s3 = min(self.c3, max(0.0, self.s3 + precip - et0))
        
        # Total excess
        total_excess = excess1 + excess2 + excess3
        
        # Route through baseflow and surface stores
        self.baseflow_store += total_excess * self.baseflow_coeff
        self.surface_store += total_excess * (1.0 - self.baseflow_coeff)
        
        # Calculate outflows
        baseflow = self.baseflow_store * self.baseflow_coeff
        surface_flow = self.surface_store * self.surface_coeff
        
        # Update stores
        self.baseflow_store -= baseflow
        self.surface_store -= surface_flow
        
        return baseflow + surface_flow
    
    def _store_excess(self, precip: float, et0: float, store: float, 
                     capacity: float, area: float) -> float:
        """
        Calculate excess runoff from a single store.
        
        Args:
            precip: Precipitation (mm)
            et0: Evapotranspiration (mm)
            store: Current store level (mm)
            capacity: Store capacity (mm)
            area: Partial area fraction
            
        Returns:
            Excess runoff (mm)
        """
        # Net input to store
        net_input = precip - et0
        
        # New store level
        new_store = store + net_input
        
        # Calculate excess
        if new_store > capacity:
            excess = (new_store - capacity) * area
        else:
            excess = 0.0
        
        return excess


class DemandModel(ABC):
    """Abstract base for demand calculation strategies."""
    
    @abstractmethod
    def calculate(self, climate: 'ClimateState') -> float:
        """
        Calculate demand for current timestep.
        
        Args:
            climate: Current climate state
            
        Returns:
            Demand volume
        """
        pass


class MunicipalDemand(DemandModel):
    """Population-based municipal demand."""
    
    def __init__(self, population: float, per_capita_demand: float):
        """
        Initialize municipal demand model.
        
        Args:
            population: Population served
            per_capita_demand: Water demand per person per day (m³/person/day)
        """
        self.population = population
        self.per_capita_demand = per_capita_demand
    
    def calculate(self, climate: 'ClimateState') -> float:
        """
        Calculate municipal demand based on population.
        
        Args:
            climate: Current climate state (unused for municipal demand)
            
        Returns:
            Demand volume (m³)
        """
        return self.population * self.per_capita_demand
    
    def get_future_demands(self, num_timesteps: int) -> List[float]:
        """
        Get future demands for look-ahead optimization.
        
        For municipal demand, this is constant over time.
        
        Args:
            num_timesteps: Number of future timesteps
            
        Returns:
            List of future demand values
        """
        demand_value = self.population * self.per_capita_demand
        return [demand_value] * num_timesteps


class AgricultureDemand(DemandModel):
    """Crop coefficient-based agricultural demand."""
    
    def __init__(self, area: float, crop_coefficient: float):
        """
        Initialize agricultural demand model.
        
        Args:
            area: Irrigated area (m²)
            crop_coefficient: Crop coefficient (Kc, dimensionless)
        """
        self.area = area
        self.kc = crop_coefficient
    
    def calculate(self, climate: 'ClimateState') -> float:
        """
        Calculate agricultural demand based on crop ET.
        
        ET_crop = Kc * ET0
        
        Args:
            climate: Current climate state (uses ET0)
            
        Returns:
            Demand volume (m³)
        """
        # ET_crop = Kc * ET0
        et_crop = self.kc * climate.et0
        # Convert from mm to m³: et_crop (mm) * area (m²) / 1000
        return et_crop * self.area / 1000.0
    
    def get_future_demands(self, num_timesteps: int, future_climate: List = None) -> List[float]:
        """
        Get future demands for look-ahead optimization.
        
        For agricultural demand, this depends on future ET0 values.
        
        Args:
            num_timesteps: Number of future timesteps
            future_climate: List of future climate states (optional)
            
        Returns:
            List of future demand values
        """
        if future_climate and len(future_climate) >= num_timesteps:
            # Use future ET0 values if available
            future_demands = []
            for i in range(num_timesteps):
                climate_state = future_climate[i]
                et_crop = self.kc * climate_state.et0
                demand = et_crop * self.area / 1000.0
                future_demands.append(demand)
            return future_demands
        else:
            # Fallback to average ET0 if future climate not available
            # Use a reasonable default ET0 value (5 mm/day)
            default_et0 = 5.0
            et_crop = self.kc * default_et0
            demand_value = et_crop * self.area / 1000.0
            return [demand_value] * num_timesteps
