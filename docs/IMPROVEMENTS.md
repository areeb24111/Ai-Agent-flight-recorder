# Improvement roadmap

Prioritized ideas to make the project better. Aligned with the [AI Observability Devtool evolution plan](ROADMAP.md). Tick off as you ship.

---

## Done (recent)

**Core & API**
- [x] Health check includes DB connectivity (`/health` returns `database: "connected"` or `"error"`).
- [x] Runs list includes truncated `user_query`; filters (agent_id, date range); pagination / "Load more"; failure_count pill.
- [x] Empty state: when there are no runs, show a short hint (SDK, RUNBOOK).
- [x] **Five failure detectors:** hallucination, planning_failure, tool_misuse, **reasoning_loop**, **memory_contradiction** (see ROADMAP).
- [x] **Analytics extended:** `GET /api/v1/analytics/runs_summary?by_detector=true` returns per-detector failure rates and avg_latency_ms per day.
- [x] **Simulation metrics:** total_runs, success, success_rate, hallucination_rate, **tool_error_rate**, avg_latency_ms in simulation.metrics.
- [x] **Task datasets:** POST/GET /api/v1/datasets; Simulation.dataset_id optional; worker uses dataset tasks when set.
- [x] **GET /api/v1/detectors** – List detector IDs and default thresholds.

**Dashboard & UX**
- [x] OpenAPI description; dashboard refresh button; loading skeletons; tooltips on metric cards.
- [x] Copy run ID; Export runs (CSV); run detail with steps and failures.
- [x] Retry in workers; webhook (WEBHOOK_URL / WEBHOOK_THRESHOLD).
- [x] CHANGELOG.md, CONTRIBUTING.md, SDK examples in README.

---

## Next (by plan – see [ROADMAP.md](ROADMAP.md))

**Week 1–2 (high impact)**
- [x] **Trace timeline UI** – Single-run view as vertical timeline; collapsible request/response (plan issue #1).
- [x] **Failure badges** – Detector-wise badges in run list and run detail with severity color (plan issue #2).
- [x] **Simulation: "View runs"** – Button on each simulation; scrolls to runs filtered by simulation_id (plan issue #7).
- [x] **Configurable detector thresholds** – Env vars DETECTOR_*_THRESHOLD; worker only persists when score >= threshold (plan issue #8).
- [x] **Responsive layout** – Tables and cards usable on small screens (breakpoints 960px, 768px, 480px).
- [x] **Workers in the cloud** – DEPLOY.md section with step-by-step (same host, separate worker services, Render background workers).
- [x] **Analytics charts** – Failure rate by detector over time in Analytics section.
- [x] **Dark mode** – Toggle in header; localStorage; CSS variables.
- [x] **Copy curl** – Run detail button copies curl command for GET run.
- [x] **Failure clusters** – GET /api/v1/failure_clusters; Clusters section in dashboard (text-based; embedding-based when Postgres + pgvector).

**Week 3–4 (polish & clustering)**
- [ ] **Analytics charts** – Failure rates over time by detector; latency p50/p95 when backend supports.
- [ ] **Failure clustering (embeddings)** – Postgres + pgvector; run_embeddings, failure_clusters (plan issue #10; defer if no Postgres).
- [ ] **Postgres by default** for deployed app (see postgres_schema.md).
- [ ] **Structured logging** – JSON logs with request ID.

---

## UX polish

- [ ] Dark mode or theme toggle (optional).
- [ ] Copy curl for run (for debugging).

---

## Features (backlog)

- [ ] **Search** – Full-text search on run input/output or failure explanations.
- [ ] **Run comparison** – Side-by-side view of two runs.

Use [ROADMAP.md](ROADMAP.md) for the full 2–4 week plan and GitHub issues list.
