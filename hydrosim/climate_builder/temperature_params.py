"""
Temperature parameter calculator for WGEN weather generator.

This module calculates temperature Fourier series parameters from observed
temperature data, following the algorithms from the legacy wgenpar.f FORTRAN code.
"""

import warnings
from typing import Dict, Tuple
import pandas as pd
import numpy as np
from scipy.optimize import curve_fit


class TemperatureParameterCalculator:
    """Calculate WGEN temperature parameters from observed data.
    
    This calculator implements the temperature parameter estimation algorithms
    from wgenpar.f, including:
    - Division of year into 13 periods of 28 days each
    - Calculation of mean and standard deviation for each period
    - Separate statistics for wet/dry days (Tmax) and combined (Tmin)
    - 13-period Fourier series fitting for seasonal patterns
    - Coefficient of variation (CV) calculation
    
    The Fourier series model is:
        T = mean + amplitude * cos(2π(period - peak) / 13)
    
    Attributes:
        wet_day_threshold: Precipitation threshold for wet day classification (mm)
        num_periods: Number of periods to divide the year into (default: 13)
        days_per_period: Number of days per period (default: 28)
    """
    
    def __init__(self, wet_day_threshold: float = 0.1, num_periods: int = 13):
        """Initialize temperature parameter calculator.
        
        Args:
            wet_day_threshold: Precipitation threshold for wet day classification in mm
                              (default: 0.1 mm, WMO standard)
            num_periods: Number of periods to divide the year into (default: 13)
        """
        if wet_day_threshold < 0:
            raise ValueError(f"wet_day_threshold must be non-negative, got {wet_day_threshold}")
        
        if num_periods < 1:
            raise ValueError(f"num_periods must be positive, got {num_periods}")
        
        self.wet_day_threshold = wet_day_threshold
        self.num_periods = num_periods
        self.days_per_period = 28  # Fixed at 28 days per period (13 * 28 = 364 days)
    
    def calculate_parameters(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate all temperature parameters from observed data.
        
        Args:
            df: DataFrame with columns 'date', 'precipitation_mm', 'tmax_c', 'tmin_c'
                Date should be datetime.date or parseable to datetime
                Values should be float (NaN for missing values)
        
        Returns:
            Dictionary with keys:
                - 'txmd': Mean Tmax on dry days (Fourier mean coefficient)
                - 'atx': Amplitude of Tmax on dry days (Fourier amplitude)
                - 'txmw': Mean Tmax on wet days (Fourier mean coefficient)
                - 'tn': Mean Tmin (Fourier mean coefficient)
                - 'atn': Amplitude of Tmin (Fourier amplitude)
                - 'cvtx': Coefficient of variation for Tmax
                - 'acvtx': Amplitude of CV for Tmax
                - 'cvtn': Coefficient of variation for Tmin
                - 'acvtn': Amplitude of CV for Tmin
        
        Raises:
            ValueError: If required columns are missing or data is insufficient
        """
        # Validate input
        required_cols = ['date', 'precipitation_mm', 'tmax_c', 'tmin_c']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"DataFrame must have columns: {missing_cols}")
        
        # Ensure date is datetime
        if not pd.api.types.is_datetime64_any_dtype(df['date']):
            df = df.copy()
            df['date'] = pd.to_datetime(df['date'])
        
        # Add period column (1-13) and wet/dry classification
        df = df.copy()
        df['period'] = self._assign_periods(df['date'])
        df['is_wet'] = df['precipitation_mm'] >= self.wet_day_threshold
        
        # Calculate period statistics
        tmax_dry_stats = self._calculate_period_stats(df, 'tmax_c', wet_status=False)
        tmax_wet_stats = self._calculate_period_stats(df, 'tmax_c', wet_status=True)
        tmin_stats = self._calculate_period_stats(df, 'tmin_c', wet_status=None)
        
        # Fit Fourier series to means
        txmd, atx_dry = self._fit_fourier_series(tmax_dry_stats['means'])
        txmw, atx_wet = self._fit_fourier_series(tmax_wet_stats['means'])
        tn, atn = self._fit_fourier_series(tmin_stats['means'])
        
        # Use dry day amplitude for atx (as per wgenpar.f)
        atx = atx_dry
        
        # Calculate coefficient of variation parameters
        cvtx, acvtx = self._calculate_cv_params(tmax_dry_stats)
        cvtn, acvtn = self._calculate_cv_params(tmin_stats)
        
        return {
            'txmd': txmd,
            'atx': atx,
            'txmw': txmw,
            'tn': tn,
            'atn': atn,
            'cvtx': cvtx,
            'acvtx': acvtx,
            'cvtn': cvtn,
            'acvtn': acvtn
        }
    
    def _assign_periods(self, dates: pd.Series) -> pd.Series:
        """Assign each date to a period (1-13).
        
        Divides the 365-day year into 13 periods of 28 days each.
        Period 1: days 1-28 (Jan 1 - Jan 28)
        Period 2: days 29-56 (Jan 29 - Feb 25)
        ...
        Period 13: days 337-364 (Dec 3 - Dec 30)
        Day 365 (Dec 31) is assigned to period 13
        
        Args:
            dates: Series of datetime dates
        
        Returns:
            Series of period numbers (1-13)
        """
        # Get day of year (1-365)
        day_of_year = dates.dt.dayofyear
        
        # Calculate period: (day_of_year - 1) // 28 + 1
        # This gives periods 1-13, with day 365 in period 13
        periods = ((day_of_year - 1) // self.days_per_period + 1).clip(upper=self.num_periods)
        
        return periods
    
    def _calculate_period_stats(
        self, 
        df: pd.DataFrame, 
        temp_col: str, 
        wet_status: bool = None
    ) -> Dict[str, np.ndarray]:
        """Calculate mean and standard deviation for each period.
        
        Args:
            df: DataFrame with 'period' column and temperature column
            temp_col: Name of temperature column ('tmax_c' or 'tmin_c')
            wet_status: Filter by wet status (True=wet, False=dry, None=all days)
        
        Returns:
            Dictionary with keys:
                - 'means': Array of 13 mean values (one per period)
                - 'stds': Array of 13 standard deviation values
                - 'counts': Array of 13 sample counts
        """
        means = np.zeros(self.num_periods)
        stds = np.zeros(self.num_periods)
        counts = np.zeros(self.num_periods, dtype=int)
        
        for period in range(1, self.num_periods + 1):
            # Filter by period
            period_data = df[df['period'] == period]
            
            # Filter by wet/dry status if specified
            if wet_status is not None:
                period_data = period_data[period_data['is_wet'] == wet_status]
            
            # Get temperature values (drop NaN)
            temp_values = period_data[temp_col].dropna()
            
            if len(temp_values) > 0:
                means[period - 1] = temp_values.mean()
                stds[period - 1] = temp_values.std(ddof=1) if len(temp_values) > 1 else 0.0
                counts[period - 1] = len(temp_values)
            else:
                # No data for this period - use neighboring periods or overall mean
                warnings.warn(
                    f"No data for period {period} "
                    f"({'wet' if wet_status else 'dry' if wet_status is False else 'all'} days). "
                    f"Using interpolated values."
                )
                # Will be filled in by interpolation below
                means[period - 1] = np.nan
                stds[period - 1] = np.nan
        
        # Fill in missing values by linear interpolation
        if np.any(np.isnan(means)):
            means = self._interpolate_missing(means)
        if np.any(np.isnan(stds)):
            stds = self._interpolate_missing(stds)
        
        return {
            'means': means,
            'stds': stds,
            'counts': counts
        }
    
    def _interpolate_missing(self, values: np.ndarray) -> np.ndarray:
        """Interpolate missing values in a circular array.
        
        Uses linear interpolation with wraparound for circular data.
        
        Args:
            values: Array with potential NaN values
        
        Returns:
            Array with NaN values filled by interpolation
        """
        if not np.any(np.isnan(values)):
            return values
        
        # Create indices
        indices = np.arange(len(values))
        
        # Find valid (non-NaN) values
        valid_mask = ~np.isnan(values)
        
        if not np.any(valid_mask):
            # All values are NaN - use a default
            warnings.warn("All period values are missing. Using default value of 0.")
            return np.zeros_like(values)
        
        # Interpolate using valid values
        # For circular data, we need to handle wraparound
        valid_indices = indices[valid_mask]
        valid_values = values[valid_mask]
        
        # Simple linear interpolation
        result = values.copy()
        for i in indices[~valid_mask]:
            # Find nearest valid neighbors
            lower_idx = valid_indices[valid_indices < i]
            upper_idx = valid_indices[valid_indices > i]
            
            if len(lower_idx) > 0 and len(upper_idx) > 0:
                # Interpolate between neighbors
                i_lower = lower_idx[-1]
                i_upper = upper_idx[0]
                v_lower = values[i_lower]
                v_upper = values[i_upper]
                
                # Linear interpolation
                weight = (i - i_lower) / (i_upper - i_lower)
                result[i] = v_lower + weight * (v_upper - v_lower)
            elif len(lower_idx) > 0:
                # Use last valid value (wrap to first)
                i_lower = lower_idx[-1]
                i_upper = valid_indices[0]
                v_lower = values[i_lower]
                v_upper = values[i_upper]
                
                # Wrap around
                dist_to_end = len(values) - i_lower
                dist_from_start = i_upper
                total_dist = dist_to_end + dist_from_start
                dist_to_i = i - i_lower
                
                weight = dist_to_i / total_dist
                result[i] = v_lower + weight * (v_upper - v_lower)
            else:
                # Use first valid value (wrap to last)
                i_upper = upper_idx[0]
                i_lower = valid_indices[-1]
                v_upper = values[i_upper]
                v_lower = values[i_lower]
                
                # Wrap around
                dist_from_end = len(values) - i_lower
                dist_to_start = i_upper
                total_dist = dist_from_end + dist_to_start
                dist_to_i = dist_from_end + i
                
                weight = dist_to_i / total_dist
                result[i] = v_lower + weight * (v_upper - v_lower)
        
        return result
    
    def _fit_fourier_series(self, period_means: np.ndarray) -> Tuple[float, float]:
        """Fit 13-period Fourier series to period means.
        
        Fits the model: T = mean + amplitude * cos(2π(period - peak) / 13)
        
        Args:
            period_means: Array of 13 mean values (one per period)
        
        Returns:
            Tuple of (mean, amplitude) coefficients
        """
        # Period indices (1-13)
        periods = np.arange(1, self.num_periods + 1)
        
        # Define Fourier model
        def fourier_model(period, mean, amplitude, phase):
            """Fourier series model with mean, amplitude, and phase."""
            return mean + amplitude * np.cos(2 * np.pi * (period - phase) / self.num_periods)
        
        try:
            # Initial guess: mean = average, amplitude = half range, phase = period of max
            mean_guess = np.mean(period_means)
            amplitude_guess = (np.max(period_means) - np.min(period_means)) / 2
            phase_guess = np.argmax(period_means) + 1  # Period of maximum
            
            # Fit the model
            popt, _ = curve_fit(
                fourier_model,
                periods,
                period_means,
                p0=[mean_guess, amplitude_guess, phase_guess],
                maxfev=10000
            )
            
            mean, amplitude, phase = popt
            
            # Ensure amplitude is positive
            amplitude = abs(amplitude)
            
        except Exception as e:
            warnings.warn(
                f"Fourier series fitting failed: {e}. "
                f"Using simple mean and amplitude estimates."
            )
            # Fallback to simple estimates
            mean = np.mean(period_means)
            amplitude = (np.max(period_means) - np.min(period_means)) / 2
        
        return mean, amplitude
    
    def _calculate_cv_params(self, stats: Dict[str, np.ndarray]) -> Tuple[float, float]:
        """Calculate coefficient of variation parameters.
        
        Calculates mean CV and amplitude of CV across periods.
        CV = std / mean (coefficient of variation)
        
        IMPORTANT: CV is calculated in Kelvin to avoid division-by-zero issues
        when temperatures in Celsius are near zero. Since CV is dimensionless,
        the Kelvin-based CV can be used directly with Celsius temperatures.
        
        Args:
            stats: Dictionary with 'means' and 'stds' arrays (in Celsius)
        
        Returns:
            Tuple of (cv_mean, cv_amplitude)
        """
        means_celsius = stats['means']
        stds_celsius = stats['stds']
        
        # Convert to Kelvin to avoid near-zero division issues
        # Temperature in Kelvin = Temperature in Celsius + 273.15
        means_kelvin = means_celsius + 273.15
        
        # Standard deviation is the same in both scales (it's a difference)
        stds_kelvin = stds_celsius
        
        # Calculate CV for each period in Kelvin
        cvs = np.zeros(self.num_periods)
        for i in range(self.num_periods):
            if means_kelvin[i] > 0:  # Should always be true for physical temperatures
                cvs[i] = stds_kelvin[i] / means_kelvin[i]
            else:
                # This should never happen for physical temperatures
                cvs[i] = 0.0
        
        # Calculate mean CV
        cv_mean = np.mean(cvs)
        
        # Calculate amplitude of CV (half the range)
        cv_amplitude = (np.max(cvs) - np.min(cvs)) / 2
        
        return cv_mean, cv_amplitude
