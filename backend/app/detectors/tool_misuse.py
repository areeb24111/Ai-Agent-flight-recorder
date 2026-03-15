from __future__ import annotations

from typing import Any, Dict, List


async def detect_tool_misuse(run: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Very simple tool misuse detector v0.

    Heuristics:
    - Flags tool_result steps where the response contains an 'error' key or
      a string with 'error'/'failed'.
    - If the same tool repeatedly errors in a run, increase risk.
    """
    steps = run.get("steps") or []
    if not steps:
        return []

    error_counts: Dict[str, int] = {}
    for s in steps:
        if s.get("step_type") not in ("tool_call", "tool_result"):
            continue
        tool_name = None
        req = s.get("request") or {}
        res = s.get("response") or {}
        if isinstance(req, dict):
            tool_name = req.get("tool") or req.get("tool_name")
        if not tool_name and isinstance(res, dict):
            tool_name = res.get("tool") or res.get("tool_name") or "unknown_tool"
        tool_name = tool_name or "unknown_tool"

        # look for basic error signals
        problem = False
        if isinstance(res, dict) and ("error" in res or "exception" in res):
            problem = True
        elif isinstance(res, str) and ("error" in res.lower() or "failed" in res.lower()):
            problem = True

        if problem:
            error_counts[tool_name] = error_counts.get(tool_name, 0) + 1

    if not error_counts:
        return []

    # derive a simple risk score: more repeated errors => higher risk
    max_errors = max(error_counts.values())
    risk = min(100, 30 + max_errors * 15)  # baseline + 15 per repeat
    explanation_parts = [
        f"{tool} had {count} error-like responses" for tool, count in error_counts.items()
    ]
    explanation = "Tool misuse suspected: " + "; ".join(explanation_parts)

    return [
        {
            "detector": "tool_misuse",
            "score": risk,
            "label": "suspicious" if risk < 70 else "likely",
            "explanation": explanation[:1000],
            "extra": {"error_counts": error_counts},
        }
    ]

