import React, { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Activity, AlertTriangle, BarChart3, Brain, CheckCircle2,
  Clock, Database, DollarSign, Loader2, Mail, Network,
  RefreshCw, Server, Shield, Target, Users, XCircle, Zap,
} from 'lucide-react'
import api from '../../services/api'

const DEFAULT_TENANT = '794d9b02-2dd6-49f0-b5c1-9f7c0b3af4b1'

const CHECKS = [
  { key: 'root',      label: 'API Gateway',       path: '/health',                       icon: Server,   critical: true  },
  { key: 'apiv1',     label: 'API v1 Core',        path: '/api/v1/health',                icon: Zap,      critical: true  },
  { key: 'readyz',    label: 'Deep Readiness',     path: '/readyz',                       icon: Activity, critical: true  },
  { key: 'ai',        label: 'AI Engine',          path: '/api/v1/ai-ops/health',         icon: Brain,    critical: true  },
  { key: 'auth',      label: 'Auth System',        path: '/api/v1/auth/gmail/status',     icon: Shield,   critical: true  },
  { key: 'email',     label: 'Email (SES)',        path: '/api/v1/gmail/status',          icon: Mail,     critical: false },
  { key: 'comms',     label: 'Comms Hub',          path: '/api/v1/communication/status',  icon: Network,  critical: false },
  { key: 'scheduler', label: 'Scheduler',          path: '/api/v1/scheduler/jobs',        icon: Clock,    critical: false },
  { key: 'agents',    label: 'Agent Network',      path: '/api/v1/agents/capacity',       icon: Users,    critical: false },
  { key: 'leads',     label: 'Lead Pipeline',      path: '/api/v1/leads/stats',           icon: Target,   critical: false },
  { key: 'db',        label: 'Database Layer',     path: '/readyz',                       icon: Database, critical: true  },
  { key: 'hud',       label: 'System HUD',         path: '/api/v1/system/hud',            icon: BarChart3,critical: false },
]

async function ping(path) {
  const t0 = Date.now()
  try {
    const res = await api.get(path, { timeout: 6000 })
    const ms = Date.now() - t0
    const s = res.data?.status || res.data?.health || ''
    const notOk = ['error', 'critical', 'down', 'unhealthy'].includes(String(s).toLowerCase())
    return { status: notOk ? 'warning' : 'ok', ms, data: res.data }
  } catch (err) {
    const ms = Date.now() - t0
    const code = err.response?.status
    if (code === 401 || code === 403) return { status: 'ok', ms, note: 'auth-gated' }
    if (code >= 200 && code < 500) return { status: 'warning', ms, note: `HTTP ${code}` }
    return { status: 'down', ms, note: err.code === 'ECONNABORTED' ? 'Timeout' : 'Unreachable' }
  }
}

const STATUS_STYLE = {
  ok:      { dot: 'bg-green-400 shadow-[0_0_6px_#4ade80]', text: 'text-green-400',  border: 'border-green-400/15 bg-green-400/5',  badge: 'text-green-300' },
  warning: { dot: 'bg-yellow-400 shadow-[0_0_6px_#facc15]', text: 'text-yellow-400', border: 'border-yellow-400/15 bg-yellow-400/5', badge: 'text-yellow-300' },
  down:    { dot: 'bg-red-400 shadow-[0_0_6px_#f87171]',   text: 'text-red-400',   border: 'border-red-400/15 bg-red-400/5',     badge: 'text-red-300' },
  pending: { dot: 'bg-white/20 animate-pulse',              text: 'text-white/30',  border: 'border-white/[0.06] bg-white/[0.02]', badge: 'text-white/30' },
}

function fmt(n) {
  const v = Number(n || 0)
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`
  if (v >= 1_000) return `$${(v / 1_000).toFixed(0)}K`
  return `$${v.toFixed(0)}`
}

export default function CommandCenter() {
  const [results, setResults]           = useState({})
  const [metrics, setMetrics]           = useState(null)
  const [aiHealth, setAiHealth]         = useState(null)
  const [aiCost, setAiCost]             = useState(null)
  const [running, setRunning]           = useState(false)
  const [lastAt, setLastAt]             = useState(null)
  const [countdown, setCountdown]       = useState(30)
  const [actionResult, setActionResult] = useState(null)
  const [actionBusy, setActionBusy]     = useState(false)

  const runAll = useCallback(async () => {
    if (running) return
    setRunning(true)

    const pairs = await Promise.all(CHECKS.map(async c => {
      const r = await ping(c.path)
      return [c.key, r]
    }))
    setResults(Object.fromEntries(pairs))

    // Supplementary data — non-blocking
    Promise.all([
      api.get('/api/v1/revenue/snapshot').catch(() => null),
      api.get('/api/v1/leads/stats').catch(() => null),
    ]).then(([rev, ls]) => {
      setMetrics({
        mrr:      rev?.data?.mrr ?? rev?.data?.monthly_recurring_revenue ?? 0,
        clients:  rev?.data?.active_clients ?? 0,
        leads:    ls?.data?.total ?? 0,
        pipeline: ls?.data?.pipeline_value ?? rev?.data?.pipeline_value ?? 0,
      })
    })

    api.get('/api/v1/ai-ops/health').then(r => setAiHealth(r.data)).catch(() => {})
    api.get('/api/v1/ai-ops/cost/today').then(r => setAiCost(r.data)).catch(() => {})

    setLastAt(new Date())
    setCountdown(30)
    setRunning(false)
  }, [running])

  useEffect(() => { runAll() }, []) // eslint-disable-line

  useEffect(() => {
    const id = setInterval(() => {
      setCountdown(c => {
        if (c <= 1) { runAll(); return 30 }
        return c - 1
      })
    }, 1000)
    return () => clearInterval(id)
  }, [runAll])

  // ── Derived status ─────────────────────────────────────────────────────────
  const allResults   = Object.values(results)
  const checked      = allResults.length
  const okCount      = allResults.filter(r => r.status === 'ok').length
  const downCritical = CHECKS.filter(c => c.critical && results[c.key]?.status === 'down')
  const anyDown      = allResults.some(r => r.status === 'down')

  const overallStatus =
    checked === 0             ? 'checking'    :
    downCritical.length > 0   ? 'critical'    :
    anyDown                   ? 'degraded'    :
    okCount === checked       ? 'operational' : 'partial'

  const overallStyle = {
    checking:    { border: 'border-white/10',        bg: 'bg-white/[0.02]',    text: 'text-white/60',    icon: <Loader2 size={18} className="text-white/30 animate-spin" /> },
    operational: { border: 'border-green-400/25',    bg: 'bg-green-400/5',     text: 'text-green-300',   icon: <CheckCircle2 size={18} className="text-green-400" /> },
    degraded:    { border: 'border-yellow-400/25',   bg: 'bg-yellow-400/5',    text: 'text-yellow-300',  icon: <AlertTriangle size={18} className="text-yellow-400" /> },
    critical:    { border: 'border-red-400/25',      bg: 'bg-red-400/5',       text: 'text-red-300',     icon: <XCircle size={18} className="text-red-400" /> },
    partial:     { border: 'border-yellow-400/25',   bg: 'bg-yellow-400/5',    text: 'text-yellow-300',  icon: <AlertTriangle size={18} className="text-yellow-400" /> },
  }[overallStatus]

  const overallLabel = {
    checking:    'Scanning all systems…',
    operational: 'All Systems Operational',
    degraded:    'System Degraded — Non-Critical Services Down',
    critical:    `Critical Outage — ${downCritical.map(c => c.label).join(', ')} Down`,
    partial:     'Partial Outage — Some Services Unavailable',
  }[overallStatus]

  // ── Quick actions ──────────────────────────────────────────────────────────
  async function doAction(label, fn) {
    setActionBusy(true)
    setActionResult(null)
    try {
      const r = await fn()
      setActionResult({ label, ok: true, data: r.data })
    } catch (e) {
      setActionResult({ label, ok: false, error: e.response?.data?.detail || e.message })
    }
    setActionBusy(false)
  }

  const ACTIONS = [
    { label: 'Morning Brief',    desc: 'Generate today\'s brief',   fn: () => api.post('/api/v1/briefing/generate',  { tenant_id: DEFAULT_TENANT }) },
    { label: 'Seed Demo Data',   desc: 'Populate demo clients/leads', fn: () => api.post('/api/v1/captain/seed-demo', { tenant_id: DEFAULT_TENANT }) },
    { label: 'Run Evolution',    desc: 'Trigger JARVIS self-learning', fn: () => api.post('/api/v1/jarvis/evolve',   { tenant_id: DEFAULT_TENANT }) },
    { label: 'Score All Leads',  desc: 'AI-score 50 leads now',    fn: () => api.post('/api/v1/leads/score-all',    { limit: 50 }) },
    { label: 'Activate Pilot',   desc: 'Enable autonomous mode',   fn: () => api.post('/api/v1/pilot/activate',     { tenant_id: DEFAULT_TENANT }) },
    { label: 'Run Radar Scan',   desc: 'Scan tech + market trends', fn: () => api.post('/api/v1/intelligence/radar/scan', { tenant_id: DEFAULT_TENANT }) },
    { label: 'Ingest Connectors', desc: 'Pull all connector data',  fn: () => api.post('/api/v1/connector-hub/ingest', { tenant_id: DEFAULT_TENANT }) },
    { label: 'Reset AI Circuit', desc: 'Reset claude provider CB', fn: () => api.post('/api/v1/ai-ops/health/claude/reset') },
    { label: 'Self-Heal Now',    desc: 'Auto-recover all systems',  fn: () => api.post('/api/v1/system/self-heal') },
  ]

  // ── AI providers map ───────────────────────────────────────────────────────
  const providerEntries = aiHealth
    ? Object.entries(aiHealth.providers || aiHealth).filter(([k]) => !['status', 'error', 'timestamp'].includes(k))
    : []

  return (
    <div className="h-full overflow-y-auto no-scrollbar p-6 space-y-5">

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-white">Command Center</h1>
          <p className="text-[11px] text-white/35 mt-0.5">
            Live backend health · system status · quick controls
          </p>
        </div>
        <div className="flex items-center gap-3">
          {lastAt && (
            <span className="text-[11px] text-white/25 flex items-center gap-1">
              <Clock size={10} /> {lastAt.toLocaleTimeString()}
            </span>
          )}
          <span className="text-[11px] text-white/20">Auto-refresh in {countdown}s</span>
          <button
            onClick={runAll}
            disabled={running}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-white/10
                       bg-white/[0.04] hover:bg-white/[0.08] text-[11px] text-white/60
                       transition-colors disabled:opacity-40"
          >
            <RefreshCw size={10} className={running ? 'animate-spin' : ''} />
            Refresh Now
          </button>
        </div>
      </div>

      {/* ── Overall status banner ───────────────────────────────────────────── */}
      <div className={`rounded-xl border p-4 flex items-center gap-3 ${overallStyle.border} ${overallStyle.bg}`}>
        {overallStyle.icon}
        <div className="flex-1">
          <p className={`text-sm font-semibold ${overallStyle.text}`}>{overallLabel}</p>
          <p className="text-[11px] text-white/30 mt-0.5">
            {checked} services monitored · {okCount} operational
            {aiCost?.total_usd != null && ` · AI cost today: $${Number(aiCost.total_usd).toFixed(4)}`}
          </p>
        </div>
        <span className="text-[10px] text-white/20 uppercase tracking-wider">JARVIS v9</span>
      </div>

      {/* ── Health check grid ───────────────────────────────────────────────── */}
      <div>
        <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-white/35 mb-3">
          Service Health
        </p>
        <div className="grid grid-cols-2 gap-2 lg:grid-cols-3 xl:grid-cols-4">
          {CHECKS.map(check => {
            const r = results[check.key]
            const st = r?.status || 'pending'
            const style = STATUS_STYLE[st]
            const Icon = check.icon
            return (
              <motion.div
                key={check.key}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className={`rounded-xl border p-3 flex items-center gap-2.5 ${style.border}`}
              >
                <div className={`w-6 h-6 rounded-md flex items-center justify-center flex-shrink-0 bg-white/[0.04]`}>
                  <Icon size={12} className={style.text} />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5">
                    <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${style.dot}`} />
                    <p className="text-[11px] font-medium text-white/75 truncate">{check.label}</p>
                  </div>
                  <p className={`text-[10px] mt-0.5 ${style.text}`}>
                    {st === 'pending' ? 'Checking…' :
                     st === 'ok'      ? `${r.ms}ms` :
                     r?.note || r?.error || st}
                  </p>
                </div>
                {check.critical && (
                  <span className="text-[8px] text-white/15 uppercase tracking-wider flex-shrink-0">core</span>
                )}
              </motion.div>
            )
          })}
        </div>
      </div>

      {/* ── Live metrics ────────────────────────────────────────────────────── */}
      <div>
        <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-white/35 mb-3">
          Live Business Metrics
        </p>
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {[
            { label: 'Monthly MRR',     value: metrics ? fmt(metrics.mrr)      : '—', icon: DollarSign, color: 'text-jarvis-gold',   glow: 'shadow-[0_0_20px_rgba(255,183,0,0.08)]' },
            { label: 'Active Clients',  value: metrics ? metrics.clients        : '—', icon: Users,      color: 'text-jarvis-cyan',   glow: 'shadow-[0_0_20px_rgba(0,200,255,0.08)]' },
            { label: 'Total Leads',     value: metrics ? metrics.leads          : '—', icon: Target,     color: 'text-blue-400',      glow: '' },
            { label: 'Pipeline Value',  value: metrics ? fmt(metrics.pipeline)  : '—', icon: BarChart3,  color: 'text-purple-400',    glow: '' },
          ].map(m => {
            const Icon = m.icon
            return (
              <div key={m.label}
                className={`rounded-xl border border-white/[0.06] bg-white/[0.02] p-4 ${m.glow}`}>
                <Icon size={14} className={`${m.color} mb-2.5 opacity-80`} />
                <p className={`text-2xl font-bold ${m.color}`}>{m.value}</p>
                <p className="text-[10px] text-white/30 mt-1">{m.label}</p>
              </div>
            )
          })}
        </div>
      </div>

      {/* ── AI Providers ────────────────────────────────────────────────────── */}
      {providerEntries.length > 0 && (
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-white/35 mb-3">
            AI Provider Status
          </p>
          <div className="flex flex-wrap gap-2">
            {providerEntries.map(([key, val]) => {
              const ok = val === true || val?.available === true || val?.status === 'ok' || val?.healthy === true
              return (
                <div key={key}
                  className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-[11px] font-medium
                    ${ok ? 'border-green-400/20 bg-green-400/5 text-green-300' : 'border-red-400/20 bg-red-400/5 text-red-300'}`}
                >
                  <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${ok ? 'bg-green-400' : 'bg-red-400'}`} />
                  {key}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* ── Quick Actions ────────────────────────────────────────────────────── */}
      <div>
        <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-white/35 mb-3">
          Quick Actions
        </p>
        <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
          {ACTIONS.map(a => (
            <button
              key={a.label}
              onClick={() => doAction(a.label, a.fn)}
              disabled={actionBusy}
              className="rounded-xl border border-white/[0.07] bg-white/[0.03] hover:bg-white/[0.07]
                         p-3 text-left transition-all duration-200 disabled:opacity-40 group"
            >
              <p className="text-[11px] font-semibold text-white/75 group-hover:text-white transition-colors">
                {a.label}
              </p>
              <p className="text-[10px] text-white/25 mt-0.5">{a.desc}</p>
            </button>
          ))}
        </div>
      </div>

      {/* ── Action result ────────────────────────────────────────────────────── */}
      <AnimatePresence>
        {actionResult && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className={`rounded-xl border p-4 ${
              actionResult.ok ? 'border-green-400/20 bg-green-400/5' : 'border-red-400/20 bg-red-400/5'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <p className={`text-xs font-semibold ${actionResult.ok ? 'text-green-300' : 'text-red-300'}`}>
                {actionResult.label} — {actionResult.ok ? 'Completed' : 'Failed'}
              </p>
              <button
                onClick={() => setActionResult(null)}
                className="text-[10px] text-white/25 hover:text-white/50 transition-colors"
              >
                Dismiss
              </button>
            </div>
            <pre className="text-[10px] text-white/45 overflow-auto max-h-36">
              {JSON.stringify(actionResult.ok ? actionResult.data : actionResult.error, null, 2)}
            </pre>
          </motion.div>
        )}
      </AnimatePresence>

    </div>
  )
}
