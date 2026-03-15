from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.deps.auth import require_api_key
from app.deps.rate_limit import rate_limit_simulations
from app.db.base import get_session
from app.db.models import Simulation
from app.schemas import SimulationCreate

router = APIRouter(prefix="/api/v1/simulations", tags=["simulations"])


@router.post("")
async def create_simulation(
    payload: SimulationCreate,
    _auth: None = Depends(require_api_key),
    _limit: None = Depends(rate_limit_simulations),
    db: Session = Depends(get_session),
) -> dict:
    dataset_id = None
    if payload.dataset_id:
        try:
            dataset_id = UUID(payload.dataset_id)
        except ValueError:
            pass
    sim = Simulation(
        name=payload.name,
        agent_endpoint=payload.agent_endpoint,
        task_template=payload.task_template,
        num_runs=payload.num_runs,
        status="pending",
        metrics={"total_runs": 0, "success": 0, "hallucinations": 0},
        dataset_id=dataset_id,
        template_config=payload.template_config,
    )
    db.add(sim)
    db.commit()
    db.refresh(sim)
    return {"simulation_id": str(sim.id)}


@router.get("")
async def list_simulations(db: Session = Depends(get_session)) -> list[dict]:
    sims = db.query(Simulation).order_by(Simulation.created_at.desc()).all()
    return [
        {
            "id": str(s.id),
            "created_at": s.created_at.isoformat(),
            "name": s.name,
            "agent_endpoint": s.agent_endpoint,
            "task_template": s.task_template,
            "num_runs": s.num_runs,
            "status": s.status,
            "metrics": s.metrics or {},
            "dataset_id": str(s.dataset_id) if s.dataset_id else None,
            "template_config": s.template_config,
        }
        for s in sims
    ]


@router.get("/{sim_id}")
async def get_simulation(sim_id: str, db: Session = Depends(get_session)) -> dict:
    try:
        uid = UUID(sim_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="simulation_not_found")
    sim = db.query(Simulation).filter(Simulation.id == uid).first()
    if not sim:
        raise HTTPException(status_code=404, detail="simulation_not_found")
    return {
        "id": str(sim.id),
        "created_at": sim.created_at.isoformat(),
        "name": sim.name,
        "agent_endpoint": sim.agent_endpoint,
        "task_template": sim.task_template,
        "num_runs": sim.num_runs,
        "status": sim.status,
        "metrics": sim.metrics or {},
        "dataset_id": str(sim.dataset_id) if sim.dataset_id else None,
        "template_config": sim.template_config,
    }

