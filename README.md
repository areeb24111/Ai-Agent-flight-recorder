# Agent Flight Recorder

Record AI agent runs, detect failures (hallucination, planning, tool misuse, reasoning loop, memory contradiction), run batch simulations, and inspect everything in a dashboard. **Why:** AI agents fail in subtle ways; without a recorder you can't replay, compare, or spot patterns. This gives you a single place to see what happened and how often it goes wrong.

**What it does:**

- Records every agent run (query, steps, tool calls, final answer) via a small SDK and ingestion API.
- Runs five automatic failure detectors (hallucination, planning, tool misuse, reasoning_loop, memory_contradiction) and shows per-run scores in the dashboard.
- Lets you run batch simulations against your agent endpoint (task templates or custom task datasets) and see success, hallucination, and tool-error rates.
- Gives you a single dashboard to replay runs, inspect steps, filter by simulation, and view analytics (including per-detector failure rates over time).

The dashboard shows metrics (runs, latency, success rate), a list of recent runs with replay, run detail (steps and failure scores), an analytics chart over time, and simulations you can click to filter runs.

![Dashboard](docs/screenshot.png)  
*Add a screenshot of the dashboard with sample data (e.g. `docs/screenshot.png`).*

## Features

- **Trace ingestion** – `POST /api/v1/runs` stores runs + steps (SDK or HTTP).
- **Failure detection** – Background worker runs five detectors (hallucination, planning, tool_misuse, reasoning_loop, memory_contradiction); scores appear in the UI.
- **Simulations** – Create jobs that call your agent endpoint with built-in task templates (**math_qa**, **doc_qa**, **multi_turn**, **code_assist**), a **custom prompt** (template `custom` + `template_config.query`), or a **task dataset**; metrics include success_rate, hallucination_rate, tool_error_rate, avg_latency_ms.
- **Task datasets** – Create named prompt sets via `POST /api/v1/datasets` and optionally attach to simulations.
- **Dashboard** – Recent runs, run detail with steps and failures, analytics chart (with optional per-detector rates), simulation list and filtering.
- **Auth & limits** – Optional API key on write endpoints; per-IP rate limits.

**Evolution plan:** See **[docs/ROADMAP.md](docs/ROADMAP.md)** for the 2–4 week roadmap (trace timeline UI, failure badges, clustering, etc.).

## Repo layout

```
backend/           # FastAPI app, workers, SDK, demo agent
  app/
    routes/        # runs, simulations, analytics, detectors, datasets, failure_patterns
    detectors/     # hallucination, planning, tool_misuse, reasoning_loop, memory_contradiction
    deps/          # auth, rate_limit
  sdk_flight_recorder.py
  simple_agent_api.py
frontend/          # Vite + React dashboard
docs/
  RUNBOOK.md        # how to run everything
```

## Quick start (local dev)

From the **repo root**, one command starts the backend (API + workers + demo agent) and optionally the dashboard. **To ingest a run and verify everything works**, see **[docs/TESTING.md](docs/TESTING.md)** (curl, Python, or SDK).

- **Windows:** `.\scripts\start.ps1 -IncludeFrontend`
- **Mac/Linux:** `python scripts/start_all.py --frontend`

Then open **http://localhost:5173** (run `cd frontend && npm install && npm run dev` first if you didn’t use the frontend flag). 

**Deploy online:** Connect [GitHub repo](https://github.com/areeb24111/Ai-Agent-flight-recorder) to [Render](https://render.com) (Blueprint from `render.yaml`) or use **[docs/DEPLOY.md](docs/DEPLOY.md)** for Railway, Google Cloud Run, and combined API + dashboard.  
**Live demo:** [Dashboard](https://ai-agent-flight-recorder.onrender.com) · [API](https://agent-flight-recorder-api.onrender.com) · [API docs (OpenAPI)](https://agent-flight-recorder-api.onrender.com/docs)

**How do other people check their agents on my deployment?** They point their agent at your API URL, send each run via `POST /api/v1/runs` (or your SDK), then open your dashboard to see runs and failures. See **[docs/HOW_OTHERS_USE_IT.md](docs/HOW_OTHERS_USE_IT.md)** for the exact steps and what to share with them (dashboard URL, API URL, optional API key).

## API summary

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | no | Liveness |
| POST | `/api/v1/runs` | if `API_KEY` set | Ingest run + steps |
| GET | `/api/v1/runs` | no | List runs (optional `simulation_id`, `agent_id`, `date_from`, `date_to`, `offset`, `limit`) |
| GET | `/api/v1/runs/agents` | no | List distinct agent IDs for filters |
| GET | `/api/v1/runs/export?format=csv\|json` | no | Export runs (optional filters) |
| GET | `/api/v1/runs/{id}` | no | Run detail + failures |
| POST | `/api/v1/simulations` | if `API_KEY` set | Create simulation (optional `template_config: { query, env }` for custom prompt) |
| GET | `/api/v1/simulations` | no | List simulations |
| GET | `/api/v1/analytics/runs_summary?days=N&by_detector=true` | no | Runs/day, hallucination rate; optional per-detector failure rates and avg_latency_ms |
| GET | `/api/v1/detectors` | no | List detector IDs and default thresholds |
| POST | `/api/v1/datasets` | if `API_KEY` set | Create task dataset (name + tasks) |
| GET | `/api/v1/datasets` | no | List task datasets |
| GET | `/api/v1/datasets/{id}` | no | Get dataset by id (full payload) |
| GET | `/api/v1/failure_patterns?days=N&detector=X` | no | Failure patterns (grouped by detector + explanation) |
| GET | `/api/v1/failure_clusters?days=N&detector=X` | no | Failure clusters (grouped similar failures; text-based; embedding-based when Postgres + pgvector) |

## SDK examples

**Python (record a run):**

```python
# See backend/sdk_flight_recorder.py and backend/send_test_run.py
import requests
RUNS_URL = "http://127.0.0.1:8000/api/v1/runs"
resp = requests.post(RUNS_URL, json={
    "agent_id": "my-agent",
    "user_query": "What is 2+2?",
    "final_answer": "4",
    "latency_ms": 120,
    "steps": [{"idx": 0, "step_type": "reasoning", "request": {}, "response": {"thought": "2+2=4"}}],
})
print(resp.json())  # {"run_id": "..."}
```

**curl (ingest + list):**

```bash
curl -X POST http://127.0.0.1:8000/api/v1/runs \
  -H "Content-Type: application/json" \
  -d '{"agent_id":"curl-agent","user_query":"Hi","final_answer":"Hello","latency_ms":50,"steps":[]}'
curl "http://127.0.0.1:8000/api/v1/runs?limit=10"
```

## Publish & share

To put the project on **GitHub** and promote it on **LinkedIn**, see **[docs/PUBLISH_AND_MARKET.md](docs/PUBLISH_AND_MARKET.md)** (repo setup, push steps, and post ideas). No pricing or paid tiers for now.

## License

Proprietary / adjust as needed.
