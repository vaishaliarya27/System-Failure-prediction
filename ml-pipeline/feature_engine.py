# feature_engine.py

import pandas as pd
import numpy as np
import sys 

# =================================================================
# 1. CONFIGURATION: ADJUST THESE VALUES BASED ON YOUR DATA
# =================================================================

# 1.1 File Paths
RAW_DATA_PATH = 'raw_system_logs.csv' 
FINAL_DATA_PATH = 'prepared_data.csv'

# 1.2 Column Names (MUST match the columns in your raw_system_logs.csv file)
TIME_COLUMN = 'timestamp'             
FAILURE_INDICATOR_COLUMN = 'is_failed' 
CORE_METRIC_COLUMN = 'sensor_A'       

# 1.3 Feature Logic
FAILURE_WINDOW_HOURS = 24  # W: How many hours *before* failure should we warn?
ROLLING_WINDOW_HOURS = 4   # The window size for calculating mean/max features

# =================================================================
# 2. DATA LOADING AND INITIAL CHECKS (FIXED for DatetimeIndex)
# =================================================================

try:
    print(f"Loading raw data from: {RAW_DATA_PATH}")
    
    # Load data
    df = pd.read_csv(RAW_DATA_PATH)
    
    # **CRITICAL FIX:** Explicitly convert the time column to datetime objects
    df[TIME_COLUMN] = pd.to_datetime(df[TIME_COLUMN]) 
    
    # Set the time column as the index and ensure it's sorted
    df = df.set_index(TIME_COLUMN).sort_index()

    # Check for required columns
    required_cols = [FAILURE_INDICATOR_COLUMN, CORE_METRIC_COLUMN]
    if not all(col in df.columns for col in required_cols):
        print("\nFATAL ERROR: Missing one or more required columns.")
        print(f"Required columns based on config: {required_cols}")
        print(f"Columns in your file: {list(df.columns)}")
        sys.exit()

except FileNotFoundError:
    print(f"\nFATAL ERROR: The raw data file '{RAW_DATA_PATH}' was not found.")
    print("Please ensure you have created this file and placed it in the project root.")
    sys.exit()


# =================================================================
# 3. FEATURE ENGINEERING (Rolling Windows)
# =================================================================

print(f"Creating rolling window features over {ROLLING_WINDOW_HOURS} hours...")
rolling_window_str = f'{ROLLING_WINDOW_HOURS}H'

# Create rolling mean and max features for the core metric
# closed='left' ensures we use only PAST data (prevents data leakage)
df[f'{CORE_METRIC_COLUMN}_mean_{ROLLING_WINDOW_HOURS}h'] = \
    df[CORE_METRIC_COLUMN].rolling(window=rolling_window_str, closed='left').mean()

df[f'{CORE_METRIC_COLUMN}_max_{ROLLING_WINDOW_HOURS}h'] = \
    df[CORE_METRIC_COLUMN].rolling(window=rolling_window_str, closed='left').max()

# Fill the initial NaN values (where the rolling window hasn't accumulated enough data) with 0
df = df.fillna(0)


# =================================================================
# 4. TARGET LABELING (Creating the 'will_fail' column)
# =================================================================

print(f"Creating the 'will_fail' target label with {FAILURE_WINDOW_HOURS}h warning...")

# Look ahead for a failure: This creates a Series that is 1 if a failure occurs 
# *at or after* the current timestamp.
future_failures = df[FAILURE_INDICATOR_COLUMN].shift(-1) 

# Check the maximum failure indicator over the next N hours. 
failure_lookahead_window = f'{FAILURE_WINDOW_HOURS}H'
df['will_fail'] = future_failures.rolling(
    window=failure_lookahead_window, min_periods=1
).max().fillna(0).astype(int)


# =================================================================
# 5. FINAL CLEANUP AND SAVE
# =================================================================

# Drop the original failure indicator, as it is a raw label, not a feature.
final_df = df.drop(columns=[FAILURE_INDICATOR_COLUMN]) 

final_df.to_csv(FINAL_DATA_PATH, index=True)

print(f"\n--- SUCCESS: FEATURE ENGINEERING COMPLETE ---")
print(f"Prepared data saved to {FINAL_DATA_PATH}.")
print(f"Final shape: {final_df.shape}")
print("You are now ready to run 'python train_model.py'.")