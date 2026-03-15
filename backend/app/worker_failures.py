from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.db.base import SessionLocal
from app.db.models import Failure, Run, Step
from app.detectors.hallucination import detect_hallucination
from app.detectors.planning import detect_planning_failure
from app.detectors.tool_misuse import detect_tool_misuse


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

    failures.extend(await detect_hallucination(run_dict))
    failures.extend(await detect_planning_failure(run_dict))
    failures.extend(await detect_tool_misuse(run_dict))

    # compute overall reliability score from individual detectors
    overall_score = 100
    for f in failures:
        det = f.get("detector")
        risk = f.get("score") or 0
        if det == "hallucination":
            overall_score -= int(risk * 0.4)
        elif det == "planning_failure":
            overall_score -= int(risk * 0.3)
        elif det == "tool_misuse":
            overall_score -= int(risk * 0.2)
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

    for f in failures:
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
    while True:
        await process_pending_runs_once()
        await asyncio.sleep(poll_interval_seconds)


if __name__ == "__main__":
    asyncio.run(main_loop())

