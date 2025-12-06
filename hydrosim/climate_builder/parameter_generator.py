"""
WGEN parameter generator orchestrator for Climate Builder.

This module coordinates all parameter calculators (precipitation, temperature, solar)
to generate a complete set of WGEN parameters from observed climate data.
"""

import warnings
from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd

from hydrosim.climate_builder.precipitation_params import PrecipitationParameterCalculator
from hydrosim.climate_builder.temperature_params import TemperatureParameterCalculator
from hydrosim.climate_builder.solar_params import SolarParameterCalculator
from hydrosim.climate_builder.parameter_csv import ParameterCSVWriter


class WGENParameterGenerator:
    """Orchestrator for generating all WGEN parameters from observed data.
    
    This class coordinates the precipitation, temperature, and solar parameter
    calculators to produce a unified set of WGEN parameters. It also validates
    parameter ranges and enforces physical constraints.
    
    Attributes:
        observed_data_path: Path to observed climate CSV file
        latitude: Site latitude in decimal degrees (-90 to 90)
        output_dir: Directory for output files
        wet_day_threshold: Precipitation threshold for wet day classification (mm)
    
    Example:
        generator = WGENParameterGenerator(
            observed_data_path="data/processed/observed_climate.csv",
            latitude=47.45,
            output_dir="./my_project"
        )
        params = generator.generate_all_parameters()
        generator.save_parameters_to_csv(params)
    """
    
    def __init__(
        self,
        observed_data_path: Path,
        latitude: float,
        output_dir: Path,
        wet_day_threshold: float = 0.1
    ):
        """Initialize WGEN parameter generator.
        
        Args:
            observed_data_path: Path to observed climate CSV file with columns:
                               date, precipitation_mm, tmax_c, tmin_c
            latitude: Site latitude in decimal degrees (-90 to 90)
            output_dir: Directory for output files
            wet_day_threshold: Precipitation threshold for wet day classification in mm
                              (default: 0.1 mm, WMO standard)
        
        Raises:
            ValueError: If latitude is outside valid range or files don't exist
        """
        # Validate latitude
        if not -90 <= latitude <= 90:
            raise ValueError(f"Latitude must be in [-90, 90], got {latitude}")
        
        # Validate paths
        observed_data_path = Path(observed_data_path)
        if not observed_data_path.exists():
            raise ValueError(f"Observed data file not found: {observed_data_path}")
        
        output_dir = Path(output_dir)
        if not output_dir.exists():
            raise ValueError(f"Output directory not found: {output_dir}")
        
        self.observed_data_path = observed_data_path
        self.latitude = latitude
        self.output_dir = output_dir
        self.wet_day_threshold = wet_day_threshold
        
        # Initialize calculators
        self.precip_calc = PrecipitationParameterCalculator(
            wet_day_threshold=wet_day_threshold
        )
        self.temp_calc = TemperatureParameterCalculator(
            wet_day_threshold=wet_day_threshold
        )
        self.solar_calc = SolarParameterCalculator(
            latitude=latitude,
            wet_day_threshold=wet_day_threshold
        )
    
    def generate_all_parameters(self, has_solar_data: bool = False) -> Dict[str, Any]:
        """Generate all WGEN parameters from observed data.
        
        This method:
        1. Loads observed climate data
        2. Calls precipitation calculator for Markov chain and Gamma parameters
        3. Calls temperature calculator for Fourier series parameters
        4. Calls solar calculator for solar radiation parameters
        5. Combines results into unified parameter dictionary
        6. Validates parameter ranges and physical constraints
        
        Args:
            has_solar_data: Whether observed solar radiation data is available
                           (default: False, will estimate solar parameters)
        
        Returns:
            Dictionary containing all WGEN parameters:
                Precipitation parameters (monthly):
                    - 'pww': List of 12 monthly P(wet|wet) probabilities
                    - 'pwd': List of 12 monthly P(wet|dry) probabilities
                    - 'alpha': List of 12 monthly Gamma shape parameters
                    - 'beta': List of 12 monthly Gamma scale parameters
                
                Temperature parameters:
                    - 'txmd': Mean Tmax on dry days (Fourier mean)
                    - 'atx': Amplitude of Tmax on dry days
                    - 'txmw': Mean Tmax on wet days (Fourier mean)
                    - 'tn': Mean Tmin (Fourier mean)
                    - 'atn': Amplitude of Tmin
                    - 'cvtx': Coefficient of variation for Tmax
                    - 'acvtx': Amplitude of CV for Tmax
                    - 'cvtn': Coefficient of variation for Tmin
                    - 'acvtn': Amplitude of CV for Tmin
                
                Solar parameters (monthly):
                    - 'rmd': List of 12 monthly mean solar on dry days (MJ/m²/day)
                    - 'rmw': List of 12 monthly mean solar on wet days (MJ/m²/day)
                    - 'ar': Amplitude of solar radiation Fourier series
                
                Location parameters:
                    - 'latitude': Site latitude in decimal degrees
        
        Raises:
            ValueError: If data is insufficient or parameters are invalid
        """
        # Load observed data
        df = self._load_observed_data()
        
        # Generate precipitation parameters
        print("Calculating precipitation parameters...")
        precip_params = self.precip_calc.calculate_parameters(df)
        
        # Generate temperature parameters
        print("Calculating temperature parameters...")
        temp_params = self.temp_calc.calculate_parameters(df)
        
        # Generate solar parameters
        print("Calculating solar radiation parameters...")
        solar_params = self.solar_calc.calculate_parameters(df, has_solar_data=has_solar_data)
        
        # Combine all parameters
        all_params = {
            # Precipitation parameters
            'pww': precip_params['pww'],
            'pwd': precip_params['pwd'],
            'alpha': precip_params['alpha'],
            'beta': precip_params['beta'],
            
            # Temperature parameters
            'txmd': temp_params['txmd'],
            'atx': temp_params['atx'],
            'txmw': temp_params['txmw'],
            'tn': temp_params['tn'],
            'atn': temp_params['atn'],
            'cvtx': temp_params['cvtx'],
            'acvtx': temp_params['acvtx'],
            'cvtn': temp_params['cvtn'],
            'acvtn': temp_params['acvtn'],
            
            # Solar parameters
            'rmd': solar_params['rmd'],
            'rmw': solar_params['rmw'],
            'ar': solar_params['ar'],
            
            # Location parameters
            'latitude': self.latitude
        }
        
        # Validate parameters
        print("Validating parameters...")
        self._validate_parameters(all_params)
        
        print("Parameter generation complete!")
        return all_params
    
    def _load_observed_data(self) -> pd.DataFrame:
        """Load observed climate data from CSV file.
        
        Returns:
            DataFrame with columns: date, precipitation_mm, tmax_c, tmin_c
                                   (and optionally solar_mjm2)
        
        Raises:
            ValueError: If required columns are missing
        """
        try:
            df = pd.read_csv(self.observed_data_path)
        except Exception as e:
            raise ValueError(f"Failed to load observed data: {e}")
        
        # Validate required columns
        required_cols = ['date', 'precipitation_mm', 'tmax_c', 'tmin_c']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(
                f"Observed data file missing required columns: {missing_cols}"
            )
        
        # Convert date column to datetime
        df['date'] = pd.to_datetime(df['date'])
        
        return df
    
    def _validate_parameters(self, params: Dict[str, Any]) -> None:
        """Validate parameter ranges and physical constraints.
        
        Checks that all parameters are within physically realistic ranges
        and issues warnings for suspicious values.
        
        Args:
            params: Dictionary of all WGEN parameters
        
        Raises:
            ValueError: If parameters are outside valid ranges
        """
        # Validate precipitation parameters
        for month_idx in range(12):
            month = month_idx + 1
            
            # PWW and PWD should be probabilities [0, 1]
            pww = params['pww'][month_idx]
            pwd = params['pwd'][month_idx]
            
            if not 0 <= pww <= 1:
                raise ValueError(
                    f"PWW for month {month} out of range [0, 1]: {pww}"
                )
            
            if not 0 <= pwd <= 1:
                raise ValueError(
                    f"PWD for month {month} out of range [0, 1]: {pwd}"
                )
            
            # Alpha and Beta should be positive
            alpha = params['alpha'][month_idx]
            beta = params['beta'][month_idx]
            
            if alpha <= 0:
                raise ValueError(
                    f"Alpha for month {month} must be positive: {alpha}"
                )
            
            if beta <= 0:
                raise ValueError(
                    f"Beta for month {month} must be positive: {beta}"
                )
            
            # Warn if parameters are unusual
            if pww < 0.1 or pww > 0.9:
                warnings.warn(
                    f"Unusual PWW value for month {month}: {pww:.3f}. "
                    f"Typical range is [0.3, 0.8]."
                )
            
            if pwd < 0.05 or pwd > 0.5:
                warnings.warn(
                    f"Unusual PWD value for month {month}: {pwd:.3f}. "
                    f"Typical range is [0.1, 0.4]."
                )
        
        # Validate temperature parameters
        temp_params = ['txmd', 'atx', 'txmw', 'tn', 'atn']
        for param_name in temp_params:
            value = params[param_name]
            
            # Temperature means should be in reasonable range
            if param_name in ['txmd', 'txmw', 'tn']:
                if not -50 <= value <= 50:
                    warnings.warn(
                        f"Unusual temperature parameter {param_name}: {value:.2f}°C. "
                        f"Expected range is roughly [-50, 50]°C."
                    )
            
            # Amplitudes should be positive and reasonable
            if param_name in ['atx', 'atn']:
                if value < 0:
                    raise ValueError(
                        f"Temperature amplitude {param_name} must be non-negative: {value}"
                    )
                
                if value > 30:
                    warnings.warn(
                        f"Large temperature amplitude {param_name}: {value:.2f}°C. "
                        f"This indicates very strong seasonal variation."
                    )
        
        # Validate CV parameters
        cv_params = ['cvtx', 'acvtx', 'cvtn', 'acvtn']
        for param_name in cv_params:
            value = params[param_name]
            
            if value < 0:
                raise ValueError(
                    f"Coefficient of variation {param_name} must be non-negative: {value}"
                )
            
            if value > 1.0:
                warnings.warn(
                    f"Large coefficient of variation {param_name}: {value:.3f}. "
                    f"This indicates high temperature variability."
                )
        
        # Validate solar parameters
        for month_idx in range(12):
            month = month_idx + 1
            
            rmd = params['rmd'][month_idx]
            rmw = params['rmw'][month_idx]
            
            # Solar radiation should be non-negative
            if rmd < 0:
                raise ValueError(
                    f"RMD for month {month} must be non-negative: {rmd}"
                )
            
            if rmw < 0:
                raise ValueError(
                    f"RMW for month {month} must be non-negative: {rmw}"
                )
            
            # RMD should be >= RMW (dry days have more solar than wet days)
            if rmd < rmw:
                warnings.warn(
                    f"Month {month}: RMD ({rmd:.2f}) < RMW ({rmw:.2f}). "
                    f"Typically dry days have more solar radiation than wet days."
                )
            
            # Solar values should be reasonable (< 50 MJ/m²/day)
            if rmd > 50:
                warnings.warn(
                    f"Very high RMD for month {month}: {rmd:.2f} MJ/m²/day. "
                    f"Typical maximum is around 40 MJ/m²/day."
                )
            
            if rmw > 50:
                warnings.warn(
                    f"Very high RMW for month {month}: {rmw:.2f} MJ/m²/day. "
                    f"Typical maximum is around 40 MJ/m²/day."
                )
        
        # Validate AR (solar amplitude)
        ar = params['ar']
        if ar < 0:
            raise ValueError(f"Solar amplitude AR must be non-negative: {ar}")
        
        if ar > 20:
            warnings.warn(
                f"Large solar amplitude AR: {ar:.2f} MJ/m²/day. "
                f"This indicates very strong seasonal variation in solar radiation."
            )
        
        # Validate latitude
        latitude = params['latitude']
        if not -90 <= latitude <= 90:
            raise ValueError(f"Latitude must be in [-90, 90], got {latitude}")
    
    def save_parameters_to_csv(self, params: Dict[str, Any], filename: str = "wgen_params.csv") -> Path:
        """Save parameters to CSV file in WGEN format.
        
        Creates a CSV file compatible with the existing CSVWGENParamsParser.
        Uses the ParameterCSVWriter class to write the structured CSV format.
        
        Args:
            params: Dictionary of all WGEN parameters
            filename: Output filename (default: "wgen_params.csv")
        
        Returns:
            Path to saved CSV file
        
        Raises:
            IOError: If file cannot be written
        """
        output_path = self.output_dir / "data" / "processed" / filename
        
        # Use ParameterCSVWriter to write the CSV file
        writer = ParameterCSVWriter()
        output_path = writer.write(params, output_path)
        
        print(f"Parameters saved to: {output_path}")
        return output_path
