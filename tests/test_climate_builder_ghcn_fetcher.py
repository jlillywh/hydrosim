"""
Tests for GHCN Data Fetcher.

This module tests the GHCNDataFetcher class functionality including:
- Station ID validation
- .dly file parsing
- Unit conversion
- Missing value handling
- February 29th exclusion
- Invalid date handling
"""

import datetime
import tempfile
from pathlib import Path
import pandas as pd
import pytest
from unittest.mock import Mock, patch, MagicMock

from hydrosim.climate_builder.ghcn_fetcher import GHCNDataFetcher


class TestGHCNDataFetcher:
    """Test suite for GHCNDataFetcher class."""
    
    def test_valid_station_id(self):
        """Test that valid station IDs are accepted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Should not raise
            fetcher = GHCNDataFetcher("USW00024233", tmpdir)
            assert fetcher.station_id == "USW00024233"
    
    def test_invalid_station_id_format(self):
        """Test that invalid station ID formats are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Too short
            with pytest.raises(ValueError, match="Invalid GHCN station ID format"):
                GHCNDataFetcher("SHORT", tmpdir)
            
            # Too long
            with pytest.raises(ValueError, match="Invalid GHCN station ID format"):
                GHCNDataFetcher("TOOLONGSTATIONID", tmpdir)
            
            # Invalid characters
            with pytest.raises(ValueError, match="Invalid GHCN station ID format"):
                GHCNDataFetcher("USW0002423!", tmpdir)
    
    def test_station_id_normalization(self):
        """Test that station IDs are normalized (uppercase, stripped)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fetcher = GHCNDataFetcher(" usw00024233 ", tmpdir)
            assert fetcher.station_id == "USW00024233"
    
    def test_project_structure_initialization(self):
        """Test that project structure is initialized on creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fetcher = GHCNDataFetcher("USW00024233", tmpdir)
            
            # Check that directories were created
            assert fetcher.project.get_raw_data_dir().exists()
            assert fetcher.project.get_processed_data_dir().exists()
            assert fetcher.project.get_config_dir().exists()
            assert fetcher.project.get_outputs_dir().exists()
    
    def test_parse_dly_file_basic(self):
        """Test parsing a basic .dly file with valid data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fetcher = GHCNDataFetcher("TEST0000001", tmpdir)
            
            # Create a simple test .dly file
            # Format: Station(11) Year(4) Month(2) Element(4) Value1(5) MFlag(1) QFlag(1) SFlag(1) ...
            # Values are right-aligned in 5-character fields
            dly_content = (
                # Station    Year Mo Element  Day1 values (8 chars each: 5 for value, 3 for flags)
                "TEST0000001201001PRCP  100     50      0     25 " + " " * 200 + "\n"
                "TEST0000001201001TMAX  150    120    135    140 " + " " * 200 + "\n"
                "TEST0000001201001TMIN   50     30     45     55 " + " " * 200 + "\n"
            )
            
            dly_path = Path(tmpdir) / "test.dly"
            with open(dly_path, 'w') as f:
                f.write(dly_content)
            
            # Parse
            df = fetcher.parse_dly_file(dly_path)
            
            # Check results
            assert len(df) == 4  # 4 days
            assert list(df.columns) == ['date', 'precipitation_mm', 'tmax_c', 'tmin_c']
            
            # Check first day (2010-01-01)
            row = df[df['date'] == datetime.date(2010, 1, 1)].iloc[0]
            assert row['precipitation_mm'] == 10.0  # 100 tenths -> 10.0 mm
            assert row['tmax_c'] == 15.0  # 150 tenths -> 15.0 C
            assert row['tmin_c'] == 5.0  # 50 tenths -> 5.0 C
    
    def test_parse_dly_file_missing_values(self):
        """Test that -9999 missing value flags are converted to NaN."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fetcher = GHCNDataFetcher("TEST0000001", tmpdir)
            
            # Create test .dly file with missing values
            # Each value is 5 chars (right-aligned), followed by 3 flag chars (8 total per day)
            # Helper to format a day's value
            def fmt_day(value):
                return f"{value:5d}   "  # 5 chars for value, 3 spaces for flags
            
            dly_content = (
                f"TEST0000001201001PRCP{fmt_day(-9999)}{fmt_day(50)}" + " " * 200 + "\n"
                f"TEST0000001201001TMAX{fmt_day(150)}{fmt_day(-9999)}" + " " * 200 + "\n"
                f"TEST0000001201001TMIN{fmt_day(-9999)}{fmt_day(30)}" + " " * 200 + "\n"
            )
            
            dly_path = Path(tmpdir) / "test.dly"
            with open(dly_path, 'w') as f:
                f.write(dly_content)
            
            # Parse
            df = fetcher.parse_dly_file(dly_path)
            
            # Check that missing values are NaN
            row1 = df[df['date'] == datetime.date(2010, 1, 1)].iloc[0]
            assert pd.isna(row1['precipitation_mm'])
            assert row1['tmax_c'] == 15.0
            assert pd.isna(row1['tmin_c'])
            
            row2 = df[df['date'] == datetime.date(2010, 1, 2)].iloc[0]
            assert row2['precipitation_mm'] == 5.0
            assert pd.isna(row2['tmax_c'])
            assert row2['tmin_c'] == 3.0
    
    def test_parse_dly_file_excludes_feb29(self):
        """Test that February 29th dates are excluded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fetcher = GHCNDataFetcher("TEST0000001", tmpdir)
            
            # Create test .dly file with Feb data including Feb 29 (leap year 2020)
            # Need to create one line with all 29 days of February
            day_values = ""
            for day in range(1, 30):  # Days 1-29 of February
                day_values += f"{day*10:5d}   "  # 5 chars for value, 3 for flags
            
            dly_content = f"TEST0000001202002PRCP{day_values}" + " " * 100 + "\n"
            
            dly_path = Path(tmpdir) / "test.dly"
            with open(dly_path, 'w') as f:
                f.write(dly_content)
            
            # Parse
            df = fetcher.parse_dly_file(dly_path)
            
            # Check that Feb 29 is not in the data
            feb29_rows = df[df['date'] == datetime.date(2020, 2, 29)]
            assert len(feb29_rows) == 0
            
            # But Feb 28 should be there
            feb28_rows = df[df['date'] == datetime.date(2020, 2, 28)]
            assert len(feb28_rows) == 1
    
    def test_parse_dly_file_invalid_dates(self):
        """Test that invalid dates (e.g., Feb 30, Apr 31) are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fetcher = GHCNDataFetcher("TEST0000001", tmpdir)
            
            # Create test .dly file with invalid dates
            dly_content = (
                # Feb 30 doesn't exist
                "TEST0000001201002PRCP" + "   100 M" * 30 + "\n"
                # Apr 31 doesn't exist  
                "TEST0000001201004PRCP" + "   100 M" * 31 + "\n"
            )
            
            dly_path = Path(tmpdir) / "test.dly"
            with open(dly_path, 'w') as f:
                f.write(dly_content)
            
            # Parse - should not raise, just skip invalid dates
            df = fetcher.parse_dly_file(dly_path)
            
            # Should have valid dates only (Feb 1-28, Apr 1-30)
            feb_dates = df[df['date'].apply(lambda d: d.month == 2)]
            assert len(feb_dates) == 28  # No Feb 29 or Feb 30
            
            apr_dates = df[df['date'].apply(lambda d: d.month == 4)]
            assert len(apr_dates) == 30  # No Apr 31
    
    def test_save_processed_data(self):
        """Test saving processed data to CSV."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fetcher = GHCNDataFetcher("TEST0000001", tmpdir)
            
            # Create test DataFrame
            df = pd.DataFrame({
                'date': [datetime.date(2010, 1, 1), datetime.date(2010, 1, 2)],
                'precipitation_mm': [10.0, 5.0],
                'tmax_c': [15.0, 12.0],
                'tmin_c': [5.0, 3.0]
            })
            
            # Save
            csv_path = fetcher.save_processed_data(df)
            
            # Check file exists
            assert csv_path.exists()
            assert csv_path.name == "observed_climate.csv"
            
            # Read back and verify
            df_read = pd.read_csv(csv_path)
            assert len(df_read) == 2
            assert list(df_read.columns) == ['date', 'precipitation_mm', 'tmax_c', 'tmin_c']
    
    def test_save_processed_data_missing_columns(self):
        """Test that saving data with missing columns raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fetcher = GHCNDataFetcher("TEST0000001", tmpdir)
            
            # Create DataFrame missing required column
            df = pd.DataFrame({
                'date': [datetime.date(2010, 1, 1)],
                'precipitation_mm': [10.0],
                # Missing tmax_c and tmin_c
            })
            
            # Should raise
            with pytest.raises(ValueError, match="missing required columns"):
                fetcher.save_processed_data(df)
    
    @patch('hydrosim.climate_builder.ghcn_fetcher.requests.get')
    def test_download_dly_file_success(self, mock_get):
        """Test successful download of .dly file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fetcher = GHCNDataFetcher("USW00024233", tmpdir)
            
            # Mock successful HTTP response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.iter_content = lambda chunk_size: [b"test data"]
            mock_get.return_value = mock_response
            
            # Download
            dly_path = fetcher.download_dly_file()
            
            # Check file was created
            assert dly_path.exists()
            assert dly_path.name == "USW00024233.dly"
            
            # Check content
            with open(dly_path, 'rb') as f:
                assert f.read() == b"test data"
    
    @patch('hydrosim.climate_builder.ghcn_fetcher.requests.get')
    def test_download_dly_file_404(self, mock_get):
        """Test that 404 error raises clear error message."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fetcher = GHCNDataFetcher("INVALID0001", tmpdir)
            
            # Mock 404 response
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.raise_for_status.side_effect = Exception("404")
            from requests.exceptions import HTTPError
            mock_get.side_effect = HTTPError(response=mock_response)
            
            # Should raise with clear message
            with pytest.raises(ValueError, match="not found on NOAA servers"):
                fetcher.download_dly_file()
    
    @patch('hydrosim.climate_builder.ghcn_fetcher.requests.get')
    def test_download_dly_file_existing(self, mock_get):
        """Test that existing files are not re-downloaded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fetcher = GHCNDataFetcher("USW00024233", tmpdir)
            
            # Create existing file
            dly_path = fetcher.project.get_dly_file_path("USW00024233")
            dly_path.write_text("existing data")
            
            # Try to download - should use existing file
            result_path = fetcher.download_dly_file()
            
            # Should not have called requests.get
            mock_get.assert_not_called()
            
            # Should return existing file
            assert result_path == dly_path
            assert result_path.read_text() == "existing data"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
