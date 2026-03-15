# Changelog

All notable changes to the Agent Flight Recorder project.

## [1.1.0] – 2026-03

### Added

- **README** – Reformatted with Problem, Solution, Features, Dashboard Screenshot, Architecture, Installation, Usage, Simulation Testing, Roadmap, Contributing, License. Added architecture diagram and dashboard screenshot placeholders.
- **Demo script** – `backend/demo_intentional_failures.py` sends 7 runs that intentionally trigger detectors (hallucination, tool misuse, reasoning loop, memory contradiction, planning, kitchen sink). Clear 401 hint when API key is required.
- **Custom simulation template** – Optional `template_config: { query, env }` for simulations; UI supports "custom" task template with custom query field. Backend and worker use `template_config` when set.
- **Five failure detectors** – reasoning_loop and memory_contradiction detectors; configurable per-detector thresholds via env (DETECTOR_*_THRESHOLD). Failure worker runs all five and persists only failures above threshold.
- **Failure clusters API & UI** – `GET /api/v1/failure_clusters` (text-based grouping); dashboard section for failure clusters with 7d/30d filter.
- **Analytics by detector** – `GET /api/v1/analytics/runs_summary?by_detector=true` returns failure_rate_per_detector per day; dashboard chart for failure rate by detector.
- **Detectors & datasets API** – `GET /api/v1/detectors`; `POST/GET /api/v1/datasets` and simulations can use `dataset_id` for task datasets.
- **Dashboard** – Trace timeline (collapsible steps), detector badges on run list, failure pills by severity, simulation "View runs" button, dark mode only, copy curl in run detail. Responsive layout.

### Changed

- Runs list includes `failure_detectors` (list of detector names that fired). Simulation model has `template_config` and `dataset_id`; worker uses template_config for custom prompt and dataset for tasks.
- SQLite migrations in `app.db.base.run_sqlite_migrations()` (template_config, dataset_id, etc.) run on API and worker startup.

## [1.0.0] – 2026-03

### Added

- **Trace ingestion** – `POST /api/v1/runs` to store agent runs and steps (SDK + HTTP).
- **Failure detection** – Background worker runs hallucination, planning, and tool-misuse detectors; scores stored per run.
- **Simulations** – Create batch jobs that call your agent endpoint with synthetic tasks; view success/hallucination rates.
- **Dashboard** – React dashboard: metrics, recent runs list, run detail (steps + failures), analytics chart, failure patterns, simulation filtering.
- **Filters & export** – Filter runs by `agent_id`, date range; "Load more" pagination; export runs as CSV or JSON via `GET /api/v1/runs/export`.
- **Refresh & copy** – Manual refresh for runs/analytics/patterns; copy run ID from run detail.
- **OpenAPI** – Improved API title/description and tag summaries for `/docs`.
- **Webhook** – Optional `WEBHOOK_URL` + `WEBHOOK_THRESHOLD`: POST when a run has failure score above threshold.
- **Worker retries** – Failure and simulation workers retry LLM/HTTP calls with backoff.
- **Health** – `/health` includes database connectivity check.
- **Auth & rate limits** – Optional `API_KEY`; per-IP rate limits for ingest and simulations.
- **Docs** – RUNBOOK, DEPLOY, PUBLISH_AND_MARKET, IMPROVEMENTS roadmap, Postgres schema design.

### Changed

- Runs list API returns `user_query` (truncated) and `failure_count` per run.
- Metric card "Hallucination Alerts" renamed to "Runs with Failures" (count of runs with any failure).
- Empty state in dashboard shows hint for sending first run (SDK, RUNBOOK).

## [Unreleased]

- Planned work tracked in GitHub issues.
