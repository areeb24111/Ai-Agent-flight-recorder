# Changelog

All notable changes to the Agent Flight Recorder project.

## [1.0.0] – 2025-03

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

- See [docs/IMPROVEMENTS.md](docs/IMPROVEMENTS.md) for planned work.
