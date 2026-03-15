from pathlib import Path

from sqlalchemy import text
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.staticfiles import StaticFiles

from app.db.base import Base, engine
import app.db.models  # noqa: F401
from app.routes import runs, simulations, analytics, failure_patterns


from app.core.config import settings as app_settings

app = FastAPI(
    title="Agent Flight Recorder API",
    description="Record AI agent runs, run failure detectors (hallucination, planning, tool misuse), and export or query runs. Use the dashboard to replay runs and view failure patterns.",
    version="1.0.0",
)

_cors_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "https://ai-agent-flight-recorder.onrender.com",
]
if app_settings.cors_origins:
    _cors_origins = [o.strip() for o in app_settings.cors_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    # Ensure tables exist (SQLite or Postgres) when the API starts.
    Base.metadata.create_all(bind=engine)
    # SQLite: add simulation_id to runs if missing (e.g. old DB created before this column).
    if "sqlite" in str(engine.url):
        with engine.connect() as conn:
            try:
                r = conn.execute(
                    __import__("sqlalchemy").text("PRAGMA table_info(runs)")
                )
                cols = [row[1] for row in r]
                if "simulation_id" not in cols:
                    conn.execute(
                        __import__("sqlalchemy").text(
                            "ALTER TABLE runs ADD COLUMN simulation_id VARCHAR(36)"
                        )
                    )
                    conn.commit()
            except Exception:
                pass


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "detail": {
                "code": "validation_error",
                "message": "Invalid request body.",
                "errors": exc.errors(),
            }
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        detail = exc.detail
        if not isinstance(detail, dict):
            detail = {"message": str(detail)}
        return JSONResponse(status_code=exc.status_code, content={"detail": detail})
    # Don't leak stack traces; log server-side in production.
    return JSONResponse(
        status_code=500,
        content={
            "detail": {
                "code": "internal_error",
                "message": "An unexpected error occurred.",
            }
        },
    )


@app.get("/health")
async def health() -> dict:
    """Liveness and optional DB connectivity check."""
    out: dict = {"status": "ok"}
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        out["database"] = "connected"
    except Exception:
        out["database"] = "error"
    return out


app.include_router(runs.router)
app.include_router(simulations.router)
app.include_router(analytics.router)
app.include_router(failure_patterns.router)

# Optional: serve frontend for single-host deploy (set STATIC_DIR to e.g. ./static).
if app_settings.static_dir:
    static_path = Path(app_settings.static_dir).resolve()
    if static_path.is_dir() and (static_path / "index.html").exists():
        app.mount("/", StaticFiles(directory=str(static_path), html=True), name="frontend")


