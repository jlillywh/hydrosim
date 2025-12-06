"""
Integration tests for Climate Builder with real GHCN data.

These tests actually download data from NOAA servers and process it through
the entire pipeline. They verify that the system works with real-world data
and can catch issues like:
- NOAA API/format changes
- Encoding issues
- Unexpected data patterns
- Network/timeout issues

Run these tests with:
    pytest -m integration

Skip these tests (default for CI):
    pytest -m "not integration"
"""

import pytest
import tempfile
from pathlib import Path
import pandas as pd

from hydrosim.climate_builder import (
    GHCNDataFetcher,
    WGENParameterGenerator,
    ProjectStructure,
)
from hydrosim.wgen_params import CSVWGENParamsParser


# Well-known stable GHCN stations for testing
TEST_STATIONS = {
    'seattle': {
        'station_id': 'USW00024233',  # Seattle-Tacoma International Airport
        'latitude': 47.45,
        'name': 'Seattle-Tacoma Airport, WA'
    },
    'denver': {
        'station_id': 'USW00023062',  # Denver International Airport
        'latitude': 39.83,
        'name': 'Denver International Airport, CO'
    }
}


@pytest.mark.integration
@pytest.mark.slow
class TestClimateBuilderIntegration:
    """Integration tests with real GHCN data."""
    
    def test_download_and_parse_real_ghcn_data(self):
        """Test downloading and parsing real GHCN data from NOAA servers.
        
        This test:
        1. Downloads a real .dly file from NOAA
        2. Parses it to extract precipitation and temperature
        3. Verifies the data has expected structure and reasonable values
        
        Uses Seattle-Tacoma Airport as a stable, well-maintained station.
        """
        station = TEST_STATIONS['seattle']
        
        with tempfile.TemporaryDirectory() as tmpdir:
            print(f"\nTesting with {station['name']} ({station['station_id']})")
            
            # Initialize fetcher
            fetcher = GHCNDataFetcher(station['station_id'], tmpdir)
            
            # Download .dly file (this actually hits NOAA servers)
            print("Downloading .dly file from NOAA...")
            dly_path = fetcher.download_dly_file()
            
            # Verify file was downloaded
            assert dly_path.exists()
            assert dly_path.name == f"{station['station_id']}.dly"
            
            # Verify file has content
            file_size = dly_path.stat().st_size
            assert file_size > 0, "Downloaded file is empty"
            print(f"Downloaded {file_size:,} bytes")
            
            # Parse the .dly file
            print("Parsing .dly file...")
            df = fetcher.parse_dly_file(dly_path)
            
            # Verify DataFrame structure
            assert isinstance(df, pd.DataFrame)
            assert list(df.columns) == ['date', 'precipitation_mm', 'tmax_c', 'tmin_c']
            
            # Verify we have substantial data
            assert len(df) > 365, "Should have at least 1 year of data"
            print(f"Parsed {len(df):,} days of data")
            
            # Verify date range
            date_range = df['date'].max() - df['date'].min()
            years = date_range.days / 365.25
            print(f"Data spans {years:.1f} years ({df['date'].min()} to {df['date'].max()})")
            
            # Verify no February 29th dates
            feb29_count = df[df['date'].apply(lambda d: d.month == 2 and d.day == 29)].shape[0]
            assert feb29_count == 0, "February 29th should be excluded"
            
            # Verify data values are reasonable for Seattle
            # (Not too strict since climate varies, but catch obvious errors)
            tmax_mean = df['tmax_c'].mean()
            tmin_mean = df['tmin_c'].mean()
            precip_mean = df['precipitation_mm'].mean()
            
            print(f"Mean Tmax: {tmax_mean:.1f}°C")
            print(f"Mean Tmin: {tmin_mean:.1f}°C")
            print(f"Mean Precip: {precip_mean:.2f} mm/day")
            
            # Seattle should have reasonable temperatures (not tropical, not arctic)
            assert -20 < tmax_mean < 40, f"Unexpected mean Tmax: {tmax_mean}°C"
            assert -30 < tmin_mean < 30, f"Unexpected mean Tmin: {tmin_mean}°C"
            assert tmax_mean > tmin_mean, "Tmax should be greater than Tmin on average"
            
            # Seattle is rainy but not extreme
            assert 0 < precip_mean < 20, f"Unexpected mean precipitation: {precip_mean} mm/day"
            
            # Save processed data
            csv_path = fetcher.save_processed_data(df)
            assert csv_path.exists()
            
            # Verify saved CSV can be read back
            df_read = pd.read_csv(csv_path)
            assert len(df_read) == len(df)
            
            print("✓ Successfully downloaded and parsed real GHCN data")
    
    def test_end_to_end_parameter_generation(self):
        """Test complete workflow: download → parse → generate parameters.
        
        This test verifies the entire pipeline works with real data:
        1. Download GHCN data
        2. Parse to observed climate CSV
        3. Generate WGEN parameters
        4. Save parameters to CSV
        5. Verify parameters can be parsed back
        
        This is the most comprehensive integration test.
        """
        station = TEST_STATIONS['seattle']
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            print(f"\nEnd-to-end test with {station['name']}")
            
            # Step 1: Download and parse GHCN data
            print("\n1. Downloading GHCN data...")
            fetcher = GHCNDataFetcher(station['station_id'], tmpdir)
            dly_path = fetcher.download_dly_file()
            
            print("2. Parsing .dly file...")
            df = fetcher.parse_dly_file(dly_path)
            
            print("3. Saving observed climate data...")
            observed_csv = fetcher.save_processed_data(df)
            
            # Step 2: Generate WGEN parameters
            print("\n4. Generating WGEN parameters...")
            generator = WGENParameterGenerator(
                observed_data_path=observed_csv,
                latitude=station['latitude'],
                output_dir=tmpdir
            )
            
            params = generator.generate_all_parameters(has_solar_data=False)
            
            # Verify all required parameters are present
            required_params = [
                'pww', 'pwd', 'alpha', 'beta',  # Precipitation
                'txmd', 'atx', 'txmw', 'tn', 'atn',  # Temperature
                'cvtx', 'acvtx', 'cvtn', 'acvtn',  # CV
                'rmd', 'rmw', 'ar',  # Solar
                'latitude'  # Location
            ]
            
            for param in required_params:
                assert param in params, f"Missing parameter: {param}"
            
            # Verify monthly parameters have 12 values
            for param in ['pww', 'pwd', 'alpha', 'beta']:
                assert len(params[param]) == 12, f"{param} should have 12 monthly values"
            
            # Verify parameter values are reasonable
            # PWW and PWD should be probabilities
            for i in range(12):
                assert 0 <= params['pww'][i] <= 1, f"PWW[{i}] out of range"
                assert 0 <= params['pwd'][i] <= 1, f"PWD[{i}] out of range"
                assert params['alpha'][i] > 0, f"Alpha[{i}] should be positive"
                assert params['beta'][i] > 0, f"Beta[{i}] should be positive"
            
            print(f"   Generated {len(required_params)} parameter sets")
            print(f"   PWW range: {min(params['pww']):.3f} - {max(params['pww']):.3f}")
            print(f"   Tmax mean: {params['txmd']:.1f}°C")
            
            # Step 3: Save parameters to CSV
            print("\n5. Saving parameters to CSV...")
            params_csv = generator.save_parameters_to_csv(params)
            assert params_csv.exists()
            
            # Step 4: Verify parameters can be parsed back
            print("6. Verifying CSV can be parsed...")
            parsed_params = CSVWGENParamsParser.parse(str(params_csv))
            
            # Verify round-trip preservation
            assert len(parsed_params.pww) == 12
            assert abs(parsed_params.pww[0] - params['pww'][0]) < 1e-5
            assert abs(parsed_params.txmd - params['txmd']) < 1e-5
            assert abs(parsed_params.latitude - station['latitude']) < 1e-5
            
            print("\n✓ Complete end-to-end workflow successful!")
            print(f"   Processed {len(df):,} days of data")
            print(f"   Generated parameters saved to: {params_csv.name}")
    
    def test_multiple_stations(self):
        """Test that the system works with different climate stations.
        
        This verifies the system handles different climates correctly:
        - Seattle: Maritime, rainy
        - Denver: Continental, dry, high elevation
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            for station_key, station in TEST_STATIONS.items():
                print(f"\n{'='*70}")
                print(f"Testing {station['name']}")
                print('='*70)
                
                # Create subdirectory for this station
                station_dir = tmpdir / station_key
                station_dir.mkdir()
                
                # Download and parse
                fetcher = GHCNDataFetcher(station['station_id'], station_dir)
                dly_path = fetcher.download_dly_file()
                df = fetcher.parse_dly_file(dly_path)
                observed_csv = fetcher.save_processed_data(df)
                
                # Generate parameters
                generator = WGENParameterGenerator(
                    observed_data_path=observed_csv,
                    latitude=station['latitude'],
                    output_dir=station_dir
                )
                params = generator.generate_all_parameters(has_solar_data=False)
                params_csv = generator.save_parameters_to_csv(params)
                
                # Verify parameters are reasonable for this climate
                print(f"  Data period: {df['date'].min()} to {df['date'].max()}")
                print(f"  Mean Tmax: {df['tmax_c'].mean():.1f}°C")
                print(f"  Mean Precip: {df['precipitation_mm'].mean():.2f} mm/day")
                print(f"  Parameters saved: {params_csv.name}")
                
                # Basic sanity checks
                assert params_csv.exists()
                assert len(params['pww']) == 12
                assert all(0 <= p <= 1 for p in params['pww'])
                
                print(f"  ✓ {station_key} successful")
    
    def test_cached_download(self):
        """Test that already-downloaded files are reused (not re-downloaded).
        
        This verifies the caching behavior works correctly.
        """
        station = TEST_STATIONS['seattle']
        
        with tempfile.TemporaryDirectory() as tmpdir:
            print(f"\nTesting download caching")
            
            # First download
            fetcher1 = GHCNDataFetcher(station['station_id'], tmpdir)
            dly_path1 = fetcher1.download_dly_file()
            
            # Record file modification time
            mtime1 = dly_path1.stat().st_mtime
            
            # Second "download" should use cached file
            fetcher2 = GHCNDataFetcher(station['station_id'], tmpdir)
            dly_path2 = fetcher2.download_dly_file()
            
            # Should be same file
            assert dly_path1 == dly_path2
            
            # Modification time should be unchanged (file not re-downloaded)
            mtime2 = dly_path2.stat().st_mtime
            assert mtime1 == mtime2, "File should not have been re-downloaded"
            
            print("✓ Cached file reused correctly")


if __name__ == "__main__":
    # Allow running this file directly for manual testing
    pytest.main([__file__, "-v", "-s", "-m", "integration"])
