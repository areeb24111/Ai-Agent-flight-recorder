"""
Task datasets API: create and list named task sets for simulation runs.
When simulation.dataset_id is set, worker_simulations can pull tasks from the dataset
instead of generate_task(template). Skeleton for future expansion (e.g. CSV upload).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.base import get_session
from app.db.models import TaskDataset
from app.schemas import TaskDatasetCreate

router = APIRouter(prefix="/api/v1/datasets", tags=["datasets"])


@router.post("")
async def create_dataset(
    payload: TaskDatasetCreate,
    db: Session = Depends(get_session),
) -> dict:
    """Create a named task dataset. tasks = list of {query, env}."""
    if not payload.tasks:
        raise HTTPException(status_code=422, detail="tasks must be a non-empty list")
    normalized = []
    for t in payload.tasks:
        if not isinstance(t, dict):
            continue
        q = t.get("query") or t.get("question") or ""
        env = t.get("env") or {}
        normalized.append({"query": str(q)[:2000], "env": env})
    if not normalized:
        raise HTTPException(status_code=422, detail="tasks must contain at least one object with 'query'")
    ds = TaskDataset(name=payload.name.strip() or "unnamed", payload={"tasks": normalized})
    db.add(ds)
    db.commit()
    db.refresh(ds)
    return {"dataset_id": str(ds.id), "name": ds.name, "task_count": len(normalized)}


@router.get("")
async def list_datasets(db: Session = Depends(get_session)) -> list[dict]:
    """List all task datasets (id, name, task_count, created_at)."""
    rows = db.query(TaskDataset).order_by(TaskDataset.created_at.desc()).all()
    return [
        {
            "id": str(r.id),
            "name": r.name,
            "task_count": len((r.payload or {}).get("tasks", [])),
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.get("/{dataset_id}")
async def get_dataset(dataset_id: str, db: Session = Depends(get_session)) -> dict:
    """Get a dataset by id (payload includes full tasks list)."""
    from uuid import UUID
    try:
        uid = UUID(dataset_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="dataset_not_found")
    ds = db.query(TaskDataset).filter(TaskDataset.id == uid).first()
    if not ds:
        raise HTTPException(status_code=404, detail="dataset_not_found")
    return {
        "id": str(ds.id),
        "name": ds.name,
        "payload": ds.payload,
        "created_at": ds.created_at.isoformat() if ds.created_at else None,
    }
