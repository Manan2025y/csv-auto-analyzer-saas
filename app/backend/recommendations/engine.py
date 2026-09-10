"""Actionable recommendations derived from analysis results."""


def generate_recommendations(result):
    recommendations = []
    quality = result.get("quality", {})
    if quality.get("missing_cells", 0):
        recommendations.append("Review columns with missing values before using them for critical KPIs.")
    if quality.get("duplicate_rows", 0):
        recommendations.append("Check duplicate rows to avoid overstating totals and order counts.")
    for col, count in list((result.get("outliers") or {}).items())[:3] if isinstance(result.get("outliers"), dict) else []:
        recommendations.append(f"Review unusual values in {col} ({count:,} potential outliers).")
    if not recommendations:
        recommendations.append("Data quality looks suitable for exploratory analysis; validate business definitions before making decisions.")
    return recommendations
