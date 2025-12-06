"""
Core data models for Climate Builder module.

This module defines the data structures used throughout the Climate Builder:
- ObservedClimateData: Represents a single day of observed climate data
- ClimateData: Represents a single day of climate data (observed or synthetic)
- DataQualityReport: Contains data quality metrics and warnings
"""

import datetime
from dataclasses import dataclass
from typing import Optional, List, Dict


@dataclass
class ObservedClimateData:
    """Observed climate data for a single day.
    
    This represents raw climate observations from GHCN or other sources.
    Missing values are represented as None (converted from NaN during parsing).
    
    Attributes:
        date: Date of observation
        precipitation_mm: Daily precipitation in millimeters (>= 0, or None if missing)
        tmax_c: Daily maximum temperature in degrees Celsius (or None if missing)
        tmin_c: Daily minimum temperature in degrees Celsius (or None if missing)
        solar_mjm2: Daily solar radiation in MJ/m²/day (optional, rarely available)
    
    Notes:
        - February 29th dates are excluded to maintain 365-day calendar
        - Missing values (-9999 in GHCN format) are represented as None
        - Precipitation values should be non-negative when present
        - Temperature values should be physically realistic (-100 to 60°C typical range)
    """
    date: datetime.date
    precipitation_mm: Optional[float]
    tmax_c: Optional[float]
    tmin_c: Optional[float]
    solar_mjm2: Optional[float] = None
    
    def __post_init__(self):
        """Validate data values."""
        # Validate precipitation is non-negative if present
        if self.precipitation_mm is not None and self.precipitation_mm < 0:
            raise ValueError(
                f"Precipitation must be non-negative, got {self.precipitation_mm} mm on {self.date}"
            )
        
        # Validate temperature range if present (basic sanity check)
        if self.tmax_c is not None and not -100 <= self.tmax_c <= 60:
            raise ValueError(
                f"Maximum temperature out of realistic range: {self.tmax_c}°C on {self.date}"
            )
        
        if self.tmin_c is not None and not -100 <= self.tmin_c <= 60:
            raise ValueError(
                f"Minimum temperature out of realistic range: {self.tmin_c}°C on {self.date}"
            )
        
        # Validate tmax >= tmin if both present
        if (self.tmax_c is not None and self.tmin_c is not None and 
            self.tmax_c < self.tmin_c):
            raise ValueError(
                f"Maximum temperature ({self.tmax_c}°C) less than minimum temperature "
                f"({self.tmin_c}°C) on {self.date}"
            )
        
        # Validate solar radiation is non-negative if present
        if self.solar_mjm2 is not None and self.solar_mjm2 < 0:
            raise ValueError(
                f"Solar radiation must be non-negative, got {self.solar_mjm2} MJ/m²/day on {self.date}"
            )
        
        # Validate no February 29th dates (WGEN uses 365-day calendar)
        if self.date.month == 2 and self.date.day == 29:
            raise ValueError(
                f"February 29th dates are not allowed (WGEN uses 365-day calendar): {self.date}"
            )
    
    def is_wet_day(self, threshold_mm: float = 0.1) -> Optional[bool]:
        """Determine if this is a wet day based on precipitation threshold.
        
        Args:
            threshold_mm: Precipitation threshold for wet day classification (default: 0.1 mm, WMO standard)
        
        Returns:
            True if wet day, False if dry day, None if precipitation data is missing
        """
        if self.precipitation_mm is None:
            return None
        return self.precipitation_mm >= threshold_mm
    
    def has_complete_data(self) -> bool:
        """Check if all required variables are present (P, Tmax, Tmin).
        
        Returns:
            True if precipitation, tmax, and tmin are all present
        """
        return (
            self.precipitation_mm is not None and
            self.tmax_c is not None and
            self.tmin_c is not None
        )


@dataclass
class ClimateData:
    """Climate data for a single day (observed or synthetic).
    
    This represents complete climate data for simulation, with all required
    variables present. Used by simulation drivers to provide climate inputs
    to the HydroSim engine.
    
    Attributes:
        date: Date of data
        precipitation_mm: Daily precipitation in millimeters (>= 0)
        tmax_c: Daily maximum temperature in degrees Celsius
        tmin_c: Daily minimum temperature in degrees Celsius
        solar_mjm2: Daily solar radiation in MJ/m²/day (>= 0)
        is_wet: Whether this is a wet day (precipitation >= 0.1 mm)
        source: Data source indicator ('observed', 'synthetic', or 'mixed')
    
    Notes:
        - All values must be present (no None values allowed)
        - Solar radiation is always synthetic in Climate Builder
        - In Mode A (Historical): P and T are observed, Solar is synthetic
        - In Mode B (Stochastic): All variables are synthetic
    """
    date: datetime.date
    precipitation_mm: float
    tmax_c: float
    tmin_c: float
    solar_mjm2: float
    is_wet: bool
    source: str = 'unknown'
    
    def __post_init__(self):
        """Validate data values."""
        # Validate all values are present
        if self.precipitation_mm is None:
            raise ValueError(f"Precipitation cannot be None on {self.date}")
        if self.tmax_c is None:
            raise ValueError(f"Maximum temperature cannot be None on {self.date}")
        if self.tmin_c is None:
            raise ValueError(f"Minimum temperature cannot be None on {self.date}")
        if self.solar_mjm2 is None:
            raise ValueError(f"Solar radiation cannot be None on {self.date}")
        
        # Validate precipitation is non-negative
        if self.precipitation_mm < 0:
            raise ValueError(
                f"Precipitation must be non-negative, got {self.precipitation_mm} mm on {self.date}"
            )
        
        # Validate temperature range (basic sanity check)
        if not -100 <= self.tmax_c <= 60:
            raise ValueError(
                f"Maximum temperature out of realistic range: {self.tmax_c}°C on {self.date}"
            )
        
        if not -100 <= self.tmin_c <= 60:
            raise ValueError(
                f"Minimum temperature out of realistic range: {self.tmin_c}°C on {self.date}"
            )
        
        # Validate tmax >= tmin
        if self.tmax_c < self.tmin_c:
            raise ValueError(
                f"Maximum temperature ({self.tmax_c}°C) less than minimum temperature "
                f"({self.tmin_c}°C) on {self.date}"
            )
        
        # Validate solar radiation is non-negative
        if self.solar_mjm2 < 0:
            raise ValueError(
                f"Solar radiation must be non-negative, got {self.solar_mjm2} MJ/m²/day on {self.date}"
            )
        
        # Validate source
        valid_sources = ['observed', 'synthetic', 'mixed', 'unknown']
        if self.source not in valid_sources:
            raise ValueError(
                f"Invalid source '{self.source}', must be one of {valid_sources}"
            )
        
        # Validate no February 29th dates
        if self.date.month == 2 and self.date.day == 29:
            raise ValueError(
                f"February 29th dates are not allowed (WGEN uses 365-day calendar): {self.date}"
            )
    
    def to_climate_state(self):
        """Convert to HydroSim ClimateState format.
        
        Returns:
            ClimateState object compatible with HydroSim engine
            
        Note:
            ET0 is not calculated here - it should be calculated by the
            climate engine based on temperature and solar radiation.
        """
        from hydrosim.climate import ClimateState
        from datetime import datetime
        
        return ClimateState(
            date=datetime.combine(self.date, datetime.min.time()),
            precip=self.precipitation_mm,
            t_max=self.tmax_c,
            t_min=self.tmin_c,
            solar=self.solar_mjm2,
            et0=0.0  # Will be calculated by climate engine
        )


@dataclass
class DataQualityReport:
    """Data quality metrics and warnings for observed climate data.
    
    This report is generated during data processing to help users assess
    whether the data is suitable for parameter generation and simulation.
    
    Attributes:
        station_id: GHCN station identifier (if applicable)
        data_period_start: First date in dataset
        data_period_end: Last date in dataset
        total_days: Total number of days in dataset
        missing_precip_pct: Percentage of missing precipitation values (0-100)
        missing_tmax_pct: Percentage of missing tmax values (0-100)
        missing_tmin_pct: Percentage of missing tmin values (0-100)
        missing_solar_pct: Percentage of missing solar values (0-100, or None if no solar data)
        unrealistic_values: List of dates with unrealistic values
        warnings: List of warning messages
        errors: List of error messages
    
    Notes:
        - Warnings are issued for >10% missing data
        - Warnings are issued for datasets <10 years
        - Errors indicate data that cannot be processed
    """
    station_id: Optional[str]
    data_period_start: datetime.date
    data_period_end: datetime.date
    total_days: int
    missing_precip_pct: float
    missing_tmax_pct: float
    missing_tmin_pct: float
    missing_solar_pct: Optional[float]
    unrealistic_values: List[Dict[str, any]]
    warnings: List[str]
    errors: List[str]
    
    def __post_init__(self):
        """Validate report values."""
        # Validate percentages are in valid range
        for pct, name in [
            (self.missing_precip_pct, 'missing_precip_pct'),
            (self.missing_tmax_pct, 'missing_tmax_pct'),
            (self.missing_tmin_pct, 'missing_tmin_pct'),
        ]:
            if not 0 <= pct <= 100:
                raise ValueError(f"{name} must be in [0, 100], got {pct}")
        
        if self.missing_solar_pct is not None and not 0 <= self.missing_solar_pct <= 100:
            raise ValueError(
                f"missing_solar_pct must be in [0, 100], got {self.missing_solar_pct}"
            )
        
        # Validate total_days is positive
        if self.total_days <= 0:
            raise ValueError(f"total_days must be positive, got {self.total_days}")
        
        # Validate date range
        if self.data_period_start > self.data_period_end:
            raise ValueError(
                f"data_period_start ({self.data_period_start}) must be <= "
                f"data_period_end ({self.data_period_end})"
            )
    
    def has_sufficient_data(self, max_missing_pct: float = 10.0) -> bool:
        """Check if data quality is sufficient for parameter generation.
        
        Args:
            max_missing_pct: Maximum acceptable percentage of missing data (default: 10%)
        
        Returns:
            True if all required variables have <= max_missing_pct missing data
        """
        return (
            self.missing_precip_pct <= max_missing_pct and
            self.missing_tmax_pct <= max_missing_pct and
            self.missing_tmin_pct <= max_missing_pct
        )
    
    def has_sufficient_length(self, min_years: int = 10) -> bool:
        """Check if dataset is long enough for reliable parameter estimation.
        
        Args:
            min_years: Minimum number of years required (default: 10)
        
        Returns:
            True if dataset spans at least min_years
        """
        years = (self.data_period_end - self.data_period_start).days / 365.25
        return years >= min_years
    
    def generate_warnings(self) -> List[str]:
        """Generate warning messages based on data quality metrics.
        
        Returns:
            List of warning messages
        """
        warnings = []
        
        # Check for high missing data
        if self.missing_precip_pct > 10:
            warnings.append(
                f"High percentage of missing precipitation data: {self.missing_precip_pct:.1f}%"
            )
        
        if self.missing_tmax_pct > 10:
            warnings.append(
                f"High percentage of missing maximum temperature data: {self.missing_tmax_pct:.1f}%"
            )
        
        if self.missing_tmin_pct > 10:
            warnings.append(
                f"High percentage of missing minimum temperature data: {self.missing_tmin_pct:.1f}%"
            )
        
        # Check for short dataset
        if not self.has_sufficient_length():
            years = (self.data_period_end - self.data_period_start).days / 365.25
            warnings.append(
                f"Dataset is relatively short ({years:.1f} years). "
                f"Parameter estimates may be unreliable. Recommend at least 10 years of data."
            )
        
        # Check for unrealistic values
        if self.unrealistic_values:
            warnings.append(
                f"Found {len(self.unrealistic_values)} days with unrealistic values. "
                f"See unrealistic_values list for details."
            )
        
        return warnings
    
    def to_text_report(self) -> str:
        """Generate a human-readable text report.
        
        Returns:
            Multi-line string containing formatted report
        """
        lines = []
        lines.append("=" * 70)
        lines.append("DATA QUALITY REPORT")
        lines.append("=" * 70)
        
        if self.station_id:
            lines.append(f"Station ID: {self.station_id}")
        
        lines.append(f"Data Period: {self.data_period_start} to {self.data_period_end}")
        lines.append(f"Total Days: {self.total_days}")
        years = (self.data_period_end - self.data_period_start).days / 365.25
        lines.append(f"Duration: {years:.1f} years")
        lines.append("")
        
        lines.append("Missing Data:")
        lines.append(f"  Precipitation: {self.missing_precip_pct:.1f}%")
        lines.append(f"  Maximum Temperature: {self.missing_tmax_pct:.1f}%")
        lines.append(f"  Minimum Temperature: {self.missing_tmin_pct:.1f}%")
        if self.missing_solar_pct is not None:
            lines.append(f"  Solar Radiation: {self.missing_solar_pct:.1f}%")
        lines.append("")
        
        if self.warnings:
            lines.append("WARNINGS:")
            for warning in self.warnings:
                lines.append(f"  - {warning}")
            lines.append("")
        
        if self.errors:
            lines.append("ERRORS:")
            for error in self.errors:
                lines.append(f"  - {error}")
            lines.append("")
        
        if self.unrealistic_values:
            lines.append(f"Unrealistic Values ({len(self.unrealistic_values)} days):")
            for item in self.unrealistic_values[:10]:  # Show first 10
                lines.append(f"  - {item}")
            if len(self.unrealistic_values) > 10:
                lines.append(f"  ... and {len(self.unrealistic_values) - 10} more")
            lines.append("")
        
        lines.append("=" * 70)
        
        return "\n".join(lines)
