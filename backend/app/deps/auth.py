"""
Optional API key authentication for ingestion and simulation-creation endpoints.

If settings.api_key is unset, auth is disabled (dev-friendly).
If set, requests must send header: X-API-Key: <key>
"""

from fastapi import Depends, HTTPException, Request, status

from app.core.config import settings


async def require_api_key(request: Request) -> None:
    if not settings.api_key:
        return  # auth disabled
    key = request.headers.get("x-api-key") or request.headers.get("X-API-Key")
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
        if token == settings.api_key:
            return
    if key and key == settings.api_key:
        return
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "invalid_api_key", "message": "Missing or invalid X-API-Key header."},
    )
