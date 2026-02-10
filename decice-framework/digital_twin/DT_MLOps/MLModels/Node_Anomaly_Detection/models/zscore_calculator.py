import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
from datetime import datetime


def calculate_zscores(df, cols=[]):
    df1 = df.copy()
    # Calculate z-scores for each column (signal)
    for col in cols:
        if col != "datetime":  # Skip datetime column
            zscore_col = col + "_zscore"
            df1[zscore_col] = stats.zscore(df1[col])

    # Identify anomalies for each signal
    for col in df1.columns:
        if "_zscore" in col:
            anomaly_col = col.replace("_zscore", "_anomaly")
            df1[anomaly_col] = df1[col].abs() > 3  # Threshold of 3 for anomaly detection

    # Create combined anomaly signal
    anomaly_cols = [col for col in df1.columns if "_anomaly" in col]
    df1["combined_anomaly"] = df1[anomaly_cols[:3]].any(axis=1).astype(bool)  # 1 if any anomaly, otherwise 0

    return df1["combined_anomaly"]
