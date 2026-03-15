# Agent Flight Recorder (MVP)

Record AI agent runs, detect failures (hallucination, planning, tool misuse), run batch simulations, and inspect everything in a small dashboard.

**What it does:**

- Records every agent run (query, steps, tool calls, final answer) via a small SDK and ingestion API.
- Runs automatic failure detectors (hallucination, planning, tool misuse) and shows per-run scores in the dashboard.
- Lets you run batch simulations against your agent endpoint and see success/hallucination rates.
- Gives you a single dashboard to replay runs, inspect steps, and filter by simulation.

The dashboard shows metrics (runs, latency, success rate), a list of recent runs with replay, run detail (steps and failure scores), an analytics chart over time, and simulations you can click to filter runs.

## Features

- **Trace ingestion** – `POST /api/v1/runs` stores runs + steps (SDK or HTTP).
- **Failure detection** – Background worker runs LLM/heuristic detectors; scores appear in the UI.
- **Simulations** – Create jobs that call your agent endpoint with synthetic tasks (`math_qa`, `doc_qa`, `multi_turn`, `code_assist`).
- **Dashboard** – Recent runs, run detail with steps, analytics chart, simulation-scoped filtering.
- **Auth & limits** – Optional API key on write endpoints; per-IP rate limits.

## Repo layout

```
backend/           # FastAPI app, workers, SDK, demo agent
  app/
    routes/        # runs, simulations, analytics
    detectors/     # hallucination, planning, tool_misuse
    deps/          # auth, rate_limit
  sdk_flight_recorder.py
  simple_agent_api.py
frontend/          # Vite + React dashboard
docs/
  RUNBOOK.md        # how to run everything
```

## Quick start (local dev)

From the **repo root**, one command starts the backend (API + workers + demo agent) and optionally the dashboard:

- **Windows:** `.\scripts\start.ps1 -IncludeFrontend`
- **Mac/Linux:** `python scripts/start_all.py --frontend`

Then open **http://localhost:5173** (run `cd frontend && npm install && npm run dev` first if you didn’t use the frontend flag). See **[docs/RUNBOOK.md](docs/RUNBOOK.md)** for env setup and **[docs/DEPLOY.md](docs/DEPLOY.md)** for deploying online (Render, Railway, **Google Cloud Run**).

## API summary

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | no | Liveness |
| POST | `/api/v1/runs` | if `API_KEY` set | Ingest run + steps |
| GET | `/api/v1/runs` | no | List runs (optional `simulation_id`) |
| GET | `/api/v1/runs/{id}` | no | Run detail + failures |
| POST | `/api/v1/simulations` | if `API_KEY` set | Create simulation job |
| GET | `/api/v1/simulations` | no | List simulations |
| GET | `/api/v1/analytics/runs_summary?days=N` | no | Runs/day + hallucination rate |
| GET | `/api/v1/failure_patterns?days=N&detector=X` | no | Failure patterns (grouped by detector + explanation) |

## Publish & share

To put the project on **GitHub** and promote it on **LinkedIn**, see **[docs/PUBLISH_AND_MARKET.md](docs/PUBLISH_AND_MARKET.md)** (repo setup, push steps, and post ideas). No pricing or paid tiers for now.

## License

Proprietary / adjust as needed.
