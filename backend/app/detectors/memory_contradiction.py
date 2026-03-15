"""
Memory contradiction detector: flags runs where the agent contradicts itself
across steps or between steps and the final answer. Uses a simple heuristic
plus optional LLM judge when OPENAI_API_KEY is set.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

import httpx

from app.core.config import settings


def _extract_short_claims(text: str, max_claims: int = 10) -> List[str]:
    """Extract short sentence-like strings that might be claims."""
    if not text or not isinstance(text, str):
        return []
    # Split on sentence boundaries and take non-empty strips
    parts = re.split(r"[.!?]\s+", text.strip())
    claims = [p.strip()[:200] for p in parts if len(p.strip()) > 15][:max_claims]
    return claims


async def detect_memory_contradiction(run: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Detect when the agent contradicts itself. Heuristic: collect claims from
    steps and final answer; if OPENAI_API_KEY is set, use LLM to judge contradiction.
    Otherwise use simple overlap/negation heuristic (e.g. same subject, opposite value).
    """
    steps = run.get("steps") or []
    output = (run.get("output") or {}) or {}
    final_answer = output.get("final_answer") or output.get("answer") or ""
    if isinstance(final_answer, dict):
        final_answer = str(final_answer).strip()[:1000]
    input_data = run.get("input") or {}
    user_query = input_data.get("user_query") or ""

    all_claims: List[str] = []
    for s in steps:
        req = s.get("request")
        res = s.get("response")
        for blob in (req, res):
            if isinstance(blob, str):
                all_claims.extend(_extract_short_claims(blob, max_claims=3))
            elif isinstance(blob, dict):
                for v in (blob.get("content") or blob.get("text") or blob.get("message"),):
                    if isinstance(v, str):
                        all_claims.extend(_extract_short_claims(v, max_claims=2))
    if final_answer:
        all_claims.extend(_extract_short_claims(final_answer, max_claims=5))

    # Dedupe and filter trivial
    seen = set()
    unique_claims = []
    for c in all_claims:
        c_lower = c.lower()
        if c_lower in seen or len(c) < 20:
            continue
        seen.add(c_lower)
        unique_claims.append(c)

    if len(unique_claims) < 2:
        return []

    # Optional: LLM judge
    if settings.openai_api_key:
        try:
            async with httpx.AsyncClient(timeout=25) as client:
                prompt = (
                    "You are evaluating whether an AI agent contradicted itself.\n"
                    "Here are statements/claims from the agent's reasoning and final answer:\n\n"
                )
                for i, claim in enumerate(unique_claims[:15], 1):
                    prompt += f"{i}. {claim}\n"
                prompt += (
                    "\nIs there a clear contradiction between any of these (e.g. saying X then not-X)? "
                    "Reply with a JSON object: {\"has_contradiction\": true/false, "
                    "\"risk\": 0-100, \"explanation\": \"brief reason\"}.\n"
                )
                r = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 200,
                    },
                )
                if r.is_success:
                    data = r.json()
                    content = (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""
                    if "has_contradiction" in content and ("true" in content or "True" in content):
                        import json
                        risk, expl = 70, "LLM detected contradiction between agent claims."
                        try:
                            start = content.find("{")
                            if start >= 0:
                                end = content.rfind("}") + 1
                                if end > start:
                                    obj = json.loads(content[start:end])
                                    risk = int(obj.get("risk", 70))
                                    expl = str(obj.get("explanation", expl))[:1000]
                        except Exception:
                            pass
                        return [
                            {
                                "detector": "memory_contradiction",
                                "score": min(100, risk),
                                "label": "likely",
                                "explanation": expl,
                                "extra": {"claim_count": len(unique_claims)},
                            }
                        ]
        except Exception:
            pass

    # Heuristic fallback: very simple negation check (e.g. "is" vs "is not" on same phrase)
    for i, a in enumerate(unique_claims):
        a_lower = a.lower()
        for b in unique_claims[i + 1 :]:
            b_lower = b.lower()
            # Same short substring but one has "not"/"no" and the other doesn't
            words_a, words_b = set(a_lower.split()), set(b_lower.split())
            if len(words_a & words_b) >= 3:
                if ("not" in a_lower or "no " in a_lower) != ("not" in b_lower or "no " in b_lower):
                    return [
                        {
                            "detector": "memory_contradiction",
                            "score": 55,
                            "label": "suspicious",
                            "explanation": "Possible contradiction: similar claims with opposite polarity (e.g. not/no).",
                            "extra": {"claim_count": len(unique_claims)},
                        }
                    ]

    return []
