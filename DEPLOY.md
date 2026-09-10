# Public deployment

The application is a web app. End users do **not** install Python or VS Code.

## Fastest public route: Streamlit Community Cloud

1. Push this repository to GitHub.
2. Open Streamlit Community Cloud and choose **New app**.
3. Select the repository and branch.
4. Set the main file to `app.py`.
5. Deploy.
6. Share the generated HTTPS URL.

The repository remains the source of truth for the backend code, while users interact only with the web UI.

## Docker / Render / Railway / other hosts

Use the included `Dockerfile`. The container exposes port `8501` and runs `app.py`.

## Important production upgrade before charging users

The current local SQLite persistence is suitable for development and a single-instance demo. For a real multi-user SaaS, replace it with managed PostgreSQL/object storage and add authentication, per-user authorization, signed share links, billing/usage limits, background jobs and encrypted file storage.
