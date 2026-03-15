from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx


class FlightRecorder:
    """Minimal client-only SDK to record agent runs and send them to the ingestion API."""

    def __init__(
        self,
        api_base_url: str,
        agent_id: str,
        agent_version: str = "dev",
        api_key: str | None = None,
    ) -> None:
        self.api_base_url = api_base_url.rstrip("/")
        self.agent_id = agent_id
        self.agent_version = agent_version
        self._api_key = api_key
        self._reset()

    def _reset(self) -> None:
        self._steps: List[Dict[str, Any]] = []
        self._start_ts: Optional[float] = None
        self._user_query: str = ""
        self._env: Dict[str, Any] = {}

    def start_run(self, user_query: str, env: Optional[Dict[str, Any]] = None) -> None:
        self._reset()
        self._start_ts = time.time()
        self._user_query = user_query
        self._env = env or {}

    def log_step(
        self,
        idx: int,
        step_type: str,
        request: Optional[Dict[str, Any]] = None,
        response: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._steps.append(
            {
                "idx": idx,
                "step_type": step_type,
                "timestamp": datetime.utcnow().isoformat(),
                "request": request,
                "response": response,
                "metadata": metadata,
            }
        )

    def end_run(self, final_answer: str) -> Dict[str, Any]:
        latency_ms = int((time.time() - self._start_ts) * 1000) if self._start_ts else 0
        payload: Dict[str, Any] = {
            "agent_id": self.agent_id,
            "agent_version": self.agent_version,
            "user_query": self._user_query,
            "env": self._env,
            "steps": self._steps,
            "final_answer": final_answer,
            "latency_ms": latency_ms,
        }
        headers = {}
        if self._api_key:
            headers["X-API-Key"] = self._api_key
        with httpx.Client(timeout=10) as client:
            resp = client.post(
                f"{self.api_base_url}/api/v1/runs", json=payload, headers=headers
            )
            resp.raise_for_status()
            return resp.json()

