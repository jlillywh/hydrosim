"""
GHCN .dly File Parser for Climate Builder.

This module provides the DLYParser class for parsing NOAA GHCN Daily format files.
The GHCN Daily format is a fixed-width text format containing daily climate observations.

Fixed-Width Format:
    - Positions 0-11: Station ID
    - Positions 11-15: Year
    - Positions 15-17: Month
    - Positions 17-21: Element (PRCP, TMAX, TMIN, etc.)
    - Positions 21+: Daily values (8 characters per day)

Each daily value consists of:
    - 5 characters: Value (in tenths of unit)
    - 1 character: Measurement flag
    - 1 character: Quality flag
    - 1 character: Source flag

Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7
"""

import datetime
from pathlib import Path
from typing import Dict, Optional
import pandas as pd


class DLYParser:
    """Parser for GHCN Daily format (.dly) files.
    
    This class handles parsing of the fixed-width GHCN Daily format:
    - Extracts PRCP (precipitation), TMAX (maximum temperature), TMIN (minimum temperature)
    - Converts from tenths of mm/°C to mm/°C
    - Handles missing value flags (-9999 → NaN)
    - Skips February 29th records (WGEN uses 365-day calendar)
    - Skips other invalid dates (e.g., February 30, April 31)
    
    Attributes:
        MISSING_VALUE_FLAG: Value indicating missing data in GHCN format (-9999)
        
    Example:
        >>> parser = DLYParser()
        >>> df = parser.parse(Path("data/raw/USW00024233.dly"))
        >>> print(df.head())
    """
    
    # Missing value flag in GHCN format
    MISSING_VALUE_FLAG = -9999
    
    def __init__(self):
        """Initialize DLY parser."""
        pass
    
    def parse(self, dly_path: Path) -> pd.DataFrame:
        """Parse GHCN fixed-width .dly format file.
        
        Parses the GHCN Daily format which uses fixed-width columns:
        - Positions 0-11: Station ID
        - Positions 11-15: Year
        - Positions 15-17: Month
        - Positions 17-21: Element (PRCP, TMAX, TMIN, etc.)
        - Positions 21+: Daily values (8 characters per day)
        
        Each daily value consists of:
        - 5 characters: Value (in tenths of unit)
        - 1 character: Measurement flag
        - 1 character: Quality flag
        - 1 character: Source flag
        
        Args:
            dly_path: Path to .dly file
            
        Returns:
            DataFrame with columns: date, precipitation_mm, tmax_c, tmin_c
            Missing values represented as NaN
            February 29th excluded
            
        Raises:
            ValueError: If file format is invalid or no valid data found
            FileNotFoundError: If file doesn't exist
            
        Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7
        
        Example:
            >>> parser = DLYParser()
            >>> df = parser.parse(Path("data/raw/USW00024233.dly"))
            >>> print(f"Parsed {len(df)} days of data")
        """
        if not dly_path.exists():
            raise FileNotFoundError(f"DLY file not found: {dly_path}")
        
        print(f"Parsing .dly file: {dly_path}")
        
        # Storage for parsed data
        data_by_date = {}
        
        # Read file line by line
        with open(dly_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    # Skip empty lines
                    if not line.strip():
                        continue
                    
                    # Parse fixed-width format
                    station = line[0:11].strip()
                    year = int(line[11:15])
                    month = int(line[15:17])
                    element = line[17:21].strip()
                    
                    # Only process PRCP, TMAX, TMIN elements
                    if element not in ['PRCP', 'TMAX', 'TMIN']:
                        continue
                    
                    # Parse daily values (up to 31 days)
                    for day in range(1, 32):
                        # Calculate position in line (8 characters per day)
                        pos = 21 + (day - 1) * 8
                        
                        # Check if we have data for this day
                        if pos + 5 > len(line):
                            break
                        
                        # Extract value (5 characters, right-aligned)
                        value_str = line[pos:pos+5]
                        
                        # Skip if empty or all spaces
                        if not value_str or not value_str.strip():
                            continue
                        
                        try:
                            value = int(value_str)
                        except ValueError:
                            # Could not parse as integer, skip
                            continue
                        
                        # Skip missing values (convert to None for NaN)
                        if value == self.MISSING_VALUE_FLAG:
                            value = None
                        else:
                            # Convert from tenths to whole units
                            # Requirements 2.1, 2.2, 2.3: Convert tenths of mm/°C to mm/°C
                            value = value / 10.0
                        
                        # Create date
                        try:
                            date = datetime.date(year, month, day)
                        except ValueError:
                            # Invalid date (e.g., Feb 30, Apr 31)
                            # Requirement 2.6: Skip invalid dates
                            continue
                        
                        # Skip February 29th (WGEN uses 365-day calendar)
                        # Requirement 2.5: Skip February 29th records
                        if date.month == 2 and date.day == 29:
                            continue
                        
                        # Initialize date entry if needed
                        if date not in data_by_date:
                            data_by_date[date] = {
                                'date': date,
                                'precipitation_mm': None,
                                'tmax_c': None,
                                'tmin_c': None
                            }
                        
                        # Store value by element type
                        if element == 'PRCP':
                            data_by_date[date]['precipitation_mm'] = value
                        elif element == 'TMAX':
                            data_by_date[date]['tmax_c'] = value
                        elif element == 'TMIN':
                            data_by_date[date]['tmin_c'] = value
                
                except Exception as e:
                    print(f"Warning: Error parsing line {line_num}: {str(e)}")
                    continue
        
        # Convert to DataFrame
        if not data_by_date:
            raise ValueError(
                f"No valid data found in .dly file: {dly_path}\n"
                f"File may be empty or corrupted."
            )
        
        # Requirement 2.7: Output DataFrame with columns: date, precipitation_mm, tmax_c, tmin_c
        df = pd.DataFrame(list(data_by_date.values()))
        df = df.sort_values('date').reset_index(drop=True)
        
        print(f"Parsed {len(df)} days of data")
        print(f"Date range: {df['date'].min()} to {df['date'].max()}")
        
        # Report missing data
        for col in ['precipitation_mm', 'tmax_c', 'tmin_c']:
            missing_count = df[col].isna().sum()
            missing_pct = 100 * missing_count / len(df)
            print(f"  {col}: {missing_pct:.1f}% missing ({missing_count}/{len(df)} days)")
        
        return df
    
    def parse_line(self, line: str) -> Dict[datetime.date, Dict[str, Optional[float]]]:
        """Parse a single line from a .dly file.
        
        This is a helper method that can be used for testing or processing
        individual lines.
        
        Args:
            line: Single line from .dly file
            
        Returns:
            Dictionary mapping dates to climate data for that line
            
        Example:
            >>> parser = DLYParser()
            >>> line = "USW00024233201001TMAX  100  110  120..."
            >>> data = parser.parse_line(line)
        """
        data_by_date = {}
        
        try:
            # Skip empty lines
            if not line.strip():
                return data_by_date
            
            # Parse fixed-width format
            station = line[0:11].strip()
            year = int(line[11:15])
            month = int(line[15:17])
            element = line[17:21].strip()
            
            # Only process PRCP, TMAX, TMIN elements
            if element not in ['PRCP', 'TMAX', 'TMIN']:
                return data_by_date
            
            # Parse daily values (up to 31 days)
            for day in range(1, 32):
                # Calculate position in line (8 characters per day)
                pos = 21 + (day - 1) * 8
                
                # Check if we have data for this day
                if pos + 5 > len(line):
                    break
                
                # Extract value (5 characters, right-aligned)
                value_str = line[pos:pos+5]
                
                # Skip if empty or all spaces
                if not value_str or not value_str.strip():
                    continue
                
                try:
                    value = int(value_str)
                except ValueError:
                    # Could not parse as integer, skip
                    continue
                
                # Skip missing values (convert to None for NaN)
                if value == self.MISSING_VALUE_FLAG:
                    value = None
                else:
                    # Convert from tenths to whole units
                    value = value / 10.0
                
                # Create date
                try:
                    date = datetime.date(year, month, day)
                except ValueError:
                    # Invalid date (e.g., Feb 30, Apr 31)
                    continue
                
                # Skip February 29th (WGEN uses 365-day calendar)
                if date.month == 2 and date.day == 29:
                    continue
                
                # Initialize date entry if needed
                if date not in data_by_date:
                    data_by_date[date] = {
                        'date': date,
                        'precipitation_mm': None,
                        'tmax_c': None,
                        'tmin_c': None
                    }
                
                # Store value by element type
                if element == 'PRCP':
                    data_by_date[date]['precipitation_mm'] = value
                elif element == 'TMAX':
                    data_by_date[date]['tmax_c'] = value
                elif element == 'TMIN':
                    data_by_date[date]['tmin_c'] = value
        
        except Exception:
            # Return empty dict on error
            return {}
        
        return data_by_date
