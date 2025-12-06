"""
Tests for DLY Parser.

This module tests the DLYParser class functionality including:
- Fixed-width format parsing
- Unit conversion (tenths to whole units)
- Missing value handling (-9999 → NaN)
- February 29th exclusion
- Invalid date handling
- Output schema validation
"""

import datetime
import tempfile
from pathlib import Path
import pandas as pd
import pytest

from hydrosim.climate_builder.dly_parser import DLYParser


class TestDLYParser:
    """Test suite for DLYParser class."""
    
    def test_parse_basic_dly_file(self):
        """Test parsing a basic .dly file with valid data."""
        parser = DLYParser()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a simple test .dly file
            # Format: Station(11) Year(4) Month(2) Element(4) Value1(5) MFlag(1) QFlag(1) SFlag(1) ...
            dly_content = (
                "TEST0000001201001PRCP  100     50      0     25 " + " " * 200 + "\n"
                "TEST0000001201001TMAX  150    120    135    140 " + " " * 200 + "\n"
                "TEST0000001201001TMIN   50     30     45     55 " + " " * 200 + "\n"
            )
            
            dly_path = Path(tmpdir) / "test.dly"
            with open(dly_path, 'w') as f:
                f.write(dly_content)
            
            # Parse
            df = parser.parse(dly_path)
            
            # Check results
            assert len(df) == 4  # 4 days
            assert list(df.columns) == ['date', 'precipitation_mm', 'tmax_c', 'tmin_c']
            
            # Check first day (2010-01-01)
            row = df[df['date'] == datetime.date(2010, 1, 1)].iloc[0]
            assert row['precipitation_mm'] == 10.0  # 100 tenths -> 10.0 mm
            assert row['tmax_c'] == 15.0  # 150 tenths -> 15.0 C
            assert row['tmin_c'] == 5.0  # 50 tenths -> 5.0 C
    
    def test_unit_conversion(self):
        """Test that values in tenths are correctly converted to whole units.
        
        Requirements: 2.1, 2.2, 2.3
        """
        parser = DLYParser()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test data with known values in tenths
            dly_content = (
                "TEST0000001201001PRCP  254 " + " " * 240 + "\n"  # 25.4 mm
                "TEST0000001201001TMAX  305 " + " " * 240 + "\n"  # 30.5 C
                "TEST0000001201001TMIN -125 " + " " * 240 + "\n"  # -12.5 C
            )
            
            dly_path = Path(tmpdir) / "test.dly"
            with open(dly_path, 'w') as f:
                f.write(dly_content)
            
            df = parser.parse(dly_path)
            
            row = df.iloc[0]
            assert row['precipitation_mm'] == 25.4
            assert row['tmax_c'] == 30.5
            assert row['tmin_c'] == -12.5
    
    def test_missing_value_handling(self):
        """Test that -9999 missing value flags are converted to NaN.
        
        Requirements: 2.4
        """
        parser = DLYParser()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test .dly file with missing values
            def fmt_day(value):
                return f"{value:5d}   "
            
            dly_content = (
                f"TEST0000001201001PRCP{fmt_day(-9999)}{fmt_day(50)}" + " " * 200 + "\n"
                f"TEST0000001201001TMAX{fmt_day(150)}{fmt_day(-9999)}" + " " * 200 + "\n"
                f"TEST0000001201001TMIN{fmt_day(-9999)}{fmt_day(30)}" + " " * 200 + "\n"
            )
            
            dly_path = Path(tmpdir) / "test.dly"
            with open(dly_path, 'w') as f:
                f.write(dly_content)
            
            df = parser.parse(dly_path)
            
            # Check that missing values are NaN
            row1 = df[df['date'] == datetime.date(2010, 1, 1)].iloc[0]
            assert pd.isna(row1['precipitation_mm'])
            assert row1['tmax_c'] == 15.0
            assert pd.isna(row1['tmin_c'])
            
            row2 = df[df['date'] == datetime.date(2010, 1, 2)].iloc[0]
            assert row2['precipitation_mm'] == 5.0
            assert pd.isna(row2['tmax_c'])
            assert row2['tmin_c'] == 3.0
    
    def test_february_29_exclusion(self):
        """Test that February 29th dates are excluded.
        
        Requirements: 2.5
        """
        parser = DLYParser()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test .dly file with Feb data including Feb 29 (leap year 2020)
            day_values = ""
            for day in range(1, 30):  # Days 1-29 of February
                day_values += f"{day*10:5d}   "
            
            dly_content = f"TEST0000001202002PRCP{day_values}" + " " * 100 + "\n"
            
            dly_path = Path(tmpdir) / "test.dly"
            with open(dly_path, 'w') as f:
                f.write(dly_content)
            
            df = parser.parse(dly_path)
            
            # Check that Feb 29 is not in the data
            feb29_rows = df[df['date'] == datetime.date(2020, 2, 29)]
            assert len(feb29_rows) == 0
            
            # But Feb 28 should be there
            feb28_rows = df[df['date'] == datetime.date(2020, 2, 28)]
            assert len(feb28_rows) == 1
    
    def test_invalid_date_handling(self):
        """Test that invalid dates (e.g., Feb 30, Apr 31) are skipped.
        
        Requirements: 2.6
        """
        parser = DLYParser()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test .dly file with invalid dates
            # Format each day properly: 5 chars for value, 3 for flags
            def fmt_days(count):
                return "".join([f"{100:5d}   " for _ in range(count)])
            
            dly_content = (
                # Feb with 30 days (Feb 30 doesn't exist)
                f"TEST0000001201002PRCP{fmt_days(30)}\n"
                # Apr with 31 days (Apr 31 doesn't exist)  
                f"TEST0000001201004PRCP{fmt_days(31)}\n"
            )
            
            dly_path = Path(tmpdir) / "test.dly"
            with open(dly_path, 'w') as f:
                f.write(dly_content)
            
            # Parse - should not raise, just skip invalid dates
            df = parser.parse(dly_path)
            
            # Should have valid dates only (Feb 1-28, Apr 1-30)
            feb_dates = df[df['date'].apply(lambda d: d.month == 2)]
            assert len(feb_dates) == 28  # No Feb 29 or Feb 30
            
            apr_dates = df[df['date'].apply(lambda d: d.month == 4)]
            assert len(apr_dates) == 30  # No Apr 31
    
    def test_output_schema(self):
        """Test that output DataFrame has correct schema.
        
        Requirements: 2.7
        """
        parser = DLYParser()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            dly_content = (
                "TEST0000001201001PRCP  100 " + " " * 240 + "\n"
                "TEST0000001201001TMAX  150 " + " " * 240 + "\n"
                "TEST0000001201001TMIN   50 " + " " * 240 + "\n"
            )
            
            dly_path = Path(tmpdir) / "test.dly"
            with open(dly_path, 'w') as f:
                f.write(dly_content)
            
            df = parser.parse(dly_path)
            
            # Check schema
            assert list(df.columns) == ['date', 'precipitation_mm', 'tmax_c', 'tmin_c']
            assert df['date'].dtype == 'object'  # date objects
            assert df['precipitation_mm'].dtype in ['float64', 'Float64']
            assert df['tmax_c'].dtype in ['float64', 'Float64']
            assert df['tmin_c'].dtype in ['float64', 'Float64']
    
    def test_parse_empty_file(self):
        """Test that parsing an empty file raises appropriate error."""
        parser = DLYParser()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            dly_path = Path(tmpdir) / "empty.dly"
            dly_path.write_text("")
            
            with pytest.raises(ValueError, match="No valid data found"):
                parser.parse(dly_path)
    
    def test_parse_nonexistent_file(self):
        """Test that parsing a nonexistent file raises FileNotFoundError."""
        parser = DLYParser()
        
        with pytest.raises(FileNotFoundError):
            parser.parse(Path("/nonexistent/file.dly"))
    
    def test_parse_line_basic(self):
        """Test parsing a single line."""
        parser = DLYParser()
        
        line = "TEST0000001201001PRCP  100     50      0 " + " " * 200
        data = parser.parse_line(line)
        
        assert len(data) == 3
        assert datetime.date(2010, 1, 1) in data
        assert data[datetime.date(2010, 1, 1)]['precipitation_mm'] == 10.0
    
    def test_parse_line_empty(self):
        """Test parsing an empty line."""
        parser = DLYParser()
        
        data = parser.parse_line("")
        assert len(data) == 0
    
    def test_parse_line_invalid_element(self):
        """Test that lines with non-PRCP/TMAX/TMIN elements are skipped."""
        parser = DLYParser()
        
        # SNOW element should be skipped
        line = "TEST0000001201001SNOW  100     50      0 " + " " * 200
        data = parser.parse_line(line)
        
        assert len(data) == 0
    
    def test_multiple_elements_same_date(self):
        """Test that multiple elements for the same date are combined."""
        parser = DLYParser()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            dly_content = (
                "TEST0000001201001PRCP  100 " + " " * 240 + "\n"
                "TEST0000001201001TMAX  150 " + " " * 240 + "\n"
                "TEST0000001201001TMIN   50 " + " " * 240 + "\n"
            )
            
            dly_path = Path(tmpdir) / "test.dly"
            with open(dly_path, 'w') as f:
                f.write(dly_content)
            
            df = parser.parse(dly_path)
            
            # Should have one row with all three elements
            assert len(df) == 1
            row = df.iloc[0]
            assert row['precipitation_mm'] == 10.0
            assert row['tmax_c'] == 15.0
            assert row['tmin_c'] == 5.0
    
    def test_negative_temperatures(self):
        """Test that negative temperatures are handled correctly."""
        parser = DLYParser()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            dly_content = (
                "TEST0000001201001TMAX -100 " + " " * 240 + "\n"  # -10.0 C
                "TEST0000001201001TMIN -250 " + " " * 240 + "\n"  # -25.0 C
            )
            
            dly_path = Path(tmpdir) / "test.dly"
            with open(dly_path, 'w') as f:
                f.write(dly_content)
            
            df = parser.parse(dly_path)
            
            row = df.iloc[0]
            assert row['tmax_c'] == -10.0
            assert row['tmin_c'] == -25.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
