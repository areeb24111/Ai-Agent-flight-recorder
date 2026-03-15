# Deploying Agent Flight Recorder online

Single-host deployment so the dashboard and API are reachable on the internet. Two options: **split** (API on one URL, frontend on another) or **combined** (one URL serves both).

---

## 1. Environment variables (backend)

Set these on your host or in your platform’s dashboard. Never commit real values.

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | No (default: SQLite file) | Use a Postgres URL for production, e.g. `postgresql://user:pass@host:5432/dbname`. |
| `API_KEY` | Recommended | Secret for `X-API-Key` on ingest and simulation creation. |
| `OPENAI_API_KEY` | For detectors | Needed for hallucination/planning detectors. |
| `CORS_ORIGINS` | If frontend on different domain | Comma-separated, e.g. `https://myapp.fly.dev,https://myapp.render.com`. |
| `STATIC_DIR` | Optional (combined deploy) | Path to built frontend, e.g. `./static`. See §4. |

---

## 2. Build the frontend with the API URL

The dashboard calls the backend using `VITE_API_BASE`. Set it at **build time**:

**If API and frontend are on the same origin (combined deploy):**

```bash
cd frontend
npm ci
VITE_API_BASE= npm run build
```

`VITE_API_BASE=` (empty) makes the app use relative URLs, so `/api/v1/...` goes to the same host.

**If API is on a different URL (split deploy):**

```bash
cd frontend
npm ci
VITE_API_BASE=https://your-api.fly.dev npm run build
```

Replace `https://your-api.fly.dev` with your real API base (no trailing slash). The built files go to `frontend/dist`.

---

## 3. Run the backend and workers

- **API:** Run with uvicorn, binding to `0.0.0.0` so the host is reachable:

  ```bash
  cd backend
  uvicorn app.main:app --host 0.0.0.0 --port 8000
  ```

  Your platform may set `PORT`; use it if present, e.g. `--port ${PORT:-8000}`.

- **Workers:** Run in separate processes (or separate “worker” services on Railway/Render/Fly):

  ```bash
  cd backend
  python -m app.worker_failures
  python -m app.worker_simulations
  ```

  Both need the same `DATABASE_URL` (and `.env` or platform env) as the API.

- **Demo agent (optional):** If you want the demo agent online, run it and set `FLIGHT_RECORDER_API_KEY` to the same value as `API_KEY`. Point `agent_endpoint` in simulations to this service’s URL (e.g. `https://demo-agent.xxx.up.railway.app/agent`).

---

## 4. Option A – Split deploy (API and frontend separate)

1. Deploy the **backend** as a web service: run `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Set `DATABASE_URL`, `API_KEY`, `OPENAI_API_KEY`, and `CORS_ORIGINS` to your frontend URL(s).
2. Build the frontend with `VITE_API_BASE=https://your-api-url` (your backend’s public URL).
3. Deploy the contents of `frontend/dist` to a static host (Vercel, Netlify, Cloudflare Pages, or the same platform’s static site). No extra env vars needed; the API URL is baked into the build.

---

## 5. Option B – Combined deploy (one URL for API + dashboard)

1. Build the frontend with same-origin API (see §2):

   ```bash
   cd frontend && VITE_API_BASE= npm run build
   ```

2. Copy the build into the backend so the API can serve it:

   ```bash
   cp -r frontend/dist backend/static
   ```

   (Or set your build output to `backend/static`.)

3. Set env for the backend:

   - `STATIC_DIR=./static` (or the path you used; relative to backend working directory).
   - `CORS_ORIGINS` can be unset if the dashboard is on the same origin.

4. Run only the API (and workers separately as in §3):

   ```bash
   cd backend
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

   - `GET /` → dashboard (index.html).
   - `GET /api/v1/...` → API.

---

## 6. Example: Render

- **Web service:** Root directory = repo root or `backend`. Build: (none for backend-only). Start: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Add env vars in dashboard.
- **Background workers:** Two separate “Background Worker” services:  
  - Worker 1: `cd backend && python -m app.worker_failures`  
  - Worker 2: `cd backend && python -m app.worker_simulations`  
  Same env vars as the web service (especially `DATABASE_URL`).
- **Frontend:** Either a static site (build command `cd frontend && npm ci && VITE_API_BASE=https://your-web.onrender.com npm run build`, publish `frontend/dist`) or use Option B and serve from the same web service with `STATIC_DIR` and a build step that copies `frontend/dist` to `backend/static`.

---

## 7. Example: Google Cloud (Cloud Run)

Deploy the API (and optionally the dashboard) to **Google Cloud Run** so it’s reachable at a `*.run.app` URL over HTTPS.

### Prerequisites

- [Google Cloud SDK (gcloud)](https://cloud.google.com/sdk/docs/install) installed and logged in (`gcloud auth login`, `gcloud config set project YOUR_PROJECT_ID`).
- [Docker](https://docs.docker.com/get-docker/) (or use Cloud Build to build the image).

### 1. Build and push the image

From the **repo root**:

```bash
# Build the backend image (backend/Dockerfile)
docker build -t gcr.io/YOUR_PROJECT_ID/agent-flight-recorder:latest ./backend

# Configure Docker for GCR and push
gcloud auth configure-docker
docker push gcr.io/YOUR_PROJECT_ID/agent-flight-recorder:latest
```

Or use **Cloud Build** (no local Docker needed):

```bash
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/agent-flight-recorder:latest ./backend
```

Replace `YOUR_PROJECT_ID` with your Google Cloud project ID.

### 2. Deploy to Cloud Run

```bash
gcloud run deploy agent-flight-recorder \
  --image gcr.io/YOUR_PROJECT_ID/agent-flight-recorder:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "DATABASE_URL=sqlite:///./agent_recorder.db" \
  --set-env-vars "API_KEY=your-secret-key" \
  --set-env-vars "OPENAI_API_KEY=your-openai-key"
```

- For production, use a **Cloud SQL (Postgres)** instance and set `DATABASE_URL` to its connection name or public IP. SQLite in the container is ephemeral (data is lost when the instance restarts).
- To add more env vars or use secrets: `--set-env-vars "CORS_ORIGINS=https://your-frontend.web.app"` or use [Secret Manager](https://cloud.google.com/run/docs/configuring/secrets).
- After deploy, the service URL is shown (e.g. `https://agent-flight-recorder-xxx-uc.a.run.app`). Set `CORS_ORIGINS` to that URL if you host the frontend elsewhere, or use the combined option below.

### 3. Optional: serve the dashboard from the same service (combined)

Build the frontend and bake it into the image:

```bash
cd frontend
npm ci
VITE_API_BASE= npm run build
cp -r dist ../backend/static
cd ../backend
```

Then in `backend/Dockerfile` uncomment the line that copies `static`:

```dockerfile
COPY static ./static
```

Set env when deploying:

```bash
--set-env-vars "STATIC_DIR=./static"
```

Rebuild and push the image, then redeploy. The same Cloud Run URL will serve both the dashboard (`/`) and the API (`/api/...`).

### 4. Workers (failure detection and simulations)

Cloud Run runs **request-based** services. The failure and simulation workers are long-running loops, so run them separately:

- **Option A – Cloud Run Jobs**  
  Create two jobs that run the worker scripts. Jobs don’t run 24/7; you can trigger them on a schedule (e.g. every 1–5 minutes) with Cloud Scheduler, or run them once. Use the same image and env vars; override the command to `python -m app.worker_failures` and `python -m app.worker_simulations`.

- **Option B – Compute Engine (VM)**  
  Spin up a small VM, clone the repo (or pull the image), set env vars, and run the two workers in the background (e.g. with `systemd` or a small script). The VM needs the same `DATABASE_URL` as the Cloud Run service (e.g. Cloud SQL).

- **Option C – Second Cloud Run service (always-on)**  
  Deploy a second service that runs a single process running both workers (e.g. a script that starts both in threads or subprocesses). Set min instances to 1 so it never scales to zero. Simpler but more expensive than Jobs + schedule.

### 5. Quick reference

| What | Command / note |
|------|-----------------|
| Build image | `docker build -t gcr.io/PROJECT_ID/agent-flight-recorder:latest ./backend` |
| Push | `docker push gcr.io/PROJECT_ID/agent-flight-recorder:latest` |
| Deploy | `gcloud run deploy agent-flight-recorder --image gcr.io/PROJECT_ID/agent-flight-recorder:latest --region us-central1 --allow-unauthenticated --set-env-vars "..."` |
| API URL | Shown after deploy; use it as `VITE_API_BASE` if the frontend is on another host. |
| Database | Prefer Cloud SQL (Postgres) and set `DATABASE_URL`; workers must use the same URL. |

---

## 8. Example: Railway

- Create a project; add a **Web Service** from the repo. Set root to `backend` or run from repo root with `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Add env vars.
- Add **Worker** services (or use Railway’s worker type) for `python -m app.worker_failures` and `python -m app.worker_simulations` with the same env.
- For combined deploy: add a build step that runs `cd frontend && npm ci && VITE_API_BASE= npm run build && cp -r dist ../backend/static`, then set `STATIC_DIR=./static` for the web service.

---

## 9. Checklist

- [ ] `DATABASE_URL` set (Postgres recommended for production).
- [ ] `API_KEY` set; agents use the same value as `X-API-Key` / `FLIGHT_RECORDER_API_KEY`.
- [ ] `OPENAI_API_KEY` set if you use hallucination/planning detectors.
- [ ] Frontend built with correct `VITE_API_BASE` (empty for same host, or your API URL for split).
- [ ] `CORS_ORIGINS` includes your frontend URL if it’s on a different domain.
- [ ] For combined deploy: `STATIC_DIR` set and `backend/static` (or your path) contains the built frontend.
- [ ] Workers run with same `DATABASE_URL` and env as the API.

For **Google Cloud Run**: use `backend/Dockerfile` and the steps in §7; build with `gcloud builds submit` or Docker, then `gcloud run deploy`. Use Cloud SQL for the database and Cloud Run Jobs or a small VM for the workers.
