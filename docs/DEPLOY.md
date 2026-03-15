# Deploying Agent Flight Recorder online

Single-host deployment so the dashboard and API are reachable on the internet. Two options: **split** (API on one URL, frontend on another) or **combined** (one URL serves both).

---

## Quick deploy (Render)

1. Push your repo to GitHub (see **Push to GitHub** below if you need to fix auth).
2. Go to [dashboard.render.com](https://dashboard.render.com) → **New** → **Blueprint**.
3. Connect the repo `https://github.com/areeb24111/Ai-Agent-flight-recorder`.
4. Render will read `render.yaml`: it creates a **Web Service** (the API) and can create a **Postgres** DB. Confirm and deploy.
5. **Add your OpenAI key:** In the service → **Environment** → **Add Environment Variable**. Key: `OPENAI_API_KEY`, Value: your OpenAI API key (starts with `sk-...`). Save; Render will redeploy. Never commit this key to the repo.
6. (Optional) Set `API_KEY` if you want to protect ingest/simulation endpoints; leave blank for open access.
7. After deploy, your API is at the URL Render shows (e.g. `https://agent-flight-recorder-api.onrender.com`). Use it as `VITE_API_BASE` when building the frontend, or add a **Static Site** on Render that points to this API.

**If the Static Site fails with "Publish directory build does not exist" or "Empty build command":** In the Static Site service go to **Settings**. Set **Build Command** to `cd frontend && npm install && npm run build` and **Publish Directory** to `frontend/dist`. In **Environment** add `VITE_API_BASE` = your API URL (e.g. `https://agent-flight-recorder-api.onrender.com`, no trailing slash). Save and run **Manual Deploy**.

**Push to GitHub (if you get “Authentication failed”):** GitHub no longer accepts account passwords over HTTPS. Use a **Personal Access Token (PAT)**: GitHub → Settings → Developer settings → Personal access tokens → Generate (classic), scope `repo`. Then run:

```bash
cd "c:\Users\areeb\Agent failure analysis"
git remote set-url origin https://YOUR_USERNAME:YOUR_PAT@github.com/areeb24111/Ai-Agent-flight-recorder.git
git push -u origin main
```

Or use **SSH**: add an SSH key to GitHub and set `git remote set-url origin git@github.com:areeb24111/Ai-Agent-flight-recorder.git`, then `git push -u origin main`.

---

## Two services: API vs dashboard

**Yes, they are different.** The Blueprint (`render.yaml`) defines **two** services:

| Service | Type | Purpose |
|--------|------|--------|
| **agent-flight-recorder-api** | Web Service (Python) | Backend: stores runs, runs failure detection, serves `/api/v1/*` and `/health`. |
| **agent-flight-recorder-dashboard** | Static Site | Frontend: the React dashboard you see in the browser. It *calls* the API to load runs and analytics. |

If you only see **one** project (e.g. only “Ai-Agent-flight-recorder” as a Static Site), the **API service was never created**. That’s why the dashboard shows “Failed to fetch”: there is no backend to talk to.

**What to do:**

1. **Use the Blueprint (recommended):** In Render go to **Dashboard** → **New** → **Blueprint**. Connect the same repo and select `render.yaml`. Render will create **both** services (API + dashboard). You can delete the old single static site if you created it separately.
2. **Or add the API manually:** **New** → **Web Service** → connect the repo, set **Root Directory** to `backend`, **Build** to `pip install -r requirements.txt`, **Start** to `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Add env vars (e.g. `OPENAI_API_KEY`). Then set the dashboard’s `VITE_API_BASE` to this new API URL and redeploy the dashboard.

After both are deployed, the dashboard URL (e.g. `https://ai-agent-flight-recorder.onrender.com`) will call the API URL (e.g. `https://agent-flight-recorder-api.onrender.com`) and the “Failed to fetch” error should go away.

---

## Free tier on Render (no Blueprint)

If the Blueprint is not available or you want to avoid it, use the free tier in one of these ways.

**Option 1: Two free services (manual)**  
Create two services by hand. Render free tier usually allows 1 Web Service and 1 Static Site.

- **API:** New → Web Service. Repo, Root Directory `backend`, Build `pip install -r requirements.txt`, Start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Add env `OPENAI_API_KEY`. Deploy and copy the service URL.
- **Dashboard:** New → Static Site. Same repo, Build `cd frontend && npm install && npm run build`, Publish `frontend/dist`. Environment: `VITE_API_BASE` = your API URL (no trailing slash). Deploy.

**Option 2: One free service (API + dashboard together)**  

One Web Service serves both the API and the dashboard. Follow these steps:

1. In Render go to **Dashboard** → **New** → **Web Service**.
2. Connect your GitHub repo (`areeb24111/Ai-Agent-flight-recorder` or your fork), branch **main**.
3. **Name:** e.g. `agent-flight-recorder`.
4. **Root Directory:** `backend`
5. **Build Command:**  
   `pip install -r requirements.txt && cd ../frontend && npm install && VITE_API_BASE= npm run build && cp -r dist ../backend/static`
6. **Start Command:**  
   `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
7. **Environment variables** (Add in the Render Environment tab):
   - `STATIC_DIR` = `./static`
   - `OPENAI_API_KEY` = your OpenAI key (for failure detectors)
   - `API_KEY` = leave blank for open access, or set a secret to protect ingest/simulation endpoints
8. Click **Create Web Service** and wait for the first deploy.

When it is live, one URL does everything: **/** shows the dashboard, **/api/v1/...** is the API, **/health** is the health check. No second service and no Blueprint. Reference: `render-one-service.yaml` in the repo.

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
| `WEBHOOK_URL` | Optional | HTTP POST when a run has failure score ≥ `WEBHOOK_THRESHOLD`. |
| `WEBHOOK_THRESHOLD` | Optional (default 80) | Score 0–100; triggers webhook when any detector exceeds it. |

**Workers in the cloud:** For failure detection and simulations to run in production, run `worker_failures` and `worker_simulations` as separate processes (e.g. Render background workers, or separate services). Point them at the same `DATABASE_URL` and `OPENAI_API_KEY`. The API only stores runs; the workers process them asynchronously. See **§ Workers in the cloud** below for step-by-step setup.

---

## Workers in the cloud (step-by-step)

To run the failure-detection and simulation workers in production so that runs get processed and simulations execute without your laptop:

### Option A: Same host as the API (e.g. one Render Web Service)

Run the API and both workers in one process using a process manager, or run them as separate **background** processes started by your start command.

**Using a shell script (Linux/macOS):**

```bash
# start.sh – run API and workers (same machine)
cd backend
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} &
python -m app.worker_failures &
python -m app.worker_simulations &
wait
```

Then set **Start Command** to `./start.sh` (and ensure the script is executable). All three share the same env (`DATABASE_URL`, `OPENAI_API_KEY`, etc.).

**Using Python only (cross-platform):**

You can start uvicorn and the two workers in one Python process (e.g. with `asyncio` and threading), but the simplest production approach is **Option B**.

### Option B: Separate worker services (Render, Railway, Fly, etc.)

Create **two extra services** that run only the workers and point at the same database and env as the API.

1. **Worker 1 – Failure detection**
   - **New** → **Background Worker** (or **Web Service** that runs a one-off command; some platforms call it “Cron” or “Worker”).
   - Repo: same as API. **Root Directory:** `backend`.
   - **Build:** `pip install -r requirements.txt`
   - **Start / Command:** `python -m app.worker_failures`
   - **Environment:** Same as API: `DATABASE_URL` (e.g. Render Postgres internal URL), `OPENAI_API_KEY`, optional `API_KEY`, `WEBHOOK_URL`, etc.
   - No `PORT` or HTTP needed; the process just polls the DB.

2. **Worker 2 – Simulations**
   - Same idea: **New** → **Background Worker**.
   - Repo and Root Directory: `backend`.
   - **Build:** `pip install -r requirements.txt`
   - **Start / Command:** `python -m app.worker_simulations`
   - **Environment:** Same `DATABASE_URL` as API (and optional `API_KEY`). No `OPENAI_API_KEY` required for this worker.

3. **Database:** If the API uses **Render Postgres**, copy the **Internal Database URL** from the Render dashboard and set it as `DATABASE_URL` on the API and on **both** workers. All three must use the same URL.

4. **Result:** The API ingests runs and serves the dashboard; `worker_failures` marks runs as processed and writes failures; `worker_simulations` picks up pending simulations and POSTs to agent endpoints, then updates metrics.

### Option C: Render “Background Worker” type

On Render, **New** → **Background Worker** lets you attach the same repo and set **Start Command** to `python -m app.worker_failures` (or `worker_simulations`). Add the same env vars as the API (especially `DATABASE_URL` and `OPENAI_API_KEY` for the failures worker). Create two background workers, one per script.

### Checklist

- [ ] `DATABASE_URL` is identical on API and both workers (e.g. Render Postgres internal URL).
- [ ] `OPENAI_API_KEY` is set on the **failure** worker so detectors can run.
- [ ] Workers have no `PORT` binding; they only poll the DB and (for simulations) call agent endpoints.
- [ ] If the API uses `API_KEY`, you do not need to set it on workers unless a worker calls your own API (e.g. for ingest); simulations worker only POSTs to the **agent** URL.

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
- [ ] Frontend build uses correct `VITE_API_BASE` (empty for same host, or your API URL for split).
- [ ] `CORS_ORIGINS` includes your frontend URL if it’s on a different domain.
- [ ] For combined deploy: `STATIC_DIR` set and `backend/static` (or your path) contains the built frontend.
- [ ] Workers run with same `DATABASE_URL` and env as the API.

For **Google Cloud Run**: use `backend/Dockerfile` and the steps in §7; build with `gcloud builds submit` or Docker, then `gcloud run deploy`. Use Cloud SQL for the database and Cloud Run Jobs or a small VM for the workers.
