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
    sim = Simulation(
        name=payload.name,
        agent_endpoint=payload.agent_endpoint,
        task_template=payload.task_template,
        num_runs=payload.num_runs,
        status="pending",
        metrics={"total_runs": 0, "success": 0, "hallucinations": 0},
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
        }
        for s in sims
    ]


@router.get("/{sim_id}")
async def get_simulation(sim_id: str, db: Session = Depends(get_session)) -> dict:
    sim = db.query(Simulation).filter(Simulation.id == sim_id).first()
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
    }

