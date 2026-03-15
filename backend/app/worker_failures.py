from __future__ import annotations

import asyncio
from typing import Any, Dict, List

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings as app_settings
from app.db.base import SessionLocal
from app.db.models import Failure, Run, Step
from app.detectors.hallucination import detect_hallucination
from app.detectors.memory_contradiction import detect_memory_contradiction
from app.detectors.planning import detect_planning_failure
from app.detectors.reasoning_loop import detect_reasoning_loop
from app.detectors.tool_misuse import detect_tool_misuse


async def _with_retry(coro_fn, max_attempts: int = 3):
    for attempt in range(max_attempts):
        try:
            return await coro_fn()
        except Exception:
            if attempt == max_attempts - 1:
                raise
            await asyncio.sleep(1.0 * (attempt + 1))


async def process_run(db: Session, run: Run) -> None:
    # load steps for planning detection
    step_rows = (
        db.query(Step)
        .filter(Step.run_id == run.id)
        .order_by(Step.idx.asc())
        .all()
    )
    steps_payload = [
        {
            "step_type": s.step_type,
            "request": s.request,
            "response": s.response,
        }
        for s in step_rows
    ]

    run_dict: Dict[str, Any] = {
        "id": str(run.id),
        "input": run.input,
        "output": run.output,
        "env": run.env,
        "steps": steps_payload,
    }
    failures: List[Dict[str, Any]] = []

    try:
        failures.extend(await _with_retry(lambda: detect_hallucination(run_dict)))
        failures.extend(await _with_retry(lambda: detect_planning_failure(run_dict)))
        failures.extend(await _with_retry(lambda: detect_tool_misuse(run_dict)))
        failures.extend(await _with_retry(lambda: detect_reasoning_loop(run_dict)))
        failures.extend(await _with_retry(lambda: detect_memory_contradiction(run_dict)))
    except Exception:
        pass

    # compute overall reliability score from individual detectors
    overall_score = 100
    for f in failures:
        det = f.get("detector")
        risk = f.get("score") or 0
        if det == "hallucination":
            overall_score -= int(risk * 0.35)
        elif det == "planning_failure":
            overall_score -= int(risk * 0.25)
        elif det == "tool_misuse":
            overall_score -= int(risk * 0.2)
        elif det == "reasoning_loop":
            overall_score -= int(risk * 0.1)
        elif det == "memory_contradiction":
            overall_score -= int(risk * 0.1)
    overall_score = max(0, min(100, overall_score))

    if failures:
        failures.append(
            {
                "detector": "overall",
                "score": overall_score,
                "label": None,
                "explanation": f"Overall reliability score based on detectors: {overall_score}/100.",
                "extra": {},
            }
        )

    def _threshold_for(detector: str) -> int | None:
        m = {
            "hallucination": app_settings.detector_hallucination_threshold,
            "planning_failure": app_settings.detector_planning_failure_threshold,
            "tool_misuse": app_settings.detector_tool_misuse_threshold,
            "reasoning_loop": app_settings.detector_reasoning_loop_threshold,
            "memory_contradiction": app_settings.detector_memory_contradiction_threshold,
        }
        return m.get(detector)

    for f in failures:
        det = f.get("detector")
        if det and det != "overall":
            th = _threshold_for(det)
            if th is not None:
                score = f.get("score")
                if score is None or score < th:
                    continue
        db.add(
            Failure(
                run_id=run.id,
                step_id=None,
                detector=f["detector"],
                score=f.get("score"),
                label=f.get("label"),
                explanation=f.get("explanation"),
                extra=f.get("extra"),
            )
        )

    run.processed_for_failures = 1

    if app_settings.webhook_url and failures:
        max_score = max(
            (f.get("score") or 0) for f in failures if f.get("detector") != "overall"
        )
        if max_score >= app_settings.webhook_threshold:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    await client.post(
                        app_settings.webhook_url,
                        json={
                            "run_id": str(run.id),
                            "max_score": max_score,
                            "detectors": [f.get("detector") for f in failures if f.get("detector") != "overall"],
                        },
                    )
            except Exception:
                pass


async def process_pending_runs_once(batch_size: int = 20) -> None:
    db = SessionLocal()
    try:
        pending = (
            db.query(Run)
            .filter(Run.processed_for_failures == 0)
            .order_by(Run.created_at.asc())
            .limit(batch_size)
            .all()
        )
        if not pending:
            return

        for run in pending:
            await process_run(db, run)

        db.commit()
    finally:
        db.close()


async def main_loop(poll_interval_seconds: int = 10) -> None:
    from app.db.base import run_sqlite_migrations
    run_sqlite_migrations()
    while True:
        await process_pending_runs_once()
        await asyncio.sleep(poll_interval_seconds)


if __name__ == "__main__":
    asyncio.run(main_loop())

