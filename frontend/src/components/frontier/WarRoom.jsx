import React, { useCallback, useEffect, useMemo, useState } from 'react'
import api from '../../services/api'
import {
  ActionCard,
  DEFAULT_TENANT,
  FrontierShell,
  Input,
  ResultBox,
  RunButton,
} from './FrontierShell'

const SEV_CFG = {
  critical: 'border-red-500/40 bg-red-500/10 text-red-300',
  high:     'border-orange-500/40 bg-orange-500/10 text-orange-300',
  medium:   'border-amber-500/40 bg-amber-500/10 text-amber-300',
  low:      'border-gray-600 bg-gray-600/10 text-gray-400',
}

function ThreatCard({ threat, onResolve }) {
  const cls = SEV_CFG[threat.severity] || SEV_CFG.low
  return (
    <div className={`rounded-xl border p-3 space-y-1 ${cls}`}>
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm font-semibold">{threat.title || threat.threat_type || 'Threat'}</p>
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-bold uppercase opacity-70">{threat.severity}</span>
          {threat.id && (
            <button
              type="button"
              onClick={() => onResolve && onResolve(threat.id)}
              className="rounded border border-white/20 bg-white/10 px-2 py-0.5 text-[10px] font-bold hover:bg-white/20 transition-colors"
            >
              Resolve
            </button>
          )}
        </div>
      </div>
      {threat.description && <p className="text-xs opacity-70 leading-5">{threat.description}</p>}
      {threat.recommended_action && <p className="text-xs opacity-60">→ {threat.recommended_action}</p>}
    </div>
  )
}

export default function WarRoom() {
  const [competitor, setCompetitor] = useState('Cognitiv+')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [threats, setThreats] = useState([])
  const [threatsLoading, setThreatsLoading] = useState(false)
  const [scanning, setScanning] = useState(false)

  const endpoints = useMemo(() => [
    { key: 'health', label: 'Emergency health', path: '/api/v1/emergency/health' },
    { key: 'incidents', label: 'Open incidents', path: '/api/v1/emergency/incidents' },
    { key: 'threats', label: 'Captain threats', path: '/api/v1/captain/threats', params: { tenant_id: DEFAULT_TENANT } },
    { key: 'activeThreats', label: 'Active threat alerts', path: '/api/v1/frontier/threats/active', params: { tenant_id: DEFAULT_TENANT } },
    { key: 'threatHistory', label: 'Threat history', path: '/api/v1/frontier/threats/history', params: { tenant_id: DEFAULT_TENANT, limit: 20 } },
    { key: 'warBrief', label: 'War-room brief', path: '/api/v1/captain/war-room-brief', params: { tenant_id: DEFAULT_TENANT } },
    { key: 'conscience', label: 'Conscience audit', path: '/api/v1/intelligence/conscience/audit', params: { tenant_id: DEFAULT_TENANT, days: 7 } },
    { key: 'approvals', label: 'Pending approvals', path: '/api/v1/approvals', params: { status: 'pending' } },
  ], [])

  const loadThreats = useCallback(async () => {
    setThreatsLoading(true)
    try {
      const r = await api.get('/api/v1/frontier/threats/active', { params: { tenant_id: DEFAULT_TENANT } })
      setThreats(r.data?.threats || r.data || [])
    } catch {}
    setThreatsLoading(false)
  }, [])

  useEffect(() => { loadThreats() }, [loadThreats])

  async function resolveThreat(threatId) {
    const resolution = window.prompt('Resolution note:')
    if (resolution === null) return
    try {
      await api.post(`/api/v1/frontier/threats/${threatId}/resolve`, {
        tenant_id: DEFAULT_TENANT,
        resolution_notes: resolution,
      })
      await loadThreats()
    } catch (err) {
      setResult({ error: err.response?.data?.detail || err.message })
    }
  }

  async function scanThreats(event) {
    event.preventDefault()
    setScanning(true)
    try {
      const r = await api.post('/api/v1/frontier/threats/scan', { tenant_id: DEFAULT_TENANT })
      setResult(r.data)
      await loadThreats()
    } catch (error) {
      setResult({ error: error.response?.data?.detail || error.message })
    }
    setScanning(false)
  }

  async function runRedTeam(event) {
    event.preventDefault()
    setLoading(true)
    try {
      const response = competitor.trim()
        ? await api.post('/api/v1/intelligence/red-team/competitor', null, {
            params: { tenant_id: DEFAULT_TENANT, competitor_name: competitor },
          })
        : await api.post('/api/v1/intelligence/red-team/run', { tenant_id: DEFAULT_TENANT })
      setResult(response.data)
    } catch (error) {
      setResult({ error: error.response?.data?.detail || error.message })
    }
    setLoading(false)
  }

  return (
    <FrontierShell
      eyebrow="Protection"
      title="War Room"
      description="Active threat alerts, incidents, ethics checks, risk reviews, and red-team analysis for high-stakes decisions."
      endpoints={endpoints}
    >
      {() => (
        <div className="space-y-4">
          {/* Active Threats Panel */}
          <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-4">
            <div className="flex items-center justify-between mb-3">
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-red-300/70">
                Active Threat Alerts {threats.length > 0 && `(${threats.length})`}
              </p>
              <button
                type="button"
                onClick={scanThreats}
                disabled={scanning}
                className="inline-flex items-center gap-1 rounded border border-red-400/30 bg-red-400/10 px-2.5 py-1 text-[11px] font-bold text-red-300 hover:bg-red-400/20 disabled:opacity-40 transition-colors"
              >
                {scanning ? '…Scanning' : '⚡ Scan Now'}
              </button>
            </div>
            {threatsLoading ? (
              <p className="text-xs text-white/40 text-center py-4">Loading threats…</p>
            ) : threats.length === 0 ? (
              <p className="text-xs text-white/30 text-center py-4">No active threats detected. Click Scan Now to check.</p>
            ) : (
              <div className="space-y-2">
                {threats.map((t, i) => <ThreatCard key={i} threat={t} onResolve={resolveThreat} />)}
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            <ActionCard title="Run Red Team" subtitle="Analyze how a competitor or market force can attack our position.">
              <form onSubmit={runRedTeam} className="space-y-3">
                <Input value={competitor} onChange={setCompetitor} placeholder="Competitor name" />
                <RunButton loading={loading}>Analyze</RunButton>
              </form>
            </ActionCard>
            <ActionCard title="Latest result" subtitle="Output from threat scan or red-team analysis.">
              <ResultBox result={result} />
            </ActionCard>
          </div>
        </div>
      )}
    </FrontierShell>
  )
}
