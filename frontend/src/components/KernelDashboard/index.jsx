import React, { useCallback, useEffect, useState } from 'react'
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Cpu,
  Database,
  GitBranch,
  Globe,
  HardDrive,
  Heart,
  Layers,
  List,
  Loader2,
  Network,
  Package,
  RefreshCw,
  Server,
  Settings,
  ShieldAlert,
  Sliders,
  Zap,
} from 'lucide-react'
import { kernelDashboard, kernelConfigSet, kernelConfigDel } from '../../services/api'

// ── Status colours ────────────────────────────────────────────────────────────
const STATUS_COLOR = {
  HEALTHY:     'text-emerald-400',
  NOMINAL:     'text-emerald-400',
  ALIVE:       'text-emerald-400',
  DEGRADED:    'text-amber-400',
  CRITICAL:    'text-red-400',
  ALERTING:    'text-red-400',
  UNKNOWN:     'text-slate-400',
  UNAVAILABLE: 'text-slate-500',
  DRAINING:    'text-amber-500',
  DR_ACTIVE:   'text-purple-400',
  SWITCHING:   'text-yellow-300',
  OPEN:        'text-red-400',
  CLOSED:      'text-emerald-400',
  HALF_OPEN:   'text-amber-400',
}

const STATUS_DOT = {
  HEALTHY:     'bg-emerald-400',
  NOMINAL:     'bg-emerald-400',
  ALIVE:       'bg-emerald-400',
  DEGRADED:    'bg-amber-400',
  CRITICAL:    'bg-red-500 animate-pulse',
  ALERTING:    'bg-red-500 animate-pulse',
  UNKNOWN:     'bg-slate-500',
  UNAVAILABLE: 'bg-slate-600',
  DRAINING:    'bg-amber-500',
  DR_ACTIVE:   'bg-purple-400',
}

function StatusDot({ status }) {
  const cls = STATUS_DOT[status] || 'bg-slate-500'
  return <span className={`inline-block w-2 h-2 rounded-full ${cls}`} />
}

function StatusLabel({ status }) {
  const cls = STATUS_COLOR[status] || 'text-slate-400'
  return <span className={`font-semibold text-xs uppercase tracking-wider ${cls}`}>{status}</span>
}

// ── Card shell ────────────────────────────────────────────────────────────────
function Card({ icon: Icon, title, children, className = '' }) {
  return (
    <div className={`bg-slate-800/60 border border-slate-700/50 rounded-xl p-4 ${className}`}>
      <div className="flex items-center gap-2 mb-3">
        {Icon && <Icon size={15} className="text-cyan-400 shrink-0" />}
        <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-widest">{title}</h3>
      </div>
      {children}
    </div>
  )
}

// ── Priority label ─────────────────────────────────────────────────────────────
const PRI_LABEL = { 1: 'CRITICAL', 2: 'HIGH', 3: 'NORMAL', 4: 'LOW' }
const PRI_COLOR = {
  1: 'text-red-400', 2: 'text-amber-400', 3: 'text-cyan-400', 4: 'text-slate-400',
}

// ── System State card ─────────────────────────────────────────────────────────
function StateCard({ data }) {
  if (!data || data.error) return (
    <Card icon={Cpu} title="System State">
      <p className="text-slate-500 text-xs">{data?.error || 'No state record'}</p>
    </Card>
  )
  return (
    <Card icon={Cpu} title="System State">
      <div className="space-y-1.5 text-xs">
        <Row label="Stage"   value={<span className="font-mono text-cyan-300">{data.stage}</span>} />
        <Row label="Status"  value={<StatusLabel status={data.status?.toUpperCase()} />} />
        <Row label="Version" value={<span className="text-slate-300">v{data.version}</span>} />
        {data.updated_at && (
          <Row label="Updated" value={<span className="text-slate-400">{fmtTime(data.updated_at)}</span>} />
        )}
      </div>
    </Card>
  )
}

// ── Health card ───────────────────────────────────────────────────────────────
function HealthCard({ data }) {
  if (!data || data.error) return <Card icon={Heart} title="Health"><p className="text-slate-500 text-xs">{data?.error || 'unavailable'}</p></Card>
  const engines = data.engines || {}
  return (
    <Card icon={Heart} title="System Health">
      <div className="flex items-center gap-2 mb-3">
        <StatusDot status={data.overall} />
        <StatusLabel status={data.overall} />
        <span className="text-slate-500 text-xs ml-auto">{Object.keys(engines).length} engines</span>
      </div>
      <div className="space-y-1">
        {Object.entries(engines).map(([name, info]) => (
          <div key={name} className="flex items-center justify-between text-xs py-0.5">
            <div className="flex items-center gap-1.5">
              <StatusDot status={info.status} />
              <span className="text-slate-300 font-mono">{name}</span>
            </div>
            <StatusLabel status={info.status} />
          </div>
        ))}
      </div>
    </Card>
  )
}

// ── Task depth card ───────────────────────────────────────────────────────────
function TaskDepthCard({ data }) {
  if (!data || data.error) return <Card icon={List} title="Task Queue"><p className="text-slate-500 text-xs">{data?.error || 'unavailable'}</p></Card>
  const total = Object.values(data).reduce((s, n) => s + (typeof n === 'number' ? n : 0), 0)
  return (
    <Card icon={List} title="Task Queue">
      <div className="text-2xl font-bold text-white mb-2">{total} <span className="text-xs text-slate-400 font-normal">pending</span></div>
      <div className="space-y-1">
        {[1, 2, 3, 4].map(p => (
          <div key={p} className="flex items-center justify-between text-xs">
            <span className={`font-medium ${PRI_COLOR[p]}`}>{PRI_LABEL[p]}</span>
            <span className="text-slate-300 font-mono tabular-nums">{data[`priority_${p}`] ?? data[p] ?? 0}</span>
          </div>
        ))}
      </div>
    </Card>
  )
}

// ── Failover card ─────────────────────────────────────────────────────────────
function FailoverCard({ data }) {
  if (!data || data.error) return <Card icon={Globe} title="Failover"><p className="text-slate-500 text-xs">{data?.error || 'unavailable'}</p></Card>
  const critSec = data.critical_since_s
  return (
    <Card icon={Globe} title="Failover Controller">
      <div className="flex items-center gap-2 mb-2">
        <StatusDot status={data.state} />
        <StatusLabel status={data.state} />
      </div>
      {critSec != null && (
        <p className="text-xs text-red-300">CRITICAL for <strong>{critSec.toFixed(0)}s</strong></p>
      )}
      {data.alert_sent && (
        <p className="text-xs text-amber-400 mt-1">⚠ Captain has been notified</p>
      )}
      {data.last_event?.triggered_at && (
        <p className="text-xs text-slate-500 mt-1">Last event: {fmtTime(data.last_event.triggered_at)}</p>
      )}
    </Card>
  )
}

// ── Service Discovery card ────────────────────────────────────────────────────
function DiscoveryCard({ data }) {
  if (!data || data.error) return <Card icon={Network} title="Service Discovery"><p className="text-slate-500 text-xs">{data?.error || 'unavailable'}</p></Card>
  const entries = Object.entries(data)
  return (
    <Card icon={Network} title="Service Discovery">
      <p className="text-xs text-slate-400 mb-2">{entries.length} registered</p>
      <div className="space-y-1 max-h-48 overflow-y-auto pr-1">
        {entries.map(([name, info]) => (
          <div key={name} className="flex items-center justify-between text-xs py-0.5">
            <div className="flex items-center gap-1.5">
              <StatusDot status={info.status} />
              <span className="text-slate-300 font-mono">{name}</span>
              <span className="text-slate-600">v{info.version}</span>
            </div>
            <span className="text-slate-500">{info.last_heartbeat_ago_s}s ago</span>
          </div>
        ))}
        {entries.length === 0 && <p className="text-slate-600 text-xs">No services registered</p>}
      </div>
    </Card>
  )
}

// ── Plugin Loader card ────────────────────────────────────────────────────────
function PluginsCard({ data }) {
  if (!data || data.error) return <Card icon={Package} title="Plugins"><p className="text-slate-500 text-xs">{data?.error || 'unavailable'}</p></Card>
  const entries = Object.entries(data)
  return (
    <Card icon={Package} title="Plugin Loader">
      <p className="text-xs text-slate-400 mb-2">{entries.length} registered</p>
      <div className="space-y-1">
        {entries.map(([name, info]) => (
          <div key={name} className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-1.5">
              <span className={info.loaded ? 'text-emerald-400' : 'text-slate-500'}>●</span>
              <span className="text-slate-300 font-mono">{name}</span>
            </div>
            <span className="text-slate-500">{info.version}</span>
          </div>
        ))}
        {entries.length === 0 && <p className="text-slate-600 text-xs">No plugins loaded</p>}
      </div>
    </Card>
  )
}

// ── Config card ───────────────────────────────────────────────────────────────
function ConfigCard({ data, onRefresh }) {
  const [expanded, setExpanded] = useState(false)
  const [editing, setEditing] = useState(null)
  const [editVal, setEditVal] = useState('')
  const [saving, setSaving] = useState(false)

  if (!data || data.error) return <Card icon={Sliders} title="Runtime Config"><p className="text-slate-500 text-xs">{data?.error || 'unavailable'}</p></Card>

  const entries = Object.entries(data)
  const visible = expanded ? entries : entries.slice(0, 8)

  const handleSave = async (key) => {
    setSaving(true)
    try {
      let parsed
      try { parsed = JSON.parse(editVal) } catch { parsed = editVal }
      await kernelConfigSet(key, parsed)
      setEditing(null)
      onRefresh()
    } catch (err) {
      alert(`Save failed: ${err?.response?.data?.detail || err.message}`)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card icon={Sliders} title="Runtime Config" className="col-span-2">
      <div className="space-y-1 text-xs font-mono max-h-64 overflow-y-auto pr-1">
        {visible.map(([key, val]) => (
          <div key={key} className="flex items-start justify-between gap-2 py-0.5 group">
            {editing === key ? (
              <>
                <span className="text-slate-300 shrink-0">{key}</span>
                <div className="flex items-center gap-1 ml-auto">
                  <input
                    className="bg-slate-700 border border-cyan-500/50 rounded px-1 py-0.5 text-xs text-white w-32"
                    value={editVal}
                    onChange={e => setEditVal(e.target.value)}
                    onKeyDown={e => { if (e.key === 'Enter') handleSave(key); if (e.key === 'Escape') setEditing(null) }}
                    autoFocus
                  />
                  <button onClick={() => handleSave(key)} disabled={saving} className="text-emerald-400 hover:text-emerald-300 disabled:opacity-50">✓</button>
                  <button onClick={() => setEditing(null)} className="text-slate-500 hover:text-slate-300">✕</button>
                </div>
              </>
            ) : (
              <>
                <span className="text-slate-400 shrink-0">{key}</span>
                <div className="flex items-center gap-2 ml-auto">
                  <span className="text-cyan-300">{JSON.stringify(val)}</span>
                  <button
                    onClick={() => { setEditing(key); setEditVal(JSON.stringify(val)) }}
                    className="text-slate-600 hover:text-cyan-400 opacity-0 group-hover:opacity-100 transition-opacity"
                  >✎</button>
                </div>
              </>
            )}
          </div>
        ))}
      </div>
      {entries.length > 8 && (
        <button onClick={() => setExpanded(!expanded)} className="mt-2 text-xs text-slate-500 hover:text-slate-300 flex items-center gap-1">
          {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
          {expanded ? 'Show less' : `Show ${entries.length - 8} more`}
        </button>
      )}
    </Card>
  )
}

// ── Audit log card ────────────────────────────────────────────────────────────
function AuditCard({ data }) {
  if (!data || data.error || !Array.isArray(data)) return <Card icon={Database} title="Audit Log"><p className="text-slate-500 text-xs">{data?.error || 'unavailable'}</p></Card>
  return (
    <Card icon={Database} title="Recent Audit Entries" className="col-span-2">
      <div className="space-y-1 text-xs max-h-48 overflow-y-auto pr-1">
        {data.slice(0, 10).map((e) => (
          <div key={e.id} className="flex items-center justify-between py-0.5 border-b border-slate-700/30">
            <div className="flex items-center gap-2">
              <span className={`font-medium ${e.outcome === 'PERMITTED' || e.outcome === 'SUCCESS' ? 'text-emerald-400' : e.outcome === 'DENIED' ? 'text-red-400' : 'text-slate-400'}`}>
                {e.outcome}
              </span>
              <span className="text-slate-300">{e.action_type}</span>
              <span className="text-slate-500">{e.actor}</span>
            </div>
            <span className="text-slate-600 shrink-0">{fmtTime(e.created_at)}</span>
          </div>
        ))}
        {data.length === 0 && <p className="text-slate-600">No audit entries</p>}
      </div>
    </Card>
  )
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function Row({ label, value }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-slate-500">{label}</span>
      <span>{value}</span>
    </div>
  )
}

function fmtTime(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch { return iso }
}

// ── Main component ────────────────────────────────────────────────────────────
export default function KernelDashboard() {
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)
  const [lastRefresh, setLastRefresh] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await kernelDashboard()
      setData(result)
      setLastRefresh(new Date())
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || 'Failed to load kernel data')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
    const interval = setInterval(load, 30_000)
    return () => clearInterval(interval)
  }, [load])

  if (error && !data) return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center">
      <div className="text-center space-y-3">
        <ShieldAlert size={40} className="text-red-400 mx-auto" />
        <p className="text-red-300 text-sm">{error}</p>
        <button onClick={load} className="text-xs text-slate-400 hover:text-white border border-slate-700 rounded px-3 py-1.5">Retry</button>
      </div>
    </div>
  )

  return (
    <div className="min-h-screen bg-slate-900 p-6 space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Layers size={22} className="text-cyan-400" />
          <div>
            <h1 className="text-lg font-bold text-white">Kernel Ops Dashboard</h1>
            <p className="text-xs text-slate-500">L3 Runtime Kernel — real-time system state</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {lastRefresh && (
            <span className="text-xs text-slate-600">
              Refreshed {lastRefresh.toLocaleTimeString()}
            </span>
          )}
          <button
            onClick={load}
            disabled={loading}
            className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white border border-slate-700 rounded-lg px-3 py-1.5 transition-colors disabled:opacity-50"
          >
            <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {/* Overall health banner */}
      {data?.health && !data.health.error && (
        <div className={`rounded-xl border px-4 py-2.5 flex items-center gap-3 ${
          data.health.overall === 'HEALTHY' ? 'border-emerald-500/30 bg-emerald-900/10' :
          data.health.overall === 'DEGRADED' ? 'border-amber-500/30 bg-amber-900/10' :
          data.health.overall === 'CRITICAL' ? 'border-red-500/30 bg-red-900/10 animate-pulse' :
          'border-slate-700/40 bg-slate-800/30'
        }`}>
          <StatusDot status={data.health.overall} />
          <span className="text-sm font-semibold text-white">System {data.health.overall}</span>
          {data.failover && !data.failover.error && data.failover.state !== 'NOMINAL' && (
            <span className="ml-auto text-xs text-amber-400">Failover: {data.failover.state}</span>
          )}
        </div>
      )}

      {loading && !data && (
        <div className="flex items-center justify-center py-20">
          <Loader2 size={28} className="animate-spin text-cyan-400" />
        </div>
      )}

      {data && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <StateCard     data={data.state} />
          <HealthCard    data={data.health} />
          <TaskDepthCard data={data.task_depth} />
          <FailoverCard  data={data.failover} />
          <DiscoveryCard data={data.discovery} />
          <PluginsCard   data={data.plugins} />
          <ConfigCard    data={data.config} onRefresh={load} />
          <AuditCard     data={data.audit} />
        </div>
      )}
    </div>
  )
}
