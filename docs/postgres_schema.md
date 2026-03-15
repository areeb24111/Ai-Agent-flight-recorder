# Postgres + pgvector schema (future)

This document describes the target schema for a Postgres deployment and where pgvector will live. No migration is run yet; use it when moving off SQLite.

---

## Current tables (map 1:1 from SQLAlchemy models)

### runs

| Column               | Type         | Notes                    |
|----------------------|--------------|--------------------------|
| id                   | UUID         | PK                       |
| created_at           | TIMESTAMP    |                          |
| agent_id             | VARCHAR      | indexed                  |
| agent_version        | VARCHAR      |                          |
| input                | JSONB        | user_query, context      |
| output               | JSONB        | final_answer, etc.       |
| latency_ms           | INTEGER      |                          |
| status               | VARCHAR      | default 'success'        |
| processed_for_failures| INTEGER      | default 0                |
| env                  | JSONB        |                          |
| simulation_id        | UUID         | nullable, FK → simulations, indexed |

### steps

| Column    | Type      | Notes        |
|-----------|-----------|--------------|
| id       | UUID      | PK           |
| run_id   | UUID      | FK → runs    |
| idx      | INTEGER   |              |
| step_type| VARCHAR   |              |
| timestamp| TIMESTAMP |              |
| request  | JSONB     |              |
| response | JSONB     |              |
| metadata | JSONB     | (meta in ORM)|

### failures

| Column      | Type    | Notes        |
|-------------|---------|--------------|
| id         | UUID    | PK           |
| run_id     | UUID    | FK → runs    |
| step_id    | UUID    | FK → steps, nullable |
| detector   | VARCHAR | e.g. hallucination, planning_failure |
| score      | INTEGER | 0–100        |
| label      | VARCHAR | nullable     |
| explanation| TEXT    | nullable     |
| extra      | JSONB   | nullable     |

### simulations

| Column         | Type      | Notes     |
|----------------|-----------|-----------|
| id            | UUID      | PK        |
| created_at    | TIMESTAMP |           |
| name          | VARCHAR   |           |
| agent_endpoint| VARCHAR   |           |
| task_template | VARCHAR   |           |
| num_runs      | INTEGER   |           |
| status        | VARCHAR   | pending, completed, etc. |
| metrics       | JSONB     | nullable  |

---

## Future tables (for clustering / embeddings)

### run_embeddings (optional, for failure-pattern clustering)

| Column    | Type           | Notes                          |
|-----------|----------------|--------------------------------|
| id        | UUID           | PK                             |
| run_id    | UUID           | FK → runs                      |
| embedding | VECTOR(1536)   | pgvector; e.g. run summary or concatenated failure text |
| created_at| TIMESTAMP      |                                |

Requires the pgvector extension: `CREATE EXTENSION IF NOT EXISTS vector;`

### clusters (optional, for grouping similar failures)

| Column   | Type    | Notes                |
|----------|---------|----------------------|
| id       | UUID    | PK                   |
| name     | VARCHAR | e.g. "hallucination: dates" |
| detector | VARCHAR |                      |
| summary  | TEXT    | optional              |
| run_ids  | JSONB   | or a junction table   |
| created_at | TIMESTAMP |                  |

---

## Switching from SQLite to Postgres

1. Set `DATABASE_URL` in the environment to a Postgres URL, e.g.  
   `postgresql://user:password@host:5432/dbname`  
   (For local Postgres: `postgresql://postgres:postgres@localhost:5432/agent_recorder`.)

2. Ensure the Postgres server has the same schema. Either:
   - Let the app create tables on startup (`Base.metadata.create_all(bind=engine)` in `main.py`), or
   - Run migrations if you introduce a migration tool later.

3. Restart the API and all workers so they use the new `DATABASE_URL`. No code changes are required; only the env var changes.

---

## Migrating existing SQLite data to Postgres (later)

When you are ready to move data from an existing SQLite file to Postgres:

1. **Stop the app and workers** so nothing writes to SQLite or Postgres during the migration.

2. **Export from SQLite**  
   Use a small script that:
   - Connects to SQLite (`sqlite:///./agent_recorder.db`) and to Postgres (`DATABASE_URL`).
   - Reads from SQLite: `runs`, `steps`, `failures`, `simulations` (in that order to respect FKs).
   - Inserts into Postgres, reusing the same UUIDs so relationships are preserved.

3. **Import into Postgres**  
   Ensure Postgres tables exist (run the app once against Postgres so `create_all` runs, or run DDL by hand). Then run the export script with the Postgres URL as the target.

4. **Point the app at Postgres**  
   Set `DATABASE_URL` to the Postgres URL and start the app and workers again.

No migration tooling (Alembic, etc.) is required for this one-off move; a script that uses SQLAlchemy models to read from SQLite and write to Postgres is enough. For ongoing schema changes after you are on Postgres, consider adding Alembic or similar.
