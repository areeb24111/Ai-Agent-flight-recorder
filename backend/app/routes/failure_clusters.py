"""
Failure clusters API: groups of similar failures (text-based for now; embedding-based later).
Returns cluster id, name, detector, summary, run_ids for dashboard "Clusters" view.
"""

import hashlib
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.base import get_session
from app.db.models import Failure, Run

router = APIRouter(prefix="/api/v1/failure_clusters", tags=["failure_clusters"])


def _normalize_explanation(explanation: str | None) -> str:
    if not explanation or not explanation.strip():
        return "unknown"
    s = explanation[:80].lower().strip()
    return " ".join(s.split())


@router.get("")
async def list_failure_clusters(
    detector: str | None = None,
    days: int | None = 7,
    db: Session = Depends(get_session),
) -> dict:
    """
    Return failure clusters: grouped by (detector, normalized explanation) with
    cluster id, name, summary, run_ids. Text-based grouping for now; embedding-based
    clustering can be added later (see docs/postgres_schema.md).
    """
    q = db.query(Failure).join(Run, Failure.run_id == Run.id).filter(Failure.detector != "overall")
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

    clusters = []
    for (det, key), items in groups.items():
        run_ids = list(dict.fromkeys(str(f.run_id) for f in items))[:10]
        cluster_id = hashlib.sha256(f"{det}:{key}".encode()).hexdigest()[:12]
        name = f"{det}: {key[:50]}{'…' if len(key) > 50 else ''}"
        clusters.append(
            {
                "id": cluster_id,
                "name": name,
                "detector": det,
                "summary": key,
                "run_ids": run_ids,
                "count": len(items),
            }
        )

    clusters.sort(key=lambda c: c["count"], reverse=True)
    return {"clusters": clusters}
