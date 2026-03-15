from __future__ import annotations

from typing import Any, Dict, List

import httpx

from app.core.config import settings


async def detect_planning_failure(run: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Planning failure detector v0.

    Uses an LLM judge that, given (user_query, steps, final_answer), decides if the
    agent followed a reasonable plan or skipped/looped steps.
    """
    api_key = settings.openai_api_key
    if not api_key:
        return []

    user_query = (run.get("input") or {}).get("user_query") or ""
    steps = run.get("steps") or []
    final_answer = (run.get("output") or {}).get("final_answer") or ""
    if not user_query or not steps:
        return []

    # create a compact text version of steps
    step_lines = []
    for s in steps[:10]:  # cap for cost
        kind = s.get("step_type", "")
        req = s.get("request") or {}
        resp = s.get("response") or {}
        step_lines.append(f"- [{kind}] req={str(req)[:120]} resp={str(resp)[:120]}")
    steps_text = "\n".join(step_lines)

    prompt = (
        "You are evaluating whether an AI agent's execution plan was followed.\n"
        "Given the user's question, the sequence of steps, and the final answer:\n"
        "1. Infer the implicit plan the agent seemed to follow.\n"
        "2. Decide if there were major planning failures: skipped essential steps, "
        "loops with no progress, or ignoring obvious subgoals.\n"
        "Return a JSON object with fields:\n"
        "- risk (integer 0-100, higher means more severe planning failure)\n"
        "- label (one of: none, mild, moderate, severe)\n"
        "- explanation (short text explaining the planning issue, if any).\n\n"
        f"User question:\n{user_query}\n\n"
        f"Steps:\n{steps_text}\n\n"
        f"Final answer:\n{final_answer}\n"
    )

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini",
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a precise evaluator of planning and execution quality for AI agents.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                },
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return []

    try:
        content = data["choices"][0]["message"]["content"]
    except Exception:
        return []

    import json

    try:
        parsed = json.loads(content)
    except Exception:
        return []

    risk = int(parsed.get("risk", 0))
    label = str(parsed.get("label", "none"))
    explanation = str(parsed.get("explanation", ""))[:1000]

    if risk <= 0:
        return []

    return [
        {
            "detector": "planning_failure",
            "score": risk,
            "label": label,
            "explanation": explanation,
            "extra": {"raw": parsed},
        }
    ]

