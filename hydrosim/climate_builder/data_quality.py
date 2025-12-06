"""
Data quality validation for Climate Builder.

This module provides the DataQualityValidator class that analyzes observed
climate data and generates quality reports. It checks for missing data,
unrealistic values, and dataset length to help users assess whether data
is suitable for parameter generation.

Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6
"""

import pandas as pd
from pathlib import Path
from typing import Optional, List, Dict, Any
import datetime

from .data_models import DataQualityReport


class DataQualityValidator:
    """Validates observed climate data quality and generates reports.
    
    This class analyzes observed climate data to identify potential issues:
    - Missing data (percentage of NaN values)
    - Physically unrealistic values
    - Short dataset length (<10 years)
    
    The validator generates warnings for quality issues and saves a detailed
    report to help users make informed decisions about data suitability.
    
    Attributes:
        df: DataFrame with observed climate data
        station_id: Optional GHCN station identifier
        
    Example:
        >>> validator = DataQualityValidator(observed_df, station_id="USW00024233")
        >>> report = validator.validate()
        >>> validator.save_report(report, output_path)
    """
    
    def __init__(self, df: pd.DataFrame, station_id: Optional[str] = None):
        """Initialize validator with observed climate data.
        
        Args:
            df: DataFrame with columns: date, precipitation_mm, tmax_c, tmin_c
                (and optionally solar_mjm2). Date should be index or column.
            station_id: Optional GHCN station identifier for reporting
            
        Raises:
            ValueError: If required columns are missing
        """
        self.station_id = station_id
        
        # Ensure date is the index
        if 'date' in df.columns:
            self.df = df.set_index('date')
        else:
            self.df = df.copy()
        
        # Validate required columns
        required_cols = ['precipitation_mm', 'tmax_c', 'tmin_c']
        missing_cols = [col for col in required_cols if col not in self.df.columns]
        if missing_cols:
            raise ValueError(
                f"DataFrame missing required columns: {missing_cols}. "
                f"Required: {required_cols}"
            )
    
    def validate(self) -> DataQualityReport:
        """Perform comprehensive data quality validation.
        
        Analyzes the dataset for:
        - Missing data percentages
        - Unrealistic values
        - Dataset length
        
        Returns:
            DataQualityReport with metrics and warnings
            
        Requirements: 13.1, 13.2, 13.3, 13.4, 13.5
        
        Example:
            >>> validator = DataQualityValidator(df)
            >>> report = validator.validate()
            >>> if not report.has_sufficient_data():
            ...     print("Warning: High percentage of missing data")
        """
        # Calculate missing data percentages
        missing_precip_pct = self._calculate_missing_percentage('precipitation_mm')
        missing_tmax_pct = self._calculate_missing_percentage('tmax_c')
        missing_tmin_pct = self._calculate_missing_percentage('tmin_c')
        
        # Check for solar data
        has_solar = 'solar_mjm2' in self.df.columns
        missing_solar_pct = None
        if has_solar:
            missing_solar_pct = self._calculate_missing_percentage('solar_mjm2')
        
        # Get date range
        dates = self.df.index
        data_period_start = dates.min()
        data_period_end = dates.max()
        total_days = len(self.df)
        
        # Convert to datetime.date if needed
        if isinstance(data_period_start, pd.Timestamp):
            data_period_start = data_period_start.date()
        if isinstance(data_period_end, pd.Timestamp):
            data_period_end = data_period_end.date()
        
        # Check for unrealistic values
        unrealistic_values = self._find_unrealistic_values()
        
        # Create report
        report = DataQualityReport(
            station_id=self.station_id,
            data_period_start=data_period_start,
            data_period_end=data_period_end,
            total_days=total_days,
            missing_precip_pct=missing_precip_pct,
            missing_tmax_pct=missing_tmax_pct,
            missing_tmin_pct=missing_tmin_pct,
            missing_solar_pct=missing_solar_pct,
            unrealistic_values=unrealistic_values,
            warnings=[],
            errors=[]
        )
        
        # Generate warnings based on metrics
        report.warnings = report.generate_warnings()
        
        return report
    
    def _calculate_missing_percentage(self, column: str) -> float:
        """Calculate percentage of missing values in a column.
        
        Args:
            column: Column name to check
            
        Returns:
            Percentage of missing values (0-100)
            
        Requirements: 13.1
        """
        if column not in self.df.columns:
            return 100.0
        
        total = len(self.df)
        if total == 0:
            return 0.0
        
        missing = self.df[column].isna().sum()
        return (missing / total) * 100.0
    
    def _find_unrealistic_values(self) -> List[Dict[str, Any]]:
        """Find physically unrealistic values in the dataset.
        
        Checks for:
        - Negative precipitation
        - Extreme temperatures (outside -100 to 60°C)
        - Tmax < Tmin
        - Negative solar radiation
        
        Returns:
            List of dictionaries describing unrealistic values
            
        Requirements: 13.3, 13.4
        """
        unrealistic = []
        
        # Check each row for unrealistic values
        for date, row in self.df.iterrows():
            issues = []
            
            # Check precipitation
            if pd.notna(row['precipitation_mm']):
                if row['precipitation_mm'] < 0:
                    issues.append(f"negative precipitation ({row['precipitation_mm']:.2f} mm)")
                elif row['precipitation_mm'] > 500:  # Extreme but possible
                    issues.append(f"very high precipitation ({row['precipitation_mm']:.2f} mm)")
            
            # Check temperatures
            if pd.notna(row['tmax_c']):
                if row['tmax_c'] < -100 or row['tmax_c'] > 60:
                    issues.append(f"extreme tmax ({row['tmax_c']:.1f}°C)")
            
            if pd.notna(row['tmin_c']):
                if row['tmin_c'] < -100 or row['tmin_c'] > 60:
                    issues.append(f"extreme tmin ({row['tmin_c']:.1f}°C)")
            
            # Check tmax >= tmin
            if pd.notna(row['tmax_c']) and pd.notna(row['tmin_c']):
                if row['tmax_c'] < row['tmin_c']:
                    issues.append(
                        f"tmax ({row['tmax_c']:.1f}°C) < tmin ({row['tmin_c']:.1f}°C)"
                    )
            
            # Check solar radiation if present
            if 'solar_mjm2' in self.df.columns and pd.notna(row['solar_mjm2']):
                if row['solar_mjm2'] < 0:
                    issues.append(f"negative solar ({row['solar_mjm2']:.2f} MJ/m²/day)")
                elif row['solar_mjm2'] > 50:  # Theoretical max is ~40-45 at equator
                    issues.append(f"very high solar ({row['solar_mjm2']:.2f} MJ/m²/day)")
            
            # Add to unrealistic list if any issues found
            if issues:
                # Convert date to string for JSON serialization
                date_str = str(date.date()) if isinstance(date, pd.Timestamp) else str(date)
                unrealistic.append({
                    'date': date_str,
                    'issues': issues
                })
        
        return unrealistic
    
    def save_report(self, report: DataQualityReport, output_path: Path) -> None:
        """Save data quality report to text file.
        
        Args:
            report: DataQualityReport to save
            output_path: Path to output file (typically data/processed/data_quality_report.txt)
            
        Requirements: 13.6
        
        Example:
            >>> validator = DataQualityValidator(df)
            >>> report = validator.validate()
            >>> validator.save_report(report, Path("data/processed/data_quality_report.txt"))
        """
        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write report to file
        with open(output_path, 'w') as f:
            f.write(report.to_text_report())
    
    @staticmethod
    def validate_and_save(
        df: pd.DataFrame,
        output_path: Path,
        station_id: Optional[str] = None
    ) -> DataQualityReport:
        """Convenience method to validate data and save report in one call.
        
        Args:
            df: DataFrame with observed climate data
            output_path: Path to save report file
            station_id: Optional GHCN station identifier
            
        Returns:
            DataQualityReport
            
        Example:
            >>> report = DataQualityValidator.validate_and_save(
            ...     df,
            ...     Path("data/processed/data_quality_report.txt"),
            ...     station_id="USW00024233"
            ... )
        """
        validator = DataQualityValidator(df, station_id=station_id)
        report = validator.validate()
        validator.save_report(report, output_path)
        return report
