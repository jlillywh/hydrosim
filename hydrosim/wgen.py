"""
WGEN stochastic weather generator.

This module implements the WGEN algorithm for generating synthetic daily
weather data including precipitation, temperature, and solar radiation.

The WGEN algorithm uses:
- First-order Markov chain for wet/dry day sequences
- Gamma distribution for precipitation amounts on wet days
- Fourier functions for seasonal temperature and radiation patterns
- Stochastic variation based on coefficient of variation parameters

Parameters can be specified in two ways:
1. Inline in YAML configuration (wgen_params dictionary)
2. External CSV file (wgen_params_file path)

For CSV parameter configuration, see:
- hydrosim.wgen_params.CSVWGENParamsParser for CSV loading
- examples/wgen_params_template.csv for template file
- README.md WGEN section for parameter descriptions and valid ranges

Example Usage:
    from hydrosim.wgen import WGENParams, WGENState, wgen_step
    import datetime
    
    # Define parameters
    params = WGENParams(
        pww=[0.45]*12, pwd=[0.25]*12,
        alpha=[1.2]*12, beta=[8.5]*12,
        txmd=20.0, atx=10.0, txmw=18.0,
        tn=10.0, atn=8.0,
        cvtx=0.1, acvtx=0.05,
        cvtn=0.1, acvtn=0.05,
        rmd=15.0, ar=5.0, rmw=12.0,
        latitude=45.0, random_seed=42
    )
    
    # Initialize state
    state = WGENState(
        is_wet=False,
        current_date=datetime.date(2024, 1, 1)
    )
    
    # Generate weather for one day
    new_state, outputs = wgen_step(params, state)
    print(f"Precipitation: {outputs.precip_mm:.1f} mm")
    print(f"Temperature: {outputs.tmin_c:.1f} to {outputs.tmax_c:.1f} °C")
    print(f"Solar radiation: {outputs.solar_mjm2:.1f} MJ/m²/day")
"""

import datetime
import numpy as np
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class WGENParams:
    """Parameters for WGEN weather generator.
    
    Attributes:
        pww: Probability of wet day following wet day (12 monthly values)
        pwd: Probability of wet day following dry day (12 monthly values)
        alpha: Gamma distribution shape parameter for precipitation (12 monthly values)
        beta: Gamma distribution scale parameter for precipitation (12 monthly values)
        txmd: Mean maximum temperature on dry days (°C)
        atx: Amplitude of seasonal variation in maximum temperature (°C)
        txmw: Mean maximum temperature on wet days (°C)
        tn: Mean minimum temperature (°C)
        atn: Amplitude of seasonal variation in minimum temperature (°C)
        cvtx: Coefficient of variation for maximum temperature
        acvtx: Amplitude of seasonal variation in cvtx
        cvtn: Coefficient of variation for minimum temperature
        acvtn: Amplitude of seasonal variation in cvtn
        rmd: Mean solar radiation on dry days (MJ/m²/day)
        ar: Amplitude of seasonal variation in solar radiation (MJ/m²/day)
        rmw: Mean solar radiation on wet days (MJ/m²/day)
        latitude: Station latitude in degrees (-90 to 90)
        random_seed: Optional random seed for reproducibility
    """
    pww: List[float]
    pwd: List[float]
    alpha: List[float]
    beta: List[float]
    txmd: float
    atx: float
    txmw: float
    tn: float
    atn: float
    cvtx: float
    acvtx: float
    cvtn: float
    acvtn: float
    rmd: float
    ar: float
    rmw: float
    latitude: float
    random_seed: Optional[int] = None
    
    def __post_init__(self):
        """Validate parameters."""
        if len(self.pww) != 12:
            raise ValueError(f"pww must have 12 values, got {len(self.pww)}")
        if len(self.pwd) != 12:
            raise ValueError(f"pwd must have 12 values, got {len(self.pwd)}")
        if len(self.alpha) != 12:
            raise ValueError(f"alpha must have 12 values, got {len(self.alpha)}")
        if len(self.beta) != 12:
            raise ValueError(f"beta must have 12 values, got {len(self.beta)}")
        
        for i, (pww, pwd) in enumerate(zip(self.pww, self.pwd)):
            if not 0 <= pww <= 1:
                raise ValueError(f"pww[{i}] must be in [0,1], got {pww}")
            if not 0 <= pwd <= 1:
                raise ValueError(f"pwd[{i}] must be in [0,1], got {pwd}")
        
        for i, (alpha, beta) in enumerate(zip(self.alpha, self.beta)):
            if alpha <= 0:
                raise ValueError(f"alpha[{i}] must be > 0, got {alpha}")
            if beta <= 0:
                raise ValueError(f"beta[{i}] must be > 0, got {beta}")
        
        if not -90 <= self.latitude <= 90:
            raise ValueError(f"latitude must be in [-90,90], got {self.latitude}")


@dataclass
class WGENState:
    """State variables for WGEN simulation.
    
    Attributes:
        is_wet: Whether the previous day was wet
        random_state: Internal RNG state for reproducibility
        current_date: Current simulation date (needed for monthly parameter selection)
    """
    is_wet: bool = False
    random_state: tuple = None
    current_date: datetime.date = None


@dataclass
class WGENOutputs:
    """Output from one WGEN timestep.
    
    Attributes:
        precip_mm: Precipitation in mm
        tmax_c: Maximum temperature in °C
        tmin_c: Minimum temperature in °C
        solar_mjm2: Solar radiation in MJ/m²/day
        is_wet: Whether this day is wet
    """
    precip_mm: float
    tmax_c: float
    tmin_c: float
    solar_mjm2: float
    is_wet: bool


def _celsius_to_kelvin(temp_c: float) -> float:
    """Convert Celsius to Kelvin."""
    return temp_c + 273.15


def _kelvin_to_celsius(temp_k: float) -> float:
    """Convert Kelvin to Celsius."""
    return temp_k - 273.15


def _get_monthly_params(params: WGENParams, 
                       month: int) -> Tuple[float, float, float, float]:
    """Extract monthly precipitation parameters for given month.
    
    Args:
        params: WGEN parameters
        month: Month number (1-12)
        
    Returns:
        Tuple of (pww, pwd, alpha, beta) for the month
    """
    idx = month - 1  # Convert to 0-indexed
    return (
        params.pww[idx],
        params.pwd[idx],
        params.alpha[idx],
        params.beta[idx]
    )


def _calculate_seasonal_temp(mean: float,
                            amplitude: float,
                            day_of_year: int,
                            latitude: float) -> float:
    """Calculate temperature using Fourier function.
    
    Args:
        mean: Mean temperature (K)
        amplitude: Seasonal amplitude (K)
        day_of_year: Day of year (1-365/366)
        latitude: Station latitude (degrees)
        
    Returns:
        Temperature for the day (K)
    """
    # Fourier function: T = mean + amplitude * cos(2π(doy - peak)/365)
    # Peak day varies with latitude (Northern Hemisphere ~200, Southern ~20)
    peak_day = 200 if latitude >= 0 else 20
    angle = 2 * np.pi * (day_of_year - peak_day) / 365
    return mean + amplitude * np.cos(angle)


def _calculate_seasonal_radiation(mean: float,
                                 amplitude: float,
                                 day_of_year: int,
                                 latitude: float) -> float:
    """Calculate solar radiation using Fourier function.
    
    Args:
        mean: Mean radiation (MJ/m²/day)
        amplitude: Seasonal amplitude (MJ/m²/day)
        day_of_year: Day of year (1-365/366)
        latitude: Station latitude (degrees)
        
    Returns:
        Solar radiation for the day (MJ/m²/day)
    """
    # Similar Fourier function for radiation
    peak_day = 172 if latitude >= 0 else 355  # Summer solstice
    angle = 2 * np.pi * (day_of_year - peak_day) / 365
    return max(0, mean + amplitude * np.cos(angle))


def wgen_step(params: WGENParams, state: WGENState) -> Tuple[WGENState, WGENOutputs]:
    """Generate one day of synthetic weather data using WGEN algorithm.
    
    Pure function with no side effects (except internal RNG state).
    
    This function uses monthly precipitation parameters (PWW, PWD, ALPHA, BETA)
    selected based on the current simulation date, and constant temperature/radiation
    parameters with Fourier-based seasonal variation.
    
    Args:
        params: Fixed parameters defining weather statistics
            - Monthly precipitation parameters: pww, pwd, alpha, beta (12 values each)
            - Constant temperature parameters: txmd, atx, txmw, tn, atn, cvtx, acvtx, cvtn, acvtn (Celsius at interface)
            - Constant radiation parameters: rmd, ar, rmw (MJ/m²/day)
            - Location: latitude (degrees, -90 to 90)
        state: Current state
            - is_wet: Whether the previous day was wet
            - random_state: Internal RNG state for reproducibility
            - current_date: Current simulation date (for monthly parameter selection)
            
    Returns:
        Tuple of (new_state, outputs) where:
            - new_state: Updated state with incremented date
            - outputs: Generated weather variables (precip_mm, tmax_c, tmin_c, solar_mjm2, is_wet)
    """
    # Validate that current_date is set
    if state.current_date is None:
        raise ValueError("WGENState.current_date must be set for monthly parameter selection")
    
    # Initialize RNG
    if state.random_state is None:
        # First call - use seed from params if available
        rng = np.random.RandomState(params.random_seed)
    else:
        # Restore previous RNG state
        rng = np.random.RandomState()
        rng.set_state(state.random_state)
    
    # Extract current month from state (1-12)
    current_month = state.current_date.month
    
    # Get monthly precipitation parameters for current month
    pww, pwd, alpha, beta = _get_monthly_params(params, current_month)
    
    # Determine if today is wet based on previous day's state
    if state.is_wet:
        is_wet_today = rng.random() < pww
    else:
        is_wet_today = rng.random() < pwd
    
    # Generate precipitation amount if wet day
    if is_wet_today:
        precip_mm = rng.gamma(alpha, beta)
    else:
        precip_mm = 0.0
    
    # Calculate day of year for Fourier functions
    day_of_year = state.current_date.timetuple().tm_yday
    
    # Convert temperature parameters from Celsius to Kelvin for internal calculations
    txmd_k = _celsius_to_kelvin(params.txmd)
    atx_k = params.atx  # Amplitude doesn't need offset conversion
    txmw_k = _celsius_to_kelvin(params.txmw)
    tn_k = _celsius_to_kelvin(params.tn)
    atn_k = params.atn  # Amplitude doesn't need offset conversion
    
    # Calculate seasonal temperature using Fourier functions
    if is_wet_today:
        tmax_k = _calculate_seasonal_temp(txmw_k, atx_k, day_of_year, params.latitude)
    else:
        tmax_k = _calculate_seasonal_temp(txmd_k, atx_k, day_of_year, params.latitude)
    
    tmin_k = _calculate_seasonal_temp(tn_k, atn_k, day_of_year, params.latitude)
    
    # Add stochastic variation to temperatures
    tmax_k += rng.normal(0, params.cvtx * tmax_k)
    tmin_k += rng.normal(0, params.cvtn * tmin_k)
    
    # Convert temperatures back to Celsius for output
    tmax_c = _kelvin_to_celsius(tmax_k)
    tmin_c = _kelvin_to_celsius(tmin_k)
    
    # Calculate seasonal radiation using Fourier functions
    if is_wet_today:
        solar_mjm2 = _calculate_seasonal_radiation(params.rmw, params.ar, day_of_year, params.latitude)
    else:
        solar_mjm2 = _calculate_seasonal_radiation(params.rmd, params.ar, day_of_year, params.latitude)
    
    # Ensure solar radiation is non-negative
    solar_mjm2 = max(0.0, solar_mjm2)
    
    # Create outputs
    outputs = WGENOutputs(
        precip_mm=precip_mm,
        tmax_c=tmax_c,
        tmin_c=tmin_c,
        solar_mjm2=solar_mjm2,
        is_wet=is_wet_today
    )
    
    # Increment date for next step
    next_date = state.current_date + datetime.timedelta(days=1)
    
    # Create new state with updated date and wetness
    new_state = WGENState(
        is_wet=is_wet_today,
        random_state=rng.get_state(),
        current_date=next_date
    )
    
    return new_state, outputs
