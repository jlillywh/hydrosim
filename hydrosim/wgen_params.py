"""
CSV parameter parser for WGEN weather generator.

This module provides functionality to load WGEN parameters from CSV files,
enabling users to manage complex parameter sets more easily and reuse them
across multiple simulations.

CSV File Format
---------------
The CSV file uses a structured format with three sections:

1. **Monthly Parameters Section** (12 rows):
   - Header: month,pww,pwd,alpha,beta
   - 12 data rows (jan through dec) with monthly precipitation parameters

2. **Temperature Parameters Section** (9 rows after blank line):
   - Header: parameter,value
   - Rows for: txmd, atx, txmw, tn, atn, cvtx, acvtx, cvtn, acvtn

3. **Radiation Parameters Section** (3 rows after blank line):
   - Header: parameter,value
   - Rows for: rmd, ar, rmw

4. **Location Parameters Section** (2 rows after blank line):
   - Header: parameter,value
   - Rows for: latitude, random_seed (optional)

Required Parameters:

**Precipitation Parameters (monthly):**
- pww: Probability of wet day following wet day [0-1]
- pwd: Probability of wet day following dry day [0-1]
- alpha: Gamma shape parameter for precipitation amount [>0]
- beta: Gamma scale parameter for precipitation amount (mm) [>0]

**Temperature Parameters:**
- txmd: Mean maximum temperature on dry days (°C) [-50 to 50]
- atx: Amplitude of seasonal variation in maximum temperature (°C) [0 to 30]
- txmw: Mean maximum temperature on wet days (°C) [-50 to 50]
- tn: Mean minimum temperature (°C) [-60 to 40]
- atn: Amplitude of seasonal variation in minimum temperature (°C) [0 to 25]
- cvtx: Coefficient of variation for maximum temperature [0.01 to 0.5]
- acvtx: Amplitude of seasonal variation in cvtx [0 to 0.2]
- cvtn: Coefficient of variation for minimum temperature [0.01 to 0.5]
- acvtn: Amplitude of seasonal variation in cvtn [0 to 0.2]

**Radiation Parameters:**
- rmd: Mean solar radiation on dry days (MJ/m²/day) [0 to 40]
- ar: Amplitude of seasonal variation in solar radiation (MJ/m²/day) [0 to 20]
- rmw: Mean solar radiation on wet days (MJ/m²/day) [0 to 35]

**Location Parameters:**
- latitude: Site latitude in degrees [-90 to 90]
- random_seed: Random seed for reproducibility (integer or empty, optional)

Usage Example
-------------
    from hydrosim.wgen_params import CSVWGENParamsParser
    
    # Parse parameters from CSV file
    params = CSVWGENParamsParser.parse('wgen_params.csv')
    
    # Create a template CSV file
    CSVWGENParamsParser.create_template('my_params_template.csv')

YAML Configuration
------------------
Reference the CSV file in your YAML configuration:

    climate:
      source_type: wgen
      start_date: "2024-01-01"
      wgen_params_file: wgen_params.csv  # Relative to YAML file location
      site:
        latitude: 45.0
        elevation: 1000.0

See Also
--------
- hydrosim.wgen.WGENParams: Parameter validation and data structure
- examples/wgen_params_template.csv: Template CSV file with example values
- examples/wgen_example.yaml: Example YAML configuration using CSV parameters
"""

import pandas as pd
from pathlib import Path
from typing import List, Dict
from hydrosim.wgen import WGENParams


class CSVWGENParamsParser:
    """Parser for WGEN parameters from CSV files.
    
    The CSV file uses a structured format with sections for monthly parameters,
    temperature parameters, radiation parameters, and location parameters.
    Each section is separated by blank lines for readability.
    """
    
    # Month names for monthly parameters
    MONTH_NAMES = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 
                   'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
    
    # Monthly parameter names (12 values each)
    MONTHLY_PARAMS = ['pww', 'pwd', 'alpha', 'beta']
    
    # Constant parameter names (single value)
    CONSTANT_PARAMS = ['txmd', 'atx', 'txmw', 'tn', 'atn', 
                       'cvtx', 'acvtx', 'cvtn', 'acvtn',
                       'rmd', 'ar', 'rmw', 'latitude']
    
    # Optional parameters
    OPTIONAL_PARAMS = ['random_seed']
    
    @staticmethod
    def parse(filepath: str) -> WGENParams:
        """
        Parse WGEN parameters from CSV file.
        
        Args:
            filepath: Path to CSV parameter file
            
        Returns:
            WGENParams object with validated parameters
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If CSV format is invalid or parameters are missing/invalid
        """
        # Check if file exists
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(
                f"WGEN parameter file not found: {filepath}\n"
                f"Expected location: Same directory as YAML configuration file"
            )
        
        # Read the entire CSV file, skipping blank lines
        try:
            # Read all lines, preserving structure
            with open(filepath, 'r') as f:
                lines = f.readlines()
        except Exception as e:
            raise ValueError(f"Failed to read CSV file {filepath}: {e}")
        
        # Parse the structured CSV
        params_dict = CSVWGENParamsParser._parse_structured_csv(lines, filepath)
        
        # Create and return WGENParams object (validation happens in __post_init__)
        try:
            return WGENParams(**params_dict)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid WGEN parameters in CSV file: {e}")
    
    @staticmethod
    def _parse_structured_csv(lines: List[str], filepath: str) -> Dict:
        """
        Parse the structured CSV format with sections.
        
        Args:
            lines: Lines from the CSV file
            filepath: Path to the file (for error messages)
            
        Returns:
            Dictionary of parameter names to values
        """
        params_dict = {}
        
        # Remove empty lines and strip whitespace
        non_empty_lines = [line.strip() for line in lines if line.strip()]
        
        if len(non_empty_lines) == 0:
            raise ValueError(
                "WGEN parameter CSV file is empty. "
                "See examples/wgen_params_template.csv for the expected format."
            )
        
        # Find section boundaries by looking for headers
        monthly_start = None
        param_value_sections = []
        
        for i, line in enumerate(non_empty_lines):
            if line.startswith('month,'):
                monthly_start = i
            elif line.startswith('parameter,value'):
                param_value_sections.append(i)
        
        # Parse monthly parameters section
        if monthly_start is None:
            raise ValueError(
                "WGEN parameter CSV is missing monthly parameters section. "
                "Expected header: 'month,pww,pwd,alpha,beta'\n"
                "See examples/wgen_params_template.csv for the expected format."
            )
        
        # Extract monthly parameters
        # Pass all lines from monthly_start onwards, let the function determine the section end
        monthly_data = CSVWGENParamsParser._parse_monthly_section(
            non_empty_lines[monthly_start:], filepath
        )
        params_dict.update(monthly_data)
        
        # Parse parameter,value sections
        constant_params = CSVWGENParamsParser._parse_param_value_sections(
            non_empty_lines, param_value_sections, filepath
        )
        params_dict.update(constant_params)
        
        return params_dict
    
    @staticmethod
    def _parse_monthly_section(lines: List[str], filepath: str) -> Dict:
        """
        Parse the monthly parameters section.
        
        Args:
            lines: Lines from the monthly section (should be header + 12 data rows)
            filepath: Path to the file (for error messages)
            
        Returns:
            Dictionary with monthly parameter arrays
        """
        # Find the end of the monthly section (next blank line or parameter,value header)
        section_end = len(lines)
        for i in range(1, len(lines)):
            if lines[i].strip() == '' or lines[i].startswith('parameter,value'):
                section_end = i
                break
        
        monthly_lines = lines[:section_end]
        
        if len(monthly_lines) < 13:
            raise ValueError(
                f"WGEN parameter CSV monthly section incomplete. "
                f"Expected 13 lines (1 header + 12 months), found {len(monthly_lines)}.\n"
                f"See examples/wgen_params_template.csv for the expected format."
            )
        
        if len(monthly_lines) > 13:
            raise ValueError(
                f"WGEN parameter CSV monthly section must have exactly 12 rows (one per month), "
                f"found {len(monthly_lines) - 1} rows."
            )
        
        # Parse as DataFrame
        from io import StringIO
        csv_text = '\n'.join(monthly_lines)
        try:
            df = pd.read_csv(StringIO(csv_text))
        except Exception as e:
            raise ValueError(f"Failed to parse monthly parameters section: {e}")
        
        # Validate we have the expected columns
        expected_cols = ['month'] + CSVWGENParamsParser.MONTHLY_PARAMS
        missing_cols = [col for col in expected_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(
                f"WGEN parameter CSV monthly section is missing columns: {', '.join(missing_cols)}\n"
                f"Expected header: month,pww,pwd,alpha,beta"
            )
        
        # Validate we have all 12 months
        if len(df) != 12:
            raise ValueError(
                f"WGEN parameter CSV monthly section must have exactly 12 rows (one per month), "
                f"found {len(df)} rows."
            )
        
        # Extract monthly parameters
        params_dict = {}
        for param_name in CSVWGENParamsParser.MONTHLY_PARAMS:
            try:
                values = [float(val) for val in df[param_name].values]
                params_dict[param_name] = values
            except (ValueError, TypeError) as e:
                raise ValueError(
                    f"Invalid values in monthly parameter '{param_name}': {e}"
                )
        
        return params_dict
    
    @staticmethod
    def _parse_param_value_sections(lines: List[str], section_starts: List[int], filepath: str) -> Dict:
        """
        Parse all parameter,value sections.
        
        Args:
            lines: All non-empty lines from the file
            section_starts: Indices where 'parameter,value' headers appear
            filepath: Path to the file (for error messages)
            
        Returns:
            Dictionary of parameter names to values
        """
        params_dict = {}
        
        for section_idx, start_idx in enumerate(section_starts):
            # Determine end of this section (start of next section or end of file)
            if section_idx + 1 < len(section_starts):
                end_idx = section_starts[section_idx + 1]
            else:
                end_idx = len(lines)
            
            # Extract section lines
            section_lines = lines[start_idx:end_idx]
            
            # Parse as DataFrame
            from io import StringIO
            csv_text = '\n'.join(section_lines)
            try:
                df = pd.read_csv(StringIO(csv_text))
            except Exception as e:
                raise ValueError(f"Failed to parse parameter,value section: {e}")
            
            # Extract parameters
            for _, row in df.iterrows():
                param_name = row['parameter']
                value = row['value']
                
                # Handle optional parameters
                if param_name in CSVWGENParamsParser.OPTIONAL_PARAMS:
                    if pd.isna(value) or value == '':
                        params_dict[param_name] = None
                    else:
                        try:
                            params_dict[param_name] = int(value) if param_name == 'random_seed' else float(value)
                        except (ValueError, TypeError):
                            params_dict[param_name] = None
                else:
                    # Required parameter
                    try:
                        params_dict[param_name] = float(value)
                    except (ValueError, TypeError) as e:
                        raise ValueError(
                            f"Invalid value for parameter '{param_name}': {value}. "
                            f"Expected a numeric value."
                        )
        
        # Check for missing required parameters
        missing_params = [p for p in CSVWGENParamsParser.CONSTANT_PARAMS if p not in params_dict]
        if missing_params:
            raise ValueError(
                f"WGEN parameter CSV is missing required parameters:\n"
                f"  - {', '.join(missing_params)}\n"
                f"See examples/wgen_params_template.csv for the complete parameter list."
            )
        
        return params_dict
    
    @staticmethod
    def create_template(filepath: str) -> None:
        """
        Create a template CSV file with all required parameters.
        
        This template includes realistic parameter values for a mid-latitude location
        and can be used as a starting point for creating custom parameter files.
        
        Args:
            filepath: Path where template should be created
        """
        # Create the template content
        lines = []
        
        # Monthly parameters section
        lines.append("month,pww,pwd,alpha,beta")
        monthly_data = [
            ("jan", 0.45, 0.25, 1.2, 8.5),
            ("feb", 0.42, 0.23, 1.1, 7.8),
            ("mar", 0.40, 0.22, 1.0, 7.2),
            ("apr", 0.38, 0.20, 0.9, 6.5),
            ("may", 0.35, 0.18, 0.8, 5.8),
            ("jun", 0.30, 0.15, 0.7, 5.0),
            ("jul", 0.25, 0.12, 0.6, 4.5),
            ("aug", 0.28, 0.15, 0.7, 5.2),
            ("sep", 0.32, 0.18, 0.8, 6.0),
            ("oct", 0.38, 0.22, 1.0, 7.0),
            ("nov", 0.42, 0.25, 1.1, 7.8),
            ("dec", 0.48, 0.27, 1.3, 9.2),
        ]
        for month, pww, pwd, alpha, beta in monthly_data:
            lines.append(f"{month},{pww},{pwd},{alpha},{beta}")
        
        lines.append("")  # Blank line
        
        # Temperature parameters section
        lines.append("parameter,value")
        temp_params = [
            ("txmd", 20.0),
            ("atx", 10.0),
            ("txmw", 18.0),
            ("tn", 10.0),
            ("atn", 8.0),
            ("cvtx", 0.1),
            ("acvtx", 0.05),
            ("cvtn", 0.1),
            ("acvtn", 0.05),
        ]
        for param, value in temp_params:
            lines.append(f"{param},{value}")
        
        lines.append("")  # Blank line
        
        # Radiation parameters section
        lines.append("parameter,value")
        rad_params = [
            ("rmd", 15.0),
            ("ar", 5.0),
            ("rmw", 12.0),
        ]
        for param, value in rad_params:
            lines.append(f"{param},{value}")
        
        lines.append("")  # Blank line
        
        # Location parameters section
        lines.append("parameter,value")
        location_params = [
            ("latitude", 45.0),
            ("random_seed", 42),
        ]
        for param, value in location_params:
            lines.append(f"{param},{value}")
        
        # Write to file
        with open(filepath, 'w') as f:
            f.write('\n'.join(lines) + '\n')
