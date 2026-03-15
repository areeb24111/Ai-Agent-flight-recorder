"""
Simple in-memory rate limiter for write endpoints (MVP; replace with Redis for multi-instance).
"""

import time
from collections import defaultdict
from threading import Lock
from typing import DefaultDict

from fastapi import HTTPException, Request, status

from app.core.config import settings

# key -> list of unix timestamps (seconds)
_buckets: DefaultDict[str, list[float]] = defaultdict(list)
_lock = Lock()


def _client_key(request: Request, route_key: str) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    else:
        ip = request.client.host if request.client else "unknown"
    return f"{ip}:{route_key}"


def _prune_bucket(key: str, window_sec: int, now: float) -> None:
    with _lock:
        bucket = _buckets[key]
        cutoff = now - window_sec
        bucket[:] = [t for t in bucket if t >= cutoff]


def _count_and_record(key: str, limit: int, now: float) -> None:
    with _lock:
        bucket = _buckets[key]
        if len(bucket) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": "rate_limited",
                    "message": "Too many requests. Retry after a short wait.",
                },
            )
        bucket.append(now)


def rate_limit_ingest(request: Request) -> None:
    """Limit POST /runs to N requests per minute per client."""
    limit = settings.rate_limit_ingest_per_minute
    if limit <= 0:
        return
    now = time.time()
    key = _client_key(request, "ingest")
    _prune_bucket(key, 60, now)
    _count_and_record(key, limit, now)


def rate_limit_simulations(request: Request) -> None:
    """Limit POST /simulations to N requests per minute per client."""
    limit = settings.rate_limit_simulations_per_minute
    if limit <= 0:
        return
    now = time.time()
    key = _client_key(request, "simulations")
    _prune_bucket(key, 60, now)
    _count_and_record(key, limit, now)
