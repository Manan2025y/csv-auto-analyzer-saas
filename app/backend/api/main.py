"""Small FastAPI service exposing the analysis engine.

The same backend can later sit behind a React/Next.js frontend and a
managed database/object store. The Streamlit UI remains useful as the
admin/developer interface during development.
"""
from io import BytesIO
import pandas as pd
from fastapi import FastAPI, File, UploadFile, HTTPException
from ..analysis.engine import analyze
from ..ecommerce.rules import detect_ecommerce_platform

app = FastAPI(title="CSV Auto-Analyzer API", version="4.0.0")
MAX_UPLOAD_BYTES = 25 * 1024 * 1024


@app.get("/health")
def health():
    return {"status": "ok", "service": "csv-auto-analyzer"}


@app.post("/v1/analyze")
async def analyze_csv(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")
    try:
        raw = await file.read()
        if len(raw) > MAX_UPLOAD_BYTES:
            raise ValueError("CSV exceeds the 25 MB API upload limit")
        df = pd.read_csv(BytesIO(raw))
        if df.empty:
            raise ValueError("CSV contains no rows")
        result = analyze(df)
        platform, amazon_score, walmart_score = detect_ecommerce_platform(df.columns)
        result["platform"] = platform
        result["platform_scores"] = {"amazon": amazon_score, "walmart": walmart_score}
        # Convert DataFrames to JSON-safe records for the API.
        result["business"] = result["business"].to_dict(orient="records")
        return result
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
