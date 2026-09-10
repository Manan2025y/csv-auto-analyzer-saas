import pandas as pd
from app.backend.forecasting.engine import forecast_series


def test_forecast_returns_future_periods():
    df = pd.DataFrame({"date": pd.date_range("2026-01-01", periods=8, freq="MS"), "sales": [10, 12, 13, 15, 17, 18, 20, 22]})
    result = forecast_series(df, "date", "sales", periods=3)
    assert len(result["forecast"]) == 3
    assert {"date", "prediction", "lower", "upper"}.issubset(result["forecast"].columns)
