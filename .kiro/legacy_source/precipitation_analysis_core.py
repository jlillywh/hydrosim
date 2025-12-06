"""
Core Precipitation Analysis Module
Reusable functions for PWW/PWD analysis across all regions
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

def calculate_pww_pwd(precip_series):
    """
    Calculate PWW and PWD probabilities for a precipitation time series
    
    PWW (Probability of Wet day following Wet day) = NWW / (NWW + NDW)
    PWD (Probability of Wet day following Dry day) = NWD / (NWD + NDD)
    
    Parameters:
    -----------
    precip_series : pandas.Series
        Daily precipitation values with datetime index
        
    Returns:
    --------
    tuple : (PWW, PWD)
        PWW and PWD probabilities, or (NaN, NaN) if insufficient data
    """
    
    if len(precip_series) < 2:
        return np.nan, np.nan
    
    # Define wet/dry days (wet > 0 mm)
    wet_days = (precip_series > 0).astype(int)
    
    if len(wet_days.unique()) < 2:
        # All days are either wet or dry - no transitions possible
        return np.nan, np.nan
    
    # Calculate transition counts
    NWW = 0  # Wet followed by Wet
    NDW = 0  # Wet followed by Dry
    NWD = 0  # Dry followed by Wet
    NDD = 0  # Dry followed by Dry
    
    for i in range(len(wet_days) - 1):
        today = wet_days.iloc[i]
        tomorrow = wet_days.iloc[i + 1]
        
        if today == 1 and tomorrow == 1:    # Wet -> Wet
            NWW += 1
        elif today == 1 and tomorrow == 0:  # Wet -> Dry
            NDW += 1
        elif today == 0 and tomorrow == 1:  # Dry -> Wet
            NWD += 1
        elif today == 0 and tomorrow == 0:  # Dry -> Dry
            NDD += 1
    
    # Calculate probabilities
    total_wet_days = NWW + NDW
    total_dry_days = NWD + NDD
    
    PWW = NWW / total_wet_days if total_wet_days > 0 else np.nan
    PWD = NWD / total_dry_days if total_dry_days > 0 else np.nan
    
    return PWW, PWD

def calculate_decadal_monthly_probabilities(df, region_name):
    """
    Calculate PWW and PWD probabilities for each month within each decade
    
    Parameters:
    -----------
    df : pandas.DataFrame
        Daily precipitation data with datetime index and station columns
    region_name : str
        Name of the region for labeling
        
    Returns:
    --------
    pandas.DataFrame
        Decadal monthly probabilities
    """
    print(f"Calculating decadal monthly PWW/PWD probabilities for {region_name}...")
    
    # Get precipitation columns
    precip_cols = [col for col in df.columns if '_mm' in col or 'PRCP_mm' in col]
    
    # Determine decade boundaries
    start_year = df.index.min().year
    end_year = df.index.max().year
    
    # Round to nearest decades for cleaner analysis
    decade_start = (start_year // 10) * 10
    decade_end = ((end_year // 10) + 1) * 10
    
    print(f"Analysis period: {decade_start} to {decade_end}")
    print(f"Available data: {start_year} to {end_year}")
    
    results = []
    months = range(1, 13)
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    for col in precip_cols:
        station_name = col.replace('_mm', '').replace('_PRCP_mm', '')
        print(f"  Processing {station_name}...")
        
        for decade_start_year in range(decade_start, decade_end, 10):
            decade_end_year = decade_start_year + 9
            
            # Filter data for this decade
            decade_mask = (
                (df.index.year >= decade_start_year) & 
                (df.index.year <= decade_end_year)
            )
            decade_data = df[decade_mask]
            
            if len(decade_data) == 0:
                continue
                
            for month in months:
                # Filter data for this month within the decade
                month_mask = decade_data.index.month == month
                month_data = decade_data[month_mask][col].dropna()
                
                if len(month_data) >= 10:  # Minimum data requirement
                    PWW, PWD = calculate_pww_pwd(month_data)
                    
                    results.append({
                        'Region': region_name,
                        'Station_ID': station_name,
                        'Decade_Start_Year': decade_start_year,
                        'Month': month,
                        'Month_Name': month_names[month-1],
                        'PWW': PWW,
                        'PWD': PWD,
                        'Data_Points': len(month_data)
                    })
    
    df_results = pd.DataFrame(results)
    print(f"✅ Calculated {len(df_results)} monthly probability values for {region_name}")
    
    return df_results

def calculate_monthly_trends(df_probs):
    """
    Calculate linear trends for PWW and PWD by month
    
    Parameters:
    -----------
    df_probs : pandas.DataFrame
        Decadal monthly probabilities
        
    Returns:
    --------
    pandas.DataFrame
        Trend analysis results
    """
    
    trend_results = []
    
    for region in df_probs['Region'].unique():
        region_data = df_probs[df_probs['Region'] == region]
        
        for station in region_data['Station_ID'].unique():
            station_data = region_data[region_data['Station_ID'] == station]
            
            for month in range(1, 13):
                month_data = station_data[station_data['Month'] == month]
                
                if len(month_data) >= 3:  # Need at least 3 decades for trend
                    decades = month_data['Decade_Start_Year'].values
                    
                    # PWW trend analysis
                    pww_valid = month_data['PWW'].dropna()
                    if len(pww_valid) >= 3:
                        valid_decades_pww = month_data.loc[pww_valid.index, 'Decade_Start_Year'].values
                        pww_slope, pww_intercept = np.polyfit(valid_decades_pww, pww_valid, 1)
                        pww_trend_total = pww_slope * (valid_decades_pww.max() - valid_decades_pww.min())
                        
                        # Calculate R-squared for trend strength
                        pww_predicted = pww_slope * valid_decades_pww + pww_intercept
                        pww_ss_res = np.sum((pww_valid - pww_predicted) ** 2)
                        pww_ss_tot = np.sum((pww_valid - np.mean(pww_valid)) ** 2)
                        pww_r_squared = 1 - (pww_ss_res / pww_ss_tot) if pww_ss_tot > 0 else 0
                    else:
                        pww_slope = np.nan
                        pww_trend_total = np.nan
                        pww_r_squared = np.nan
                    
                    # PWD trend analysis
                    pwd_valid = month_data['PWD'].dropna()
                    if len(pwd_valid) >= 3:
                        valid_decades_pwd = month_data.loc[pwd_valid.index, 'Decade_Start_Year'].values
                        pwd_slope, pwd_intercept = np.polyfit(valid_decades_pwd, pwd_valid, 1)
                        pwd_trend_total = pwd_slope * (valid_decades_pwd.max() - valid_decades_pwd.min())
                        
                        # Calculate R-squared for trend strength
                        pwd_predicted = pwd_slope * valid_decades_pwd + pwd_intercept
                        pwd_ss_res = np.sum((pwd_valid - pwd_predicted) ** 2)
                        pwd_ss_tot = np.sum((pwd_valid - np.mean(pwd_valid)) ** 2)
                        pwd_r_squared = 1 - (pwd_ss_res / pwd_ss_tot) if pwd_ss_tot > 0 else 0
                    else:
                        pwd_slope = np.nan
                        pwd_trend_total = np.nan
                        pwd_r_squared = np.nan
                    
                    # Determine significance (combination of magnitude and R-squared)
                    pww_significant = (abs(pww_trend_total) > 0.05) and (pww_r_squared > 0.3) if not np.isnan(pww_trend_total) else False
                    pwd_significant = (abs(pwd_trend_total) > 0.05) and (pwd_r_squared > 0.3) if not np.isnan(pwd_trend_total) else False
                    
                    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
                    
                    trend_results.append({
                        'Region': region,
                        'Station_ID': station,
                        'Month': month,
                        'Month_Name': month_names[month-1],
                        'PWW_Slope_per_decade': pww_slope,
                        'PWW_Total_Change': pww_trend_total,
                        'PWW_R_Squared': pww_r_squared,
                        'PWW_Significant': pww_significant,
                        'PWD_Slope_per_decade': pwd_slope,
                        'PWD_Total_Change': pwd_trend_total,
                        'PWD_R_Squared': pwd_r_squared,
                        'PWD_Significant': pwd_significant,
                        'Decades_Available': len(month_data)
                    })
    
    return pd.DataFrame(trend_results)

def identify_significant_trends(trend_df, min_change=0.05, min_r_squared=0.3):
    """
    Identify and summarize significant trends across all regions
    
    Parameters:
    -----------
    trend_df : pandas.DataFrame
        Trend analysis results
    min_change : float
        Minimum total change to consider significant
    min_r_squared : float
        Minimum R-squared to consider trend reliable
        
    Returns:
    --------
    dict
        Summary of significant trends
    """
    
    # Filter for significant trends
    pww_trends = trend_df[
        (abs(trend_df['PWW_Total_Change']) >= min_change) & 
        (trend_df['PWW_R_Squared'] >= min_r_squared) &
        (trend_df['PWW_Significant'] == True)
    ].copy()
    
    pwd_trends = trend_df[
        (abs(trend_df['PWD_Total_Change']) >= min_change) & 
        (trend_df['PWD_R_Squared'] >= min_r_squared) &
        (trend_df['PWD_Significant'] == True)
    ].copy()
    
    # Add trend direction
    pww_trends['Trend_Direction'] = pww_trends['PWW_Total_Change'].apply(lambda x: 'Increasing' if x > 0 else 'Decreasing')
    pwd_trends['Trend_Direction'] = pwd_trends['PWD_Total_Change'].apply(lambda x: 'Increasing' if x > 0 else 'Decreasing')
    
    summary = {
        'pww_significant_trends': len(pww_trends),
        'pwd_significant_trends': len(pwd_trends),
        'pww_trends_detail': pww_trends[['Region', 'Station_ID', 'Month_Name', 'PWW_Total_Change', 'PWW_R_Squared', 'Trend_Direction']],
        'pwd_trends_detail': pwd_trends[['Region', 'Station_ID', 'Month_Name', 'PWD_Total_Change', 'PWD_R_Squared', 'Trend_Direction']],
        'months_with_trends': set(list(pww_trends['Month_Name']) + list(pwd_trends['Month_Name'])),
        'regions_with_trends': set(list(pww_trends['Region']) + list(pwd_trends['Region']))
    }
    
    return summary

def apply_data_quality_control(df_raw, df_filled, region_name, min_completeness=0.7):
    """
    Apply data quality control to identify and exclude problematic years
    
    Parameters:
    -----------
    df_raw : pandas.DataFrame
        Raw precipitation data
    df_filled : pandas.DataFrame  
        Gap-filled precipitation data
    region_name : str
        Name of the region
    min_completeness : float
        Minimum data completeness required
        
    Returns:
    --------
    tuple : (df_clean, quality_report)
        Clean dataset and quality assessment
    """
    
    print(f"Applying data quality control for {region_name}...")
    
    annual_stats = []
    
    for year in range(df_filled.index.year.min(), df_filled.index.year.max() + 1):
        # Filled data stats
        filled_year = df_filled[df_filled.index.year == year]
        if len(filled_year) > 0:
            col_name = filled_year.columns[0]
            filled_total = filled_year[col_name].sum()
            filled_wet_days = (filled_year[col_name] > 0).sum()
            filled_unique_values = len(filled_year[col_name].unique())
            
            # Raw data completeness
            raw_year = df_raw[df_raw.index.year == year]
            if len(raw_year) > 0:
                raw_col = raw_year.columns[0]
                missing_count = raw_year[raw_col].isna().sum()
                completeness = 1 - (missing_count / len(raw_year))
            else:
                completeness = 0
            
            # Quality scoring
            quality_score = 1.0
            flags = []
            
            if completeness < min_completeness:
                flags.append("LOW_COMPLETENESS")
                quality_score *= 0.3
            
            if filled_wet_days > 366:  # Impossible wet days
                flags.append("IMPOSSIBLE_WET_DAYS")
                quality_score = 0
            
            if filled_total < 50:  # Unrealistically low precipitation
                flags.append("UNREALISTIC_LOW_PRECIP")
                quality_score *= 0.2
            
            if filled_unique_values < 10:  # Too few unique values
                flags.append("LOW_VARIABILITY")
                quality_score *= 0.5
            
            annual_stats.append({
                'Year': year,
                'Completeness': completeness,
                'Quality_Score': quality_score,
                'Flags': ', '.join(flags) if flags else 'GOOD',
                'Include': quality_score >= 0.7
            })
    
    quality_df = pd.DataFrame(annual_stats)
    good_years = quality_df[quality_df['Include']]['Year'].tolist()
    
    # Filter dataset
    df_clean = df_filled[df_filled.index.year.isin(good_years)].copy()
    
    print(f"  Quality assessment: {len(good_years)}/{len(quality_df)} years retained")
    
    return df_clean, quality_df
