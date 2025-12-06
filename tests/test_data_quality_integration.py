"""
Integration test for data quality validation with DLY parser.

This test verifies that the DataQualityValidator works correctly with
data parsed from .dly files.
"""

import tempfile
from pathlib import Path
import pytest

from hydrosim.climate_builder.dly_parser import DLYParser
from hydrosim.climate_builder.data_quality import DataQualityValidator


def test_data_quality_with_parsed_dly():
    """Test data quality validation with parsed DLY data."""
    parser = DLYParser()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test .dly file with some missing values
        def fmt_day(value):
            return f"{value:5d}   "
        
        # Create 3 years of data with some missing values
        dly_lines = []
        for year in [2018, 2019, 2020]:
            for month in range(1, 13):
                # PRCP line with some missing values
                prcp_line = f"TEST0000001{year}{month:02d}PRCP"
                for day in range(1, 32):
                    if day % 10 == 0:  # 10% missing
                        prcp_line += fmt_day(-9999)
                    else:
                        prcp_line += fmt_day(50)
                dly_lines.append(prcp_line + "\n")
                
                # TMAX line
                tmax_line = f"TEST0000001{year}{month:02d}TMAX"
                for day in range(1, 32):
                    tmax_line += fmt_day(200)
                dly_lines.append(tmax_line + "\n")
                
                # TMIN line
                tmin_line = f"TEST0000001{year}{month:02d}TMIN"
                for day in range(1, 32):
                    tmin_line += fmt_day(100)
                dly_lines.append(tmin_line + "\n")
        
        dly_path = Path(tmpdir) / "test.dly"
        with open(dly_path, 'w') as f:
            f.writelines(dly_lines)
        
        # Parse the file
        df = parser.parse(dly_path)
        
        # Validate data quality
        validator = DataQualityValidator(df, station_id="TEST0000001")
        report = validator.validate()
        
        # Check report
        assert report.station_id == "TEST0000001"
        assert report.total_days > 0
        assert report.missing_precip_pct > 0  # Should have some missing data
        assert report.missing_tmax_pct == 0.0  # No missing tmax
        assert report.missing_tmin_pct == 0.0  # No missing tmin
        
        # Should have sufficient length (3 years)
        assert not report.has_sufficient_length()  # Less than 10 years
        assert any('short' in w.lower() for w in report.warnings)
        
        # Save report
        report_path = Path(tmpdir) / "data_quality_report.txt"
        validator.save_report(report, report_path)
        
        # Verify file was created
        assert report_path.exists()
        content = report_path.read_text()
        assert "TEST0000001" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
