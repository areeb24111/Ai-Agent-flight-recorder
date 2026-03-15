from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class StepIn(BaseModel):
    idx: int
    step_type: str
    timestamp: datetime
    request: Optional[Dict[str, Any]] = None
    response: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class RunIn(BaseModel):
    agent_id: str
    agent_version: Optional[str] = None
    user_query: str
    env: Optional[Dict[str, Any]] = None
    steps: List[StepIn]
    final_answer: str
    latency_ms: int


class SimulationCreate(BaseModel):
    name: str
    agent_endpoint: str
    task_template: str = "math_qa"
    num_runs: int = 10

