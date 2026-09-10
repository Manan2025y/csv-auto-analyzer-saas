"""Reusable data-quality checks."""
import pandas as pd


def profile(df):
    rows, cols = df.shape
    missing = int(df.isna().sum().sum())
    duplicates = int(df.duplicated().sum())
    cells = max(rows * cols, 1)
    completeness = round((1 - missing / cells) * 100, 1)
    score = max(0, min(100, round(completeness - (duplicates / max(rows, 1)) * 10)))
    return {
        "rows": rows,
        "columns": cols,
        "missing_cells": missing,
        "duplicate_rows": duplicates,
        "completeness_pct": completeness,
        "health_score": score,
    }
