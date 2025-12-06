"""
Precipitation parameter calculator for WGEN weather generator.

This module calculates monthly Markov chain transition probabilities and
Gamma distribution parameters from observed precipitation data, following
the algorithms from the legacy wgenpar.f FORTRAN code.
"""

import warnings
from typing import Dict, List, Tuple
import pandas as pd
import numpy as np
from scipy import stats


class PrecipitationParameterCalculator:
    """Calculate WGEN precipitation parameters from observed data.
    
    This calculator implements the precipitation parameter estimation algorithms
    from wgenpar.f, including:
    - Wet/dry day classification using 0.1 mm threshold (WMO standard)
    - Monthly Markov chain transition probabilities (PWW, PWD)
    - Gamma distribution fitting for wet day precipitation amounts
    
    Attributes:
        wet_day_threshold: Precipitation threshold for wet day classification (mm)
        min_wet_days: Minimum number of wet days required for reliable parameter estimation
    """
    
    def __init__(self, wet_day_threshold: float = 0.1, min_wet_days: int = 10):
        """Initialize precipitation parameter calculator.
        
        Args:
            wet_day_threshold: Precipitation threshold for wet day classification in mm
                              (default: 0.1 mm, WMO standard)
            min_wet_days: Minimum number of wet days per month for reliable estimation
                         (default: 10)
        """
        if wet_day_threshold < 0:
            raise ValueError(f"wet_day_threshold must be non-negative, got {wet_day_threshold}")
        
        if min_wet_days < 1:
            raise ValueError(f"min_wet_days must be positive, got {min_wet_days}")
        
        self.wet_day_threshold = wet_day_threshold
        self.min_wet_days = min_wet_days
    
    def calculate_parameters(self, df: pd.DataFrame) -> Dict[str, List[float]]:
        """Calculate all precipitation parameters from observed data.
        
        Args:
            df: DataFrame with columns 'date' and 'precipitation_mm'
                Date should be datetime.date or parseable to datetime
                precipitation_mm should be float (NaN for missing values)
        
        Returns:
            Dictionary with keys:
                - 'pww': List of 12 monthly probabilities (wet|wet)
                - 'pwd': List of 12 monthly probabilities (wet|dry)
                - 'alpha': List of 12 monthly Gamma shape parameters
                - 'beta': List of 12 monthly Gamma scale parameters
        
        Raises:
            ValueError: If required columns are missing or data is insufficient
        """
        # Validate input
        if 'date' not in df.columns:
            raise ValueError("DataFrame must have 'date' column")
        if 'precipitation_mm' not in df.columns:
            raise ValueError("DataFrame must have 'precipitation_mm' column")
        
        # Ensure date is datetime
        if not pd.api.types.is_datetime64_any_dtype(df['date']):
            df = df.copy()
            df['date'] = pd.to_datetime(df['date'])
        
        # Add month column for grouping
        df = df.copy()
        df['month'] = df['date'].dt.month
        
        # Classify wet/dry days
        df['is_wet'] = self._classify_wet_dry(df['precipitation_mm'])
        
        # Calculate Markov chain parameters by month
        pww_list = []
        pwd_list = []
        
        for month in range(1, 13):
            month_data = df[df['month'] == month].copy()
            pww, pwd = self._calculate_markov_params(month_data, month)
            pww_list.append(pww)
            pwd_list.append(pwd)
        
        # Calculate Gamma distribution parameters by month
        alpha_list = []
        beta_list = []
        
        for month in range(1, 13):
            month_data = df[df['month'] == month].copy()
            alpha, beta = self._calculate_gamma_params(month_data, month)
            alpha_list.append(alpha)
            beta_list.append(beta)
        
        return {
            'pww': pww_list,
            'pwd': pwd_list,
            'alpha': alpha_list,
            'beta': beta_list
        }
    
    def _classify_wet_dry(self, precip_series: pd.Series) -> pd.Series:
        """Classify days as wet or dry based on precipitation threshold.
        
        Args:
            precip_series: Series of precipitation values in mm
        
        Returns:
            Boolean series: True for wet days, False for dry days, NaN for missing
        """
        # Days with precipitation >= threshold are wet
        # Days with precipitation < threshold are dry
        # Missing values (NaN) remain NaN
        return precip_series >= self.wet_day_threshold
    
    def _calculate_markov_params(self, month_data: pd.DataFrame, month: int) -> Tuple[float, float]:
        """Calculate Markov chain transition probabilities for a month.
        
        Calculates:
        - PWW = P(wet day | previous day was wet) = NWW / (NWW + NDW)
        - PWD = P(wet day | previous day was dry) = NWD / (NWD + NDD)
        
        Where:
        - NWW = number of wet-to-wet transitions
        - NDW = number of wet-to-dry transitions
        - NWD = number of dry-to-wet transitions
        - NDD = number of dry-to-dry transitions
        
        Args:
            month_data: DataFrame for a specific month with 'is_wet' column
            month: Month number (1-12) for warning messages
        
        Returns:
            Tuple of (pww, pwd)
        """
        # Remove rows with missing wet/dry classification
        valid_data = month_data.dropna(subset=['is_wet'])
        
        if len(valid_data) < 2:
            warnings.warn(
                f"Insufficient data for month {month} Markov chain calculation. "
                f"Using default values (PWW=0.5, PWD=0.3)."
            )
            return 0.5, 0.3
        
        # Count transitions
        is_wet = valid_data['is_wet'].values
        
        # Calculate transitions (current day, previous day)
        nww = 0  # wet -> wet
        ndw = 0  # wet -> dry
        nwd = 0  # dry -> wet
        ndd = 0  # dry -> dry
        
        for i in range(1, len(is_wet)):
            prev_wet = is_wet[i-1]
            curr_wet = is_wet[i]
            
            if prev_wet and curr_wet:
                nww += 1
            elif prev_wet and not curr_wet:
                ndw += 1
            elif not prev_wet and curr_wet:
                nwd += 1
            else:  # not prev_wet and not curr_wet
                ndd += 1
        
        # Calculate probabilities
        # PWW = P(wet | previous wet) = NWW / (NWW + NDW)
        if nww + ndw > 0:
            pww = nww / (nww + ndw)
        else:
            warnings.warn(
                f"No wet days found in month {month} for PWW calculation. "
                f"Using default value (PWW=0.5)."
            )
            pww = 0.5
        
        # PWD = P(wet | previous dry) = NWD / (NWD + NDD)
        if nwd + ndd > 0:
            pwd = nwd / (nwd + ndd)
        else:
            warnings.warn(
                f"No dry days found in month {month} for PWD calculation. "
                f"Using default value (PWD=0.3)."
            )
            pwd = 0.3
        
        return pww, pwd
    
    def _calculate_gamma_params(self, month_data: pd.DataFrame, month: int) -> Tuple[float, float]:
        """Calculate Gamma distribution parameters for wet day precipitation amounts.
        
        Fits a Gamma distribution to precipitation amounts on wet days only.
        Uses method of moments for parameter estimation.
        
        Args:
            month_data: DataFrame for a specific month with 'precipitation_mm' and 'is_wet' columns
            month: Month number (1-12) for warning messages
        
        Returns:
            Tuple of (alpha, beta) where:
                - alpha: shape parameter
                - beta: scale parameter
        """
        # Get wet day precipitation amounts (excluding missing values)
        wet_days = month_data[month_data['is_wet'] == True]['precipitation_mm'].dropna()
        
        # Filter out zero or near-zero values (should already be classified as dry, but double-check)
        wet_amounts = wet_days[wet_days >= self.wet_day_threshold].values
        
        if len(wet_amounts) < self.min_wet_days:
            warnings.warn(
                f"Insufficient wet days in month {month} for Gamma parameter estimation. "
                f"Found {len(wet_amounts)} wet days, need at least {self.min_wet_days}. "
                f"Using neighboring month values or defaults."
            )
            # Return reasonable default values
            # These are typical values for moderate precipitation climates
            return 1.5, 5.0
        
        # Method of moments estimation
        # For Gamma distribution: mean = alpha * beta, variance = alpha * beta^2
        # Therefore: alpha = mean^2 / variance, beta = variance / mean
        mean_precip = np.mean(wet_amounts)
        var_precip = np.var(wet_amounts, ddof=1)  # Use sample variance
        
        if var_precip <= 0 or mean_precip <= 0:
            warnings.warn(
                f"Invalid statistics for month {month} Gamma fitting "
                f"(mean={mean_precip:.2f}, var={var_precip:.2f}). "
                f"Using default values."
            )
            return 1.5, 5.0
        
        # Calculate parameters
        beta = var_precip / mean_precip
        alpha = mean_precip / beta
        
        # Validate parameters are positive
        if alpha <= 0 or beta <= 0:
            warnings.warn(
                f"Invalid Gamma parameters for month {month} "
                f"(alpha={alpha:.2f}, beta={beta:.2f}). "
                f"Using default values."
            )
            return 1.5, 5.0
        
        return alpha, beta
    
    def handle_insufficient_months(
        self, 
        params: Dict[str, List[float]], 
        min_wet_days_per_month: Dict[int, int]
    ) -> Dict[str, List[float]]:
        """Handle months with insufficient wet days by using neighboring months.
        
        For months with insufficient data, uses the average of neighboring months
        (or the nearest available month if neighbors are also insufficient).
        
        Args:
            params: Dictionary of parameter lists (pww, pwd, alpha, beta)
            min_wet_days_per_month: Dictionary mapping month (1-12) to number of wet days
        
        Returns:
            Updated parameter dictionary with filled-in values for insufficient months
        """
        # Identify months with insufficient data
        insufficient_months = [
            month for month, count in min_wet_days_per_month.items()
            if count < self.min_wet_days
        ]
        
        if not insufficient_months:
            return params
        
        # For each insufficient month, use neighboring months
        for month in insufficient_months:
            # Get neighboring months (wrap around for Jan/Dec)
            prev_month = month - 1 if month > 1 else 12
            next_month = month + 1 if month < 12 else 1
            
            # Try to use average of neighbors
            neighbors = []
            if min_wet_days_per_month.get(prev_month, 0) >= self.min_wet_days:
                neighbors.append(prev_month)
            if min_wet_days_per_month.get(next_month, 0) >= self.min_wet_days:
                neighbors.append(next_month)
            
            if neighbors:
                # Use average of available neighbors
                for param_name in ['pww', 'pwd', 'alpha', 'beta']:
                    neighbor_values = [params[param_name][m-1] for m in neighbors]
                    params[param_name][month-1] = np.mean(neighbor_values)
                
                warnings.warn(
                    f"Month {month} has insufficient wet days. "
                    f"Using average of neighboring months {neighbors}."
                )
            else:
                # No good neighbors, use annual average
                for param_name in ['pww', 'pwd', 'alpha', 'beta']:
                    # Calculate average from months with sufficient data
                    valid_values = [
                        params[param_name][m-1] 
                        for m in range(1, 13)
                        if min_wet_days_per_month.get(m, 0) >= self.min_wet_days
                    ]
                    if valid_values:
                        params[param_name][month-1] = np.mean(valid_values)
                    # else: keep the default value already assigned
                
                warnings.warn(
                    f"Month {month} has insufficient wet days and no valid neighbors. "
                    f"Using annual average from valid months."
                )
        
        return params
