"""
Strategy pattern implementations for generation and demand calculation.

Strategies allow pluggable algorithms for inflow generation and demand modeling.
This enables flexible modeling of different hydrologic processes, demand
patterns, and water use behaviors within the same network framework.

Example:
    >>> import hydrosim as hs
    >>> import pandas as pd
    >>> 
    >>> # Time series inflow strategy
    >>> inflow_data = pd.read_csv('inflows.csv', parse_dates=['date'])
    >>> inflow_strategy = hs.TimeSeriesStrategy(inflow_data, 'flow_cms')
    >>> 
    >>> # Municipal demand strategy
    >>> municipal_demand = hs.MunicipalDemand(
    ...     base_demand=50.0,           # ML/day
    ...     seasonal_factor=1.2,        # summer peak
    ...     growth_rate=0.02            # 2% annual growth
    ... )
    >>> 
    >>> # Agricultural demand strategy
    >>> ag_demand = hs.AgricultureDemand(
    ...     crop_coefficient=1.1,       # crop factor
    ...     irrigated_area=1000.0,      # hectares
    ...     efficiency=0.8              # irrigation efficiency
    ... )
    >>> 
    >>> # AWBM rainfall-runoff strategy (recommended for SourceNodes)
    >>> awbm_strategy = hs.AWBMGeneratorStrategy(
    ...     catchment_area=5.0e7,       # 50 km² in m²
    ...     a1=134.0, a2=433.0, a3=433.0,  # store capacities (mm)
    ...     f1=0.3, f2=0.3, f3=0.4,    # partial area fractions
    ...     bfi=0.35,                   # baseflow index
    ...     k_base=0.95,               # recession constant
    ...     initial_storage=0.5         # initial saturation
    ... )
    >>> 
    >>> # Legacy AWBM model (for compatibility)
    >>> legacy_awbm = hs.AWBMModel(
    ...     c1=0.134, c2=0.433, c3=0.433,  # capacity parameters
    ...     a1=0.300, a2=0.700, a3=0.500   # area parameters
    ... )

Available Strategies:
    Generation: TimeSeriesStrategy, HydrologyStrategy, AWBMGeneratorStrategy, AWBMModel, Snow17Model
    Demand: MunicipalDemand, AgricultureDemand, TimeSeriesStrategy
    
Strategies are assigned to nodes during network configuration and execute
during each simulation timestep to calculate inflows and demands.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Dict, Any, List
from dataclasses import dataclass
import pandas as pd

if TYPE_CHECKING:
    from hydrosim.climate import ClimateState


@dataclass
class AWBMParameters:
    """AWBM model parameters with validation."""
    a1: float  # Store 1 capacity (mm, > 0)
    a2: float  # Store 2 capacity (mm, > 0)
    a3: float  # Store 3 capacity (mm, > 0)
    f1: float  # Partial area fraction 1 (0-1)
    f2: float  # Partial area fraction 2 (0-1)
    f3: float  # Partial area fraction 3 (0-1)
    bfi: float  # Baseflow index (0-1)
    k_base: float  # Recession constant (0-1)
    
    def __post_init__(self):
        """Validate parameter constraints."""
        # Validate positive capacities
        if any(x <= 0 for x in [self.a1, self.a2, self.a3]):
            raise ValueError("Store capacities must be positive")
        
        # Validate partial area fractions
        if not (0 <= self.f1 <= 1 and 0 <= self.f2 <= 1 and 0 <= self.f3 <= 1):
            raise ValueError("Partial area fractions must be between 0 and 1")
        
        if abs(self.f1 + self.f2 + self.f3 - 1.0) > 1e-6:
            raise ValueError("Partial area fractions must sum to 1.0")
        
        # Validate BFI and recession constant
        if not (0 <= self.bfi <= 1):
            raise ValueError("Baseflow Index must be between 0 and 1")
        
        if not (0 <= self.k_base <= 1):
            raise ValueError("Recession constant must be between 0 and 1")


@dataclass
class AWBMState:
    """Internal state of AWBM model."""
    s1: float  # Store 1 level (mm)
    s2: float  # Store 2 level (mm) 
    s3: float  # Store 3 level (mm)
    baseflow_store: float  # Baseflow store level (mm)


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


class AWBMGeneratorStrategy(GeneratorStrategy):
    """AWBM rainfall-runoff generator strategy for SourceNodes."""
    
    def __init__(self, catchment_area: float, a1: float, a2: float, a3: float,
                 f1: float, f2: float, f3: float, bfi: float, k_base: float,
                 initial_storage: float = 0.5):
        """
        Initialize AWBM strategy.
        
        Args:
            catchment_area: Catchment area in square meters
            a1, a2, a3: Surface store capacities in mm
            f1, f2, f3: Partial area fractions (must sum to 1.0)
            bfi: Baseflow Index (0.0 to 1.0)
            k_base: Baseflow recession constant (0.0 to 1.0)
            initial_storage: Initial saturation fraction (0.0 to 1.0)
        """
        # Validate catchment area
        if catchment_area <= 0:
            raise ValueError("Catchment area must be positive")
        
        if not (0 <= initial_storage <= 1):
            raise ValueError("Initial storage must be between 0 and 1")
        
        # Create and validate parameters
        self.parameters = AWBMParameters(
            a1=a1, a2=a2, a3=a3,
            f1=f1, f2=f2, f3=f3,
            bfi=bfi, k_base=k_base
        )
        
        self.catchment_area = catchment_area
        self.initial_storage = initial_storage
        
        # State tracking for continuity and mass balance verification
        self.timestep_count = 0
        self.cumulative_inflow = 0.0  # Total precipitation input (mm)
        self.cumulative_et = 0.0      # Total evapotranspiration (mm)
        self.cumulative_outflow = 0.0 # Total runoff output (mm)
        self.initial_total_storage = 0.0  # Initial total storage (mm)
        
        # Initialize state
        self._initialize_state()
    
    def _initialize_state(self):
        """Initialize AWBM state variables."""
        self.state = AWBMState(
            s1=self.parameters.a1 * self.initial_storage,
            s2=self.parameters.a2 * self.initial_storage,
            s3=self.parameters.a3 * self.initial_storage,
            baseflow_store=0.0  # Baseflow store starts empty
        )
        
        # Calculate initial total storage for mass balance tracking
        self.initial_total_storage = (
            self.state.s1 + self.state.s2 + self.state.s3 + self.state.baseflow_store
        )
    
    def generate(self, climate: 'ClimateState') -> float:
        """
        Generate daily inflow volume using AWBM physics.
        
        Args:
            climate: Current climate state (uses precip and et0)
            
        Returns:
            Daily inflow volume in cubic meters
        """
        # Validate climate inputs and ensure numerical stability
        if climate.precip < 0:
            raise ValueError("Precipitation cannot be negative")
        if climate.et0 < 0:
            raise ValueError("ET0 cannot be negative")
        
        # Handle extreme values for numerical stability
        precip = max(0.0, min(climate.precip, 1000.0))  # Cap at 1000mm/day
        et0 = max(0.0, min(climate.et0, 50.0))  # Cap at 50mm/day
        
        # Store initial state for mass balance verification
        initial_s1 = self.state.s1
        initial_s2 = self.state.s2
        initial_s3 = self.state.s3
        initial_baseflow = self.state.baseflow_store
        initial_total_storage = initial_s1 + initial_s2 + initial_s3 + initial_baseflow
        
        # Step 1: Surface store water balance calculations
        # Calculate excess from each surface store
        excess1 = self._calculate_store_excess(
            precip, et0, self.state.s1, 
            self.parameters.a1, self.parameters.f1
        )
        excess2 = self._calculate_store_excess(
            precip, et0, self.state.s2, 
            self.parameters.a2, self.parameters.f2
        )
        excess3 = self._calculate_store_excess(
            precip, et0, self.state.s3, 
            self.parameters.a3, self.parameters.f3
        )
        
        # Update surface store levels
        self.state.s1 = self._update_store_level(
            precip, et0, self.state.s1, self.parameters.a1
        )
        self.state.s2 = self._update_store_level(
            precip, et0, self.state.s2, self.parameters.a2
        )
        self.state.s3 = self._update_store_level(
            precip, et0, self.state.s3, self.parameters.a3
        )
        
        # Step 2: Calculate total excess water
        total_excess = excess1 + excess2 + excess3
        
        # Step 3: Flow partitioning logic
        # Partition excess between surface runoff and baseflow using BFI
        surface_runoff = total_excess * (1.0 - self.parameters.bfi)
        baseflow_input = total_excess * self.parameters.bfi
        
        # Step 4: Baseflow store management with exponential recession
        # Add new baseflow input to baseflow store
        self.state.baseflow_store += baseflow_input
        
        # Calculate baseflow output using exponential recession
        baseflow_output = self.state.baseflow_store * (1.0 - self.parameters.k_base)
        
        # Update baseflow store (subtract what flows out)
        self.state.baseflow_store *= self.parameters.k_base
        
        # Step 5: Total discharge calculation (surface + baseflow)
        total_runoff_mm = surface_runoff + baseflow_output
        
        # Calculate actual ET that occurred (for better mass balance tracking)
        actual_et = self._calculate_actual_et(
            initial_s1, initial_s2, initial_s3, precip, et0
        )
        
        # Update state tracking for continuity and mass balance verification
        self.timestep_count += 1
        self.cumulative_inflow += precip
        self.cumulative_et += actual_et  # Track actual ET
        self.cumulative_outflow += total_runoff_mm
        
        # Perform mass balance verification for debugging
        self._verify_mass_balance_detailed(
            initial_s1, initial_s2, initial_s3, initial_baseflow,
            precip, et0, total_runoff_mm
        )
        
        # Convert runoff depth (mm) to volume (m³)
        # Formula: volume = depth_mm * area_m2 / 1000
        total_volume_m3 = total_runoff_mm * self.catchment_area / 1000.0
        
        return total_volume_m3
    
    def reset(self) -> None:
        """Reset all stores to initial conditions."""
        # Reset state tracking variables
        self.timestep_count = 0
        self.cumulative_inflow = 0.0
        self.cumulative_et = 0.0
        self.cumulative_outflow = 0.0
        
        # Reset state variables
        self._initialize_state()
    
    def _calculate_store_excess(self, precip: float, et0: float, 
                               current_level: float, capacity: float, 
                               partial_area: float) -> float:
        """
        Calculate excess runoff from a single surface store.
        
        Args:
            precip: Precipitation (mm)
            et0: Evapotranspiration (mm)
            current_level: Current store level (mm)
            capacity: Store capacity (mm)
            partial_area: Partial area fraction for this store
            
        Returns:
            Excess runoff (mm) weighted by partial area
        """
        # Net input to store (precipitation minus evapotranspiration)
        net_input = precip - et0
        
        # Calculate potential new store level
        potential_level = current_level + net_input
        
        # Calculate excess if store capacity is exceeded
        if potential_level > capacity:
            excess_depth = potential_level - capacity
            # Weight by partial area fraction
            excess_runoff = excess_depth * partial_area
        else:
            excess_runoff = 0.0
        
        return excess_runoff
    
    def _update_store_level(self, precip: float, et0: float, 
                           current_level: float, capacity: float) -> float:
        """
        Update surface store level after water balance calculation.
        
        Args:
            precip: Precipitation (mm)
            et0: Evapotranspiration (mm)
            current_level: Current store level (mm)
            capacity: Store capacity (mm)
            
        Returns:
            Updated store level (mm), constrained to [0, capacity]
        """
        # Net input to store
        net_input = precip - et0
        
        # Calculate new level
        new_level = current_level + net_input
        
        # Constrain to valid range [0, capacity]
        new_level = max(0.0, min(new_level, capacity))
        
        return new_level
    
    def _verify_mass_balance_detailed(self, initial_s1: float, initial_s2: float, 
                                    initial_s3: float, initial_baseflow: float,
                                    precip: float, et0: float, total_runoff: float) -> None:
        """
        Verify detailed mass balance for debugging purposes.
        
        For each store: Initial + Precip - ET - Excess = Final
        For baseflow: Initial + Inflow - Outflow = Final
        
        Args:
            initial_s1, initial_s2, initial_s3: Initial surface store levels (mm)
            initial_baseflow: Initial baseflow store level (mm)
            precip: Precipitation input (mm)
            et0: Evapotranspiration (mm)
            total_runoff: Total runoff output (mm)
        """
        # Calculate what each store should be based on the water balance equations
        
        # For surface stores: new_level = max(0, min(capacity, initial + precip - et0))
        expected_s1 = max(0.0, min(self.parameters.a1, initial_s1 + precip - et0))
        expected_s2 = max(0.0, min(self.parameters.a2, initial_s2 + precip - et0))
        expected_s3 = max(0.0, min(self.parameters.a3, initial_s3 + precip - et0))
        
        # Calculate excess from each store
        excess1 = max(0.0, (initial_s1 + precip - et0) - self.parameters.a1) * self.parameters.f1
        excess2 = max(0.0, (initial_s2 + precip - et0) - self.parameters.a2) * self.parameters.f2
        excess3 = max(0.0, (initial_s3 + precip - et0) - self.parameters.a3) * self.parameters.f3
        total_excess = excess1 + excess2 + excess3
        
        # Baseflow calculations
        baseflow_input = total_excess * self.parameters.bfi
        expected_baseflow_before_output = initial_baseflow + baseflow_input
        baseflow_output = expected_baseflow_before_output * (1.0 - self.parameters.k_base)
        expected_baseflow = expected_baseflow_before_output * self.parameters.k_base
        
        # Surface runoff
        surface_runoff = total_excess * (1.0 - self.parameters.bfi)
        expected_total_runoff = surface_runoff + baseflow_output
        
        # Check each component
        s1_error = abs(self.state.s1 - expected_s1)
        s2_error = abs(self.state.s2 - expected_s2)
        s3_error = abs(self.state.s3 - expected_s3)
        baseflow_error = abs(self.state.baseflow_store - expected_baseflow)
        runoff_error = abs(total_runoff - expected_total_runoff)
        
        # Overall mass balance error
        total_error = s1_error + s2_error + s3_error + baseflow_error + runoff_error
        
        # Store for debugging
        self._last_mass_balance_error = total_error
        
        # Store detailed errors for debugging
        self._detailed_errors = {
            's1_error': s1_error,
            's2_error': s2_error, 
            's3_error': s3_error,
            'baseflow_error': baseflow_error,
            'runoff_error': runoff_error,
            'total_error': total_error
        }
    
    def get_state_summary(self) -> Dict[str, float]:
        """
        Get current state summary for debugging and monitoring.
        
        Returns:
            Dictionary containing current state information
        """
        total_surface_storage = self.state.s1 + self.state.s2 + self.state.s3
        total_storage = total_surface_storage + self.state.baseflow_store
        
        result = {
            'timestep_count': self.timestep_count,
            'surface_store_1': self.state.s1,
            'surface_store_2': self.state.s2,
            'surface_store_3': self.state.s3,
            'baseflow_store': self.state.baseflow_store,
            'total_surface_storage': total_surface_storage,
            'total_storage': total_storage,
            'cumulative_inflow': self.cumulative_inflow,
            'cumulative_et': self.cumulative_et,
            'cumulative_outflow': self.cumulative_outflow,
            'last_mass_balance_error': getattr(self, '_last_mass_balance_error', 0.0)
        }
        
        # Add detailed errors if available
        if hasattr(self, '_detailed_errors'):
            result.update(self._detailed_errors)
            
        return result
    
    def get_mass_balance_summary(self) -> Dict[str, float]:
        """
        Get cumulative mass balance summary for verification.
        
        In AWBM, stores represent area fractions of the catchment, not separate water bodies.
        The mass balance must account for this conceptual model.
        
        Returns:
            Dictionary containing mass balance information
        """
        current_total_storage = (
            self.state.s1 + self.state.s2 + self.state.s3 + self.state.baseflow_store
        )
        
        # Calculate storage change
        storage_change = current_total_storage - self.initial_total_storage
        
        # In AWBM, each store gets the full precipitation depth, but they represent
        # different area fractions. The total precipitation input to the system is
        # the precipitation depth times the total area (which is 1.0).
        # However, in terms of storage accounting, each store increases by the full
        # precipitation amount.
        
        # The mass balance equation for AWBM is:
        # ΔStorage = Precip_input - ET_actual - Runoff_output
        # where all terms are in mm depth over the catchment
        
        mass_balance_residual = (
            self.cumulative_inflow - self.cumulative_et - 
            self.cumulative_outflow - storage_change
        )
        
        return {
            'initial_storage': self.initial_total_storage,
            'current_storage': current_total_storage,
            'storage_change': storage_change,
            'cumulative_inflow': self.cumulative_inflow,
            'cumulative_actual_et': self.cumulative_et,
            'cumulative_outflow': self.cumulative_outflow,
            'mass_balance_residual': mass_balance_residual,
            'note': 'AWBM stores represent area fractions; mass balance in mm depth',
            'timesteps_processed': self.timestep_count
        }
    
    def check_numerical_stability(self) -> Dict[str, bool]:
        """
        Check for numerical stability issues.
        
        Returns:
            Dictionary indicating potential stability issues
        """
        checks = {
            'stores_within_bounds': True,
            'no_negative_values': True,
            'reasonable_magnitudes': True
        }
        
        # Check store bounds
        if (self.state.s1 > self.parameters.a1 + 1e-6 or
            self.state.s2 > self.parameters.a2 + 1e-6 or
            self.state.s3 > self.parameters.a3 + 1e-6):
            checks['stores_within_bounds'] = False
        
        # Check for negative values
        if (self.state.s1 < -1e-6 or self.state.s2 < -1e-6 or 
            self.state.s3 < -1e-6 or self.state.baseflow_store < -1e-6):
            checks['no_negative_values'] = False
        
        # Check for unreasonably large values (> 10,000 mm)
        max_reasonable = 10000.0
        if (self.state.s1 > max_reasonable or self.state.s2 > max_reasonable or
            self.state.s3 > max_reasonable or self.state.baseflow_store > max_reasonable):
            checks['reasonable_magnitudes'] = False
        
        return checks
    
    def _calculate_actual_et(self, initial_s1: float, initial_s2: float, 
                           initial_s3: float, precip: float, et0: float) -> float:
        """
        Calculate actual evapotranspiration that occurred.
        
        In AWBM, the precipitation and ET are applied uniformly across the catchment.
        Each store represents a portion of the catchment and experiences the same
        precipitation and ET rates, but the actual ET is limited by available water.
        
        Args:
            initial_s1, initial_s2, initial_s3: Initial store levels (mm)
            precip: Precipitation (mm)
            et0: Potential evapotranspiration (mm)
            
        Returns:
            Actual evapotranspiration (mm) - catchment average
        """
        # For each store, calculate actual ET (limited by available water)
        
        # Store 1: ET limited by available water after precipitation
        available_1 = initial_s1 + precip
        actual_et_1 = min(et0, max(0.0, available_1))
        
        # Store 2
        available_2 = initial_s2 + precip  
        actual_et_2 = min(et0, max(0.0, available_2))
        
        # Store 3
        available_3 = initial_s3 + precip
        actual_et_3 = min(et0, max(0.0, available_3))
        
        # The catchment-average actual ET is weighted by area fractions
        catchment_actual_et = (
            actual_et_1 * self.parameters.f1 +
            actual_et_2 * self.parameters.f2 +
            actual_et_3 * self.parameters.f3
        )
        
        return catchment_actual_et


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
