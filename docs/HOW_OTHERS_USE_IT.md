# How other people check their agents online

This explains how **another developer** (or team) uses **your** deployed Agent Flight Recorder to record and inspect **their** AI agent’s runs.

---

## The idea

1. **You** deploy the Agent Flight Recorder (API + dashboard) online (e.g. on Render). You get:
   - **Dashboard URL** – e.g. `https://your-app.onrender.com` (or your combined API+dashboard URL).
   - **API URL** – e.g. `https://your-api.onrender.com` (same as dashboard if you use one combined service).
   - **API key** (optional) – if you set `API_KEY` on the server, you give this to users so they can ingest runs and create simulations.

2. **They** add a small integration to **their** agent (their app, their API, their backend). Whenever their agent handles a request, it sends one run to **your** API.

3. **They** (or you) open **your** dashboard, sign in or use the same API key, and see **their** runs: replay, failure scores, analytics, and simulations.

So: **their agent runs elsewhere; your Flight Recorder stores and analyzes the runs; everyone views results in your dashboard.**

---

## What you give them

Send them:

| What | Example |
|------|--------|
| **Dashboard URL** | `https://your-app.onrender.com` – where they open the UI. |
| **API base URL** | `https://your-app.onrender.com` (if combined) or `https://your-api.onrender.com` (if split). No trailing slash. |
| **API key** (if you use auth) | The value of `API_KEY` you set on the server. They use it in their code and optionally store it in the dashboard (Get started). |

If you didn’t set `API_KEY`, they can ingest runs and use the dashboard without any key.

---

## What they do in their agent

They need to **send each run** to your API with a **POST** to your API base URL.

### Option 1: Use your SDK (Python)

They install `httpx` and copy your SDK (or you publish it). They use **your API URL** and optional **API key**:

```python
from sdk_flight_recorder import FlightRecorder

# Your deployed API URL and the API key you gave them
rec = FlightRecorder(
    api_base_url="https://your-api.onrender.com",  # or your combined URL
    agent_id="their-agent-name",
    agent_version="v1",
    api_key="the-api-key-you-gave-them",  # omit if you don't use API_KEY
)

# Inside their agent, for each user request:
rec.start_run(user_query="What is the weather in Paris?", env={})

# As their agent does steps (reasoning, tool calls, etc.):
rec.log_step(idx=0, step_type="reasoning", request={}, response={"thought": "I'll call the weather API."})
rec.log_step(idx=1, step_type="tool_call", request={"tool": "get_weather", "args": {"city": "Paris"}}, response={})
rec.log_step(idx=2, step_type="tool_result", request={}, response={"temp": "22°C"})

# When their agent has the final answer:
rec.end_run(final_answer="The weather in Paris is 22°C.")
```

Every run will show up under **your** dashboard; they filter or search by `agent_id` (e.g. `their-agent-name`) if multiple teams use the same deployment.

### Option 2: Call the API directly (any language)

They **POST** a JSON body to `{API_BASE_URL}/api/v1/runs`:

```bash
curl -X POST "https://your-api.onrender.com/api/v1/runs" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: the-api-key-you-gave-them" \
  -d '{
    "agent_id": "their-agent",
    "user_query": "What is 2+2?",
    "steps": [{"idx": 0, "step_type": "reasoning", "request": {}, "response": {}}],
    "final_answer": "4",
    "latency_ms": 120
  }'
```

Required fields: `agent_id`, `user_query`, `steps` (array), `final_answer`, `latency_ms`. If they don’t use auth, they omit the `X-API-Key` header.

---

## How they view results online

1. They open **your dashboard URL** in a browser (e.g. `https://your-app.onrender.com`).
2. If you use API key auth, they can paste the same API key in **Get started** so the dashboard can create simulations if needed.
3. They use **Recent Runs** to see their runs (filter by **agent** = their `agent_id`).
4. They click a run to see the **trace timeline**, **failure scores**, and **Copy curl** for debugging.
5. They can use **Analytics** and **Failure patterns** / **Failure clusters** to see trends and recurring failure types.

So **checking their agents online** = their code sends runs to your API, and they (or you) look at everything in your dashboard.

---

## Optional: they run simulations against their agent

If their agent exposes an **HTTP endpoint** (e.g. `https://their-agent.fly.dev/agent`) that accepts a JSON body like `{"query": "...", "env": {...}}` and returns a response:

1. In your dashboard they (or you) go to **Get started** or the Simulations section.
2. They create a simulation: **Agent endpoint** = their URL, template (e.g. `math_qa`), number of runs.
3. Your **simulation worker** (running next to your API) calls their endpoint repeatedly and records each run.
4. They see the new runs in the dashboard and metrics (success rate, hallucination rate, tool errors) for that simulation.

So they can **batch-test** their agent through your deployed Flight Recorder without running anything on their own machine.

---

## Summary

| Step | Who | What |
|------|-----|------|
| 1 | You | Deploy Flight Recorder (API + dashboard), get URLs and optional API key. |
| 2 | You | Share with them: dashboard URL, API base URL, API key (if used). |
| 3 | They | In their agent code: POST each run to your API (SDK or raw HTTP). |
| 4 | They / You | Open your dashboard, filter by their `agent_id`, view runs and failures. |
| 5 | Optional | They create a simulation pointing at their agent’s URL; your worker runs the tests and records runs. |

**So “other people check their agents online” by: (1) sending runs from their agent to your API, and (2) opening your dashboard to inspect those runs and failure detection.**
