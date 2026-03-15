"""
API for listing available failure detectors and optional config (e.g. thresholds).
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/detectors", tags=["detectors"])

DETECTOR_META = [
    {"id": "hallucination", "description": "Flags when the agent's answer is unsupported or contradicts evidence.", "threshold_default": 80},
    {"id": "planning_failure", "description": "Flags when the agent skips steps, loops with no progress, or ignores subgoals.", "threshold_default": 80},
    {"id": "tool_misuse", "description": "Flags tool calls or results that indicate errors or repeated failures.", "threshold_default": 70},
    {"id": "reasoning_loop", "description": "Flags when the same or near-identical step content is repeated with no progress.", "threshold_default": 70},
    {"id": "memory_contradiction", "description": "Flags when the agent contradicts itself across steps or vs final answer.", "threshold_default": 60},
]


@router.get("")
async def list_detectors() -> dict:
    """Return the list of failure detectors and their metadata."""
    return {"detectors": DETECTOR_META}
