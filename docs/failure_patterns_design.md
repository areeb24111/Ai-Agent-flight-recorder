# Failure patterns (design)

Lightweight grouping of similar failures without embeddings. The failure patterns API and UI are implemented (GET /api/v1/failure_patterns). **Evolution:** Embedding-based clustering (pgvector, run_embeddings, failure_clusters) is in the [ROADMAP](ROADMAP.md) (week 4 or post-MVP); see also [postgres_schema.md](postgres_schema.md).

---

## 1. Failure pattern concept

A **failure pattern** is a bucket of failures that share:

- **detector** (e.g. `hallucination`, `planning_failure`, `tool_misuse`)
- **normalized explanation** – short, stable key from the failure’s `explanation` text (e.g. first 80 chars, lowercased, whitespace collapsed)

**Fields to expose per pattern:**

| Field | Type | Description |
|-------|------|-------------|
| `detector` | string | Detector that produced the failures |
| `explanation_key` | string | Normalized summary (e.g. first 80 chars of explanation) |
| `count` | int | Number of failures in this bucket |
| `example_run_ids` | string[] | Up to 3–5 run IDs for “View runs” / drill-down |

Optional later: `label`, `avg_score`, `last_seen_at`.

---

## 2. Grouping function (no embeddings)

- Query all `Failure` rows (optionally filtered by `detector` or time range).
- Normalize `explanation`: take first 80 characters, strip, lowercase, collapse whitespace to a single space. If `explanation` is null/empty, use `"unknown"`.
- Group by `(detector, explanation_key)`.
- For each group: count rows, collect up to 5 distinct `run_id`s as `example_run_ids`.

Pseudocode:

```
def normalize_explanation(explanation: str | None) -> str:
    if not explanation or not explanation.strip():
        return "unknown"
    s = explanation[:80].lower().strip()
    return " ".join(s.split())

def compute_failure_patterns(failures: list[Failure]) -> list[FailurePattern]:
    groups = defaultdict(list)  # (detector, key) -> [Failure]
    for f in failures:
        key = normalize_explanation(f.explanation)
        groups[(f.detector, key)].append(f)
    return [
        FailurePattern(
            detector=d,
            explanation_key=k,
            count=len(items),
            example_run_ids=[f.run_id for f in items[:5]],
        )
        for (d, k), items in groups.items()
    ]
```

---

## 3. Backend: endpoint

- **GET** `/api/v1/failure_patterns`
  - Optional query: `detector=hallucination`, `days=7` (only failures from runs in last N days).
  - Response: list of pattern objects, e.g.  
    `[{ "detector": "hallucination", "explanation_key": "...", "count": 12, "example_run_ids": ["uuid1", "uuid2"] }, ...]`
  - Implementation: query `Failure` (join `Run` if filtering by `created_at`), then run the grouping function in Python. No new tables required for this version.

---

## 4. Frontend: UI

- **Placement:** “Patterns” tab in the dashboard, or a collapsible section under Analytics (e.g. “Failure patterns”).
- **Content:** Table with columns: Detector, Summary (explanation_key), Count, Actions.
  - “View runs” (or one run ID as link) opens run detail or filters Recent Runs to those run IDs.
- **Refresh:** Load on tab open or when Analytics is loaded; same `API_BASE` as rest of app.

This gives a minimal “see recurring failure types” experience; later you can add embeddings and `run_embeddings` / clusters and swap the grouping logic.
