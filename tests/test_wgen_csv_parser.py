"""
Tests for WGEN CSV parameter parser error handling.

This module tests error handling scenarios for the CSV parameter parser including:
- Missing CSV file (FileNotFoundError)
- Missing required parameters (ValueError)
- Invalid parameter values (ValueError)
- Wrong number of data rows (ValueError)
- Missing header row (ValueError)
"""

import pytest
import pandas as pd
import tempfile
import os
from pathlib import Path

from hydrosim.wgen_params import CSVWGENParamsParser
from hydrosim.wgen import WGENParams


# ============================================================================
# Helper Functions
# ============================================================================

def create_valid_csv_content():
    """Create valid CSV content with all required parameters in new format."""
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
    
    return '\n'.join(lines) + '\n'


def create_temp_csv(content):
    """Create a temporary CSV file with given content."""
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='')
    temp_file.write(content)
    temp_file.close()
    return temp_file.name


# ============================================================================
# Missing CSV File Tests (FileNotFoundError)
# ============================================================================

def test_missing_csv_file():
    """Test that FileNotFoundError is raised when CSV file doesn't exist."""
    non_existent_path = "/path/to/nonexistent/file.csv"
    
    with pytest.raises(FileNotFoundError) as exc_info:
        CSVWGENParamsParser.parse(non_existent_path)
    
    # Check error message contains the file path
    error_msg = str(exc_info.value)
    assert non_existent_path in error_msg
    assert "not found" in error_msg.lower()


def test_missing_csv_file_relative_path():
    """Test that FileNotFoundError is raised for missing file with relative path."""
    relative_path = "nonexistent_params.csv"
    
    with pytest.raises(FileNotFoundError) as exc_info:
        CSVWGENParamsParser.parse(relative_path)
    
    error_msg = str(exc_info.value)
    assert "not found" in error_msg.lower()


def test_missing_csv_file_error_message_helpful():
    """Test that FileNotFoundError provides helpful guidance."""
    with pytest.raises(FileNotFoundError) as exc_info:
        CSVWGENParamsParser.parse("missing.csv")
    
    error_msg = str(exc_info.value)
    assert "expected location" in error_msg.lower() or "same directory" in error_msg.lower()


# ============================================================================
# Missing Parameter Tests (ValueError)
# ============================================================================

def test_missing_monthly_parameter_columns():
    """Test that ValueError is raised when monthly parameter columns are missing."""
    # Create CSV missing some monthly parameters
    content = create_valid_csv_content()
    # Remove pww from the monthly section
    content = content.replace(",pww,", ",")
    
    temp_file = create_temp_csv(content)
    
    try:
        with pytest.raises(ValueError) as exc_info:
            CSVWGENParamsParser.parse(temp_file)
        
        error_msg = str(exc_info.value)
        assert "pww" in error_msg.lower() or "missing" in error_msg.lower()
    finally:
        os.unlink(temp_file)


def test_missing_constant_parameter():
    """Test that ValueError is raised when a constant parameter is missing."""
    # Create CSV missing latitude
    content = create_valid_csv_content()
    lines = content.split('\n')
    # Remove the latitude line
    lines = [line for line in lines if not line.startswith('latitude,')]
    content = '\n'.join(lines)
    
    temp_file = create_temp_csv(content)
    
    try:
        with pytest.raises(ValueError) as exc_info:
            CSVWGENParamsParser.parse(temp_file)
        
        error_msg = str(exc_info.value)
        assert "latitude" in error_msg
    finally:
        os.unlink(temp_file)


def test_missing_multiple_parameters():
    """Test that ValueError lists all missing parameters."""
    # Create CSV missing multiple parameters
    content = create_valid_csv_content()
    lines = content.split('\n')
    # Remove latitude and rmd
    lines = [line for line in lines if not line.startswith('latitude,') and not line.startswith('rmd,')]
    content = '\n'.join(lines)
    
    temp_file = create_temp_csv(content)
    
    try:
        with pytest.raises(ValueError) as exc_info:
            CSVWGENParamsParser.parse(temp_file)
        
        error_msg = str(exc_info.value)
        # Should mention missing parameters
        assert "missing" in error_msg.lower()
    finally:
        os.unlink(temp_file)


def test_missing_parameter_error_references_template():
    """Test that missing parameter error references the template file."""
    # Create CSV with missing parameters
    content = "month,pww,pwd,alpha,beta\njan,0.5,0.3,1.0,8.0\n"
    
    temp_file = create_temp_csv(content)
    
    try:
        with pytest.raises(ValueError) as exc_info:
            CSVWGENParamsParser.parse(temp_file)
        
        error_msg = str(exc_info.value)
        assert "wgen_params_template.csv" in error_msg.lower()
    finally:
        os.unlink(temp_file)


# ============================================================================
# Invalid Parameter Value Tests (ValueError)
# ============================================================================

def test_invalid_probability_value_above_one():
    """Test that ValueError is raised when probability value exceeds 1.0."""
    content = create_valid_csv_content()
    # Replace a pww value with invalid value
    content = content.replace("jan,0.45,", "jan,1.5,")
    
    temp_file = create_temp_csv(content)
    
    try:
        with pytest.raises(ValueError) as exc_info:
            CSVWGENParamsParser.parse(temp_file)
        
        error_msg = str(exc_info.value)
        assert "invalid" in error_msg.lower()
    finally:
        os.unlink(temp_file)


def test_invalid_probability_value_negative():
    """Test that ValueError is raised when probability value is negative."""
    content = create_valid_csv_content()
    # Replace a pwd value with negative value
    content = content.replace(",0.25,1.2,", ",-0.1,1.2,")
    
    temp_file = create_temp_csv(content)
    
    try:
        with pytest.raises(ValueError) as exc_info:
            CSVWGENParamsParser.parse(temp_file)
        
        error_msg = str(exc_info.value)
        assert "invalid" in error_msg.lower()
    finally:
        os.unlink(temp_file)


def test_invalid_alpha_parameter_negative():
    """Test that ValueError is raised when alpha parameter is negative."""
    content = create_valid_csv_content()
    # Replace an alpha value with negative value
    content = content.replace(",1.2,8.5", ",-0.5,8.5")
    
    temp_file = create_temp_csv(content)
    
    try:
        with pytest.raises(ValueError) as exc_info:
            CSVWGENParamsParser.parse(temp_file)
        
        error_msg = str(exc_info.value)
        assert "invalid" in error_msg.lower()
    finally:
        os.unlink(temp_file)


def test_invalid_beta_parameter_negative():
    """Test that ValueError is raised when beta parameter is negative."""
    content = create_valid_csv_content()
    # Replace a beta value with negative value
    content = content.replace(",8.5\n", ",-2.0\n")
    
    temp_file = create_temp_csv(content)
    
    try:
        with pytest.raises(ValueError) as exc_info:
            CSVWGENParamsParser.parse(temp_file)
        
        error_msg = str(exc_info.value)
        assert "invalid" in error_msg.lower()
    finally:
        os.unlink(temp_file)


def test_invalid_latitude_above_range():
    """Test that ValueError is raised when latitude exceeds 90 degrees."""
    content = create_valid_csv_content()
    content = content.replace("latitude,45.0", "latitude,95.0")
    
    temp_file = create_temp_csv(content)
    
    try:
        with pytest.raises(ValueError) as exc_info:
            CSVWGENParamsParser.parse(temp_file)
        
        error_msg = str(exc_info.value)
        assert "invalid" in error_msg.lower()
    finally:
        os.unlink(temp_file)


def test_invalid_latitude_below_range():
    """Test that ValueError is raised when latitude is below -90 degrees."""
    content = create_valid_csv_content()
    content = content.replace("latitude,45.0", "latitude,-95.0")
    
    temp_file = create_temp_csv(content)
    
    try:
        with pytest.raises(ValueError) as exc_info:
            CSVWGENParamsParser.parse(temp_file)
        
        error_msg = str(exc_info.value)
        assert "invalid" in error_msg.lower()
    finally:
        os.unlink(temp_file)


def test_invalid_non_numeric_value():
    """Test that ValueError is raised when parameter value is not numeric."""
    content = create_valid_csv_content()
    content = content.replace("txmd,20.0", "txmd,not_a_number")
    
    temp_file = create_temp_csv(content)
    
    try:
        with pytest.raises(ValueError) as exc_info:
            CSVWGENParamsParser.parse(temp_file)
        
        error_msg = str(exc_info.value)
        assert "invalid" in error_msg.lower() or "numeric" in error_msg.lower()
    finally:
        os.unlink(temp_file)


# ============================================================================
# CSV Structure Tests (ValueError)
# ============================================================================

def test_zero_data_rows():
    """Test that ValueError is raised when CSV has no data rows."""
    # Just headers, no data
    content = "month,pww,pwd,alpha,beta\n"
    
    temp_file = create_temp_csv(content)
    
    try:
        with pytest.raises(ValueError) as exc_info:
            CSVWGENParamsParser.parse(temp_file)
        
        error_msg = str(exc_info.value)
        assert "incomplete" in error_msg.lower() or "expected" in error_msg.lower()
    finally:
        os.unlink(temp_file)


def test_multiple_data_rows():
    """Test that ValueError is raised when monthly section has too many rows."""
    content = create_valid_csv_content()
    # Add an extra month row BEFORE the blank line
    lines = content.split('\n')
    # Find the blank line after dec and insert before it
    for i, line in enumerate(lines):
        if line.startswith('dec,'):
            # Insert the extra row right after dec, before the blank line
            lines.insert(i+1, "extra,0.5,0.3,1.0,8.0")
            break
    content = '\n'.join(lines)
    
    temp_file = create_temp_csv(content)
    
    try:
        with pytest.raises(ValueError) as exc_info:
            CSVWGENParamsParser.parse(temp_file)
        
        error_msg = str(exc_info.value)
        assert "12" in error_msg or "exactly" in error_msg.lower()
    finally:
        os.unlink(temp_file)


def test_two_data_rows():
    """Test that ValueError is raised when monthly section has 13 rows instead of 12."""
    content = create_valid_csv_content()
    # Add an extra month row BEFORE the blank line
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if line.startswith('dec,'):
            # Insert right after dec, before the blank line
            lines.insert(i+1, "jan2,0.5,0.3,1.0,8.0")
            break
    content = '\n'.join(lines)
    
    temp_file = create_temp_csv(content)
    
    try:
        with pytest.raises(ValueError) as exc_info:
            CSVWGENParamsParser.parse(temp_file)
        
        error_msg = str(exc_info.value)
        assert "12" in error_msg or "exactly" in error_msg.lower()
    finally:
        os.unlink(temp_file)


def test_wrong_row_count_error_message():
    """Test that error message clearly states expected row count."""
    content = create_valid_csv_content()
    # Add extra rows BEFORE the blank line
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if line.startswith('dec,'):
            # Insert right after dec, before the blank line
            lines.insert(i+1, "extra,0.5,0.3,1.0,8.0")
            break
    content = '\n'.join(lines)
    
    temp_file = create_temp_csv(content)
    
    try:
        with pytest.raises(ValueError) as exc_info:
            CSVWGENParamsParser.parse(temp_file)
        
        error_msg = str(exc_info.value)
        assert "12" in error_msg
    finally:
        os.unlink(temp_file)


def test_empty_csv_file():
    """Test that ValueError is raised when CSV file is completely empty."""
    temp_file = create_temp_csv("")
    
    try:
        with pytest.raises(ValueError) as exc_info:
            CSVWGENParamsParser.parse(temp_file)
        
        error_msg = str(exc_info.value)
        assert "empty" in error_msg.lower()
    finally:
        os.unlink(temp_file)


def test_csv_with_only_values_no_header():
    """Test that ValueError is raised when CSV has no header row."""
    # Just values, no header
    content = "jan,0.45,0.25,1.2,8.5\n"
    
    temp_file = create_temp_csv(content)
    
    try:
        with pytest.raises(ValueError) as exc_info:
            CSVWGENParamsParser.parse(temp_file)
        
        error_msg = str(exc_info.value)
        # Should fail because it doesn't have the proper structure
        assert "missing" in error_msg.lower() or "expected" in error_msg.lower()
    finally:
        os.unlink(temp_file)


def test_malformed_csv_structure():
    """Test that ValueError is raised when CSV structure is malformed."""
    # Malformed CSV with inconsistent columns
    content = "month,pww\njan,0.45,extra_value\n"
    
    temp_file = create_temp_csv(content)
    
    try:
        with pytest.raises(ValueError) as exc_info:
            CSVWGENParamsParser.parse(temp_file)
        
        error_msg = str(exc_info.value)
        # Should fail due to missing structure
        assert "missing" in error_msg.lower() or "expected" in error_msg.lower()
    finally:
        os.unlink(temp_file)


# ============================================================================
# Valid CSV Tests
# ============================================================================

def test_valid_csv_parses_successfully():
    """Test that a valid CSV file parses successfully."""
    content = create_valid_csv_content()
    temp_file = create_temp_csv(content)
    
    try:
        params = CSVWGENParamsParser.parse(temp_file)
        
        # Verify it's a WGENParams object
        assert isinstance(params, WGENParams)
        
        # Verify some parameter values
        assert len(params.pww) == 12
        assert params.pww[0] == 0.45  # January
        assert params.latitude == 45.0
        assert params.random_seed == 42
    finally:
        os.unlink(temp_file)


def test_valid_csv_with_optional_parameter():
    """Test that CSV with optional random_seed parameter parses correctly."""
    content = create_valid_csv_content()
    temp_file = create_temp_csv(content)
    
    try:
        params = CSVWGENParamsParser.parse(temp_file)
        assert params.random_seed == 42
    finally:
        os.unlink(temp_file)


def test_valid_csv_without_optional_parameter():
    """Test that CSV without optional random_seed parameter parses correctly."""
    content = create_valid_csv_content()
    # Remove random_seed line
    lines = content.split('\n')
    lines = [line for line in lines if not line.startswith('random_seed,')]
    content = '\n'.join(lines)
    
    temp_file = create_temp_csv(content)
    
    try:
        params = CSVWGENParamsParser.parse(temp_file)
        assert params.random_seed is None
    finally:
        os.unlink(temp_file)
