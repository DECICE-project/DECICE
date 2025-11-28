from datetime import datetime, timedelta
import pandas as pd
from matplotlib import pyplot as plt

MODEL_PATH = "app/prophet_model.pkl"

def load_model():
    import joblib
    return joblib.load(MODEL_PATH)

def make_forecast_from_now(model, periods=168):
    now = pd.Timestamp.now().round('H')  # round to nearest hour
    future = pd.date_range(start=now, periods=periods+1, freq='H')  # +1 for inclusive
    future_df = pd.DataFrame({'ds': future})
    forecast = model.predict(future_df)
    forecast['yhat'] = forecast['yhat'].clip(lower=10)
    # forecast['yhat_lower'] = forecast['yhat_lower'].clip(lower=10)
    # forecast['yhat_upper'] = forecast['yhat_upper'].clip(lower=10)
    forecast = forecast[['ds', 'yhat']]
    forecast = forecast.rename(columns={'ds': 'timestamp', 'yhat': 'ci'})
    return forecast


def make_forecast_from_range(model, start: pd.Timestamp, end: pd.Timestamp):
    future = pd.date_range(start=start, end=end, freq='H')
    future_df = pd.DataFrame({'ds': future})
    forecast = model.predict(future_df)
    forecast['yhat'] = forecast['yhat'].clip(lower=10)
    forecast = forecast[['ds', 'yhat']]
    forecast = forecast.rename(columns={'ds': 'timestamp', 'yhat': 'ci'})
    return forecast
