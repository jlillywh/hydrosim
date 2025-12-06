"""
GHCN Data Fetcher for Climate Builder.

This module provides functionality to download and parse observed climate data
from NOAA's Global Historical Climatology Network (GHCN) Daily database.

The GHCNDataFetcher class:
1. Downloads .dly files from NOAA servers via HTTP
2. Parses the fixed-width GHCN Daily format
3. Converts units (tenths to whole units)
4. Handles missing values (-9999 → NaN)
5. Excludes February 29th dates (WGEN uses 365-day calendar)
6. Saves processed data to CSV

Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7
"""

import datetime
import re
from pathlib import Path
from typing import Optional, List
import pandas as pd
import requests
from requests.exceptions import HTTPError, Timeout, RequestException

from hydrosim.climate_builder.data_models import ObservedClimateData
from hydrosim.climate_builder.project_structure import ProjectStructure
from hydrosim.climate_builder.dly_parser import DLYParser


class GHCNDataFetcher:
    """Fetches and parses observed climate data from NOAA GHCN stations.
    
    This class handles the complete workflow of acquiring observed climate data:
    1. Download .dly file from NOAA servers
    2. Parse fixed-width format
    3. Extract precipitation, tmax, tmin
    4. Convert units and handle missing values
    5. Save to standardized CSV format
    
    Attributes:
        station_id: NOAA GHCN station identifier (e.g., "USW00024233")
        project: ProjectStructure instance managing directory layout
        
    Example:
        >>> fetcher = GHCNDataFetcher("USW00024233", output_dir="./my_project")
        >>> dly_path = fetcher.download_dly_file()
        >>> df = fetcher.parse_dly_file(dly_path)
        >>> csv_path = fetcher.save_processed_data(df)
    """
    
    # NOAA GHCN Daily data URL pattern
    GHCN_BASE_URL = "https://www1.ncdc.noaa.gov/pub/data/ghcn/daily/all"
    
    # GHCN station ID pattern (11 characters)
    STATION_ID_PATTERN = re.compile(r'^[A-Z0-9]{11}$')
    
    # Missing value flag in GHCN format
    MISSING_VALUE_FLAG = -9999
    
    def __init__(self, station_id: str, output_dir: Path | str):
        """Initialize GHCN data fetcher.
        
        Args:
            station_id: NOAA GHCN station identifier (11-character code)
            output_dir: Project root directory for saving data
            
        Raises:
            ValueError: If station_id format is invalid
            
        Example:
            >>> fetcher = GHCNDataFetcher("USW00024233", "./my_project")
        """
        self.station_id = station_id.strip().upper()
        self.project = ProjectStructure(output_dir)
        self.parser = DLYParser()
        
        # Validate station ID format
        if not self.STATION_ID_PATTERN.match(self.station_id):
            raise ValueError(
                f"Invalid GHCN station ID format: '{station_id}'\n"
                f"Expected format: 11-character code (e.g., 'USW00024233')\n"
                f"Station IDs typically follow patterns like:\n"
                f"  - US stations: USW, USC, USS prefix\n"
                f"  - International: Country code prefix\n"
                f"See https://www.ncdc.noaa.gov/ghcn-daily-description for station list"
            )
        
        # Ensure project structure exists
        self.project.initialize_structure()
    
    def download_dly_file(self, timeout: int = 30) -> Path:
        """Download .dly file from NOAA servers.
        
        Downloads the GHCN Daily format file for the specified station from
        NOAA's FTP server via HTTP. The file is saved to data/raw/ directory.
        
        Args:
            timeout: HTTP request timeout in seconds (default: 30)
            
        Returns:
            Path to downloaded .dly file in data/raw/ directory
            
        Raises:
            HTTPError: If station not found (404) or server error
            Timeout: If download exceeds timeout
            RequestException: For other network errors
            
        Requirements: 1.1, 1.2, 1.3, 1.4
        
        Example:
            >>> fetcher = GHCNDataFetcher("USW00024233", "./my_project")
            >>> dly_path = fetcher.download_dly_file()
            >>> print(f"Downloaded to: {dly_path}")
        """
        # Construct download URL
        url = f"{self.GHCN_BASE_URL}/{self.station_id}.dly"
        
        # Get output path
        output_path = self.project.get_dly_file_path(self.station_id)
        
        # Check if file already exists
        if output_path.exists():
            print(f"File already exists: {output_path}")
            print(f"Using existing file. Delete it to re-download.")
            return output_path
        
        print(f"Downloading GHCN data for station {self.station_id}...")
        print(f"URL: {url}")
        
        try:
            # Download file with streaming to handle large files
            response = requests.get(url, timeout=timeout, stream=True)
            response.raise_for_status()
            
            # Save to file
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"Successfully downloaded to: {output_path}")
            return output_path
            
        except HTTPError as e:
            if e.response.status_code == 404:
                raise ValueError(
                    f"Station '{self.station_id}' not found on NOAA servers.\n"
                    f"URL: {url}\n"
                    f"Please verify the station ID is correct.\n"
                    f"Search for stations at: https://www.ncdc.noaa.gov/cdo-web/search"
                ) from e
            else:
                raise HTTPError(
                    f"HTTP error downloading station data: {e.response.status_code}\n"
                    f"URL: {url}\n"
                    f"Error: {str(e)}"
                ) from e
                
        except Timeout as e:
            raise Timeout(
                f"Download timed out after {timeout} seconds.\n"
                f"URL: {url}\n"
                f"Try increasing timeout or check network connection."
            ) from e
            
        except RequestException as e:
            raise RequestException(
                f"Network error downloading station data.\n"
                f"URL: {url}\n"
                f"Error: {str(e)}\n"
                f"Check network connection and try again."
            ) from e
    
    def parse_dly_file(self, dly_path: Path) -> pd.DataFrame:
        """Parse GHCN fixed-width .dly format file.
        
        This method delegates to the DLYParser class for actual parsing.
        
        Args:
            dly_path: Path to .dly file
            
        Returns:
            DataFrame with columns: date, precipitation_mm, tmax_c, tmin_c
            Missing values represented as NaN
            February 29th excluded
            
        Raises:
            ValueError: If file format is invalid
            FileNotFoundError: If file doesn't exist
            
        Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7
        
        Example:
            >>> fetcher = GHCNDataFetcher("USW00024233", "./my_project")
            >>> df = fetcher.parse_dly_file(Path("data/raw/USW00024233.dly"))
            >>> print(df.head())
        """
        return self.parser.parse(dly_path)
    
    def save_processed_data(self, df: pd.DataFrame) -> Path:
        """Save processed climate data to CSV.
        
        Saves the parsed and processed climate data to the standard location:
        data/processed/observed_climate.csv
        
        Args:
            df: DataFrame with columns: date, precipitation_mm, tmax_c, tmin_c
            
        Returns:
            Path to saved CSV file
            
        Raises:
            ValueError: If DataFrame is missing required columns
            
        Requirements: 2.7
        
        Example:
            >>> fetcher = GHCNDataFetcher("USW00024233", "./my_project")
            >>> df = fetcher.parse_dly_file(dly_path)
            >>> csv_path = fetcher.save_processed_data(df)
        """
        # Validate DataFrame has required columns
        required_cols = ['date', 'precipitation_mm', 'tmax_c', 'tmin_c']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(
                f"DataFrame missing required columns: {missing_cols}\n"
                f"Required columns: {required_cols}"
            )
        
        # Get output path
        output_path = self.project.get_observed_climate_path()
        
        # Save to CSV
        df.to_csv(output_path, index=False, date_format='%Y-%m-%d')
        
        print(f"Saved processed data to: {output_path}")
        
        return output_path
    
    def fetch_and_process(self, timeout: int = 30) -> tuple[Path, pd.DataFrame]:
        """Complete workflow: download, parse, and save climate data.
        
        This is a convenience method that runs the complete data acquisition
        workflow in one call:
        1. Download .dly file from NOAA
        2. Parse fixed-width format
        3. Save processed data to CSV
        
        Args:
            timeout: HTTP request timeout in seconds (default: 30)
            
        Returns:
            Tuple of (dly_path, dataframe)
            
        Example:
            >>> fetcher = GHCNDataFetcher("USW00024233", "./my_project")
            >>> dly_path, df = fetcher.fetch_and_process()
            >>> print(f"Downloaded {len(df)} days of data")
        """
        # Download
        dly_path = self.download_dly_file(timeout=timeout)
        
        # Parse
        df = self.parse_dly_file(dly_path)
        
        # Save
        self.save_processed_data(df)
        
        return dly_path, df
