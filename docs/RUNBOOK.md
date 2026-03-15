# Agent Flight Recorder – Runbook

Quick reference to run the stack locally and send your first traced run.

## Quick start (one command)

From the **repo root**:

**Windows (PowerShell):**
```powershell
.\scripts\start.ps1
# Optional: include the dashboard
.\scripts\start.ps1 -IncludeFrontend
```

**Cross-platform (Python):**
```bash
python scripts/start_all.py
# Optional: include the dashboard
python scripts/start_all.py --frontend
```

This starts the API (8000), demo agent (8001), and both workers in the background. If you used `-IncludeFrontend` / `--frontend`, open http://localhost:5173. Otherwise run the dashboard once: `cd frontend && npm install && npm run dev`, then open http://localhost:5173.

### Clean stop

To stop all backend processes (API, demo agent, workers):

```powershell
Get-Process -Name python, uvicorn -ErrorAction SilentlyContinue | Stop-Process -Force
```

Then close the frontend window (or stop the npm process) if it was started by the script. Restart by running the start script again from the repo root.

---

## Prerequisites

- Python 3.10+ with the backend venv and dependencies installed
- Node (for the dashboard) if you use the React UI

## 1. Environment

In `backend/.env` (copy from `backend/.env.example` if needed):

```env
DATABASE_URL=sqlite:///./agent_recorder.db
OPENAI_API_KEY=...          # optional; needed for hallucination/planning detectors
API_KEY=                    # optional; if set, protects POST /runs and POST /simulations. The start script reads this and passes it to the demo agent as FLIGHT_RECORDER_API_KEY.
```

To use **Postgres** instead of SQLite, set `DATABASE_URL` to your Postgres URL (e.g. `postgresql://user:pass@localhost:5432/agent_recorder`). All processes (API and workers) must use the same URL. See **[docs/postgres_schema.md](postgres_schema.md)** for the target schema and how to migrate data from SQLite later.

If `API_KEY` is set:

- All **ingestion** (`POST /api/v1/runs`) and **simulation creation** (`POST /api/v1/simulations`) must send:
  - Header: `X-API-Key: <your-key>`
  - Or: `Authorization: Bearer <your-key>`

Set the same value in the shell when running the demo agent so the SDK can ingest:

```powershell
$env:FLIGHT_RECORDER_API_KEY = "your-key"
```

## 2. Start services (manual, four terminals)

If you prefer to run each process in its own terminal, from the `backend` folder:

```powershell
cd backend

# Terminal 1 – API
.\.venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000

# Terminal 2 – Demo agent (simulation target)
$env:FLIGHT_RECORDER_API_KEY = "your-key"   # if API_KEY is set
.\.venv\Scripts\uvicorn simple_agent_api:app --host 127.0.0.1 --port 8001

# Terminal 3 – Failure worker (runs five detectors: hallucination, planning, tool_misuse, reasoning_loop, memory_contradiction)
.\.venv\Scripts\python -m app.worker_failures

# Terminal 4 – Simulation worker
.\.venv\Scripts\python -m app.worker_simulations
```

## 3. Dashboard

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 – use **Get started** in the header to set/store your API key and follow the steps.

## 4. Send a test run (Python)

With API key:

```python
import os
import httpx

payload = {
    "agent_id": "my-agent",
    "agent_version": "v0",
    "user_query": "What is 2+2?",
    "env": {},
    "steps": [],
    "final_answer": "4",
    "latency_ms": 0,
}
headers = {}
if os.environ.get("API_KEY"):
    headers["X-API-Key"] = os.environ["API_KEY"]

r = httpx.post("http://127.0.0.1:8000/api/v1/runs", json=payload, headers=headers)
print(r.status_code, r.json())
```

## 5. Create a simulation

```python
import os, httpx
headers = {}
if os.environ.get("API_KEY"):
    headers["X-API-Key"] = os.environ["API_KEY"]

r = httpx.post(
    "http://127.0.0.1:8000/api/v1/simulations",
    json={
        "name": "smoke-test",
        "agent_endpoint": "http://127.0.0.1:8001/agent",
        "task_template": "math_qa",
        "num_runs": 3,
    },
    headers=headers,
)
print(r.status_code, r.json())
```

Wait for the simulation worker to process; then refresh the dashboard to see runs and metrics.

### How to interpret simulations

- **Task templates:** `math_qa` (arithmetic), `doc_qa` (question from a short doc), `multi_turn`, `code_assist`, `generic`. You can also attach a **task dataset** (optional `dataset_id` when creating a simulation); the worker then uses tasks from that dataset instead of generating from the template.
- **Metrics:** Each simulation stores `total_runs`, `success`, `success_rate`, `hallucination_rate`, `tool_error_rate` (runs with tool_misuse failures), and `avg_latency_ms`.
- **% success:** Share of runs with `status == "success"`. Failures (e.g. agent timeout or crash) lower this.
- **% hallucinations / tool errors:** Share of runs where the hallucination or tool_misuse detector recorded a finding. Use Run Detail on individual runs to see all five detector scores (hallucination, planning_failure, tool_misuse, reasoning_loop, memory_contradiction).
- **Filtering:** Click a simulation in the list to show only its runs in Recent Runs; click “Show all runs” to clear the filter.

*(Status badges: later we may show green / yellow / red from thresholds, e.g. green: success ≥ 90% and hallucinations ≤ 5%; red: success &lt; 70% or hallucinations &gt; 20%.)*

## 5a. Real agent example (OpenAI)

A second agent that calls OpenAI and records runs is in `backend/real_llm_agent.py`. Install the OpenAI client if needed: `pip install openai`.

**Start it** (from `backend`, in a separate terminal):

```powershell
cd backend
$env:FLIGHT_RECORDER_API_KEY = "your-key"   # if API_KEY is set
$env:OPENAI_API_KEY = "your-openai-key"
.\.venv\Scripts\uvicorn real_llm_agent:app --host 127.0.0.1 --port 8002
```

**Call it manually:**

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8002/agent" -Method Post -ContentType "application/json" -Body '{"query":"What is 17 * 23?"}'
```

**Point a simulation at it:** In the dashboard (Get started → step 3) or via API, set agent endpoint to `http://127.0.0.1:8002/agent`. Runs will appear with `agent_id` `openai-agent` and you can inspect real LLM answers and detector scores.

**Example prompts that often surface interesting failures:** “What is the population of Paris in 2024?” (out-of-date or hallucinated numbers), “Summarize the plot of the 1972 film that won Best Picture” (factual check), “Write a Python function that returns the nth Fibonacci number in O(1) time” (impossible claim).

## 6. Rate limits (defaults)

- Ingest: **120/min** per client IP
- Simulation create: **30/min** per client IP

Override in `.env` if needed:

```env
RATE_LIMIT_INGEST_PER_MINUTE=120
RATE_LIMIT_SIMULATIONS_PER_MINUTE=30
```

Set to `0` to disable.

## 7. Troubleshooting

| Issue | What to do |
|-------|------------|
| `401` on POST | Set `X-API-Key` or disable auth by leaving `API_KEY` empty |
| `429` | Back off; you hit per-minute rate limit |
| `500` on ingest | Check API logs; ensure DB file exists and tables created (API startup runs `create_all`) |
| Workers not processing | Ensure workers use same `DATABASE_URL` as the API |
| PowerShell won't run script | Run `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` once |
| Dashboard shows "Failed to fetch" or no data | Backend may have exited. Check `backend\logs\api.err.log` and `demo_agent.err.log`. If port 8000 is in use, run the **Clean stop** command above, then start the script again. Ensure `API_KEY` in `backend\.env` is set if you use auth; the start script passes it to the demo agent. |
| Port 8000 or 8001 already in use | Another process is using the port. Use **Clean stop** to kill Python/uvicorn, or find the process with `Get-NetTCPConnection -LocalPort 8000` (Windows) and close that application. |

## 7a. Detectors and extra APIs

- **Detectors:** The failure worker runs five detectors: `hallucination`, `planning_failure`, `tool_misuse`, `reasoning_loop`, `memory_contradiction`. See `GET /api/v1/detectors` for IDs and default thresholds.
- **Analytics:** `GET /api/v1/analytics/runs_summary?days=7&by_detector=true` returns runs per day, avg_latency_ms per day, and `failure_rate_per_detector` (per-day rates for each detector).
- **Task datasets:** `POST /api/v1/datasets` with `{"name": "...", "tasks": [{"query": "...", "env": {}}, ...]}` creates a dataset. Use the returned `dataset_id` in `POST /api/v1/simulations` (body: `dataset_id`) to run simulations from that dataset instead of a template.

## 8. Going online (deployment)

See **[docs/DEPLOY.md](DEPLOY.md)** for step-by-step deployment (single host, env vars, frontend build, optional combined API + dashboard).

**Summary:**

- **Backend env:** `DATABASE_URL`, `API_KEY`, `OPENAI_API_KEY`; for cross-origin frontend set `CORS_ORIGINS` to your dashboard URL(s).
- **Frontend:** Build with `VITE_API_BASE=` (same host) or `VITE_API_BASE=https://your-api-url` (split). Deploy `frontend/dist` or copy to `backend/static` and set `STATIC_DIR=./static` for combined deploy.
- **Processes:** Run API (uvicorn), then worker_failures and worker_simulations as separate processes or platform workers. To run workers in the cloud (e.g. Render background workers), see Workers in the cloud in [docs/DEPLOY.md](DEPLOY.md).
- **TLS:** Use the platform’s HTTPS or a reverse proxy; never commit secrets.

---

## 9. Checklist for you (what to do on your side)

- **Local run:** Copy `backend/.env.example` to `backend/.env`, set `OPENAI_API_KEY` (and optionally `API_KEY`). Run `.\scripts\start.ps1 -IncludeFrontend` (or the Python start script) from the repo root; open http://localhost:5173.
- **Real agent:** Start `real_llm_agent.py` on port 8002 with `FLIGHT_RECORDER_API_KEY` and `OPENAI_API_KEY` set; create a simulation pointing to `http://127.0.0.1:8002/agent` to see real LLM runs and detector scores.
- **Going online:** After the productization pass, deploy to one host (e.g. Railway, Render, Fly), set env vars, build the frontend and point it at your API URL. See §8 above.
- **Design docs:** `docs/postgres_schema.md`, `docs/failure_patterns_design.md` are for implementation later. **Evolution plan:** See [docs/ROADMAP.md](ROADMAP.md) for the 2–4 week roadmap (trace timeline, failure badges, clustering, etc.).
