"""
Real LLM-backed agent example. Calls OpenAI and records the run via the Flight Recorder SDK.
Run with: uvicorn real_llm_agent:app --host 127.0.0.1 --port 8002
Then point simulations or manual requests to http://127.0.0.1:8002/agent
"""

import os

from fastapi import FastAPI
from pydantic import BaseModel

from openai import OpenAI
from sdk_flight_recorder import FlightRecorder

app = FastAPI(title="Real LLM Agent (OpenAI)")

RECORDER_API_KEY = os.environ.get("FLIGHT_RECORDER_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")


class AgentRequest(BaseModel):
    query: str
    env: dict | None = None


@app.post("/agent")
async def agent(req: AgentRequest) -> dict:
    rec = FlightRecorder(
        api_base_url="http://127.0.0.1:8000",
        agent_id="openai-agent",
        agent_version="gpt-4o-mini",
        api_key=RECORDER_API_KEY,
    )
    rec.start_run(req.query, env=req.env or {})

    rec.log_step(
        idx=0,
        step_type="thought",
        request={"thought": f"Calling OpenAI for: {req.query[:80]}..."},
        response=None,
    )

    if not OPENAI_API_KEY:
        final_answer = "OPENAI_API_KEY not set; cannot call the model."
        result = rec.end_run(final_answer)
        return {"ok": False, "answer": final_answer, "run": result}

    client = OpenAI(api_key=OPENAI_API_KEY)
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": req.query}],
    )
    final_answer = resp.choices[0].message.content or ""

    rec.log_step(
        idx=1,
        step_type="message",
        request={"role": "assistant"},
        response={"content": final_answer},
    )
    result = rec.end_run(final_answer)
    return {"ok": True, "answer": final_answer, "run": result}
