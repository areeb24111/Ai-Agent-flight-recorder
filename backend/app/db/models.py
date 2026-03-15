import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class Run(Base):
    __tablename__ = "runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    agent_id = Column(String, index=True, nullable=False)
    agent_version = Column(String, nullable=True)
    input = Column(JSON, nullable=False)   # {"user_query": ..., "context": {...}}
    output = Column(JSON, nullable=False)  # {"final_answer": ..., "finish_reason": ...}
    latency_ms = Column(Integer, nullable=True)
    status = Column(String, default="success", nullable=False)
    processed_for_failures = Column(Integer, default=0, nullable=False)
    env = Column(JSON, nullable=True)
    simulation_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    steps = relationship("Step", back_populates="run", cascade="all, delete-orphan")


class Step(Base):
    __tablename__ = "steps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id"), index=True, nullable=False)
    idx = Column(Integer, nullable=False)
    step_type = Column(String, nullable=False)  # thought, tool_call, tool_result, etc.
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    request = Column(JSON, nullable=True)
    response = Column(JSON, nullable=True)
    meta = Column("metadata", JSON, nullable=True)

    run = relationship("Run", back_populates="steps")


class Failure(Base):
    __tablename__ = "failures"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id"), index=True, nullable=False)
    step_id = Column(UUID(as_uuid=True), ForeignKey("steps.id"), nullable=True)
    detector = Column(String, nullable=False)  # e.g., hallucination, planning_failure
    score = Column(Integer, nullable=True)  # store 0-100 for simplicity
    label = Column(String, nullable=True)  # none, suspicious, likely, confirmed
    explanation = Column(String, nullable=True)
    extra = Column(JSON, nullable=True)


class TaskDataset(Base):
    """
    Named set of tasks for simulation runs. payload.tasks = list of {query, env}.
    Optional: when simulation.dataset_id is set, worker uses these tasks instead of generate_task.
    """
    __tablename__ = "task_datasets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    name = Column(String, nullable=False, index=True)
    payload = Column(JSON, nullable=False)  # {"tasks": [{"query": "...", "env": {...}}, ...]}


class Simulation(Base):
    __tablename__ = "simulations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    name = Column(String, nullable=False)
    agent_endpoint = Column(String, nullable=False)
    task_template = Column(String, nullable=False)
    num_runs = Column(Integer, nullable=False)
    status = Column(String, default="pending", nullable=False)  # pending, running, completed, failed
    metrics = Column(JSON, nullable=True)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("task_datasets.id"), nullable=True, index=True)
    template_config = Column(JSON, nullable=True)  # optional {"query": "...", "env": {...}} for custom template

