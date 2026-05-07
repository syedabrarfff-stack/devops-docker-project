import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  Cpu, Zap, DollarSign, Shield, Activity, AlertTriangle,
  CheckCircle, XCircle, RotateCcw, RefreshCw, Clock, Key,
} from 'lucide-react'
import {
  getAIOpsHealth, getAIOpsCostToday, getAIOpsCostSummary,
  getAIOpsAudit, getAIOpsCredentials, getAIOpsRoutingTable,
  getAIOpsPulse, resetAICircuit,
} from '../../services/api'

const STATE_COLORS = {
  CLOSED:    { bg: 'bg-emerald-400/10', text: 'text-emerald-400', border: 'border-emerald-400/20', dot: 'bg-emerald-400' },
  HALF_OPEN: { bg: 'bg-amber-400/10',   text: 'text-amber-400',   border: 'border-amber-400/20',   dot: 'bg-amber-400' },
  OPEN:      { bg: 'bg-red-400/10',     text: 'text-red-400',     border: 'border-red-400/20',     dot: 'bg-red-400' },
  unknown:   { bg: 'bg-white/5',        text: 'text-white/40',    border: 'border-white/10',       dot: 'bg-white/30' },
}

const SEVERITY_COLORS = {
  critical: 'text-red-400',
  high:     'text-orange-400',
  medium:   'text-amber-400',
  low:      'text-white/40',
}

function PulseCards({ pulse }) {
  if (!pulse) return null
  const cards = [
    { label: 'AI Providers Active', value: `${pulse.ai_providers_available}/${pulse.ai_providers_total}`, icon: Cpu, color: pulse.ai_providers_available > 0 ? 'text-emerald-400' : 'text-red-400' },
    { label: 'Open Circuits', value: pulse.open_circuits, icon: AlertTriangle, color: pulse.open_circuits > 0 ? 'text-red-400' : 'text-emerald-400' },
    { label: "Today's AI Spend", value: `$${pulse.today_cost_usd?.toFixed(4) || '0.0000'}`, icon: DollarSign, color: pulse.cost_surge_alert ? 'text-red-400' : 'text-jarvis-blue' },
    { label: 'Credentials OK', value: `${pulse.credentials_configured}/${pulse.credentials_total}`, icon: Key, color: pulse.system_ready ? 'text-emerald-400' : 'text-amber-400' },
  ]
  return (
    <div className="grid grid-cols-4 gap-3">
      {cards.map(({ label, value, icon: Icon, color }) => (
        <div key={label} className="glass border border-white/[0.07] rounded-xl px-4 py-3">
          <div className="flex items-center gap-2 mb-1">
            <Icon size={14} className={color} />
            <span className="text-[10px] text-white/40 uppercase tracking-wider">{label}</span>
          </div>
          <p className={`text-xl font-bold ${color}`}>{value}</p>
        </div>
      ))}
    </div>
  )
}

function CircuitBreakerCard({ cb, onReset }) {
  const [resetting, setResetting] = useState(false)
  const colors = STATE_COLORS[cb.state] || STATE_COLORS.unknown

  const handleReset = async () => {
    setResetting(true)
    try { await onReset(cb.provider) } catch (_) { /* */ }
    finally { setResetting(false) }
  }

  return (
    <div className={`glass border rounded-xl p-4 ${colors.border}`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${colors.dot} ${cb.state === 'OPEN' ? 'animate-pulse' : ''}`} />
          <span className="text-sm font-semibold text-white capitalize">{cb.provider}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full border ${colors.bg} ${colors.text} ${colors.border}`}>
            {cb.state}
          </span>
          {cb.state === 'OPEN' && (
            <button
              onClick={handleReset}
              disabled={resetting}
              className="flex items-center gap-1 px-2 py-1 rounded-md text-[10px] bg-white/[0.05] hover:bg-white/[0.08] text-white/60 transition-colors"
            >
              <RotateCcw size={10} className={resetting ? 'animate-spin' : ''} />
              Reset
            </button>
          )}
        </div>
      </div>
      <div className="grid grid-cols-3 gap-2 text-[10px]">
        <div>
          <p className="text-white/30">Requests</p>
          <p className="text-white/70 font-medium">{cb.total_requests?.toLocaleString() || 0}</p>
        </div>
        <div>
          <p className="text-white/30">Failures</p>
          <p className={`font-medium ${cb.total_failures > 0 ? 'text-red-400' : 'text-white/70'}`}>{cb.total_failures || 0}</p>
        </div>
        <div>
          <p className="text-white/30">Avg Latency</p>
          <p className="text-white/70 font-medium">{Math.round(cb.avg_latency_ms || 0)}ms</p>
        </div>
      </div>
      <div className="mt-2 h-1 bg-white/[0.06] rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${cb.total_failures > 0 ? 'bg-red-400/60' : 'bg-emerald-400/60'}`}
          style={{ width: `${cb.uptime_pct || 100}%` }}
        />
      </div>
      <p className="text-[9px] text-white/30 mt-1">{cb.uptime_pct?.toFixed(1) || 100}% uptime</p>
    </div>
  )
}

function CostChart({ summary }) {
  if (!summary?.daily?.length) return null
  const max = Math.max(...summary.daily.map(d => d.cost_usd), 0.01)
  return (
    <div className="glass border border-white/[0.07] rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm font-semibold text-white">7-Day AI Spend</p>
        <p className="text-xs text-white/40">Total: <span className="text-jarvis-blue">${summary.total_cost_usd?.toFixed(4)}</span></p>
      </div>
      <div className="flex items-end gap-1 h-16">
        {summary.daily.map((d, i) => {
          const h = max > 0 ? (d.cost_usd / max) * 100 : 2
          const isToday = i === summary.daily.length - 1
          return (
            <div key={d.date} className="flex-1 flex flex-col items-center gap-1">
              <div
                className={`w-full rounded-t transition-all ${isToday ? 'bg-jarvis-blue/60' : 'bg-white/[0.1]'}`}
                style={{ height: `${Math.max(h, 2)}%` }}
                title={`${d.date}: $${d.cost_usd.toFixed(4)}`}
              />
              <span className="text-[8px] text-white/20 rotate-45 origin-left">{d.date.slice(5)}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function CredentialRow({ check }) {
  const sev = SEVERITY_COLORS[check.severity] || 'text-white/40'
  return (
    <div className="flex items-center gap-3 py-2 border-b border-white/[0.04] last:border-0">
      {check.configured
        ? <CheckCircle size={12} className="text-emerald-400 flex-shrink-0" />
        : <XCircle size={12} className={`${sev} flex-shrink-0`} />}
      <div className="flex-1 min-w-0">
        <p className="text-xs text-white/80 font-mono">{check.name}</p>
        <p className="text-[10px] text-white/30 truncate">{check.description}</p>
      </div>
      <div className="flex items-center gap-2 flex-shrink-0">
        {check.masked_value && (
          <span className="text-[10px] font-mono text-white/30">{check.masked_value}</span>
        )}
        <span className={`text-[9px] uppercase font-medium ${sev}`}>{check.severity}</span>
      </div>
    </div>
  )
}

function AuditLog({ logs }) {
  if (!logs?.length) return <p className="text-xs text-white/30 py-4 text-center">No requests logged yet</p>
  return (
    <div className="space-y-1">
      {logs.slice(0, 20).map((log) => (
        <div key={log.id} className="flex items-center gap-3 py-1.5 text-[10px] border-b border-white/[0.04] last:border-0">
          {log.success
            ? <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 flex-shrink-0" />
            : <div className="w-1.5 h-1.5 rounded-full bg-red-400 flex-shrink-0 animate-pulse" />}
          <span className="text-white/60 font-medium w-20 truncate capitalize">{log.provider}</span>
          <span className="text-white/40 flex-1 truncate">{log.model}</span>
          <span className="text-white/30 w-16 text-right">{log.task_type}</span>
          <span className="text-white/30 w-16 text-right">{log.latency_ms}ms</span>
          <span className="text-jarvis-blue w-20 text-right">${log.cost_estimate_usd?.toFixed(5)}</span>
        </div>
      ))}
    </div>
  )
}

const TABS = ['Overview', 'Circuit Breakers', 'Costs', 'Credentials', 'Audit Log']

export default function AIOpsDashboard() {
  const [tab, setTab] = useState('Overview')
  const [pulse, setPulse] = useState(null)
  const [health, setHealth] = useState(null)
  const [costToday, setCostToday] = useState(null)
  const [costSummary, setCostSummary] = useState(null)
  const [credentials, setCredentials] = useState(null)
  const [auditLogs, setAuditLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const load = async () => {
    try {
      const [p, h, ct, cs, cred, audit] = await Promise.allSettled([
        getAIOpsPulse(),
        getAIOpsHealth(),
        getAIOpsCostToday(),
        getAIOpsCostSummary(7),
        getAIOpsCredentials(),
        getAIOpsAudit(50),
      ])
      if (p.status === 'fulfilled') setPulse(p.value)
      if (h.status === 'fulfilled') setHealth(h.value)
      if (ct.status === 'fulfilled') setCostToday(ct.value)
      if (cs.status === 'fulfilled') setCostSummary(cs.value)
      if (cred.status === 'fulfilled') setCredentials(cred.value)
      if (audit.status === 'fulfilled') setAuditLogs(audit.value.logs || [])
    } catch (_) { /* no-op */ }
    finally { setLoading(false); setRefreshing(false) }
  }

  useEffect(() => { load() }, [])

  const handleRefresh = () => { setRefreshing(true); load() }

  const handleResetCircuit = async (provider) => {
    await resetAICircuit(provider)
    await load()
  }

  const circuits = health?.circuit_breakers || []
  const credChecks = credentials?.checks || []
  const criticalMissing = credChecks.filter(c => !c.configured && c.severity === 'critical')
  const highMissing = credChecks.filter(c => !c.configured && c.severity === 'high')

  return (
    <div className="h-full flex flex-col overflow-hidden p-6 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">AI Operations</h1>
          <p className="text-xs text-white/40 mt-0.5">Multi-model infrastructure · Circuit breakers · Cost tracking · Security</p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border
                     bg-white/[0.03] border-white/[0.08] text-white/50 hover:text-white/70 transition-all"
        >
          <RefreshCw size={12} className={refreshing ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* Pulse cards */}
      {!loading && <PulseCards pulse={pulse} />}

      {/* Surge alert */}
      {costToday?.surge_alert && (
        <motion.div
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-3 px-4 py-3 rounded-xl bg-red-400/10 border border-red-400/20"
        >
          <AlertTriangle size={16} className="text-red-400 flex-shrink-0" />
          <p className="text-xs text-red-400 font-medium">
            AI cost surge — Today's spend ${costToday.total_cost_usd?.toFixed(2)} exceeds ${costToday.surge_threshold_usd} threshold. Captain review required.
          </p>
        </motion.div>
      )}

      {/* Critical credentials warning */}
      {criticalMissing.length > 0 && (
        <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-red-400/10 border border-red-400/20">
          <XCircle size={16} className="text-red-400 flex-shrink-0" />
          <p className="text-xs text-red-400">Critical credentials missing: {criticalMissing.map(c => c.name).join(', ')}</p>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b border-white/[0.06] pb-0">
        {TABS.map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-xs font-medium rounded-t-lg transition-all border-b-2 -mb-px
              ${tab === t
                ? 'text-jarvis-blue border-jarvis-blue'
                : 'text-white/40 border-transparent hover:text-white/60'}`}
          >
            {t}
            {t === 'Credentials' && (criticalMissing.length + highMissing.length) > 0 && (
              <span className="ml-1.5 bg-amber-500 text-black text-[9px] font-bold w-4 h-4 rounded-full inline-flex items-center justify-center">
                {criticalMissing.length + highMissing.length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto no-scrollbar">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Activity size={20} className="text-jarvis-blue animate-pulse" />
          </div>
        ) : (
          <>
            {/* ── Overview ──────────────────────────────────────────────── */}
            {tab === 'Overview' && (
              <div className="space-y-4">
                <div className="glass border border-white/[0.07] rounded-xl p-4">
                  <p className="text-xs font-semibold text-white/60 mb-3 uppercase tracking-wider">Provider Status</p>
                  <div className="grid grid-cols-3 gap-2">
                    {Object.entries(health?.providers || {}).map(([name, info]) => (
                      <div key={name} className="flex items-center gap-2 py-1.5 px-3 rounded-lg bg-white/[0.03] border border-white/[0.05]">
                        <div className={`w-1.5 h-1.5 rounded-full ${info.available ? 'bg-emerald-400' : 'bg-white/20'}`} />
                        <span className="text-xs text-white/70 capitalize">{name}</span>
                        {info.available && <Zap size={10} className="text-jarvis-blue ml-auto" />}
                      </div>
                    ))}
                  </div>
                </div>
                <CostChart summary={costSummary} />
              </div>
            )}

            {/* ── Circuit Breakers ──────────────────────────────────────── */}
            {tab === 'Circuit Breakers' && (
              <div className="grid grid-cols-2 gap-3">
                {circuits.length === 0 ? (
                  <p className="text-xs text-white/30 col-span-2 text-center py-8">No circuit breaker data yet — run some AI requests first</p>
                ) : (
                  circuits.map(cb => (
                    <CircuitBreakerCard key={cb.provider} cb={cb} onReset={handleResetCircuit} />
                  ))
                )}
              </div>
            )}

            {/* ── Costs ─────────────────────────────────────────────────── */}
            {tab === 'Costs' && (
              <div className="space-y-4">
                <CostChart summary={costSummary} />
                {costToday?.by_provider && Object.keys(costToday.by_provider).length > 0 ? (
                  <div className="glass border border-white/[0.07] rounded-xl p-4">
                    <p className="text-xs font-semibold text-white/60 mb-3 uppercase tracking-wider">Today by Provider</p>
                    {Object.entries(costToday.by_provider).map(([provider, data]) => (
                      <div key={provider} className="flex items-center gap-3 py-2 border-b border-white/[0.04] last:border-0">
                        <span className="text-xs text-white/70 capitalize w-24">{provider}</span>
                        <div className="flex-1">
                          <div className="h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
                            <div className="h-full bg-jarvis-blue/50 rounded-full" style={{ width: `${Math.min((data.cost_usd / (costToday.total_cost_usd || 1)) * 100, 100)}%` }} />
                          </div>
                        </div>
                        <span className="text-xs text-jarvis-blue w-20 text-right">${data.cost_usd.toFixed(4)}</span>
                        <span className="text-[10px] text-white/30 w-16 text-right">{data.requests} req</span>
                        <span className="text-[10px] text-white/30 w-16 text-right">{data.avg_latency_ms}ms avg</span>
                      </div>
                    ))}
                    <div className="flex justify-between pt-3 text-xs border-t border-white/[0.06]">
                      <span className="text-white/40">Total today</span>
                      <span className="text-white font-bold">${costToday.total_cost_usd?.toFixed(4)}</span>
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-white/30 text-center py-6">No cost data for today — make some AI requests</p>
                )}
              </div>
            )}

            {/* ── Credentials ───────────────────────────────────────────── */}
            {tab === 'Credentials' && credentials && (
              <div className="space-y-3">
                <div className="glass border border-white/[0.07] rounded-xl p-4">
                  <div className="flex items-center justify-between mb-3">
                    <p className="text-xs font-semibold text-white/60 uppercase tracking-wider">Security Audit</p>
                    <div className="flex items-center gap-3 text-[10px]">
                      <span className="text-emerald-400">{credentials.configured} configured</span>
                      <span className="text-white/30">·</span>
                      <span className="text-amber-400">{credentials.missing} missing</span>
                      {credentials.critical_missing > 0 && <>
                        <span className="text-white/30">·</span>
                        <span className="text-red-400">{credentials.critical_missing} critical</span>
                      </>}
                    </div>
                  </div>
                  {credChecks.map(check => <CredentialRow key={check.name} check={check} />)}
                </div>
              </div>
            )}

            {/* ── Audit Log ─────────────────────────────────────────────── */}
            {tab === 'Audit Log' && (
              <div className="glass border border-white/[0.07] rounded-xl p-4">
                <div className="flex items-center justify-between mb-3">
                  <p className="text-xs font-semibold text-white/60 uppercase tracking-wider">Request Audit Log</p>
                  <div className="flex gap-4 text-[10px] text-white/30">
                    <span>Provider</span><span>Model</span><span className="w-16 text-right">Type</span>
                    <span className="w-16 text-right">Latency</span><span className="w-20 text-right">Cost</span>
                  </div>
                </div>
                <AuditLog logs={auditLogs} />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
