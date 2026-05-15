import React, { useEffect, useState } from 'react'
import { Activity, AlertTriangle, Bot, CheckCircle2, KeyRound, MapPin, Play, RefreshCw, ShieldCheck, Workflow, XCircle } from 'lucide-react'
import {
  getAutomationRuns,
  getAutomationWorkflows,
  getCapabilityStatus,
  getN8nStatus,
  runAutomationWorkflow,
  runLocalMarketDiscovery,
} from '../../services/api'

const card = 'glass rounded-xl border border-white/[0.07] bg-white/[0.03]'
const input = 'w-full rounded-lg border border-white/10 bg-white/[0.05] px-3 py-2 text-sm text-white outline-none placeholder:text-white/25 focus:border-jarvis-blue/50'

function StatePill({ state }) {
  const ok = ['ready', 'completed', 'dashboard_only'].includes(state)
  const warn = ['degraded', 'blocked', 'running'].includes(state)
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-1 text-[11px] font-medium ${
      ok ? 'border-emerald-400/25 bg-emerald-400/10 text-emerald-300'
        : warn ? 'border-amber-400/25 bg-amber-400/10 text-amber-300'
          : 'border-white/10 bg-white/[0.04] text-white/45'
    }`}>
      {ok ? <CheckCircle2 size={12} /> : warn ? <AlertTriangle size={12} /> : <XCircle size={12} />}
      {state}
    </span>
  )
}

export default function AutomationCenter() {
  const [capabilities, setCapabilities] = useState(null)
  const [n8n, setN8n] = useState(null)
  const [workflows, setWorkflows] = useState([])
  const [runs, setRuns] = useState([])
  const [discovery, setDiscovery] = useState({ industry: 'clinics', location: 'New York', service_angle: 'AI receptionist and appointment booking', limit: 20 })
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  const load = async () => {
    const [cap, n8nStatus, wf, runData] = await Promise.all([
      getCapabilityStatus().catch(() => null),
      getN8nStatus().catch(() => null),
      getAutomationWorkflows().catch(() => ({ workflows: [] })),
      getAutomationRuns().catch(() => ({ runs: [] })),
    ])
    setCapabilities(cap)
    setN8n(n8nStatus)
    setWorkflows(wf.workflows || [])
    setRuns(runData.runs || [])
  }

  useEffect(() => { load() }, [])

  const runDiscovery = async () => {
    setLoading(true)
    setResult(null)
    try {
      const data = await runLocalMarketDiscovery({ ...discovery, limit: Number(discovery.limit) })
      setResult(data)
      await load()
    } catch (err) {
      setResult({ error: err.response?.data?.detail || err.message })
    }
    setLoading(false)
  }

  const triggerWorkflow = async (key) => {
    setLoading(true)
    try {
      const data = await runAutomationWorkflow(key, discovery)
      setResult(data)
      await load()
    } catch (err) {
      setResult({ error: err.response?.data?.detail || err.message })
    }
    setLoading(false)
  }

  const readyCount = capabilities?.capabilities?.filter(c => ['ready', 'dashboard_only'].includes(c.state)).length || 0
  const blockers = capabilities?.blockers || []

  return (
    <div className="h-full overflow-y-auto p-6 space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Automation Center</h1>
          <p className="mt-1 text-sm text-white/45">Jarvis command brain, n8n tool army, local market hunter, and sales war room.</p>
        </div>
        <button onClick={load} className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/[0.04] px-3 py-2 text-sm text-white/65 hover:text-white">
          <RefreshCw size={15} /> Refresh
        </button>
      </div>

      <div className="grid gap-4 xl:grid-cols-4 md:grid-cols-2">
        <div className={`${card} p-4`}>
          <div className="flex items-center gap-2 text-sm font-semibold text-white"><Bot size={16} className="text-jarvis-blue" /> Command Brain</div>
          <p className="mt-3 text-2xl font-bold text-white">{readyCount}</p>
          <p className="text-xs text-white/35">capabilities ready</p>
        </div>
        <div className={`${card} p-4`}>
          <div className="flex items-center gap-2 text-sm font-semibold text-white"><Workflow size={16} className="text-jarvis-blue" /> n8n Tool Army</div>
          <p className="mt-3 text-sm text-white/70">{n8n?.reachable ? 'Reachable' : 'Needs setup'}</p>
          <p className="truncate text-xs text-white/35">{n8n?.base_url || 'No n8n URL'}</p>
        </div>
        <div className={`${card} p-4`}>
          <div className="flex items-center gap-2 text-sm font-semibold text-white"><ShieldCheck size={16} className="text-jarvis-blue" /> Permission Mode</div>
          <p className="mt-3 text-sm text-white/70">Auto safe work</p>
          <p className="text-xs text-white/35">approval for external impact</p>
        </div>
        <div className={`${card} p-4`}>
          <div className="flex items-center gap-2 text-sm font-semibold text-white"><AlertTriangle size={16} className="text-amber-300" /> Blockers</div>
          <p className="mt-3 text-2xl font-bold text-white">{blockers.length}</p>
          <p className="text-xs text-white/35">exact setup items</p>
        </div>
      </div>

      {blockers.length > 0 && (
        <div className={`${card} p-4`}>
          <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-white"><KeyRound size={16} className="text-amber-300" /> Access Needed</div>
          <div className="grid gap-3 lg:grid-cols-2">
            {blockers.map((b) => (
              <div key={b.id} className="rounded-lg border border-amber-400/15 bg-amber-400/[0.06] p-3">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-medium text-white">{b.name}</p>
                  <StatePill state={b.state} />
                </div>
                <p className="mt-1 text-xs text-white/45">{b.summary}</p>
                {b.missing?.length > 0 && <p className="mt-2 text-xs text-amber-200">Missing: {b.missing.join(', ')}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid gap-5 xl:grid-cols-[0.9fr_1.1fr]">
        <div className={`${card} p-5`}>
          <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-white"><MapPin size={16} className="text-jarvis-blue" /> Local Market Hunter</div>
          <div className="space-y-3">
            <input className={input} value={discovery.industry} onChange={e => setDiscovery(s => ({ ...s, industry: e.target.value }))} placeholder="Industry, e.g. clinics" />
            <input className={input} value={discovery.location} onChange={e => setDiscovery(s => ({ ...s, location: e.target.value }))} placeholder="Location, e.g. New York" />
            <input className={input} value={discovery.service_angle} onChange={e => setDiscovery(s => ({ ...s, service_angle: e.target.value }))} placeholder="Service angle" />
            <input className={input} type="number" min="1" max="60" value={discovery.limit} onChange={e => setDiscovery(s => ({ ...s, limit: e.target.value }))} />
            <div className="flex flex-wrap gap-3">
              <button onClick={runDiscovery} disabled={loading} className="inline-flex items-center gap-2 rounded-lg bg-jarvis-blue px-4 py-2 text-sm font-semibold text-black disabled:opacity-50">
                <Play size={15} /> Run Discovery
              </button>
              <button onClick={() => triggerWorkflow('local_market_discovery')} disabled={loading} className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/[0.04] px-4 py-2 text-sm text-white/70 disabled:opacity-50">
                <Workflow size={15} /> Trigger n8n
              </button>
            </div>
          </div>
        </div>

        <div className={`${card} p-5`}>
          <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-white"><Activity size={16} className="text-jarvis-blue" /> Sales War Room Output</div>
          {!result && <p className="text-sm text-white/35">Run discovery to create leads, pain signals, scores, and next actions.</p>}
          {result?.error && <pre className="whitespace-pre-wrap rounded-lg border border-red-400/20 bg-red-400/10 p-3 text-xs text-red-200">{JSON.stringify(result.error, null, 2)}</pre>}
          {result?.leads && (
            <div className="space-y-3">
              <p className="text-sm text-emerald-300">Created {result.created}, updated {result.updated}. Next: {result.next_action}</p>
              {result.leads.slice(0, 8).map((lead) => (
                <div key={`${lead.company}-${lead.id}`} className="rounded-lg border border-white/[0.06] bg-white/[0.03] p-3">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-semibold text-white">{lead.company}</p>
                    <span className="text-xs text-jarvis-blue">Score {lead.score} · Tier {lead.tier}</span>
                  </div>
                  <p className="mt-1 text-xs text-white/45">{lead.opportunity_type}</p>
                  <p className="mt-2 text-xs text-white/35">{lead.pain_points.join(' · ')}</p>
                </div>
              ))}
            </div>
          )}
          {result && !result.leads && !result.error && <pre className="max-h-72 overflow-auto whitespace-pre-wrap text-xs text-white/55">{JSON.stringify(result, null, 2)}</pre>}
        </div>
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <div className={`${card} p-5`}>
          <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-white"><Workflow size={16} className="text-jarvis-blue" /> Registered Workflows</div>
          <div className="space-y-3">
            {workflows.map((wf) => (
              <div key={wf.key} className="rounded-lg border border-white/[0.06] bg-white/[0.03] p-3">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-semibold text-white">{wf.name}</p>
                  <span className="text-xs text-white/35">{wf.risk}</span>
                </div>
                <p className="mt-1 text-xs text-white/45">{wf.description}</p>
                <p className="mt-2 text-xs text-emerald-300">{wf.approval_rule}</p>
              </div>
            ))}
          </div>
        </div>
        <div className={`${card} p-5`}>
          <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-white"><Activity size={16} className="text-jarvis-blue" /> Latest Runs</div>
          <div className="space-y-3">
            {runs.length === 0 && <p className="text-sm text-white/35">No automation runs yet.</p>}
            {runs.map((run) => (
              <div key={run.id} className="rounded-lg border border-white/[0.06] bg-white/[0.03] p-3">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-semibold text-white">{run.workflow_name}</p>
                  <StatePill state={run.status} />
                </div>
                {run.error && <p className="mt-2 text-xs text-amber-200">{run.error}</p>}
                <p className="mt-2 text-[11px] text-white/25">{run.started_at}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
