"""
Tests for Data Quality Validator.

This module tests the DataQualityValidator class functionality including:
- Missing data percentage calculation
- Unrealistic value detection
- Dataset length warnings
- Report generation and saving
"""

import datetime
import tempfile
from pathlib import Path
import pandas as pd
import pytest

from hydrosim.climate_builder.data_quality import DataQualityValidator
from hydrosim.climate_builder.data_models import DataQualityReport


class TestDataQualityValidator:
    """Test suite for DataQualityValidator class."""
    
    def test_validate_complete_data(self):
        """Test validation with complete, high-quality data."""
        # Create test data with no missing values
        dates = pd.date_range('2010-01-01', '2020-12-31', freq='D')
        df = pd.DataFrame({
            'date': dates,
            'precipitation_mm': [5.0] * len(dates),
            'tmax_c': [20.0] * len(dates),
            'tmin_c': [10.0] * len(dates),
        })
        
        validator = DataQualityValidator(df, station_id="TEST001")
        report = validator.validate()
        
        # Check report
        assert report.station_id == "TEST001"
        assert report.missing_precip_pct == 0.0
        assert report.missing_tmax_pct == 0.0
        assert report.missing_tmin_pct == 0.0
        assert report.has_sufficient_data()
        assert report.has_sufficient_length()
        assert len(report.unrealistic_values) == 0
        assert len(report.warnings) == 0
    
    def test_calculate_missing_percentage(self):
        """Test calculation of missing data percentages.
        
        Requirements: 13.1
        """
        # Create test data with 20% missing values
        dates = pd.date_range('2010-01-01', '2010-01-10', freq='D')
        df = pd.DataFrame({
            'date': dates,
            'precipitation_mm': [5.0, None, 5.0, None, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0],
            'tmax_c': [20.0] * 10,
            'tmin_c': [10.0] * 10,
        })
        
        validator = DataQualityValidator(df)
        report = validator.validate()
        
        # 2 out of 10 = 20%
        assert report.missing_precip_pct == 20.0
        assert report.missing_tmax_pct == 0.0
        assert report.missing_tmin_pct == 0.0
    
    def test_missing_data_warning(self):
        """Test that warnings are issued for >10% missing data.
        
        Requirements: 13.2
        """
        # Create test data with 15% missing values
        dates = pd.date_range('2010-01-01', '2010-01-20', freq='D')
        precip = [5.0] * 20
        precip[0] = None
        precip[1] = None
        precip[2] = None  # 3 out of 20 = 15%
        
        df = pd.DataFrame({
            'date': dates,
            'precipitation_mm': precip,
            'tmax_c': [20.0] * 20,
            'tmin_c': [10.0] * 20,
        })
        
        validator = DataQualityValidator(df)
        report = validator.validate()
        
        # Should have warning about missing precipitation
        assert any('precipitation' in w.lower() for w in report.warnings)
        assert not report.has_sufficient_data()
    
    def test_unrealistic_value_detection_negative_precip(self):
        """Test detection of negative precipitation.
        
        Requirements: 13.3, 13.4
        """
        dates = pd.date_range('2010-01-01', '2010-01-05', freq='D')
        df = pd.DataFrame({
            'date': dates,
            'precipitation_mm': [5.0, -2.0, 5.0, 5.0, 5.0],  # Negative precip
            'tmax_c': [20.0] * 5,
            'tmin_c': [10.0] * 5,
        })
        
        validator = DataQualityValidator(df)
        report = validator.validate()
        
        # Should detect unrealistic value
        assert len(report.unrealistic_values) == 1
        assert 'negative precipitation' in report.unrealistic_values[0]['issues'][0]
    
    def test_unrealistic_value_detection_extreme_temp(self):
        """Test detection of extreme temperatures.
        
        Requirements: 13.3, 13.4
        """
        dates = pd.date_range('2010-01-01', '2010-01-05', freq='D')
        df = pd.DataFrame({
            'date': dates,
            'precipitation_mm': [5.0] * 5,
            'tmax_c': [20.0, 150.0, 20.0, 20.0, 20.0],  # Extreme temp
            'tmin_c': [10.0] * 5,
        })
        
        validator = DataQualityValidator(df)
        report = validator.validate()
        
        # Should detect unrealistic value
        assert len(report.unrealistic_values) == 1
        assert 'extreme tmax' in report.unrealistic_values[0]['issues'][0]
    
    def test_unrealistic_value_detection_tmax_less_than_tmin(self):
        """Test detection of tmax < tmin.
        
        Requirements: 13.3, 13.4
        """
        dates = pd.date_range('2010-01-01', '2010-01-05', freq='D')
        df = pd.DataFrame({
            'date': dates,
            'precipitation_mm': [5.0] * 5,
            'tmax_c': [20.0, 5.0, 20.0, 20.0, 20.0],  # tmax < tmin
            'tmin_c': [10.0] * 5,
        })
        
        validator = DataQualityValidator(df)
        report = validator.validate()
        
        # Should detect unrealistic value
        assert len(report.unrealistic_values) == 1
        assert 'tmax' in report.unrealistic_values[0]['issues'][0]
        assert 'tmin' in report.unrealistic_values[0]['issues'][0]
    
    def test_short_dataset_warning(self):
        """Test that warnings are issued for datasets <10 years.
        
        Requirements: 13.5
        """
        # Create 5 years of data
        dates = pd.date_range('2010-01-01', '2014-12-31', freq='D')
        df = pd.DataFrame({
            'date': dates,
            'precipitation_mm': [5.0] * len(dates),
            'tmax_c': [20.0] * len(dates),
            'tmin_c': [10.0] * len(dates),
        })
        
        validator = DataQualityValidator(df)
        report = validator.validate()
        
        # Should have warning about short dataset
        assert not report.has_sufficient_length()
        assert any('short' in w.lower() for w in report.warnings)
    
    def test_save_report(self):
        """Test saving report to file.
        
        Requirements: 13.6
        """
        dates = pd.date_range('2010-01-01', '2020-12-31', freq='D')
        df = pd.DataFrame({
            'date': dates,
            'precipitation_mm': [5.0] * len(dates),
            'tmax_c': [20.0] * len(dates),
            'tmin_c': [10.0] * len(dates),
        })
        
        validator = DataQualityValidator(df, station_id="TEST001")
        report = validator.validate()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "data" / "processed" / "data_quality_report.txt"
            validator.save_report(report, output_path)
            
            # Check file was created
            assert output_path.exists()
            
            # Check content
            content = output_path.read_text()
            assert "DATA QUALITY REPORT" in content
            assert "TEST001" in content
            assert "2010-01-01" in content
            assert "2020-12-31" in content
    
    def test_validate_and_save_convenience_method(self):
        """Test the convenience method for validate and save."""
        dates = pd.date_range('2010-01-01', '2020-12-31', freq='D')
        df = pd.DataFrame({
            'date': dates,
            'precipitation_mm': [5.0] * len(dates),
            'tmax_c': [20.0] * len(dates),
            'tmin_c': [10.0] * len(dates),
        })
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.txt"
            
            report = DataQualityValidator.validate_and_save(
                df, output_path, station_id="TEST001"
            )
            
            # Check report was returned
            assert isinstance(report, DataQualityReport)
            assert report.station_id == "TEST001"
            
            # Check file was created
            assert output_path.exists()
    
    def test_missing_required_columns(self):
        """Test that validator raises error if required columns are missing."""
        df = pd.DataFrame({
            'date': pd.date_range('2010-01-01', '2010-01-10', freq='D'),
            'precipitation_mm': [5.0] * 10,
            # Missing tmax_c and tmin_c
        })
        
        with pytest.raises(ValueError, match="missing required columns"):
            DataQualityValidator(df)
    
    def test_date_as_index(self):
        """Test that validator works with date as index."""
        dates = pd.date_range('2010-01-01', '2010-01-10', freq='D')
        df = pd.DataFrame({
            'precipitation_mm': [5.0] * 10,
            'tmax_c': [20.0] * 10,
            'tmin_c': [10.0] * 10,
        }, index=dates)
        
        validator = DataQualityValidator(df)
        report = validator.validate()
        
        assert report.total_days == 10
    
    def test_date_as_column(self):
        """Test that validator works with date as column."""
        dates = pd.date_range('2010-01-01', '2010-01-10', freq='D')
        df = pd.DataFrame({
            'date': dates,
            'precipitation_mm': [5.0] * 10,
            'tmax_c': [20.0] * 10,
            'tmin_c': [10.0] * 10,
        })
        
        validator = DataQualityValidator(df)
        report = validator.validate()
        
        assert report.total_days == 10
    
    def test_solar_data_optional(self):
        """Test that solar data is optional."""
        dates = pd.date_range('2010-01-01', '2010-01-10', freq='D')
        df = pd.DataFrame({
            'date': dates,
            'precipitation_mm': [5.0] * 10,
            'tmax_c': [20.0] * 10,
            'tmin_c': [10.0] * 10,
            'solar_mjm2': [15.0] * 10,
        })
        
        validator = DataQualityValidator(df)
        report = validator.validate()
        
        # Should have solar percentage
        assert report.missing_solar_pct is not None
        assert report.missing_solar_pct == 0.0
    
    def test_unrealistic_solar_detection(self):
        """Test detection of unrealistic solar values."""
        dates = pd.date_range('2010-01-01', '2010-01-05', freq='D')
        df = pd.DataFrame({
            'date': dates,
            'precipitation_mm': [5.0] * 5,
            'tmax_c': [20.0] * 5,
            'tmin_c': [10.0] * 5,
            'solar_mjm2': [15.0, -5.0, 15.0, 15.0, 15.0],  # Negative solar
        })
        
        validator = DataQualityValidator(df)
        report = validator.validate()
        
        # Should detect unrealistic value
        assert len(report.unrealistic_values) == 1
        assert 'negative solar' in report.unrealistic_values[0]['issues'][0]
    
    def test_multiple_issues_same_day(self):
        """Test that multiple issues on the same day are all reported."""
        dates = pd.date_range('2010-01-01', '2010-01-05', freq='D')
        df = pd.DataFrame({
            'date': dates,
            'precipitation_mm': [5.0, -2.0, 5.0, 5.0, 5.0],  # Negative
            'tmax_c': [20.0, 5.0, 20.0, 20.0, 20.0],  # Less than tmin
            'tmin_c': [10.0] * 5,
        })
        
        validator = DataQualityValidator(df)
        report = validator.validate()
        
        # Should detect both issues on day 2
        assert len(report.unrealistic_values) == 1
        assert len(report.unrealistic_values[0]['issues']) == 2
    
    def test_report_text_format(self):
        """Test that text report is properly formatted."""
        dates = pd.date_range('2010-01-01', '2020-12-31', freq='D')
        df = pd.DataFrame({
            'date': dates,
            'precipitation_mm': [5.0] * len(dates),
            'tmax_c': [20.0] * len(dates),
            'tmin_c': [10.0] * len(dates),
        })
        
        validator = DataQualityValidator(df, station_id="TEST001")
        report = validator.validate()
        
        text = report.to_text_report()
        
        # Check key sections are present
        assert "DATA QUALITY REPORT" in text
        assert "Station ID: TEST001" in text
        assert "Data Period:" in text
        assert "Missing Data:" in text
        assert "Precipitation:" in text
        assert "Maximum Temperature:" in text
        assert "Minimum Temperature:" in text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
