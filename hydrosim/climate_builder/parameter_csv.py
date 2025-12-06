"""
Parameter CSV writer for WGEN parameters.

This module provides functionality to write WGEN parameters to CSV files
in a format compatible with the existing CSVWGENParamsParser.
"""

from pathlib import Path
from typing import Dict, Any
import numpy as np


class ParameterCSVWriter:
    """Writer for WGEN parameters to CSV files.
    
    This class writes WGEN parameters to a structured CSV format with sections
    for monthly parameters, temperature parameters, radiation parameters, and
    location parameters. The format is compatible with CSVWGENParamsParser.
    
    CSV File Format:
    ----------------
    1. Monthly Parameters Section (12 rows):
       - Header: month,pww,pwd,alpha,beta
       - 12 data rows (jan through dec) with monthly precipitation parameters
    
    2. Temperature Parameters Section (9 rows after blank line):
       - Header: parameter,value
       - Rows for: txmd, atx, txmw, tn, atn, cvtx, acvtx, cvtn, acvtn
    
    3. Radiation Parameters Section (3 rows after blank line):
       - Header: parameter,value
       - Rows for: rmd, ar, rmw
    
    4. Location Parameters Section (2 rows after blank line):
       - Header: parameter,value
       - Rows for: latitude, random_seed
    
    Example:
        writer = ParameterCSVWriter()
        params = {
            'pww': [0.45, 0.42, ...],  # 12 monthly values
            'pwd': [0.25, 0.23, ...],  # 12 monthly values
            'alpha': [1.2, 1.1, ...],  # 12 monthly values
            'beta': [8.5, 7.8, ...],   # 12 monthly values
            'txmd': 20.0,
            'atx': 10.0,
            # ... other parameters
            'latitude': 47.45
        }
        writer.write(params, 'data/processed/wgen_params.csv')
    """
    
    # Month names for monthly parameters
    MONTH_NAMES = ['jan', 'feb', 'mar', 'apr', 'may', 'jun',
                   'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
    
    # Monthly parameter names (12 values each)
    MONTHLY_PARAMS = ['pww', 'pwd', 'alpha', 'beta']
    
    # Temperature parameter names (single value each)
    TEMPERATURE_PARAMS = ['txmd', 'atx', 'txmw', 'tn', 'atn',
                         'cvtx', 'acvtx', 'cvtn', 'acvtn']
    
    # Radiation parameter names (single value each)
    RADIATION_PARAMS = ['rmd', 'ar', 'rmw']
    
    # Location parameter names
    LOCATION_PARAMS = ['latitude', 'random_seed']
    
    def __init__(self):
        """Initialize the parameter CSV writer."""
        pass
    
    def write(
        self,
        params: Dict[str, Any],
        output_path: Path,
        random_seed: int = 42
    ) -> Path:
        """Write WGEN parameters to CSV file.
        
        Args:
            params: Dictionary containing all WGEN parameters:
                Monthly parameters (lists of 12 values):
                    - 'pww': P(wet|wet) probabilities
                    - 'pwd': P(wet|dry) probabilities
                    - 'alpha': Gamma shape parameters
                    - 'beta': Gamma scale parameters
                
                Temperature parameters (single values):
                    - 'txmd': Mean Tmax on dry days
                    - 'atx': Amplitude of Tmax on dry days
                    - 'txmw': Mean Tmax on wet days
                    - 'tn': Mean Tmin
                    - 'atn': Amplitude of Tmin
                    - 'cvtx': CV for Tmax
                    - 'acvtx': Amplitude of CV for Tmax
                    - 'cvtn': CV for Tmin
                    - 'acvtn': Amplitude of CV for Tmin
                
                Radiation parameters:
                    - 'rmd': Mean solar on dry days (single value or list of 12)
                    - 'rmw': Mean solar on wet days (single value or list of 12)
                    - 'ar': Solar amplitude (single value)
                
                Location parameters:
                    - 'latitude': Site latitude in decimal degrees
            
            output_path: Path where CSV file should be written
            random_seed: Random seed for reproducibility (default: 42)
        
        Returns:
            Path to the written CSV file
        
        Raises:
            ValueError: If required parameters are missing or invalid
            IOError: If file cannot be written
        """
        # Validate parameters
        self._validate_parameters(params)
        
        # Convert output_path to Path object
        output_path = Path(output_path)
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert monthly rmd/rmw to annual averages if they are lists
        # (for compatibility with existing WGEN implementation)
        rmd_value = self._get_annual_value(params['rmd'])
        rmw_value = self._get_annual_value(params['rmw'])
        
        try:
            with open(output_path, 'w') as f:
                # Write monthly precipitation parameters section
                self._write_monthly_section(f, params)
                
                # Write blank line separator
                f.write("\n")
                
                # Write temperature parameters section
                self._write_temperature_section(f, params)
                
                # Write blank line separator
                f.write("\n")
                
                # Write radiation parameters section
                self._write_radiation_section(f, params, rmd_value, rmw_value)
                
                # Write blank line separator
                f.write("\n")
                
                # Write location parameters section
                self._write_location_section(f, params, random_seed)
        
        except Exception as e:
            raise IOError(f"Failed to write parameters to {output_path}: {e}")
        
        return output_path
    
    def _validate_parameters(self, params: Dict[str, Any]) -> None:
        """Validate that all required parameters are present.
        
        Args:
            params: Dictionary of WGEN parameters
        
        Raises:
            ValueError: If required parameters are missing
        """
        # Check monthly parameters
        for param_name in self.MONTHLY_PARAMS:
            if param_name not in params:
                raise ValueError(
                    f"Missing required monthly parameter: {param_name}"
                )
            
            # Validate it's a list with 12 values
            param_value = params[param_name]
            if not isinstance(param_value, (list, tuple, np.ndarray)):
                raise ValueError(
                    f"Monthly parameter '{param_name}' must be a list/array, "
                    f"got {type(param_value)}"
                )
            
            if len(param_value) != 12:
                raise ValueError(
                    f"Monthly parameter '{param_name}' must have 12 values, "
                    f"got {len(param_value)}"
                )
        
        # Check temperature parameters
        for param_name in self.TEMPERATURE_PARAMS:
            if param_name not in params:
                raise ValueError(
                    f"Missing required temperature parameter: {param_name}"
                )
        
        # Check radiation parameters
        for param_name in self.RADIATION_PARAMS:
            if param_name not in params:
                raise ValueError(
                    f"Missing required radiation parameter: {param_name}"
                )
        
        # Check latitude
        if 'latitude' not in params:
            raise ValueError("Missing required location parameter: latitude")
    
    def _get_annual_value(self, value: Any) -> float:
        """Convert monthly values to annual average, or return single value.
        
        Args:
            value: Either a single numeric value or a list of 12 monthly values
        
        Returns:
            Single float value (annual average if input was monthly)
        """
        if isinstance(value, (list, tuple, np.ndarray)):
            # Convert monthly values to annual average
            return float(np.mean(value))
        else:
            # Already a single value
            return float(value)
    
    def _write_monthly_section(self, f, params: Dict[str, Any]) -> None:
        """Write the monthly precipitation parameters section.
        
        Args:
            f: File handle to write to
            params: Dictionary of WGEN parameters
        """
        # Write header
        f.write("month,pww,pwd,alpha,beta\n")
        
        # Write 12 monthly rows
        for i, month_name in enumerate(self.MONTH_NAMES):
            pww = params['pww'][i]
            pwd = params['pwd'][i]
            alpha = params['alpha'][i]
            beta = params['beta'][i]
            
            f.write(f"{month_name},{pww:.6f},{pwd:.6f},"
                   f"{alpha:.6f},{beta:.6f}\n")
    
    def _write_temperature_section(self, f, params: Dict[str, Any]) -> None:
        """Write the temperature parameters section.
        
        Args:
            f: File handle to write to
            params: Dictionary of WGEN parameters
        """
        # Write header
        f.write("parameter,value\n")
        
        # Write temperature parameters
        for param_name in self.TEMPERATURE_PARAMS:
            value = params[param_name]
            f.write(f"{param_name},{value:.6f}\n")
    
    def _write_radiation_section(
        self,
        f,
        params: Dict[str, Any],
        rmd_value: float,
        rmw_value: float
    ) -> None:
        """Write the radiation parameters section.
        
        Args:
            f: File handle to write to
            params: Dictionary of WGEN parameters
            rmd_value: Annual average RMD value
            rmw_value: Annual average RMW value
        """
        # Write header
        f.write("parameter,value\n")
        
        # Write radiation parameters
        f.write(f"rmd,{rmd_value:.6f}\n")
        f.write(f"ar,{params['ar']:.6f}\n")
        f.write(f"rmw,{rmw_value:.6f}\n")
    
    def _write_location_section(
        self,
        f,
        params: Dict[str, Any],
        random_seed: int
    ) -> None:
        """Write the location parameters section.
        
        Args:
            f: File handle to write to
            params: Dictionary of WGEN parameters
            random_seed: Random seed value
        """
        # Write header
        f.write("parameter,value\n")
        
        # Write location parameters
        f.write(f"latitude,{params['latitude']:.6f}\n")
        f.write(f"random_seed,{random_seed}\n")
