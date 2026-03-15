"""
Simulation worker: runs pending simulation jobs by calling the agent endpoint
with synthetic tasks, then recomputes metrics from stored runs and failures.

Metrics semantics:
- total_runs: count of runs linked to this simulation (run.env.simulation_id == sim.id).
- success_rate: percentage of those runs with status == "success".
- hallucination_rate: percentage of runs where the hallucination detector recorded a failure.
- avg_latency_ms: mean latency_ms across those runs.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict

import httpx
from sqlalchemy.orm import Session

from app.db.base import SessionLocal
from app.db.models import Simulation, Run, Failure, TaskDataset


def generate_task(template: str) -> Dict[str, Any]:
    if template == "math_qa":
        return {"query": "What is 17 * 23?", "env": {"task_type": "math_qa"}}
    if template == "doc_qa":
        doc = "The Agent Flight Recorder logs all agent steps and failures."
        return {
            "query": "According to the docs, what does the Agent Flight Recorder log?",
            "env": {"task_type": "doc_qa", "doc_snippet": doc},
        }
    if template == "multi_turn":
        return {
            "query": "Help me debug my agent, ask me for logs first.",
            "env": {"task_type": "multi_turn"},
        }
    if template == "code_assist":
        return {
            "query": "Write a Python function to reverse a list.",
            "env": {"task_type": "code_assist"},
        }
    return {"query": "Say hello", "env": {"task_type": "generic"}}


async def _post_with_retry(client: httpx.AsyncClient, url: str, json: dict, max_attempts: int = 3) -> bool:
    for attempt in range(max_attempts):
        try:
            r = await client.post(url, json=json)
            if r.is_success:
                return True
        except Exception:
            pass
        if attempt < max_attempts - 1:
            await asyncio.sleep(1.0 * (attempt + 1))
    return False


def _get_tasks_for_simulation(db: Session, sim: Simulation) -> list[Dict[str, Any]]:
    """Return list of task payloads (query + env) for this simulation."""
    if sim.dataset_id:
        ds = db.query(TaskDataset).filter(TaskDataset.id == sim.dataset_id).first()
        if ds and ds.payload and isinstance(ds.payload.get("tasks"), list):
            tasks = []
            for t in ds.payload["tasks"][: sim.num_runs]:
                if isinstance(t, dict) and t.get("query"):
                    env = dict(t.get("env") or {})
                    env["simulation_id"] = str(sim.id)
                    tasks.append({"query": t["query"], "env": env})
            if tasks:
                return tasks
    # Custom template: use template_config.query (repeated num_runs times)
    if sim.template_config and isinstance(sim.template_config, dict) and sim.template_config.get("query"):
        q = str(sim.template_config["query"]).strip()
        if q:
            env = dict(sim.template_config.get("env") or {})
            env["simulation_id"] = str(sim.id)
            env["task_type"] = "custom"
            return [{"query": q, "env": env} for _ in range(sim.num_runs)]
    # Fallback: use task_template
    out = []
    for _ in range(sim.num_runs):
        g = generate_task(sim.task_template)
        env = dict(g.get("env") or {})
        env["simulation_id"] = str(sim.id)
        out.append({"query": g.get("query", ""), "env": env})
    return out


async def run_simulation_once(db: Session, sim: Simulation) -> None:
    tasks = _get_tasks_for_simulation(db, sim)
    if not tasks:
        # Ensure we have at least num_runs from template
        for _ in range(sim.num_runs):
            payload = generate_task(sim.task_template)
            payload.setdefault("env", {})["simulation_id"] = str(sim.id)
            tasks.append(payload)

    async with httpx.AsyncClient(timeout=30) as client:
        for payload in tasks:
            if "env" not in payload:
                payload["env"] = {}
            payload["env"]["simulation_id"] = str(sim.id)
            await _post_with_retry(client, sim.agent_endpoint, payload)

    # Recompute metrics: total_runs, success_rate, hallucination_rate, tool_error_rate, avg_latency_ms.
    runs = db.query(Run).filter(Run.simulation_id == sim.id).all()
    total = len(runs)
    run_ids = [r.id for r in runs]
    if total == 0:
        sim.metrics = {
            "total_runs": 0,
            "success": 0,
            "success_rate": 0,
            "hallucination_rate": 0,
            "tool_error_rate": 0,
            "avg_latency_ms": None,
        }
    else:
        successes = sum(1 for r in runs if r.status == "success")
        avg_latency = int(sum((r.latency_ms or 0) for r in runs) / total)
        hallucinated_run_count = (
            db.query(Failure.run_id)
            .filter(Failure.run_id.in_(run_ids), Failure.detector == "hallucination")
            .distinct()
            .count()
        )
        tool_error_run_count = (
            db.query(Failure.run_id)
            .filter(Failure.run_id.in_(run_ids), Failure.detector == "tool_misuse")
            .distinct()
            .count()
        )
        sim.metrics = {
            "total_runs": total,
            "success": successes,
            "success_rate": round(100 * successes / total),
            "hallucination_rate": round(100 * hallucinated_run_count / total),
            "tool_error_rate": round(100 * tool_error_run_count / total),
            "avg_latency_ms": avg_latency,
        }
    sim.status = "completed"


async def process_pending_simulations_once(batch_size: int = 5) -> None:
    db = SessionLocal()
    try:
        sims = (
            db.query(Simulation)
            .filter(Simulation.status == "pending")
            .order_by(Simulation.created_at.asc())
            .limit(batch_size)
            .all()
        )
        if not sims:
            return

        for sim in sims:
            sim.status = "running"
            db.commit()
            await run_simulation_once(db, sim)
            db.commit()
    finally:
        db.close()


async def main_loop(poll_interval_seconds: int = 10) -> None:
    from app.db.base import run_sqlite_migrations
    run_sqlite_migrations()
    while True:
        await process_pending_simulations_once()
        await asyncio.sleep(poll_interval_seconds)


if __name__ == "__main__":
    asyncio.run(main_loop())

