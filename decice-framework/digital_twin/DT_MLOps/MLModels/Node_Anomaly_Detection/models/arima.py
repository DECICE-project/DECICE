import pandas as pd
import numpy as np
import itertools
from statsmodels.tsa.arima.model import ARIMA
from scipy import stats
import warnings
from statsmodels.tools.sm_exceptions import ConvergenceWarning

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=ConvergenceWarning)


def preprocess_data(df, column_names=None):
    zscores = {}
    for column_name in column_names:
        # Calculate z-score for anomaly detection
        zscore = stats.zscore(df[column_name])
        zscores[column_name] = zscore
    return pd.DataFrame(zscores)


def fit_arima_model(data, order):
    model = ARIMA(data, order=order)
    model_fit = model.fit()
    return model_fit


def tune_arima_model(data, p_values, d_values, q_values):
    best_aic = np.inf
    best_order = None
    best_model = None

    # Grid search over p, d, q parameters
    for p, d, q in itertools.product(p_values, d_values, q_values):
        try:
            model = ARIMA(data, order=(p, d, q))
            model_fit = model.fit()
            aic = model_fit.aic  # Use AIC to select the best model

            if aic < best_aic:
                best_aic = aic
                best_order = (p, d, q)
                best_model = model_fit
        except Exception as e:
            continue  # Skip invalid configurations

    return best_model, best_order


def detect_anomalies_arima(df, column_names=None, p_values=[0, 1, 2], d_values=[0, 1], q_values=[0, 1, 2], threshold=1):
    anomalies = pd.DataFrame(index=df.index)
    if df.index.freq is None:
        df = df.asfreq("5s")
    for column_name in column_names:
        # Preprocess data for ARIMA model
        data = preprocess_data(df, [column_name])[column_name]

        # Tune ARIMA model and fit the best model
        best_model, best_order = tune_arima_model(data, p_values, d_values, q_values)
        residuals = best_model.resid

        # Identify anomalies based on residual errors
        anomalies[column_name + "_anomaly"] = np.abs(residuals) > threshold

    # Combine anomalies across all signals
    anomalies["combined_anomaly"] = anomalies.any(axis=1)

    # Add original columns back to the anomalies DataFrame
    for column_name in column_names:
        anomalies[column_name] = df[column_name]

    return anomalies["combined_anomaly"]
