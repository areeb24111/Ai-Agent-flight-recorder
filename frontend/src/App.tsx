import { useEffect, useState } from 'react'
import './App.css'

type RunSummary = {
  id: string
  created_at: string
  agent_id: string
  agent_version: string | null
  latency_ms: number | null
  status: string
  user_query?: string | null
  failure_count?: number
}

type RunDetail = {
  run: {
    id: string
    created_at: string
    agent_id: string
    agent_version: string | null
    input: { user_query?: string; [k: string]: unknown }
    output: { final_answer?: string; [k: string]: unknown }
    latency_ms: number | null
    status: string
    env: Record<string, unknown> | null
  }
  steps: Array<{
    id: string
    idx: number
    step_type: string
    timestamp: string
    request: unknown
    response: unknown
    metadata: unknown
  }>
  failures: Array<{
    id: string
    detector: string
    score: number | null
    label: string | null
    explanation: string | null
    extra: unknown
  }>
}

type Simulation = {
  id: string
  created_at: string
  name: string
  agent_endpoint: string
  task_template: string
  num_runs: number
  status: string
  metrics: {
    total_runs?: number
    success_rate?: number
    hallucination_rate?: number
    avg_latency_ms?: number
  }
}

type FailurePattern = {
  detector: string
  explanation_key: string
  count: number
  example_run_ids: string[]
}

const API_BASE =
  import.meta.env.VITE_API_BASE !== undefined
    ? (import.meta.env.VITE_API_BASE as string)
    : 'http://127.0.0.1:8000'
const STORAGE_ONBOARDING = 'afr_onboarding_done'
const STORAGE_API_KEY = 'afr_api_key'

function App() {
  const [runs, setRuns] = useState<RunSummary[]>([])
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null)
  const [selectedRun, setSelectedRun] = useState<RunDetail | null>(null)
  const [loadingRuns, setLoadingRuns] = useState(false)
  const [loadingRunDetail, setLoadingRunDetail] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [analyticsTab, setAnalyticsTab] = useState<'30d' | '7d' | '24h'>('30d')
  const [simulations, setSimulations] = useState<Simulation[]>([])
  const [selectedSimulationId, setSelectedSimulationId] = useState<string | null>(null)
  const [runsPerDay, setRunsPerDay] = useState<{ day: string; count: number; hallucination_rate: number }[]>([])
  const [showOnboarding, setShowOnboarding] = useState(
    () => typeof localStorage !== 'undefined' && !localStorage.getItem(STORAGE_ONBOARDING),
  )
  const [apiKey, setApiKey] = useState(
    () => (typeof localStorage !== 'undefined' && localStorage.getItem(STORAGE_API_KEY)) || '',
  )
  const [onboardingStep, setOnboardingStep] = useState(0)
  const [simForm, setSimForm] = useState({
    name: 'smoke-test',
    agent_endpoint: 'http://127.0.0.1:8001/agent',
    task_template: 'math_qa',
    num_runs: 3,
  })
  const [simCreateMsg, setSimCreateMsg] = useState<string | null>(null)
  const [patterns, setPatterns] = useState<FailurePattern[]>([])
  const [patternsDays, setPatternsDays] = useState<7 | 30>(7)
  const [hasMoreRuns, setHasMoreRuns] = useState(false)
  const [loadingMore, setLoadingMore] = useState(false)
  const [agents, setAgents] = useState<string[]>([])
  const [filterAgentId, setFilterAgentId] = useState<string>('')
  const [filterDateFrom, setFilterDateFrom] = useState('')
  const [filterDateTo, setFilterDateTo] = useState('')
  const [copyRunIdMsg, setCopyRunIdMsg] = useState<string | null>(null)

  const saveApiKey = () => {
    if (apiKey.trim()) localStorage.setItem(STORAGE_API_KEY, apiKey.trim())
    else localStorage.removeItem(STORAGE_API_KEY)
  }

  const dismissOnboarding = () => {
    localStorage.setItem(STORAGE_ONBOARDING, '1')
    setShowOnboarding(false)
  }

  const createSimulationFromUi = async () => {
    setSimCreateMsg(null)
    const headers: Record<string, string> = { 'Content-Type': 'application/json' }
    if (apiKey.trim()) headers['X-API-Key'] = apiKey.trim()
    try {
      const res = await fetch(`${API_BASE}/api/v1/simulations`, {
        method: 'POST',
        headers,
        body: JSON.stringify(simForm),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        setSimCreateMsg(res.status === 401 ? 'Invalid API key (set API_KEY on server or leave empty).' : JSON.stringify(data))
        return
      }
      setSimCreateMsg(`Created simulation ${data.simulation_id}. Refresh the page in a moment to see runs.`)
      const listRes = await fetch(`${API_BASE}/api/v1/simulations`)
      if (listRes.ok) setSimulations(await listRes.json())
    } catch (e) {
      setSimCreateMsg((e as Error).message)
    }
  }

  const limit = 50

  const buildRunsUrl = (offset: number) => {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) })
    if (selectedSimulationId) params.set('simulation_id', selectedSimulationId)
    if (filterAgentId) params.set('agent_id', filterAgentId)
    if (filterDateFrom) params.set('date_from', filterDateFrom)
    if (filterDateTo) params.set('date_to', filterDateTo)
    return `${API_BASE}/api/v1/runs?${params}`
  }

  const fetchRuns = async (offset: number, append: boolean) => {
    if (append) setLoadingMore(true)
    else setLoadingRuns(true)
    try {
      const res = await fetch(buildRunsUrl(offset))
      if (!res.ok) throw new Error(`Failed to load runs: ${res.status}`)
      const data: RunSummary[] = await res.json()
      if (append) setRuns((prev) => (offset === 0 ? data : [...prev, ...data]))
      else setRuns(data)
      setHasMoreRuns(data.length === limit)
      setError(null)
      if (data.length > 0 && !selectedRunId && offset === 0) setSelectedRunId(data[0].id)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoadingMore(false)
      setLoadingRuns(false)
    }
  }

  const loadMore = () => {
    fetchRuns(runs.length, true)
  }

  const refreshAll = () => {
    fetchRuns(0, false)
    setRunsPerDay([])
    setPatterns([])
    fetch(`${API_BASE}/api/v1/analytics/runs_summary?days=${analyticsTab === '30d' ? 30 : analyticsTab === '7d' ? 7 : 1}`)
      .then((r) => r.ok && r.json())
      .then((d) => d && setRunsPerDay(d.runs_per_day ?? []))
      .catch(() => {})
    fetch(`${API_BASE}/api/v1/failure_patterns?days=${patternsDays}`)
      .then((r) => r.ok && r.json())
      .then((d) => d && setPatterns(d.patterns ?? []))
      .catch(() => {})
    fetch(`${API_BASE}/api/v1/simulations`)
      .then((r) => r.ok && r.json())
      .then((d) => d && setSimulations(d))
      .catch(() => {})
    if (selectedRunId) {
      fetch(`${API_BASE}/api/v1/runs/${selectedRunId}`)
        .then((r) => r.ok && r.json())
        .then((d) => d && setSelectedRun(d))
        .catch(() => {})
    }
  }

  useEffect(() => {
    fetchRuns(0, false)
  }, [selectedSimulationId, filterAgentId, filterDateFrom, filterDateTo])

  useEffect(() => {
    fetch(`${API_BASE}/api/v1/runs/agents`)
      .then((r) => r.ok && r.json())
      .then((d) => Array.isArray(d) && setAgents(d))
      .catch(() => {})
  }, [])

  useEffect(() => {
    const fetchRunDetail = async () => {
      if (!selectedRunId) return
      try {
        setLoadingRunDetail(true)
        const res = await fetch(`${API_BASE}/api/v1/runs/${selectedRunId}`)
        if (!res.ok) throw new Error(`Failed to load run: ${res.status}`)
        const data: RunDetail = await res.json()
        setSelectedRun(data)
        setError(null)
      } catch (e) {
        setError((e as Error).message)
      } finally {
        setLoadingRunDetail(false)
      }
    }
    fetchRunDetail()
  }, [selectedRunId])

  useEffect(() => {
    const fetchSimulations = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/v1/simulations`)
        if (!res.ok) return
        const data: Simulation[] = await res.json()
        setSimulations(data)
      } catch {
        // ignore for now
      }
    }
    fetchSimulations()
  }, [])

  useEffect(() => {
    const fetchAnalytics = async () => {
      const days = analyticsTab === '30d' ? 30 : analyticsTab === '7d' ? 7 : 1
      try {
        const res = await fetch(`${API_BASE}/api/v1/analytics/runs_summary?days=${days}`)
        if (!res.ok) return
        const data = await res.json()
        setRunsPerDay(data.runs_per_day ?? [])
      } catch {
        setRunsPerDay([])
      }
    }
    fetchAnalytics()
  }, [analyticsTab])

  useEffect(() => {
    const fetchPatterns = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/v1/failure_patterns?days=${patternsDays}`)
        if (!res.ok) return
        const data = await res.json()
        setPatterns(data.patterns ?? [])
      } catch {
        setPatterns([])
      }
    }
    fetchPatterns()
  }, [patternsDays])

  const avgLatency =
    runs.length > 0
      ? Math.round(
          runs.reduce((sum, r) => sum + (r.latency_ms ?? 0), 0) / Math.max(1, runs.length),
        )
      : null

  const successRate =
    runs.length > 0
      ? Math.round(
          (runs.filter((r) => r.status === 'success').length / runs.length) * 100,
        )
      : null

  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <h1>Agent Flight Recorder</h1>
          <p>Replay and analyze AI agent executions.</p>
        </div>
        <div className="header-actions">
          <button type="button" className="btn-header" onClick={refreshAll} title="Refresh runs, analytics, and patterns">
            Refresh
          </button>
          <button type="button" className="btn-header" onClick={() => setShowOnboarding(true)}>
            Get started
          </button>
        </div>
      </header>

      {showOnboarding && (
        <div className="onboarding-backdrop" role="dialog" aria-modal="true">
          <div className="onboarding-modal">
            <div className="onboarding-header">
              <h2>Get started</h2>
              <button type="button" className="onboarding-close" onClick={dismissOnboarding} aria-label="Close">
                ×
              </button>
            </div>
            <div className="onboarding-steps">
              <button
                type="button"
                className={onboardingStep === 0 ? 'step-tab active' : 'step-tab'}
                onClick={() => setOnboardingStep(0)}
              >
                1. API key
              </button>
              <button
                type="button"
                className={onboardingStep === 1 ? 'step-tab active' : 'step-tab'}
                onClick={() => setOnboardingStep(1)}
              >
                2. Run stack
              </button>
              <button
                type="button"
                className={onboardingStep === 2 ? 'step-tab active' : 'step-tab'}
                onClick={() => setOnboardingStep(2)}
              >
                3. Simulation
              </button>
            </div>
            {onboardingStep === 0 && (
              <div className="onboarding-panel">
                <p>
                  <strong>Optional.</strong> If your backend has <code>API_KEY</code> set in <code>backend/.env</code>,
                  paste the same value here so the dashboard can create simulations. Leave blank if auth is disabled.
                </p>
                <label className="onboarding-label">
                  API key (stored in browser only)
                  <input
                    type="password"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    placeholder="Optional"
                    className="onboarding-input"
                  />
                </label>
                <button type="button" className="btn-primary" onClick={saveApiKey}>
                  Save
                </button>
              </div>
            )}
            {onboardingStep === 1 && (
              <div className="onboarding-panel">
                <ol className="onboarding-list">
                  <li>
                    From the repo root run: <code>.\scripts\start.ps1 -IncludeFrontend</code> (Windows) or{' '}
                    <code>python scripts/start_all.py --frontend</code> (Mac/Linux).
                  </li>
                  <li>This starts the API, demo agent, and workers in the background.</li>
                  <li>
                    If you set <code>API_KEY</code> in <code>backend/.env</code>, the script passes it to the demo agent as{' '}
                    <code>FLIGHT_RECORDER_API_KEY</code>.
                  </li>
                </ol>
                <p className="onboarding-hint">See <code>docs/RUNBOOK.md</code> for full commands.</p>
              </div>
            )}
            {onboardingStep === 2 && (
              <div className="onboarding-panel">
                <p>
                  Create a simulation job. Use the demo agent (<code>http://127.0.0.1:8001/agent</code>) or your own
                  agent endpoint. The simulation worker and your agent must be running.
                </p>
                <label className="onboarding-label">
                  Name
                  <input
                    className="onboarding-input"
                    value={simForm.name}
                    onChange={(e) => setSimForm({ ...simForm, name: e.target.value })}
                  />
                </label>
                <label className="onboarding-label">
                  Agent endpoint
                  <input
                    className="onboarding-input"
                    value={simForm.agent_endpoint}
                    onChange={(e) => setSimForm({ ...simForm, agent_endpoint: e.target.value })}
                  />
                </label>
                <label className="onboarding-label">
                  Task template
                  <select
                    className="onboarding-input"
                    value={simForm.task_template}
                    onChange={(e) => setSimForm({ ...simForm, task_template: e.target.value })}
                  >
                    <option value="math_qa">math_qa</option>
                    <option value="doc_qa">doc_qa</option>
                    <option value="multi_turn">multi_turn</option>
                    <option value="code_assist">code_assist</option>
                  </select>
                </label>
                <label className="onboarding-label">
                  Number of runs
                  <input
                    type="number"
                    min={1}
                    className="onboarding-input"
                    value={simForm.num_runs}
                    onChange={(e) =>
                      setSimForm({ ...simForm, num_runs: Math.max(1, parseInt(e.target.value, 10) || 1) })
                    }
                  />
                </label>
                <button type="button" className="btn-primary" onClick={createSimulationFromUi}>
                  Create simulation
                </button>
                {simCreateMsg && <p className="onboarding-msg">{simCreateMsg}</p>}
              </div>
            )}
            <div className="onboarding-footer">
              <button type="button" className="btn-secondary" onClick={dismissOnboarding}>
                Done
              </button>
            </div>
          </div>
        </div>
      )}

      <main className="app-main">
        <section className="metrics-row">
          <div className="metric-card" title="Number of runs currently loaded in the list (use filters or Load more to change scope).">
            <div className="metric-label">Total Runs</div>
            <div className="metric-value">{runs.length}</div>
            <div className="metric-trend">
              <span className="badge-up">+0%</span>
              <span>vs. previous</span>
            </div>
          </div>
          <div className="metric-card" title="Average response time in milliseconds across the loaded runs.">
            <div className="metric-label">Avg Latency</div>
            <div className="metric-value">
              {avgLatency !== null ? `${avgLatency} ms` : '—'}
            </div>
            <div className="metric-trend">
              <span className="badge-up">+0%</span>
              <span>vs. previous</span>
            </div>
          </div>
          <div className="metric-card" title="Percentage of loaded runs with status 'success'.">
            <div className="metric-label">Success Rate</div>
            <div className="metric-value">
              {successRate !== null ? `${successRate}%` : '—'}
            </div>
            <div className="metric-trend">
              <span className="badge-up">+0%</span>
              <span>vs. previous</span>
            </div>
          </div>
          <div className="metric-card" title="Runs with at least one failure detected (hallucination, planning, or tool misuse).">
            <div className="metric-label">Runs with Failures</div>
            <div className="metric-value">
              {runs.filter((r) => (r.failure_count ?? 0) > 0).length}
            </div>
            <div className="metric-trend">
              <span className="badge-up">+0%</span>
              <span>vs. previous</span>
            </div>
          </div>
        </section>

        <section className="runs-analytics-row">
          <div className="card-panel runs-list">
            <div className="card-header">
              <div>
                <h2>Recent Runs</h2>
                <div className="card-subtitle">
                  Latest executions recorded via the Flight Recorder.
                </div>
              </div>
              <button
                type="button"
                className="btn-header"
                onClick={() => {
                  const q = new URLSearchParams({ format: 'csv', limit: '1000' })
                  if (filterAgentId) q.set('agent_id', filterAgentId)
                  if (filterDateFrom) q.set('date_from', filterDateFrom)
                  if (filterDateTo) q.set('date_to', filterDateTo)
                  fetch(`${API_BASE}/api/v1/runs/export?${q}`)
                    .then((r) => r.blob())
                    .then((blob) => {
                      const a = document.createElement('a')
                      a.href = URL.createObjectURL(blob)
                      a.download = 'runs.csv'
                      a.click()
                      URL.revokeObjectURL(a.href)
                    })
                    .catch(() => {})
                }}
              >
                Export CSV
              </button>
            </div>
            {error && (
              <p className="error">Could not reach API or load runs ({error}). Check that the backend is running.</p>
            )}
            <div className="runs-toolbar">
              {agents.length > 0 && (
                <select
                  className="filter-select"
                  value={filterAgentId}
                  onChange={(e) => setFilterAgentId(e.target.value)}
                  title="Filter by agent"
                >
                  <option value="">All agents</option>
                  {agents.map((a) => (
                    <option key={a} value={a}>{a}</option>
                  ))}
                </select>
              )}
              <input
                type="date"
                className="filter-input"
                value={filterDateFrom}
                onChange={(e) => setFilterDateFrom(e.target.value)}
                title="From date"
              />
              <input
                type="date"
                className="filter-input"
                value={filterDateTo}
                onChange={(e) => setFilterDateTo(e.target.value)}
                title="To date"
              />
              {selectedSimulationId && !error && (
                <button type="button" className="btn-clear-filter" onClick={() => setSelectedSimulationId(null)}>
                  Show all runs
                </button>
              )}
            </div>
            {loadingRuns && (
              <div className="skeleton-list">
                {[1, 2, 3, 4, 5].map((i) => (
                  <div key={i} className="skeleton-line" />
                ))}
              </div>
            )}
            {!loadingRuns && runs.length === 0 && !error && (
              <div className="empty-state">
                <p>No runs yet.</p>
                <p className="empty-state-hint">Send your first run with the SDK or run a simulation. See <code>docs/RUNBOOK.md</code> for <code>send_test_run.py</code> and API examples.</p>
              </div>
            )}
            {!loadingRuns && runs.length > 0 && (
              <>
                <ul>
                  {runs.map((run) => (
                    <li
                      key={run.id}
                      className={run.id === selectedRunId ? 'run-item selected' : 'run-item'}
                      onClick={() => setSelectedRunId(run.id)}
                    >
                      <div className="run-title">
                        <span className="run-agent">{run.agent_id}</span>
                        <span className={`run-status status-${run.status}`}>{run.status}</span>
                        {(run.failure_count ?? 0) > 0 && (
                          <span className="run-failure-pill" title="Failure count">{run.failure_count} failures</span>
                        )}
                      </div>
                      {run.user_query && (
                        <div className="run-query-preview" title={run.user_query}>{run.user_query}</div>
                      )}
                      <div className="run-meta">
                        <span>{new Date(run.created_at).toLocaleString()}</span>
                        {run.latency_ms != null && <span>{run.latency_ms} ms</span>}
                      </div>
                    </li>
                  ))}
                </ul>
                {hasMoreRuns && (
                  <button type="button" className="btn-load-more" onClick={loadMore} disabled={loadingMore}>
                    {loadingMore ? 'Loading…' : 'Load more'}
                  </button>
                )}
              </>
            )}
          </div>

          <div className="card-panel run-detail">
            <div className="card-header">
              <div>
                <h2>Run Detail</h2>
                <div className="card-subtitle">
                  Step-by-step reasoning and tool calls for the selected run.
                </div>
              </div>
            </div>
            {loadingRunDetail && (
              <div className="skeleton-detail">
                <div className="skeleton-line" style={{ width: '60%' }} />
                <div className="skeleton-line" style={{ width: '90%' }} />
                <div className="skeleton-line" style={{ width: '40%' }} />
              </div>
            )}
            {!loadingRunDetail && !selectedRun && (
              <p>Select a run from the left to inspect it.</p>
            )}
            {selectedRun && (
              <>
                <div className="run-detail-header-actions">
                  <button
                    type="button"
                    className="btn-link"
                    onClick={() => {
                      if (selectedRun?.run.id) {
                        navigator.clipboard.writeText(selectedRun.run.id)
                        setCopyRunIdMsg('Copied!')
                        setTimeout(() => setCopyRunIdMsg(null), 2000)
                      }
                    }}
                  >
                    {copyRunIdMsg ?? 'Copy run ID'}
                  </button>
                </div>
                <div className="run-summary">
                  <p>
                    <strong>Agent:</strong> {selectedRun.run.agent_id}{' '}
                    {selectedRun.run.agent_version && `(${selectedRun.run.agent_version})`}
                  </p>
                  <p>
                    <strong>User query:</strong> {selectedRun.run.input?.user_query ?? '—'}
                  </p>
                  <p>
                    <strong>Final answer:</strong> {selectedRun.run.output?.final_answer ?? '—'}
                  </p>
                  {selectedRun.failures.length > 0 && (
                    <div className="failure-summary">
                      {selectedRun.failures
                        .filter((f) => f.detector === 'overall')
                        .slice(0, 1)
                        .map((f) => (
                          <div key={f.id} className="failure-pill overall">
                            <span className="failure-label">Overall reliability</span>
                            <span className="failure-score">
                              {f.score !== null ? `${f.score}/100` : 'n/a'}
                            </span>
                          </div>
                        ))}
                      {selectedRun.failures
                        .filter((f) => f.detector === 'hallucination')
                        .slice(0, 1)
                        .map((f) => (
                          <div key={f.id} className="failure-pill">
                            <span className="failure-label">Hallucination risk</span>
                            <span className="failure-score">
                              {f.score !== null ? `${f.score}/100` : 'n/a'}
                            </span>
                            {f.label && <span className="failure-tag">{f.label}</span>}
                          </div>
                        ))}
                      {selectedRun.failures
                        .filter((f) => f.detector === 'hallucination')
                        .slice(0, 1)
                        .map((f) =>
                          f.explanation ? (
                            <p key={`${f.id}-ex`} className="failure-explanation">
                              {f.explanation}
                            </p>
                          ) : null,
                        )}
                      {selectedRun.failures
                        .filter((f) => f.detector === 'planning_failure')
                        .slice(0, 1)
                        .map((f) => (
                          <div key={f.id} className="failure-pill planning">
                            <span className="failure-label">Planning risk</span>
                            <span className="failure-score">
                              {f.score !== null ? `${f.score}/100` : 'n/a'}
                            </span>
                            {f.label && <span className="failure-tag">{f.label}</span>}
                          </div>
                        ))}
                      {selectedRun.failures
                        .filter((f) => f.detector === 'planning_failure')
                        .slice(0, 1)
                        .map((f) =>
                          f.explanation ? (
                            <p key={`${f.id}-pf-ex`} className="failure-explanation">
                              {f.explanation}
                            </p>
                          ) : null,
                        )}
                    </div>
                  )}
                </div>

                <div className="steps-timeline">
                  <h3>Steps</h3>
                  {selectedRun.steps.length === 0 && <p>No steps recorded.</p>}
                  <ol>
                    {selectedRun.steps.map((s) => (
                      <li key={s.id} className={`step step-${s.step_type}`}>
                        <div className="step-header">
                          <span className="step-idx">#{s.idx}</span>
                          <span className="step-type">{s.step_type}</span>
                          <span className="step-time">
                            {new Date(s.timestamp).toLocaleTimeString()}
                          </span>
                        </div>
                        <div className="step-body">
                          {s.request != null && (
                            <pre className="step-block">
                              <strong>Request</strong>
                              {'\n'}
                              {JSON.stringify(s.request, null, 2)}
                            </pre>
                          )}
                          {s.response != null && (
                            <pre className="step-block">
                              <strong>Response</strong>
                              {'\n'}
                              {JSON.stringify(s.response, null, 2)}
                            </pre>
                          )}
                        </div>
                      </li>
                    ))}
                  </ol>
                </div>
              </>
            )}
          </div>
        </section>

        <section className="card-panel">
          <div className="card-header">
            <div>
              <h2>Analytics</h2>
              <div className="card-subtitle">
                Run volume and reliability over time.
              </div>
            </div>
            <div className="tabs">
              <button
                type="button"
                className={`tab ${analyticsTab === '30d' ? 'active' : ''}`}
                onClick={() => setAnalyticsTab('30d')}
              >
                30 days
              </button>
              <button
                type="button"
                className={`tab ${analyticsTab === '7d' ? 'active' : ''}`}
                onClick={() => setAnalyticsTab('7d')}
              >
                7 days
              </button>
              <button
                type="button"
                className={`tab ${analyticsTab === '24h' ? 'active' : ''}`}
                onClick={() => setAnalyticsTab('24h')}
              >
                24 hours
              </button>
            </div>
          </div>
          <div className="analytics-chart">
            {runsPerDay.length === 0 && (
              <p className="analytics-empty">No data for this period.</p>
            )}
            {runsPerDay.length > 0 && (
              <div className="analytics-bars">
                {runsPerDay.map((d) => (
                  <div key={d.day} className="analytics-bar">
                    <div
                      className="bar-runs"
                      style={{ height: `${Math.min(100, Math.max(8, d.count * 12))}px` }}
                      title={`${d.count} runs`}
                    />
                    <div
                      className="bar-halluc"
                      style={{ height: `${Math.min(80, d.hallucination_rate)}px` }}
                      title={`${d.hallucination_rate}% hallucinations`}
                    />
                    <span className="bar-label">
                      {new Date(d.day).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>

        <section className="card-panel">
          <div className="card-header">
            <div>
              <h2>Failure patterns</h2>
              <div className="card-subtitle">
                Recurring failure types grouped by detector and explanation. Click a run to open Run Detail.
              </div>
            </div>
            <div className="tabs">
              <button
                type="button"
                className={`tab ${patternsDays === 7 ? 'active' : ''}`}
                onClick={() => setPatternsDays(7)}
              >
                7d
              </button>
              <button
                type="button"
                className={`tab ${patternsDays === 30 ? 'active' : ''}`}
                onClick={() => setPatternsDays(30)}
              >
                30d
              </button>
            </div>
          </div>
          {patterns.length === 0 && <p>No failure patterns in this period.</p>}
          {patterns.length > 0 && (
            <div className="patterns-table-wrap">
              <table className="patterns-table">
                <thead>
                  <tr>
                    <th>Detector</th>
                    <th>Summary</th>
                    <th>Count</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {patterns.map((p, i) => (
                    <tr key={`${p.detector}-${p.explanation_key}-${i}`}>
                      <td><span className="pattern-detector">{p.detector}</span></td>
                      <td className="pattern-summary" title={p.explanation_key}>{p.explanation_key}</td>
                      <td>{p.count}</td>
                      <td>
                        {p.example_run_ids.length > 0 ? (
                          <button
                            type="button"
                            className="btn-link"
                            onClick={() => {
                              setSelectedRunId(p.example_run_ids[0])
                              setSelectedRun(null)
                            }}
                          >
                            View run
                          </button>
                        ) : null}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section className="card-panel">
          <div className="card-header">
            <div>
              <h2>Simulations</h2>
              <div className="card-subtitle">
                Batch tests against your agent. Total runs = completed calls; success % = runs with status success;
                hallucinations % = runs where the hallucination detector fired. Click a simulation to filter Recent Runs.
              </div>
            </div>
          </div>
          {simulations.length === 0 && <p>No simulations yet.</p>}
          {simulations.length > 0 && (
            <ul>
              {simulations.map((s) => (
                <li
                  key={s.id}
                  className={s.id === selectedSimulationId ? 'run-item selected' : 'run-item'}
                  onClick={() => setSelectedSimulationId(s.id)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => e.key === 'Enter' && setSelectedSimulationId(s.id)}
                >
                  <div className="run-title">
                    <span className="run-agent">{s.name}</span>
                    <span className={`run-status status-${s.status}`}>{s.status}</span>
                  </div>
                  <div className="run-meta">
                    <span>{new Date(s.created_at).toLocaleString()}</span>
                    <span>{s.num_runs} runs</span>
                    <span>{s.metrics.total_runs ?? 0} completed</span>
                    {typeof s.metrics.success_rate === 'number' && (
                      <span>{s.metrics.success_rate}% success</span>
                    )}
                    {typeof s.metrics.hallucination_rate === 'number' && (
                      <span>{s.metrics.hallucination_rate}% hallucinations</span>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </main>
    </div>
  )
}

export default App
