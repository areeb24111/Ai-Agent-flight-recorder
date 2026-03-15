# Pricing and quotas (design only — not current)

**Not selling or monetizing right now.** This doc is for possible future use. No billing or quota enforcement is implemented.

---

## 1. Current state

- **Rate limiting:** Per client IP, in-memory: ingest (e.g. 120/min), simulation creation (e.g. 30/min). Configurable via env; set to 0 to disable.
- **Auth:** Optional `API_KEY` on write endpoints (ingest, create simulation). No per-key identity or quotas.

---

## 2. Per-API-key quotas (design)

To support multiple teams or customers, associate usage with an API key and enforce limits per key.

**Metrics to track (per key, per billing window):**

- **Runs ingested** – count of `POST /api/v1/runs` per month (or per day).
- **Simulation runs** – total “run equivalents” created via simulations (e.g. sum of `num_runs` for simulations created this month), or count of simulation jobs.

**Enforcement options:**

1. **Database:** Table `api_key_usage(key_id, window_start, runs_count, simulation_runs_count)`. On each ingest/simulation create, resolve key → key_id, increment counter, then check against plan limits before accepting the request.
2. **Cache (Redis):** Key `usage:{key_id}:{window}` with counters; same check-and-increment.
3. **Hybrid:** Count in DB for persistence; cache for fast “over limit?” checks.

**Response when over limit:** Return `429` with a body like `{ "detail": { "code": "quota_exceeded", "message": "Runs limit for this month exceeded.", "retry_after": "next month" } }`.

---

## 3. Tier table (sketch)

| Tier | Runs / month | Simulations / month | Retention | Notes |
|------|----------------|---------------------|-----------|--------|
| **Free** | 1,000 | 10 jobs | 7 days | Single API key; no SLA. |
| **Pro** | 50,000 | 200 jobs | 90 days | Multiple keys; email support. |
| **Enterprise** | Custom | Custom | Custom | On-prem or dedicated; SLA; SSO. |

- **Runs:** Ingested run count.
- **Simulations:** Number of simulation *jobs* created (each job can have many `num_runs`); optionally cap total runs executed per month (e.g. 10,000 run executions on Pro).
- **Retention:** How long run/trace data is kept before deletion or archival.

Adjust numbers when you have real usage and cost data. Use this as a starting point for positioning and for implementing quota checks later.
