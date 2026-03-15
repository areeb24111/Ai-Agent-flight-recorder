from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.base import get_session
from app.db.models import Failure, Run

router = APIRouter(prefix="/api/v1/failure_patterns", tags=["failure_patterns"])


def _normalize_explanation(explanation: str | None) -> str:
    if not explanation or not explanation.strip():
        return "unknown"
    s = explanation[:80].lower().strip()
    return " ".join(s.split())


@router.get("")
async def list_failure_patterns(
    detector: str | None = None,
    days: int | None = None,
    db: Session = Depends(get_session),
) -> dict:
    """
    Group failures by (detector, normalized explanation). Optional filter by detector
    and by runs in the last N days.
    """
    q = db.query(Failure).join(Run, Failure.run_id == Run.id)
    if detector:
        q = q.filter(Failure.detector == detector)
    if days is not None and days > 0:
        cutoff = datetime.utcnow() - timedelta(days=days)
        q = q.filter(Run.created_at >= cutoff)
    failures = q.all()

    groups: dict[tuple[str, str], list[Failure]] = defaultdict(list)
    for f in failures:
        key = _normalize_explanation(f.explanation)
        groups[(f.detector, key)].append(f)

    patterns: list[dict[str, Any]] = []
    for (det, key), items in groups.items():
        run_ids = list(dict.fromkeys(str(f.run_id) for f in items))[:5]
        patterns.append(
            {
                "detector": det,
                "explanation_key": key,
                "count": len(items),
                "example_run_ids": run_ids,
            }
        )

    # Sort by count descending so most common patterns appear first
    patterns.sort(key=lambda p: p["count"], reverse=True)
    return {"patterns": patterns}
