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
from app.db.models import Simulation, Run, Failure


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


async def run_simulation_once(db: Session, sim: Simulation) -> None:
    async with httpx.AsyncClient(timeout=30) as client:
        for _ in range(sim.num_runs):
            payload = generate_task(sim.task_template)
            payload["env"]["simulation_id"] = str(sim.id)
            await _post_with_retry(client, sim.agent_endpoint, payload)

    # Recompute metrics: total_runs = runs linked via simulation_id; success_rate = % with
    # status "success"; hallucination_rate = % of runs with at least one hallucination failure.
    runs = db.query(Run).filter(Run.simulation_id == sim.id).all()
    total = len(runs)
    if total == 0:
        sim.metrics = {"total_runs": 0, "success_rate": 0, "hallucination_rate": 0, "avg_latency_ms": None}
    else:
        successes = sum(1 for r in runs if r.status == "success")
        avg_latency = int(
            sum((r.latency_ms or 0) for r in runs) / max(1, total)
        )
        hallucinated_run_count = (
            db.query(Failure.run_id)
            .filter(Failure.run_id.in_([r.id for r in runs]), Failure.detector == "hallucination")
            .distinct()
            .count()
        )
        sim.metrics = {
            "total_runs": total,
            "success_rate": round(100 * successes / total),
            "hallucination_rate": round(100 * hallucinated_run_count / total),
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
    while True:
        await process_pending_simulations_once()
        await asyncio.sleep(poll_interval_seconds)


if __name__ == "__main__":
    asyncio.run(main_loop())

