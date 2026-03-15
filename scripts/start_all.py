#!/usr/bin/env python3
"""
Start all Agent Flight Recorder services (API, demo agent, workers) and optionally the frontend.
Cross-platform. Run from repo root: python scripts/start_all.py
Optional: python scripts/start_all.py --frontend
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND = REPO_ROOT / "backend"
FRONTEND = REPO_ROOT / "frontend"
VENV = BACKEND / ".venv"

IS_WIN = sys.platform == "win32"
VENV_BIN = VENV / ("Scripts" if IS_WIN else "bin")
VENV_PYTHON = VENV_BIN / ("python.exe" if IS_WIN else "python")
VENV_UVICORN = VENV_BIN / ("uvicorn.exe" if IS_WIN else "uvicorn")


def main() -> None:
    ap = argparse.ArgumentParser(description="Start Agent Flight Recorder stack")
    ap.add_argument("--frontend", action="store_true", help="Also start the dashboard (npm run dev)")
    args = ap.parse_args()

    if not BACKEND.is_dir():
        print("Backend folder not found. Run from repo root.", file=sys.stderr)
        sys.exit(1)
    if not VENV_PYTHON.exists():
        print("Backend venv not found. Create it: cd backend && python -m venv .venv && pip install ...", file=sys.stderr)
        sys.exit(1)

    uvicorn_cmd = [str(VENV_UVICORN)] if VENV_UVICORN.exists() else [str(VENV_PYTHON), "-m", "uvicorn"]
    python_cmd = [str(VENV_PYTHON)]

    procs = []

    # API
    procs.append(
        subprocess.Popen(
            uvicorn_cmd + ["app.main:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=BACKEND,
            env=os.environ.copy(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    )
    print("[1/5] API started (http://127.0.0.1:8000)")

    # Demo agent
    procs.append(
        subprocess.Popen(
            uvicorn_cmd + ["simple_agent_api:app", "--host", "127.0.0.1", "--port", "8001"],
            cwd=BACKEND,
            env=os.environ.copy(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    )
    print("[2/5] Demo agent started (http://127.0.0.1:8001)")

    # Failure worker
    procs.append(
        subprocess.Popen(
            python_cmd + ["-m", "app.worker_failures"],
            cwd=BACKEND,
            env=os.environ.copy(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    )
    print("[3/5] Failure worker started")

    # Simulation worker
    procs.append(
        subprocess.Popen(
            python_cmd + ["-m", "app.worker_simulations"],
            cwd=BACKEND,
            env=os.environ.copy(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    )
    print("[4/5] Simulation worker started")

    if args.frontend and FRONTEND.is_dir():
        try:
            subprocess.Popen(
                ["npm", "run", "dev"],
                cwd=FRONTEND,
                env=os.environ.copy(),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=IS_WIN,
            )
            print("[5/5] Frontend started (http://localhost:5173)")
        except FileNotFoundError:
            print("[5/5] npm not found; run 'cd frontend && npm run dev' manually.")
    else:
        print("[5/5] Frontend skipped (use --frontend to start it)")

    print("")
    print("Backend processes are running. Press Ctrl+C to stop all.")
    try:
        for p in procs:
            p.wait()
    except KeyboardInterrupt:
        for p in procs:
            p.terminate()
        for p in procs:
            p.wait(timeout=5)
        print("Stopped.")


if __name__ == "__main__":
    main()
