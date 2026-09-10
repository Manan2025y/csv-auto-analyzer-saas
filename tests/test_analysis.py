import pandas as pd
from app.backend.analysis.engine import analyze


def test_analysis_returns_core_sections():
    df = pd.DataFrame({"Date": ["2026-01-01", "2026-02-01", "2026-03-01"], "Revenue": [100, 150, 125], "Product": ["A", "A", "B"]})
    result = analyze(df)
    assert "business" in result
    assert "quality" in result
    assert "kpis" in result
    assert "insights" in result
