# How to test the Agent Flight Recorder

Quick guide to ingest a run and confirm everything works.

---

## 1. Start the stack

From the **repo root**:

**Windows (PowerShell):**
```powershell
.\scripts\start.ps1 -IncludeFrontend
```

**Mac/Linux:**
```bash
python scripts/start_all.py --frontend
```

This starts the **API** (port 8000), **demo agent** (8001), and **both workers**. With `-IncludeFrontend` / `--frontend` the dashboard runs at http://localhost:5173.

If you prefer to run processes yourself, see [RUNBOOK.md](RUNBOOK.md) §2 (four terminals: API, demo agent, worker_failures, worker_simulations).

---

## 2. Ingest a run (three ways)

### Option A: curl (fastest)

If your API does **not** require an API key (default):

```bash
curl -X POST http://127.0.0.1:8000/api/v1/runs \
  -H "Content-Type: application/json" \
  -d "{\"agent_id\":\"test-agent\",\"user_query\":\"What is 2+2?\",\"final_answer\":\"4\",\"latency_ms\":100,\"steps\":[]}"
```

You should see something like: `{"run_id":"xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"}`.

If the API **requires** an API key (you set `API_KEY` in `backend/.env`):

```bash
curl -X POST http://127.0.0.1:8000/api/v1/runs \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d "{\"agent_id\":\"test-agent\",\"user_query\":\"What is 2+2?\",\"final_answer\":\"4\",\"latency_ms\":100,\"steps\":[]}"
```

Replace `YOUR_API_KEY` with the value from `backend/.env`.

### Option B: Python (requests)

From any directory (install `requests` if needed: `pip install requests`):

```python
import requests

url = "http://127.0.0.1:8000/api/v1/runs"
payload = {
    "agent_id": "my-agent",
    "agent_version": "v0",
    "user_query": "What is the capital of France?",
    "env": {},
    "steps": [
        {"idx": 0, "step_type": "reasoning", "request": {}, "response": {"thought": "Paris."}}
    ],
    "final_answer": "Paris.",
    "latency_ms": 50,
}
headers = {"Content-Type": "application/json"}
# If API_KEY is set in backend/.env, add: headers["X-API-Key"] = "your-key"

r = requests.post(url, json=payload, headers=headers)
print(r.status_code, r.json())  # 200 {'run_id': '...'}
```

### Option C: Script with SDK (backend folder)

From the **backend** folder, using the project’s SDK and demo script:

```powershell
cd backend
$env:FLIGHT_RECORDER_API_KEY = "your-api-key"   # only if API_KEY is set in .env
.\.venv\Scripts\python send_test_run.py
```

You should see: `Recorded run: {'run_id': '...'}`.

---

## 3. Check that everything is working

1. **Dashboard:** Open http://localhost:5173. The new run should appear in **Recent Runs** (you may need to click **Refresh**).
2. **Run detail:** Click the run. You should see:
   - User query and final answer
   - **Trace timeline** (user query → steps → final output)
   - **Copy run ID** and **Copy curl**
3. **Failure detection:** The **worker_failures** process runs in the background. After a short delay (a few seconds), refresh the run or the list. If detectors fired, you’ll see failure pills (e.g. Hallucination, Planning) and possibly an “N failures” pill in the list.
4. **API:** Open http://127.0.0.1:8000/docs and try **GET /api/v1/runs** to see the run in the API response.

---

## 4. Optional: create a simulation

Simulations call your agent endpoint many times and record each run. To test:

1. In the dashboard, click **Get started** and (if needed) enter your API key.
2. Create a simulation: name (e.g. `smoke-test`), agent endpoint `http://127.0.0.1:8001/agent` (demo agent), task template `math_qa` (or **custom** and type your own prompt in “Custom query”), num runs `3`.
3. Submit. The **worker_simulations** process will POST to the demo agent; runs will appear in **Recent Runs**. Click the simulation and **View runs** to filter.

For more detail, see [RUNBOOK.md](RUNBOOK.md) §4 and §5.
