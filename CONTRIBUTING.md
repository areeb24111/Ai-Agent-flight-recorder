# Contributing

Thanks for your interest in improving the Agent Flight Recorder. This doc covers how to run the project locally and how to submit changes.

## Setup

1. **Clone the repo** and open a terminal in the project root.

2. **Backend (Python 3.10+):**
   - `cd backend`
   - Create a virtualenv: `python -m venv .venv` then activate it (e.g. `.venv\Scripts\activate` on Windows).
   - Install deps: `pip install -r requirements.txt`
   - Copy `.env.example` to `.env` and set `OPENAI_API_KEY` if you want failure detectors to run.
   - Start API: `uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`
   - Optionally run workers: `python -m app.worker_failures` and `python -m app.worker_simulations` in separate terminals.
   - Optional demo agent: `uvicorn simple_agent_api:app --host 127.0.0.1 --port 8001`

3. **Frontend:**
   - `cd frontend`
   - `npm install && npm run dev`
   - Open http://localhost:5173

See README for full setup, usage, and deployment notes.

## Running tests

- Backend: from `backend`, run `pytest` (if tests are added).
- Frontend: from `frontend`, run `npm run build` to ensure the app compiles.

## Submitting changes

1. Open an issue or pick an existing one to discuss the change.
2. Create a branch from `main` (e.g. `feature/export-csv`).
3. Make your changes; keep commits focused and messages clear.
4. Ensure the app still runs and the frontend builds.
5. Open a pull request against `main` with a short description and link to the issue.
6. Address any review feedback.

## Code style

- **Backend:** Python with type hints; follow existing patterns in `app/` (FastAPI, SQLAlchemy).
- **Frontend:** TypeScript/React; follow existing patterns in `frontend/src`.
- Prefer small, reviewable PRs over large ones.

## Questions

Open a GitHub issue for bugs, feature ideas, or questions.
