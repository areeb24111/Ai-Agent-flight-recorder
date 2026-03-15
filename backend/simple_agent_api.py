"""
Demo agent with a hard-coded wrong answer. Use this to test the recorder and detectors
without calling an LLM. For a real LLM-backed agent, use real_llm_agent.py.
"""

import os

from fastapi import FastAPI
from pydantic import BaseModel

from sdk_flight_recorder import FlightRecorder

app = FastAPI(title="Demo Sim Agent")

RECORDER_API_KEY = os.environ.get("FLIGHT_RECORDER_API_KEY")


class AgentRequest(BaseModel):
    query: str
    env: dict | None = None


@app.post("/agent")
async def agent(req: AgentRequest) -> dict:
    rec = FlightRecorder(
        api_base_url="http://127.0.0.1:8000",
        agent_id="demo-sim-agent",
        agent_version="sim-v0",
        api_key=RECORDER_API_KEY,
    )
    rec.start_run(req.query, env=req.env or {})
    rec.log_step(
        idx=0,
        step_type="thought",
        request={"thought": f"Answering: {req.query}"},
        response=None,
    )
    final_answer = "The result is approximately 391."  # deliberately wrong for testing
    result = rec.end_run(final_answer)
    return {"ok": True, "run": result}
