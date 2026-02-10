import sys
from prophet import Prophet
import pandas as pd


def load_data():
    f2021 = "dataset/IT-NO_2021_hourly.csv"
    f2022 = "dataset/IT-NO_2022_hourly.csv"
    f2023 = "dataset/IT-NO_2023_hourly.csv"
    f2024 = "dataset/IT-NO_2024_hourly.csv"

    df1 = pd.read_csv(f2021, index_col="Datetime (UTC)", parse_dates=True)
    df2 = pd.read_csv(f2022, index_col="Datetime (UTC)", parse_dates=True)
    df3 = pd.read_csv(f2023, index_col="Datetime (UTC)", parse_dates=True)
    df4 = pd.read_csv(f2024, index_col="Datetime (UTC)", parse_dates=True)

    df = pd.concat([df1, df2, df3, df4], axis=0)
    df.sort_index(inplace=True)
    df.index.rename("timestamp", inplace=True)  # Index renaming
    df = df[["Carbon Intensity gCO₂eq/kWh (direct)"]]
    print(df.columns)
    df = df.reset_index()
    df.rename(columns={"timestamp": "ds", "Carbon Intensity gCO₂eq/kWh (direct)": "y"}, inplace=True)  # Column renaming

    return df


df = load_data()
# Add floor and cap columns
df["floor"] = 65
df["cap"] = 500


def train_and_save_model(MODEL_PATH):
    df = load_data()
    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=True,
        changepoint_prior_scale=0.05,
        seasonality_prior_scale=1.0,
    )
    model.fit(df)
    import joblib

    joblib.dump(model, MODEL_PATH)


MODEL_PATH = "prophet_model.pkl"
train_and_save_model(MODEL_PATH)
