# Improvement roadmap

Prioritized ideas to make the project better. Tick off as you ship.

---

## Done (recent)

- [x] Health check includes DB connectivity (`/health` returns `database: "connected"` or `"error"`).
- [x] Runs list includes truncated `user_query` so you can distinguish runs at a glance.
- [x] Empty state: when there are no runs, show a short hint (SDK, RUNBOOK, `send_test_run.py`).
- [x] Removed duplicate error message in Recent Runs.
- [x] README: added "Why", live demo links, OpenAPI docs link.
- [x] **Pagination / "Load more"** – Frontend "Load more" button; backend offset/limit.
- [x] **Filter runs** – By agent_id and date range in UI and API.
- [x] **OpenAPI description** – FastAPI title, description, version for /docs.
- [x] **Dashboard: refresh button** – Manual refresh for runs, analytics, patterns, simulations.
- [x] **Run list: failure summary** – API returns failure_count; UI shows "N failures" pill.
- [x] **Loading skeletons** – For runs list and run detail.
- [x] **Tooltips** – Title attributes on metric cards.
- [x] **Copy run ID** – Button in run detail.
- [x] **Export runs** – GET /api/v1/runs/export; dashboard "Export CSV" button.
- [x] **Retry in workers** – Detector and simulation HTTP retries with backoff.
- [x] **Webhook** – WEBHOOK_URL + WEBHOOK_THRESHOLD env.
- [x] **CHANGELOG.md**, screenshot placeholder in README, SDK examples, CONTRIBUTING.md.

---

## High impact (next)

- [ ] **Responsive layout** – Improve tables and cards on small screens.
- [ ] **Workers in the cloud** – Run workers as Render/other background workers (see DEPLOY.md).


---

## UX polish

- [ ] Dark mode or theme toggle (optional).
- [ ] Copy curl for run (for debugging).

---

## Reliability & ops

- [ ] **Postgres by default** for deployed app (see docs/postgres_schema.md).
- [ ] **Structured logging** (JSON logs with request ID).

---

## Features

- [ ] **Search** – Full-text search on run input/output or failure explanations.
- [ ] **Configurable detector thresholds** – Env or API to tune risk cutoffs.
- [ ] **Run comparison** – Side-by-side view of two runs.

Use this list to pick the next batch; start with "High impact" then "UX polish" or "Reliability" depending on whether you care more about first-time experience or production readiness.
