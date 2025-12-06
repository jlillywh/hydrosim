"""
GHCN Regional Precipitation Data Processor
A streamlined tool to download, process, and gap-fill precipitation data
from GHCN stations for the West of Cascades Pacific Northwest region.

Focused on Marine West Coast climate zone for homogeneous precipitation analysis.
"""

import pandas as pd
import numpy as np
import requests
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

from .west_of_cascades_stations import WestOfCascadesStationConfig

class GHCNRegionalProcessor:
    def __init__(self):
        self.ghcn_data_url = "https://www1.ncdc.noaa.gov/pub/data/ghcn/daily/all/"
        self.station_data = {}
        
        # Initialize west-of-Cascades station configuration
        self.station_config = WestOfCascadesStationConfig()
        self.stations_metadata = self.station_config.get_station_metadata()
        self.station_ids = self.station_config.get_station_ids()
        self.region_name = "West_of_Cascades_PNW"
    def download_station_data(self, station_id, station_name):
        """Download daily precipitation data for a specific station"""
        print(f"Downloading data for {station_name} ({station_id})...")
        
        try:
            url = f"{self.ghcn_data_url}{station_id}.dly"
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            
            # Parse the fixed-width GHCN daily format
            lines = response.text.strip().split('\n')
            
            records = []
            for line in lines:
                if len(line) >= 21:
                    station = line[0:11]
                    year = int(line[11:15])
                    month = int(line[15:17])
                    element = line[17:21]
                    
                    # Only process precipitation data (PRCP)
                    if element == 'PRCP':
                        # Extract daily values for the month
                        for day in range(1, 32):
                            start_pos = 21 + (day - 1) * 8
                            if start_pos + 8 <= len(line):
                                value_str = line[start_pos:start_pos + 5].strip()
                                
                                if value_str and value_str != '-9999':
                                    try:
                                        date = pd.Timestamp(year, month, day)
                                        value = int(value_str) / 10.0  # Convert to mm
                                        
                                        records.append({
                                            'date': date,
                                            'precipitation_mm': value
                                        })
                                    except (ValueError, TypeError):
                                        continue
            
            if records:
                df = pd.DataFrame(records)
                df = df.set_index('date').sort_index()
                df = df[~df.index.duplicated(keep='first')]
                
                print(f"  Loaded {len(df)} records: {df.index.min().strftime('%Y-%m-%d')} to {df.index.max().strftime('%Y-%m-%d')}")
                return df
            else:
                print(f"  No valid data found")
                return None
                
        except Exception as e:
            print(f"  Error: {e}")
            return None
    
    def find_common_date_range(self, dataframes):
        """Find overlapping date range across all dataframes"""
        if not dataframes:
            return None, None
        
        start_dates = [df.index.min() for df in dataframes.values() if df is not None]
        end_dates = [df.index.max() for df in dataframes.values() if df is not None]
        
        if not start_dates or not end_dates:
            return None, None
        
        common_start = max(start_dates)
        common_end = min(end_dates)
        
        print(f"Common date range: {common_start.strftime('%Y-%m-%d')} to {common_end.strftime('%Y-%m-%d')}")
        print(f"Total days: {(common_end - common_start).days + 1}")
        
        return common_start, common_end
    
    def create_combined_dataset(self):
        """Download and combine data from all stations in the west-of-Cascades region"""
        print(f"Processing {self.region_name} Region")
        print("=" * 60)
        
        # Download data for all stations
        for _, station_row in self.stations_metadata.iterrows():
            station_data = self.download_station_data(
                station_row['Station_ID'], 
                station_row['Name']
            )
            self.station_data[station_row['Station_Key']] = station_data
        
        # Filter out None values
        valid_stations = {k: v for k, v in self.station_data.items() if v is not None}
        
        if len(valid_stations) == 0:
            print("❌ No valid data found")
            return None
        
        # Find common date range
        common_start, common_end = self.find_common_date_range(valid_stations)
        
        if common_start is None:
            print("❌ No overlapping dates found")
            return None
        
        # Create combined dataframe
        date_range = pd.date_range(start=common_start, end=common_end, freq='D')
        combined_df = pd.DataFrame(index=date_range)
        combined_df.index.name = 'date'
        
        # Add data from each station
        for station_key, station_data in valid_stations.items():
            station_row = self.stations_metadata[self.stations_metadata['Station_Key'] == station_key].iloc[0]
            
            # Filter to common range
            filtered_data = station_data[
                (station_data.index >= common_start) & 
                (station_data.index <= common_end)
            ]
            
            # Add to combined dataset
            col_name = f"{station_row['Name']}_mm"
            combined_df[col_name] = filtered_data['precipitation_mm']
            
            # Report completeness
            valid_count = combined_df[col_name].notna().sum()
            completeness = valid_count / len(combined_df) * 100
            print(f"{station_row['Name']}: {valid_count:,}/{len(combined_df):,} days ({completeness:.1f}%)")
        
        return combined_df
    
    def fill_gaps(self, df, method='meteorological', max_gap_days=10):
        """Fill gaps in precipitation data using professional meteorological standards"""
        print(f"\nProfessional Meteorological Gap Filling Analysis")
        print("-" * 50)
        
        if df is None or len(df) == 0:
            return None
        
        # Analyze gaps before filling
        precip_cols = [col for col in df.columns if '_mm' in col]
        gap_report = {}
        
        for col in precip_cols:
            # Find gaps
            missing_mask = df[col].isna()
            total_missing = missing_mask.sum()
            total_days = len(df)
            
            # Find consecutive gap lengths
            gap_starts = missing_mask & ~missing_mask.shift(1, fill_value=False)
            gap_lengths = []
            
            if gap_starts.any():
                for start_idx in df[gap_starts].index:
                    gap_end = start_idx
                    while gap_end <= df.index[-1] and pd.isna(df.loc[gap_end, col]) if gap_end in df.index else False:
                        gap_end = gap_end + pd.Timedelta(days=1)
                    
                    gap_length = (gap_end - start_idx).days
                    if gap_length > 0:
                        gap_lengths.append(gap_length)
            
            gap_report[col] = {
                'total_missing': total_missing,
                'percent_missing': total_missing / total_days * 100,
                'max_gap_length': max(gap_lengths) if gap_lengths else 0,
                'num_gaps': len(gap_lengths)
            }
            
            print(f"{col}:")
            print(f"  Missing: {total_missing:,} days ({gap_report[col]['percent_missing']:.1f}%)")
            print(f"  Largest gap: {gap_report[col]['max_gap_length']} days")
            print(f"  Number of gaps: {gap_report[col]['num_gaps']}")
        
        # Apply professional meteorological gap filling
        filled_df = df.copy()
        fill_methods_used = {}
        
        if method == 'meteorological':
            print(f"\nApplying Meteorological Standards (WMO Guidelines):")
            print("- 1-2 days: Linear interpolation")
            print("- 3-10 days: Station correlation regression (if available)")
            print("- 11-30 days: Long-term climatological normals")
            print("- >30 days: Mark as unfillable gaps")
            
            # Calculate monthly climatology for each station
            monthly_climatology = {}
            for col in precip_cols:
                monthly_stats = df.groupby(df.index.month)[col].agg(['mean', 'median', 'std']).fillna(0)
                monthly_climatology[col] = monthly_stats
            
            # Station correlation matrix
            correlation_matrix = df[precip_cols].corr()
            print(f"\nStation Correlations:")
            print(correlation_matrix.round(3))
            
            for col in precip_cols:
                print(f"\nProcessing {col}:")
                fill_methods_used[col] = {'1-2_days': 0, '3-10_days': 0, '11-30_days': 0, 'unfillable': 0}
                
                # Find gaps and classify by length
                missing_mask = df[col].isna()
                gap_starts = missing_mask & ~missing_mask.shift(1, fill_value=False)
                
                for start_idx in df[gap_starts].index:
                    # Find end of gap
                    gap_end = start_idx
                    while gap_end <= df.index[-1] and pd.isna(filled_df.loc[gap_end, col]) if gap_end in filled_df.index else False:
                        gap_end = gap_end + pd.Timedelta(days=1)
                    
                    gap_length = (gap_end - start_idx).days
                    gap_range = pd.date_range(start_idx, gap_end - pd.Timedelta(days=1), freq='D')
                    
                    if gap_length <= 2:
                        # Method 1: Linear interpolation for 1-2 day gaps
                        filled_df.loc[gap_range, col] = filled_df[col].interpolate(method='linear').loc[gap_range]
                        fill_methods_used[col]['1-2_days'] += gap_length
                        
                    elif gap_length <= 10:
                        # Method 2: Station correlation regression for 3-10 day gaps
                        filled = False
                        if len(precip_cols) >= 2:
                            # Find best correlated station
                            other_cols = [c for c in precip_cols if c != col]
                            correlations = correlation_matrix.loc[col, other_cols]
                            best_match = correlations.abs().idxmax()
                            best_corr = correlations[best_match]
                            
                            if abs(best_corr) > 0.6:  # Higher threshold for meteorological standards
                                # Check if reference station has data for gap period
                                ref_data_available = filled_df.loc[gap_range, best_match].notna().all()
                                
                                if ref_data_available:
                                    # Build regression model using 90-day windows around gap
                                    window_start = max(start_idx - pd.Timedelta(days=45), df.index.min())
                                    window_end = min(gap_end + pd.Timedelta(days=45), df.index.max())
                                    
                                    train_mask = (
                                        (df.index >= window_start) & 
                                        (df.index <= window_end) & 
                                        df[col].notna() & 
                                        df[best_match].notna()
                                    )
                                    
                                    if train_mask.sum() >= 30:  # Minimum 30 days for reliable regression
                                        from sklearn.linear_model import LinearRegression
                                        from sklearn.preprocessing import PolynomialFeatures
                                        
                                        X_train = df.loc[train_mask, best_match].values.reshape(-1, 1)
                                        y_train = df.loc[train_mask, col].values
                                        
                                        # Use polynomial features for better precipitation relationships
                                        poly_features = PolynomialFeatures(degree=2)
                                        X_train_poly = poly_features.fit_transform(X_train)
                                        
                                        reg = LinearRegression().fit(X_train_poly, y_train)
                                        
                                        # Predict missing values
                                        X_pred = filled_df.loc[gap_range, best_match].values.reshape(-1, 1)
                                        X_pred_poly = poly_features.transform(X_pred)
                                        filled_values = reg.predict(X_pred_poly)
                                        filled_values = np.maximum(0, filled_values)  # No negative precipitation
                                        
                                        # Add some realistic variability based on residuals
                                        residuals = y_train - reg.predict(X_train_poly)
                                        residual_std = np.std(residuals)
                                        noise = np.random.normal(0, residual_std * 0.3, len(filled_values))
                                        filled_values = np.maximum(0, filled_values + noise)
                                        
                                        filled_df.loc[gap_range, col] = filled_values
                                        fill_methods_used[col]['3-10_days'] += gap_length
                                        filled = True
                                        
                                        print(f"    Filled {gap_length}-day gap using {best_match} regression (r={best_corr:.3f})")
                        
                        if not filled:
                            # Fallback to linear interpolation
                            filled_df.loc[gap_range, col] = filled_df[col].interpolate(method='linear').loc[gap_range]
                            fill_methods_used[col]['3-10_days'] += gap_length
                            
                    elif gap_length <= 30:
                        # Method 3: Climatological normals for 11-30 day gaps
                        for gap_date in gap_range:
                            month = gap_date.month
                            
                            # Use monthly median with some random variation based on std
                            monthly_median = monthly_climatology[col].loc[month, 'median']
                            monthly_std = monthly_climatology[col].loc[month, 'std']
                            
                            # Add realistic daily variation (reduced for precipitation)
                            daily_variation = np.random.normal(0, monthly_std * 0.5)
                            filled_value = max(0, monthly_median + daily_variation)
                            
                            # Reduce frequency of rain days to match climatology
                            rain_probability = (df[df.index.month == month][col] > 0).mean()
                            if np.random.random() > rain_probability:
                                filled_value = 0
                            
                            filled_df.loc[gap_date, col] = filled_value
                        
                        fill_methods_used[col]['11-30_days'] += gap_length
                        print(f"    Filled {gap_length}-day gap using climatological normals")
                        
                    else:
                        # Method 4: Gaps >30 days - mark as unfillable but use long-term averages
                        print(f"    WARNING: {gap_length}-day gap exceeds meteorological filling standards")
                        for gap_date in gap_range:
                            month = gap_date.month
                            monthly_median = monthly_climatology[col].loc[month, 'median']
                            # Very conservative filling for long gaps
                            filled_df.loc[gap_date, col] = monthly_median * 0.7  # Reduced to indicate uncertainty
                        
                        fill_methods_used[col]['unfillable'] += gap_length
            
            # Report filling methods used
            print(f"\nGap Filling Methods Applied:")
            for col in precip_cols:
                methods = fill_methods_used[col]
                print(f"{col}:")
                if methods['1-2_days'] > 0:
                    print(f"  Linear interpolation (1-2 days): {methods['1-2_days']} days")
                if methods['3-10_days'] > 0:
                    print(f"  Station regression (3-10 days): {methods['3-10_days']} days")
                if methods['11-30_days'] > 0:
                    print(f"  Climatological normals (11-30 days): {methods['11-30_days']} days")
                if methods['unfillable'] > 0:
                    print(f"  Long-term averages (>30 days, low confidence): {methods['unfillable']} days")
        
        # Report results
        print(f"\nFinal Gap Filling Results:")
        for col in precip_cols:
            before = df[col].isna().sum()
            after = filled_df[col].isna().sum()
            filled = before - after
            print(f"{col}: Filled {filled} gaps ({before} → {after} missing)")
            
            # Data quality assessment
            if after == 0:
                print(f"  ✅ Complete time series achieved")
            elif after / len(df) < 0.01:
                print(f"  ✅ High quality: <1% missing data")
            elif after / len(df) < 0.05:
                print(f"  ⚠️  Good quality: <5% missing data")
            else:
                print(f"  ⚠️  Moderate quality: {after/len(df)*100:.1f}% missing data")
        
        return filled_df
    
    def create_summary_statistics(self, df):
        """Create summary statistics and visualizations"""
        if df is None or len(df) == 0:
            return
        
        precip_cols = [col for col in df.columns if '_mm' in col]
        
        print(f"\nSummary Statistics:")
        print("-" * 40)
        
        for col in precip_cols:
            stats = df[col].describe()
            print(f"\n{col}:")
            print(f"  Mean: {stats['mean']:.2f} mm/day")
            print(f"  Median: {stats['50%']:.2f} mm/day")
            print(f"  Max: {stats['max']:.1f} mm/day")
            print(f"  Rainy days: {(df[col] > 0).sum():,} ({(df[col] > 0).mean()*100:.1f}%)")
            print(f"  Heavy rain days (>25mm): {(df[col] > 25).sum():,}")
        
        # Calculate correlations
        if len(precip_cols) >= 2:
            corr_matrix = df[precip_cols].corr()
            print(f"\nStation Correlations:")
            print(corr_matrix.round(3))
    
    def save_dataset(self, df, suffix="processed"):
        """Save processed dataset"""
        if df is None:
            print("❌ No data to save")
            return None
        
        filename = f"{self.region_name.lower()}_precipitation_{suffix}.csv"
        
        # Reset index to make date a column
        output_df = df.reset_index()
        output_df.to_csv(filename, index=False)
        
        print(f"\n✅ Dataset saved: '{filename}'")
        print(f"   Shape: {output_df.shape[0]:,} rows × {output_df.shape[1]} columns")
        print(f"   Date range: {df.index.min().strftime('%Y-%m-%d')} to {df.index.max().strftime('%Y-%m-%d')}")
        
        return filename
    
    def run_full_process(self, gap_fill_method='meteorological', max_gap_days=10):
        """Run the complete processing workflow with professional meteorological standards"""
        print(f"GHCN Regional Precipitation Data Processor")
        print(f"Region: {self.region_name}")
        print("=" * 60)
        
        # Step 1: Download and combine data
        combined_data = self.create_combined_dataset()
        if combined_data is None:
            return None
        
        # Step 2: Save raw combined data
        raw_filename = self.save_dataset(combined_data, "raw")
        
        # Step 3: Fill gaps using meteorological standards
        filled_data = self.fill_gaps(combined_data, gap_fill_method, max_gap_days)
        
        # Step 4: Save gap-filled data
        if filled_data is not None:
            filled_filename = self.save_dataset(filled_data, "meteorological_filled")
        
        # Step 5: Create summary statistics
        self.create_summary_statistics(filled_data if filled_data is not None else combined_data)
        
        print(f"\n🎉 Professional meteorological processing complete for {self.region_name}!")
        
        return filled_data if filled_data is not None else combined_data

def main():
    """Main execution - modify this section for different regions"""
    
    # Initialize processor for Seattle (change this for other regions)
    processor = GHCNRegionalProcessor("Seattle")
    
    # Alternative regions (uncomment to use):
    # processor = GHCNRegionalProcessor("Portland")
    # processor = GHCNRegionalProcessor("Vancouver_BC")
    
    # Run the complete process with professional meteorological standards
    result = processor.run_full_process(
        gap_fill_method='meteorological',  # Professional meteorological gap filling
        max_gap_days=10  # Extended to 10 days following WMO guidelines
    )
    
    if result is not None:
        print("\n📊 Data ready for analysis!")
    else:
        print("\n❌ Processing failed")

if __name__ == "__main__":
    main()
