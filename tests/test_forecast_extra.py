import pandas as pd
from app.backend.forecasting.engine import forecast_series

def test_forecast_reports_horizon_and_model_scores():
    df=pd.DataFrame({"Date":pd.date_range("2024-01-01",periods=18,freq="MS"),"Sales":[100+i*3 for i in range(18)]})
    out=forecast_series(df,"Date","Sales",6,"MS","Auto")
    assert len(out["forecast"])==6
    assert out["diagnostics"]["forecast_periods"]==6
    assert out["diagnostics"]["model_scores"]
