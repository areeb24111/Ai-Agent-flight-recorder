from __future__ import annotations

from typing import Any, Dict, List

import httpx

from app.core.config import settings


async def detect_hallucination(run: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Very simple hallucination detector v0.

    Uses an LLM judge that, given (user_query, final_answer), returns a risk score 0-100
    and short explanation. If OPENAI_API_KEY is not configured, returns an empty list.
    """
    api_key = settings.openai_api_key
    if not api_key:
        return []

    user_query = (run.get("input") or {}).get("user_query") or ""
    final_answer = (run.get("output") or {}).get("final_answer") or ""
    if not user_query or not final_answer:
        return []

    # optional retrieval: collect any evidence from env or retrieval steps
    evidence_chunks: List[str] = []
    env = run.get("env") or {}
    docs = env.get("retrieval_docs") or []
    if isinstance(docs, list):
        for d in docs[:5]:
            if isinstance(d, str):
                evidence_chunks.append(d)
            elif isinstance(d, dict):
                text = d.get("text") or d.get("content")
                if isinstance(text, str):
                    evidence_chunks.append(text)
    for s in run.get("steps") or []:
        if s.get("step_type") == "retrieval":
            res = s.get("response") or {}
            if isinstance(res, dict):
                texts = res.get("documents") or res.get("docs") or []
                if isinstance(texts, list):
                    for t in texts[:3]:
                        if isinstance(t, str):
                            evidence_chunks.append(t)
                        elif isinstance(t, dict):
                            text = t.get("text") or t.get("content")
                            if isinstance(text, str):
                                evidence_chunks.append(text)

    evidence_text = "\n\n".join(evidence_chunks[:5])

    prompt = (
        "You are evaluating an AI assistant answer for hallucinations.\n"
        "Given the user's question and the assistant's final answer, "
        "return a JSON object with fields:\n"
        "- risk (integer 0-100, higher means more likely hallucination)\n"
        "- label (one of: none, suspicious, likely, confirmed)\n"
        "- explanation (short text explaining why)\n\n"
        f"User question:\n{user_query}\n\n"
        f"Assistant answer:\n{final_answer}\n\n"
        + (
            f"Retrieved evidence:\n{evidence_text}\n"
            if evidence_text
            else "No external evidence is available; judge based on general knowledge.\n"
        )
    )

    # Use OpenAI's chat completions API (json mode) – v0 endpoint pattern.
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
                        {"role": "system", "content": "You are a precise hallucination evaluator."},
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
            "detector": "hallucination",
            "score": risk,
            "label": label,
            "explanation": explanation,
            "extra": {"raw": parsed},
        }
    ]

