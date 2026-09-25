# Deployment Guide

**None of the steps below were executed in the build sandbox** — that
environment has no internet access and no accounts on any of these
platforms, so nothing here has been deployed or tested end-to-end. Every
command mirrors what was verified locally in principle (Docker Compose YAML
validated for syntax, FastAPI/dashboard logic verified against real data —
see README.md Section 4), but you are the one actually standing this up.
Report back the exact error if any step fails.

## Option A: Streamlit Community Cloud (fastest — dashboard only, free)

1. Push this repo to GitHub (public or private with Streamlit Cloud access).
2. Go to https://share.streamlit.io, sign in, "New app".
3. Point it at your repo, branch `main`, file path `dashboard/app.py`.
4. **Important**: Streamlit Cloud won't run your data pipeline for you. Either:
   - Commit a small pre-generated `data/raw/*.csv` and `data/processed/*.csv`
     (remove them from `.gitignore` first, and note in your README that this
     sample data is committed for demo purposes), or
   - Add a `@st.cache_resource` startup step in `dashboard/app.py` that runs
     the generator + ETL on first load if the files don't exist.
5. Deploy. You'll get a `*.streamlit.app` URL — this is the one worth putting
   in your SOP/CV, since it needs no setup for a reviewer to open.

## Option B: Render or Railway (API + dashboard, more control)

Both platforms can build directly from `docker-compose.yml` or from
`docker/Dockerfile` with a custom start command per service.

### Render
1. Create a **Web Service** for the API: connect the repo, set the Dockerfile
   path to `docker/Dockerfile`, start command `uvicorn api.main:app --host
   0.0.0.0 --port $PORT` (Render injects `$PORT`; adjust the command
   accordingly since the Dockerfile's default CMD doesn't reference it).
2. Create a second **Web Service** for the dashboard, same Dockerfile, start
   command `streamlit run dashboard/app.py --server.address=0.0.0.0
   --server.port=$PORT`.
3. Add a **persistent disk** or run the pipeline as part of the service's
   build/start command (e.g. prepend `python src/ingestion/generate_synthetic_data.py
   --n-users 5000 && python src/preprocessing/etl.py &&` to each start command),
   since Render's free tier doesn't guarantee a shared volume between services.

### Railway
1. `railway init`, then `railway up` from the project root — Railway can
   often auto-detect `docker-compose.yml`, but Railway's own docs should be
   checked for current multi-service Compose support, since platform
   behaviour here changes and wasn't something this sandbox could verify.
2. Set environment/start commands the same way as the Render steps above if
   auto-detection doesn't pick up the three services correctly.

## Option C: Run Docker Compose locally (no cloud deployment needed for a demo)

```bash
docker compose up --build
# API docs:  http://localhost:8000/docs
# Dashboard: http://localhost:8501
```
This is the fastest way to prove the *whole* system (pipeline + API +
dashboard) works together, even before deciding on a cloud platform. Good
enough for a live interview demo on your own laptop if you don't want to
manage a public deployment at all.

## What to actually put in your case study / CV

A public dashboard link is worth more than a private repo link — a reviewer
can open it in one click without cloning anything. If you only deploy one
thing, deploy Option A (Streamlit Community Cloud); it's free, fast, and
needs no infrastructure knowledge from whoever's looking at it.
