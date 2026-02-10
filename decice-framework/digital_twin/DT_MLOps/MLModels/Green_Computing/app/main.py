from fastapi import FastAPI, Query
from app.model import load_model, make_forecast_from_now, make_forecast_from_range
from datetime import datetime
import pandas as pd

app = FastAPI()


# health check endpoint
@app.get("/")
def health_check():
    return {"status": "ok", "message": "Carbon Intensity Forecasting API is running."}


@app.get("/predictday")
def predict_day():
    model = load_model()
    forecast = make_forecast_from_now(model=model, periods=24)
    return forecast.to_dict(orient="records")


@app.get("/predictweek")
def predict_week():
    model = load_model()
    forecast = make_forecast_from_now(model=model, periods=168)
    return forecast.to_dict(orient="records")


@app.get("/predictmonth")
def predict_month():
    model = load_model()
    forecast = make_forecast_from_now(model=model, periods=720)
    return forecast.to_dict(orient="records")


@app.get("/predictrange")
def predict_range(start: str = Query(...), end: str = Query(...)):
    """
    Example: /predictrange?start=2025-08-01T00:00:00&end=2025-08-07T23:00:00
    """
    try:
        start_dt = pd.to_datetime(start).round("H")
        end_dt = pd.to_datetime(end).round("H")
        if end_dt <= start_dt:
            return {"error": "End time must be after start time."}
        model = load_model()
        forecast = make_forecast_from_range(model, start=start_dt, end=end_dt)
        return forecast.to_dict(orient="records")
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
