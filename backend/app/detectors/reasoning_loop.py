"""
Reasoning loop detector: flags runs where the agent repeats the same or very similar
step content with no progress (e.g. identical reasoning or tool calls in a loop).
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List


def _step_fingerprint(step: Dict[str, Any], max_len: int = 200) -> str:
    """Normalize step content to a string and hash for comparison."""
    parts = []
    kind = step.get("step_type") or ""
    req = step.get("request")
    res = step.get("response")
    if isinstance(req, dict):
        parts.append(str(sorted((k, str(v)[:100]) for k, v in (req or {}).items()))[:max_len])
    elif req is not None:
        parts.append(str(req)[:max_len])
    if isinstance(res, dict):
        parts.append(str(sorted((k, str(v)[:100]) for k, v in (res or {}).items()))[:max_len])
    elif res is not None:
        parts.append(str(res)[:max_len])
    key = f"{kind}|" + "|".join(parts)
    return hashlib.sha256(key.encode()).hexdigest()


async def detect_reasoning_loop(run: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Detect when the agent repeats the same or very similar step content.
    Heuristic: count consecutive or near-consecutive steps with the same fingerprint;
    if any fingerprint appears >= REPEAT_THRESHOLD times, flag as reasoning loop.
    """
    steps = run.get("steps") or []
    if len(steps) < 3:
        return []

    REPEAT_THRESHOLD = 3
    fingerprints = [_step_fingerprint(s) for s in steps]
    counts: Dict[str, int] = {}
    for fp in fingerprints:
        counts[fp] = counts.get(fp, 0) + 1

    max_repeats = max(counts.values()) if counts else 0
    if max_repeats < REPEAT_THRESHOLD:
        return []

    # Score: higher when more repeats and more of the run is repeated
    repeat_ratio = max_repeats / len(steps)
    risk = min(100, 40 + int(max_repeats * 15) + int(repeat_ratio * 30))
    explanation = (
        f"Reasoning loop: same or near-identical step content repeated {max_repeats} times "
        f"in a run of {len(steps)} steps."
    )

    return [
        {
            "detector": "reasoning_loop",
            "score": risk,
            "label": "mild" if risk < 60 else "moderate" if risk < 80 else "severe",
            "explanation": explanation[:1000],
            "extra": {"max_repeats": max_repeats, "total_steps": len(steps)},
        }
    ]
