"""
Solar radiation parameter calculator for WGEN weather generator.

This module calculates solar radiation parameters from observed data or
estimates them when observed solar data is unavailable, following the
algorithms from the legacy wgenpar.f FORTRAN code.
"""

import warnings
from typing import Dict, Tuple, Optional
import pandas as pd
import numpy as np
from scipy.optimize import curve_fit


class SolarParameterCalculator:
    """Calculate WGEN solar radiation parameters from observed data.
    
    This calculator implements the solar radiation parameter estimation algorithms
    from wgenpar.f, including:
    - Theoretical maximum solar radiation calculation based on latitude
    - Monthly mean solar radiation for wet and dry days (RMW, RMD)
    - Estimation of solar parameters when observed data is unavailable
    - 13-period Fourier series fitting for seasonal patterns
    - Physical constraint enforcement (solar <= theoretical max)
    
    CRITICAL: Uses solar constant coefficient of 37.2 MJ/m²/day (not 889 Langleys).
    The original FORTRAN code used 889.2305 Langleys, which converts to:
    889.2305 * 0.04184 ≈ 37.2 MJ/m²/day
    
    Attributes:
        latitude: Site latitude in decimal degrees (-90 to 90)
        wet_day_threshold: Precipitation threshold for wet day classification (mm)
        num_periods: Number of periods for Fourier series (default: 13)
    """
    
    def __init__(self, latitude: float, wet_day_threshold: float = 0.1, num_periods: int = 13):
        """Initialize solar parameter calculator.
        
        Args:
            latitude: Site latitude in decimal degrees (-90 to 90)
            wet_day_threshold: Precipitation threshold for wet day classification in mm
                              (default: 0.1 mm, WMO standard)
            num_periods: Number of periods for Fourier series (default: 13)
        
        Raises:
            ValueError: If latitude is outside valid range
        """
        if not -90 <= latitude <= 90:
            raise ValueError(f"Latitude must be in [-90, 90], got {latitude}")
        
        if wet_day_threshold < 0:
            raise ValueError(f"wet_day_threshold must be non-negative, got {wet_day_threshold}")
        
        if num_periods < 1:
            raise ValueError(f"num_periods must be positive, got {num_periods}")
        
        self.latitude = latitude
        self.wet_day_threshold = wet_day_threshold
        self.num_periods = num_periods
        
        # Pre-calculate theoretical maximum for all 365 days
        self.theoretical_max = self._calculate_theoretical_max_all_days()
    
    def calculate_parameters(
        self, 
        df: pd.DataFrame, 
        has_solar_data: bool = False
    ) -> Dict[str, any]:
        """Calculate all solar radiation parameters from observed data.
        
        Args:
            df: DataFrame with columns 'date', 'precipitation_mm'
                If has_solar_data=True, must also have 'solar_mjm2' column
                Date should be datetime.date or parseable to datetime
                Values should be float (NaN for missing values)
            has_solar_data: Whether observed solar radiation data is available
        
        Returns:
            Dictionary with keys:
                - 'rmd': List of 12 monthly mean solar radiation on dry days (MJ/m²/day)
                - 'rmw': List of 12 monthly mean solar radiation on wet days (MJ/m²/day)
                - 'ar': Amplitude of solar radiation Fourier series
                - 'latitude': Site latitude (for reference)
        
        Raises:
            ValueError: If required columns are missing or data is insufficient
        """
        # Validate input
        required_cols = ['date', 'precipitation_mm']
        if has_solar_data:
            required_cols.append('solar_mjm2')
        
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"DataFrame must have columns: {missing_cols}")
        
        # Ensure date is datetime
        if not pd.api.types.is_datetime64_any_dtype(df['date']):
            df = df.copy()
            df['date'] = pd.to_datetime(df['date'])
        
        # Add month and wet/dry classification
        df = df.copy()
        df['month'] = df['date'].dt.month
        df['is_wet'] = df['precipitation_mm'] >= self.wet_day_threshold
        
        if has_solar_data:
            # Calculate RMD and RMW from observed data
            rmd_list, rmw_list = self._calculate_observed_solar_params(df)
            
            # Enforce physical constraint: solar <= theoretical max
            rmd_list, rmw_list = self._enforce_physical_constraints(df, rmd_list, rmw_list)
        else:
            # Estimate RMD and RMW when no observed solar data
            rmd_list, rmw_list = self._estimate_solar_params(df)
        
        # Calculate Fourier series amplitude
        # Use RMD for Fourier fitting (dry day solar)
        ar = self._calculate_fourier_amplitude(rmd_list)
        
        return {
            'rmd': rmd_list,
            'rmw': rmw_list,
            'ar': ar,
            'latitude': self.latitude
        }
    
    def _calculate_theoretical_max_all_days(self) -> np.ndarray:
        """Calculate theoretical maximum solar radiation for all 365 days.
        
        Uses the solar geometry equations from wgenpar.f, converted to MJ/m²/day.
        
        CRITICAL: Uses solar constant coefficient of 37.2 MJ/m²/day (not 889 Langleys).
        
        Returns:
            Array of 365 theoretical maximum values (MJ/m²/day)
        """
        theoretical_max = np.zeros(365)
        
        for day in range(1, 366):
            theoretical_max[day - 1] = self.calculate_theoretical_solar_max(day)
        
        return theoretical_max
    
    def calculate_theoretical_solar_max(self, day_of_year: int) -> float:
        """Calculate theoretical maximum solar radiation for a specific day.
        
        Uses latitude-based solar geometry from wgenpar.f.
        
        CRITICAL: Returns MJ/m²/day (not Langleys).
        Solar constant coefficient: 37.2 MJ/m²/day (not 889 Langleys).
        
        The calculation follows these steps:
        1. Convert latitude to radians
        2. Calculate solar declination based on day of year
        3. Calculate hour angle (sunrise/sunset)
        4. Calculate earth-sun distance factor
        5. Calculate solar radiation using solar constant
        6. Apply atmospheric attenuation factor (0.80)
        
        Args:
            day_of_year: Day of year (1-365)
        
        Returns:
            Theoretical max solar radiation in MJ/m²/day
        
        Raises:
            ValueError: If day_of_year is outside valid range
        """
        if not 1 <= day_of_year <= 365:
            raise ValueError(f"day_of_year must be in [1, 365], got {day_of_year}")
        
        # Convert latitude to radians
        xlat = self.latitude * 2 * np.pi / 360
        
        # Solar declination (radians)
        sd = 0.4102 * np.sin(0.0172 * (day_of_year - 80.25))
        
        # Hour angle at sunrise/sunset
        ch = -np.tan(xlat) * np.tan(sd)
        
        if ch > 1.0:
            # Sun never rises (polar night)
            h = 0.0
        elif ch < -1.0:
            # Sun never sets (polar day)
            h = np.pi
        else:
            h = np.arccos(ch)
        
        # Earth-sun distance factor
        dd = 1.0 + 0.0335 * np.sin(0.0172 * (day_of_year - 88.2))
        
        # Solar radiation (MJ/m²/day)
        # Original FORTRAN used 889.2305 for Langleys
        # Conversion: 1 Langley = 0.04184 MJ/m²
        # Therefore: 889.2305 * 0.04184 ≈ 37.2 MJ/m²/day
        solar_constant = 37.2  # MJ/m²/day
        
        rc = solar_constant * dd * (
            (h * np.sin(xlat) * np.sin(sd)) + 
            (np.cos(xlat) * np.cos(sd) * np.sin(h))
        )
        
        # Apply atmospheric attenuation factor
        rc = rc * 0.80
        
        # Ensure non-negative
        rc = max(0.0, rc)
        
        return rc
    
    def _calculate_observed_solar_params(
        self, 
        df: pd.DataFrame
    ) -> Tuple[list, list]:
        """Calculate RMD and RMW from observed solar radiation data.
        
        Calculates monthly mean solar radiation separately for wet and dry days.
        
        Args:
            df: DataFrame with 'month', 'is_wet', and 'solar_mjm2' columns
        
        Returns:
            Tuple of (rmd_list, rmw_list) - 12 monthly values each
        """
        rmd_list = []
        rmw_list = []
        
        for month in range(1, 13):
            month_data = df[df['month'] == month]
            
            # Dry days
            dry_solar = month_data[month_data['is_wet'] == False]['solar_mjm2'].dropna()
            if len(dry_solar) > 0:
                rmd = dry_solar.mean()
            else:
                # No dry days with solar data - estimate
                warnings.warn(
                    f"No dry day solar data for month {month}. "
                    f"Using estimated value."
                )
                # Get theoretical max for mid-month
                mid_month_day = self._get_mid_month_day(month)
                theoretical = self.theoretical_max[mid_month_day - 1]
                rmd = 0.75 * theoretical
            
            # Wet days
            wet_solar = month_data[month_data['is_wet'] == True]['solar_mjm2'].dropna()
            if len(wet_solar) > 0:
                rmw = wet_solar.mean()
            else:
                # No wet days with solar data - estimate
                warnings.warn(
                    f"No wet day solar data for month {month}. "
                    f"Using estimated value."
                )
                # Get theoretical max for mid-month
                mid_month_day = self._get_mid_month_day(month)
                theoretical = self.theoretical_max[mid_month_day - 1]
                rmw = 0.50 * theoretical
            
            rmd_list.append(rmd)
            rmw_list.append(rmw)
        
        return rmd_list, rmw_list
    
    def _estimate_solar_params(self, df: pd.DataFrame) -> Tuple[list, list]:
        """Estimate RMD and RMW when no observed solar data is available.
        
        Uses the estimation rule from wgenpar.f:
        - RMD = 0.75 * theoretical_max (dry days get 75% of theoretical max)
        - RMW = 0.50 * theoretical_max (wet days get 50% of theoretical max)
        
        Args:
            df: DataFrame with 'month' column
        
        Returns:
            Tuple of (rmd_list, rmw_list) - 12 monthly values each
        """
        rmd_list = []
        rmw_list = []
        
        for month in range(1, 13):
            # Get theoretical max for mid-month day
            mid_month_day = self._get_mid_month_day(month)
            theoretical = self.theoretical_max[mid_month_day - 1]
            
            # Apply estimation factors
            rmd = 0.75 * theoretical
            rmw = 0.50 * theoretical
            
            rmd_list.append(rmd)
            rmw_list.append(rmw)
        
        return rmd_list, rmw_list
    
    def _get_mid_month_day(self, month: int) -> int:
        """Get the day of year for the middle of a month.
        
        Args:
            month: Month number (1-12)
        
        Returns:
            Day of year (1-365) for mid-month
        """
        # Days in each month (non-leap year)
        days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        
        # Calculate day of year for start of month
        day_of_year = sum(days_in_month[:month-1]) + 1
        
        # Add half the days in the month
        mid_month_day = day_of_year + days_in_month[month-1] // 2
        
        return mid_month_day
    
    def _enforce_physical_constraints(
        self, 
        df: pd.DataFrame, 
        rmd_list: list, 
        rmw_list: list
    ) -> Tuple[list, list]:
        """Enforce physical constraint that solar <= theoretical max.
        
        Checks each monthly value against the theoretical maximum for that month
        and caps values that exceed the theoretical maximum.
        
        Args:
            df: DataFrame with date information
            rmd_list: List of 12 monthly RMD values
            rmw_list: List of 12 monthly RMW values
        
        Returns:
            Tuple of (rmd_list, rmw_list) with constraints enforced
        """
        rmd_constrained = []
        rmw_constrained = []
        
        for month in range(1, 13):
            # Get theoretical max for mid-month
            mid_month_day = self._get_mid_month_day(month)
            theoretical = self.theoretical_max[mid_month_day - 1]
            
            # Enforce constraint for RMD
            rmd = rmd_list[month - 1]
            if rmd > theoretical:
                warnings.warn(
                    f"Month {month} RMD ({rmd:.2f} MJ/m²/day) exceeds theoretical max "
                    f"({theoretical:.2f} MJ/m²/day). Capping to theoretical max."
                )
                rmd = theoretical
            
            # Enforce constraint for RMW
            rmw = rmw_list[month - 1]
            if rmw > theoretical:
                warnings.warn(
                    f"Month {month} RMW ({rmw:.2f} MJ/m²/day) exceeds theoretical max "
                    f"({theoretical:.2f} MJ/m²/day). Capping to theoretical max."
                )
                rmw = theoretical
            
            rmd_constrained.append(rmd)
            rmw_constrained.append(rmw)
        
        return rmd_constrained, rmw_constrained
    
    def _calculate_fourier_amplitude(self, rmd_list: list) -> float:
        """Calculate Fourier series amplitude for solar radiation.
        
        Fits a 13-period Fourier series to monthly RMD values and extracts
        the amplitude parameter.
        
        Args:
            rmd_list: List of 12 monthly RMD values
        
        Returns:
            Amplitude (AR) parameter
        """
        # Convert monthly values to 13-period values
        # Interpolate 12 monthly values to 13 periods
        months = np.arange(1, 13)
        periods = np.linspace(1, 13, 13)
        
        # Interpolate monthly values to 13 periods
        period_values = np.interp(
            periods,
            np.linspace(1, 13, 12),
            rmd_list
        )
        
        # Define Fourier model
        def fourier_model(period, mean, amplitude, phase):
            """Fourier series model with mean, amplitude, and phase."""
            return mean + amplitude * np.cos(2 * np.pi * (period - phase) / self.num_periods)
        
        try:
            # Initial guess
            mean_guess = np.mean(period_values)
            amplitude_guess = (np.max(period_values) - np.min(period_values)) / 2
            phase_guess = np.argmax(period_values) + 1
            
            # Fit the model
            popt, _ = curve_fit(
                fourier_model,
                periods,
                period_values,
                p0=[mean_guess, amplitude_guess, phase_guess],
                maxfev=10000
            )
            
            mean, amplitude, phase = popt
            
            # Ensure amplitude is positive
            amplitude = abs(amplitude)
            
        except Exception as e:
            warnings.warn(
                f"Fourier series fitting failed for solar radiation: {e}. "
                f"Using simple amplitude estimate."
            )
            # Fallback to simple estimate
            amplitude = (np.max(period_values) - np.min(period_values)) / 2
        
        return amplitude
