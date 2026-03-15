from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.base import get_session
from app.db.models import Failure, Run

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])

DETECTORS = ("hallucination", "planning_failure", "tool_misuse", "reasoning_loop", "memory_contradiction")


def _failure_counts_by_day(
    db: Session, cutoff: datetime, detector: str
) -> dict[str, int]:
    """Return map day -> count of distinct runs that have at least one failure for this detector."""
    q = (
        db.query(
            func.date(Run.created_at).label("day"),
            func.count(func.distinct(Run.id)).label("n"),
        )
        .join(Failure, Failure.run_id == Run.id)
        .filter(Run.created_at >= cutoff, Failure.detector == detector)
        .group_by(func.date(Run.created_at))
        .all()
    )
    return {str(row.day): row.n for row in q}


@router.get("/runs_summary")
async def runs_summary(
    days: int = 7,
    by_detector: bool = False,
    db: Session = Depends(get_session),
) -> dict:
    """
    Runs per day with hallucination_rate. If by_detector=true, also returns
    failure_rate_per_detector: { day: { detector: rate_pct } } and
    latency_avg_ms per day when available.
    """
    cutoff = datetime.utcnow() - timedelta(days=days)

    runs_q = (
        db.query(
            func.date(Run.created_at).label("day"),
            func.count(Run.id).label("count"),
            func.avg(Run.latency_ms).label("avg_latency"),
        )
        .filter(Run.created_at >= cutoff)
        .group_by(func.date(Run.created_at))
        .order_by(func.date(Run.created_at))
        .all()
    )
    runs_per_day = [
        {
            "day": str(row.day),
            "count": row.count,
            "avg_latency_ms": int(row.avg_latency) if row.avg_latency is not None else None,
        }
        for row in runs_q
    ]

    halluc_by_day = _failure_counts_by_day(db, cutoff, "hallucination")
    summary: list[dict[str, Any]] = []
    for item in runs_per_day:
        day = item["day"]
        total = item["count"]
        hruns = halluc_by_day.get(day, 0)
        rate = round(100 * hruns / total) if total else 0
        row = {**item, "hallucination_rate": rate}
        summary.append(row)

    out: dict[str, Any] = {"runs_per_day": summary}

    if by_detector:
        failure_counts: dict[str, dict[str, int]] = {}
        for det in DETECTORS:
            by_day = _failure_counts_by_day(db, cutoff, det)
            for day, n in by_day.items():
                if day not in failure_counts:
                    failure_counts[day] = {}
                failure_counts[day][det] = n
        # Convert to rates per day
        failure_rate_per_detector: dict[str, dict[str, int]] = {}
        for item in summary:
            day = item["day"]
            total = item["count"]
            failure_rate_per_detector[day] = {}
            for det in DETECTORS:
                n = (failure_counts.get(day) or {}).get(det, 0)
                failure_rate_per_detector[day][det] = round(100 * n / total) if total else 0
        out["failure_rate_per_detector"] = failure_rate_per_detector

    return out
