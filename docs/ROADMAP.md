# AI Observability Devtool – Evolution Roadmap

Phased plan to evolve the Agent Flight Recorder into a serious AI observability devtool ("Datadog for AI Agents"): trace timeline UI, stronger failure detection and clustering, simulation engine improvements, and richer analytics. Scoped for a single developer over **2–4 weeks**.

---

## Architecture (target)

- **Trace ingestion:** SDK / Agent → Runs API → SQLite or Postgres.
- **Failure detection:** `worker_failures` runs detectors (hallucination, planning, tool_misuse, reasoning_loop, memory_contradiction) and writes to `Failure`.
- **Clustering (optional, later):** Embedding pipeline + failure clusters (Postgres/pgvector); see [postgres_schema.md](postgres_schema.md).
- **Simulation engine:** Simulations API + `worker_simulations`; task templates or **task datasets**; worker POSTs to agent and recomputes metrics from runs/failures.
- **Analytics:** Runs summary, per-detector failure rates, latency; daily granularity.
- **Dashboard:** React UI → API and analytics; run list, run detail (steps + failures), analytics charts, simulation create/list and "View runs."

---

## Backend (current + planned)

| Area | Status | Notes |
|------|--------|------|
| **Detectors** | Done | Five: hallucination, planning_failure, tool_misuse, **reasoning_loop**, **memory_contradiction**. |
| **Analytics** | Done | `GET /api/v1/analytics/runs_summary?by_detector=true` returns failure_rate_per_detector and avg_latency_ms per day. |
| **Simulation metrics** | Done | `metrics`: total_runs, success, success_rate, hallucination_rate, **tool_error_rate**, avg_latency_ms. |
| **Task datasets** | Done | `POST/GET /api/v1/datasets`; Simulation has optional `dataset_id`; worker uses dataset tasks when set. |
| **Detectors API** | Done | `GET /api/v1/detectors` lists detector IDs and default thresholds. |
| **Configurable thresholds** | Planned | Env vars e.g. `DETECTOR_HALLUCINATION_THRESHOLD=80` (optional). |
| **Clustering (embeddings)** | Week 4+ | Postgres + pgvector; run_embeddings, failure_clusters; see postgres_schema.md. |

---

## Frontend (current + planned)

| Area | Status | Notes |
|------|--------|------|
| Run list + detail, steps, failures | Done | Filters, load more, failure count pill, copy run ID. |
| Analytics bar chart | Done | Runs per day + hallucination rate; optional by_detector in API. |
| Failure patterns table | Done | Grouped by detector + explanation_key. |
| Simulation create/list | Done | Status, metrics (success_rate, hallucination_rate, tool_error_rate, avg_latency). |
| **Trace timeline UI** | Done | Single-run view as vertical timeline: User query → steps (reasoning/tool call/result) → final output; collapsible request/response. |
| **Failure badges** | Done | Detector-wise badges in run list and run detail with severity color; list API returns failure_detectors. |
| **Simulation: View runs** | Done | "View runs" button on each simulation; tool_error_rate and avg_latency in list. |
| **Configurable thresholds** | Done | Env vars DETECTOR_*_THRESHOLD; worker only persists Failure when score >= threshold. |
| **Analytics charts** | Done | Failure rates by detector over time (stacked bars + legend). |
| **Responsive layout** | Done | Breakpoints at 960px, 768px, 480px; stacked panels and tables. |
| **Dark mode** | Done | Toggle in header; persisted in localStorage. |
| **Copy curl** | Done | Run detail: Copy curl button for GET run by id. |
| **Failure clusters** | Done | GET /api/v1/failure_clusters (text-based); Clusters section in dashboard. Embedding-based clustering ready when Postgres + pgvector added. |

---

## 2–4 week implementation roadmap

### Week 1 – Trace timeline and failure UX
- [x] **Trace timeline** in frontend (User query → steps → final output); detector badges in run list/detail.
- [x] Reasoning_loop and memory_contradiction detectors; registered in worker.

### Week 2 – Analytics and simulation metrics
- [x] Analytics: per-detector failure rates and latency in runs_summary; frontend can consume.
- [x] Simulation worker: tool_error_rate and avg_latency_ms in metrics; UI shows them.
- [x] Configurable detector thresholds (env); worker only persists when score >= threshold.

### Week 3 – Simulation and datasets
- [x] Task datasets: backend model and API (create/list); simulation create accepts optional dataset_id; worker runs tasks from dataset.
- [x] Dashboard: "View runs" button on simulations; simulation list shows tool_error_rate and avg_latency_ms.

### Week 4 – Clustering and polish
- [x] Failure clusters API and UI (text-based grouping); embedding-based when Postgres/pgvector available.
- [x] Polish: responsive layout, copy-curl for run, dark mode; workers-in-cloud docs in DEPLOY.md.

---

## GitHub issues (from plan)

| # | Title | Est. |
|---|--------|-----|
| 1 | Trace timeline UI (debugger-like) | 1–2 d |
| 2 | Failure badges and per-run detector summary | 0.5 d |
| 3 | Reasoning loop detector | 1 d *(done)* |
| 4 | Memory contradiction detector | 1 d *(done)* |
| 5 | Analytics: failure rates and latency over time | 1 d *(done)* |
| 6 | Simulation metrics: tool_error_rate and avg_latency_ms | 0.5 d *(done)* |
| 7 | Simulation UI: status and "View runs" | 0.5 d |
| 8 | Configurable detector thresholds (env) | 0.5 d |
| 9 | Task datasets (create/list and use in simulations) | 1–2 d *(done)* |
| 10 | Failure clustering with embeddings (optional) | 2–3 d |

**Suggested order for next sprint:** 1 → 2 → 7 → 8, then clustering (10) if Postgres is available.

---

## Dataset collection

The existing store of **runs + failures** is the "Agent Failure Benchmark Dataset." Export is available via `GET /api/v1/runs/export?format=csv|json`. Task datasets (`/api/v1/datasets`) are named prompt sets for simulations; the benchmark dataset grows from every ingested run and detector output.

---

## References

- [IMPROVEMENTS.md](IMPROVEMENTS.md) – Prioritized improvement list (responsive, workers in cloud, etc.).
- [failure_patterns_design.md](failure_patterns_design.md) – Text-based patterns; embedding-based clustering is the next step.
- [postgres_schema.md](postgres_schema.md) – Target schema for Postgres and pgvector (run_embeddings, failure_clusters).
