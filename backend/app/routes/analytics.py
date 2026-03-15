from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.base import get_session
from app.db.models import Failure, Run


router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/runs_summary")
async def runs_summary(days: int = 7, db: Session = Depends(get_session)) -> dict:
    cutoff = datetime.utcnow() - timedelta(days=days)

    # runs per day (use date() for SQLite/Postgres compatibility)
    runs_q = (
        db.query(
            func.date(Run.created_at).label("day"),
            func.count(Run.id).label("count"),
        )
        .filter(Run.created_at >= cutoff)
        .group_by(func.date(Run.created_at))
        .order_by(func.date(Run.created_at))
        .all()
    )
    runs_per_day = [{"day": str(row.day), "count": row.count} for row in runs_q]

    # hallucination run count per day (runs that have at least one hallucination failure)
    halluc_q = (
        db.query(
            func.date(Run.created_at).label("day"),
            func.count(func.distinct(Run.id)).label("halluc_runs"),
        )
        .join(Failure, Failure.run_id == Run.id)
        .filter(
            Run.created_at >= cutoff,
            Failure.detector == "hallucination",
        )
        .group_by(func.date(Run.created_at))
        .all()
    )
    halluc_by_day = {str(row.day): row.halluc_runs for row in halluc_q}

    summary = []
    for item in runs_per_day:
        day = item["day"]
        total = item["count"]
        hruns = halluc_by_day.get(day, 0)
        rate = round(100 * hruns / total) if total else 0
        summary.append({**item, "hallucination_rate": rate})

    return {"runs_per_day": summary}
