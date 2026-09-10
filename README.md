# CSV Auto-Analyzer — Global SaaS Release Candidate

A business intelligence web application that turns CSV files into explainable dashboards, KPIs, charts, data-quality findings, recommendations and practical forecasts.

## What is fixed / included

- Robust Data Intelligence: no ambiguous pandas DataFrame truth-value checks.
- Business-semantic column classification for general business and e-commerce data.
- Amazon/Walmart signal detection.
- Automatic dashboard with **8+ charts** and responsive layout.
- Chart Studio with Add Chart, Hide Settings, Add to Dashboard, delete, compare, slicers/filters, ranking and 12 distinct colour palettes.
- Chart types: bar, line, area, scatter, pie, donut, treemap, histogram, box, funnel, table and card.
- Custom chart background colour.
- KPI Studio with Add KPI, Hide Settings, Add to Dashboard, delete, colour and formula support.
- Formula functions: `SUM`, `AVG`, `AVERAGE`, `MIN`, `MAX`, `MEDIAN`, `COUNT`, `UNIQUE` plus arithmetic.
- Custom KPI background colour and number/currency/percent formatting.
- Dashboard background, card background and chart background controls.
- Day, Night, Soft Light and Midnight Blue themes with readable text contrast.
- 30+ currency display options.
- Data Q&A for deterministic questions about totals, averages, counts, unique values, missing data, min/max and dataset size.
- Forecasting with Auto model selection, holdout comparison, multiple methods, explicit forecast horizon, historical/forecast boundary connector and uncertainty band.
- Saved dashboard persistence foundation.
- PDF and Excel reports.
- FastAPI backend for programmatic access.
- Docker deployment support.

## Local development

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Public web deployment

Users do **not** need Python or VS Code after deployment. Deploy the GitHub repository to Streamlit Community Cloud and set the app entry point to `app.py`, or use the included Dockerfile on a container host.

See `DEPLOY.md` for the deployment path and the production items that must be added before accepting real customer payments/data at scale.

## Architecture

```text
CSV
 ↓
Streamlit Web UI / FastAPI
 ↓
Data Intelligence
 ↓
KPI Engine ─ Chart Engine ─ Data Quality
 ↓
Forecasting ─ Recommendations
 ↓
Reports / Saved Dashboards / API
```

The current SQLite storage is a development persistence layer. A production multi-user SaaS should use managed PostgreSQL + object storage, authentication/authorization, billing/usage limits, signed sharing links, background jobs and encrypted storage.
