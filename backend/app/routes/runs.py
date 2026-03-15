from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.deps.auth import require_api_key
from app.deps.rate_limit import rate_limit_ingest
from app.db.base import get_session
from app.db.models import Failure, Run, Step
from app.schemas import RunIn


router = APIRouter(prefix="/api/v1/runs", tags=["runs"])


@router.post("")
async def ingest_run(
    run_in: RunIn,
    _auth: None = Depends(require_api_key),
    _limit: None = Depends(rate_limit_ingest),
    db: Session = Depends(get_session),
) -> dict:
    raw_sim_id = (run_in.env or {}).get("simulation_id")
    sim_id = None
    if isinstance(raw_sim_id, str):
        try:
            sim_id = UUID(raw_sim_id)
        except ValueError:
            sim_id = None
    run = Run(
        agent_id=run_in.agent_id,
        agent_version=run_in.agent_version,
        input={"user_query": run_in.user_query},
        output={"final_answer": run_in.final_answer},
        latency_ms=run_in.latency_ms,
        env=run_in.env or {},
        simulation_id=sim_id,
    )
    db.add(run)
    db.flush()

    for s in run_in.steps:
        step = Step(
            run_id=run.id,
            idx=s.idx,
            step_type=s.step_type,
            timestamp=s.timestamp,
            request=s.request,
            response=s.response,
            meta=s.metadata,
        )
        db.add(step)

    db.commit()
    return {"run_id": str(run.id)}


@router.get("")
async def list_runs(
    limit: int = 50,
    offset: int = 0,
    simulation_id: str | None = None,
    agent_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    db: Session = Depends(get_session),
) -> list[dict]:
    limit = max(1, min(limit, 200))
    q = db.query(Run)
    if simulation_id:
        try:
            sim_uuid = UUID(simulation_id)
        except ValueError:
            sim_uuid = None
        if sim_uuid:
            q = q.filter(Run.simulation_id == sim_uuid)
    if agent_id:
        q = q.filter(Run.agent_id == agent_id)
    if date_from:
        try:
            if len(date_from) == 10:
                q = q.filter(Run.created_at >= datetime.fromisoformat(date_from + "T00:00:00"))
            else:
                q = q.filter(Run.created_at >= datetime.fromisoformat(date_from.replace("Z", "+00:00")))
        except ValueError:
            pass
    if date_to:
        try:
            if len(date_to) == 10:
                q = q.filter(Run.created_at <= datetime.fromisoformat(date_to + "T23:59:59"))
            else:
                q = q.filter(Run.created_at <= datetime.fromisoformat(date_to.replace("Z", "+00:00")))
        except ValueError:
            pass
    q = q.order_by(Run.created_at.desc()).offset(offset).limit(limit)
    runs = q.all()
    run_ids = [r.id for r in runs]
    failure_counts = {}
    if run_ids:
        rows = (
            db.query(Failure.run_id, func.count(Failure.id).label("n"))
            .filter(Failure.run_id.in_(run_ids))
            .group_by(Failure.run_id)
            .all()
        )
        failure_counts = {r.run_id: r.n for r in rows}
    return [
        {
            "id": str(r.id),
            "created_at": r.created_at.isoformat(),
            "agent_id": r.agent_id,
            "agent_version": r.agent_version,
            "latency_ms": r.latency_ms,
            "status": r.status,
            "user_query": (r.input or {}).get("user_query", "")[:120] or None,
            "failure_count": failure_counts.get(r.id, 0),
        }
        for r in runs
    ]


@router.get("/agents")
async def list_agents(db: Session = Depends(get_session)) -> list[str]:
    """List distinct agent_id values for filter dropdowns."""
    rows = db.query(Run.agent_id).distinct().order_by(Run.agent_id).all()
    return [r.agent_id for r in rows]


@router.get("/export")
async def export_runs(
    format: str = "json",
    limit: int = 1000,
    agent_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    db: Session = Depends(get_session),
):
    """Export runs as JSON or CSV. Max limit 5000."""
    limit = max(1, min(limit, 5000))
    q = db.query(Run).order_by(Run.created_at.desc()).limit(limit)
    if agent_id:
        q = q.filter(Run.agent_id == agent_id)
    if date_from:
        try:
            if len(date_from) == 10:
                q = q.filter(Run.created_at >= datetime.fromisoformat(date_from + "T00:00:00"))
            else:
                q = q.filter(Run.created_at >= datetime.fromisoformat(date_from.replace("Z", "+00:00")))
        except ValueError:
            pass
    if date_to:
        try:
            if len(date_to) == 10:
                q = q.filter(Run.created_at <= datetime.fromisoformat(date_to + "T23:59:59"))
            else:
                q = q.filter(Run.created_at <= datetime.fromisoformat(date_to.replace("Z", "+00:00")))
        except ValueError:
            pass
    runs = q.all()
    if format == "csv":
        import csv
        import io
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["id", "created_at", "agent_id", "agent_version", "status", "latency_ms", "user_query", "final_answer"])
        for r in runs:
            inp = r.input or {}
            out = r.output or {}
            w.writerow([
                str(r.id),
                r.created_at.isoformat() if r.created_at else "",
                r.agent_id or "",
                r.agent_version or "",
                r.status or "",
                r.latency_ms or "",
                (inp.get("user_query") or "")[:500],
                (out.get("final_answer") or "")[:500],
            ])
        buf.seek(0)
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=runs.csv"},
        )
    return [
        {
            "id": str(r.id),
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "agent_id": r.agent_id,
            "agent_version": r.agent_version,
            "status": r.status,
            "latency_ms": r.latency_ms,
            "user_query": (r.input or {}).get("user_query"),
            "final_answer": (r.output or {}).get("final_answer"),
        }
        for r in runs
    ]


@router.get("/{run_id}")
async def get_run(run_id: str, db: Session = Depends(get_session)) -> dict:
    try:
        run_uuid = UUID(run_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="run_not_found")

    run = db.query(Run).filter(Run.id == run_uuid).first()
    if not run:
        raise HTTPException(status_code=404, detail="run_not_found")

    steps = (
        db.query(Step)
        .filter(Step.run_id == run.id)
        .order_by(Step.idx.asc())
        .all()
    )

    failures = db.query(Failure).filter(Failure.run_id == run.id).all()

    return {
        "run": {
            "id": str(run.id),
            "created_at": run.created_at.isoformat(),
            "agent_id": run.agent_id,
            "agent_version": run.agent_version,
            "input": run.input,
            "output": run.output,
            "latency_ms": run.latency_ms,
            "status": run.status,
            "env": run.env,
        },
        "steps": [
            {
                "id": str(s.id),
                "idx": s.idx,
                "step_type": s.step_type,
                "timestamp": s.timestamp.isoformat(),
                "request": s.request,
                "response": s.response,
                "metadata": s.meta,
            }
            for s in steps
        ],
        "failures": [
            {
                "id": str(f.id),
                "detector": f.detector,
                "score": f.score,
                "label": f.label,
                "explanation": f.explanation,
                "extra": f.extra,
            }
            for f in failures
        ],
    }
