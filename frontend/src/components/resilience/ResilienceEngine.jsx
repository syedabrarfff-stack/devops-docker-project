import { useState, useEffect } from 'react'

const SEVERITY_COLORS = { critical: 'bg-rose-500/20 text-rose-400 border-rose-500/30', high: 'bg-amber-500/20 text-amber-400 border-amber-500/30', medium: 'bg-blue-500/20 text-blue-400 border-blue-500/30', low: 'bg-gray-500/20 text-gray-400 border-gray-500/30' }
const INCIDENT_TYPES = ['aws_outage','db_outage','ai_provider_outage','ses_outage','stripe_outage','redis_outage','dns_outage','security_incident','client_churn','captain_unavailable']

export default function ResilienceEngine() {
  const [status, setStatus] = useState(null)
  const [active, setActive] = useState([])
  const [playbooks, setPlaybooks] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [expanded, setExpanded] = useState(null)
  const [incidentType, setIncidentType] = useState('aws_outage')
  const [submitting, setSubmitting] = useState(false)
  const [msg, setMsg] = useState(null)

  const load = async () => {
    setLoading(true)
    try {
      const [s, a, p] = await Promise.all([
        fetch('/api/v1/resilience/status', { credentials: 'include' }).then(r => r.json()),
        fetch('/api/v1/resilience/active', { credentials: 'include' }).then(r => r.json()),
        fetch('/api/v1/resilience/playbooks', { credentials: 'include' }).then(r => r.json()),
      ])
      setStatus(s); setActive(Array.isArray(a) ? a : []); setPlaybooks(p || {})
    } catch (e) { setError(e.message) }
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const triggerIncident = async () => {
    setSubmitting(true)
    try {
      const res = await fetch('/api/v1/resilience/incident', {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ incident_type: incidentType, details: {} }),
      })
      const data = await res.json()
      setMsg(`Incident triggered: ${data.playbook} (${data.severity})`)
      load()
    } catch (e) { setMsg(`Error: ${e.message}`) }
    setSubmitting(false)
  }

  if (loading) return <div className="text-gray-400 p-8">Loading Resilience Engine...</div>
  if (error) return <div className="text-rose-400 p-8">Error: {error}</div>

  const systemHealthColor = (status?.active_incident_count || 0) === 0 ? 'text-emerald-400' : 'text-rose-400'

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Resilience Engine</h1>
        <p className="text-gray-400 text-sm mt-1">Operational Continuity — Playbook-Driven Recovery System</p>
      </div>

      {msg && <div className="bg-blue-500/20 border border-blue-500/30 rounded-lg p-3 text-blue-300 text-sm">{msg}</div>}

      {/* Status Bar */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white/5 border border-white/10 rounded-xl p-4 text-center">
          <p className="text-gray-400 text-xs mb-1">Active Incidents</p>
          <p className={`text-3xl font-bold ${systemHealthColor}`}>{status?.active_incident_count ?? 0}</p>
        </div>
        <div className="bg-white/5 border border-white/10 rounded-xl p-4 text-center">
          <p className="text-gray-400 text-xs mb-1">System Health</p>
          <p className={`text-lg font-bold ${systemHealthColor}`}>{status?.system_health?.toUpperCase() ?? 'NOMINAL'}</p>
        </div>
        <div className="bg-white/5 border border-white/10 rounded-xl p-4 text-center">
          <p className="text-gray-400 text-xs mb-1">Playbooks Available</p>
          <p className="text-3xl font-bold text-blue-400">{status?.playbook_count ?? Object.keys(playbooks).length}</p>
        </div>
      </div>

      {/* Active Incidents */}
      {active.length > 0 && (
        <div>
          <h2 className="text-white font-semibold mb-3">Active Incidents</h2>
          {active.map(inc => (
            <div key={inc.event_id} className={`border rounded-xl p-4 mb-2 ${SEVERITY_COLORS[inc.severity] || SEVERITY_COLORS.medium}`}>
              <div className="flex justify-between items-start">
                <div>
                  <p className="font-medium">{inc.incident_type?.replace(/_/g, ' ').toUpperCase()}</p>
                  <p className="text-xs opacity-70 mt-0.5">Status: {inc.status} | ETA: {inc.estimated_recovery_minutes}min | Notified: {inc.captain_notified ? 'Yes' : 'No'}</p>
                </div>
                <span className="text-xs px-2 py-1 rounded-full bg-black/20">{inc.severity}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Playbook Grid */}
      <div>
        <h2 className="text-white font-semibold mb-3">Incident Playbooks</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {Object.entries(playbooks).map(([key, pb]) => (
            <div key={key} className="bg-white/5 border border-white/10 rounded-xl p-4">
              <div className="flex items-start justify-between mb-2">
                <p className="text-white text-sm font-medium">{pb.name}</p>
                <span className={`text-xs px-2 py-0.5 rounded-full border ${SEVERITY_COLORS[pb.severity] || SEVERITY_COLORS.medium}`}>{pb.severity}</span>
              </div>
              <p className="text-gray-400 text-xs mb-2">RTO: {pb.estimated_rto_minutes}min | RPO: {pb.estimated_rpo_minutes}min</p>
              {expanded === key ? (
                <div>
                  <p className="text-gray-300 text-xs mb-1 font-medium">Immediate Actions:</p>
                  {pb.immediate_actions?.map((a, i) => <p key={i} className="text-gray-400 text-xs">• {a}</p>)}
                  <button onClick={() => setExpanded(null)} className="text-blue-400 text-xs mt-2">Hide</button>
                </div>
              ) : (
                <div>
                  {pb.immediate_actions?.slice(0, 1).map((a, i) => <p key={i} className="text-gray-500 text-xs">• {a}</p>)}
                  <button onClick={() => setExpanded(key)} className="text-blue-400 text-xs mt-2">View Playbook</button>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Trigger Incident (Testing) */}
      <div className="bg-white/5 border border-white/10 rounded-xl p-4">
        <h3 className="text-white text-sm font-semibold mb-3">Test Incident Response</h3>
        <div className="flex gap-3">
          <select className="flex-1 bg-white/10 border border-white/20 rounded-lg p-2 text-white text-sm" value={incidentType} onChange={e => setIncidentType(e.target.value)}>
            {INCIDENT_TYPES.map(t => <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>)}
          </select>
          <button onClick={triggerIncident} disabled={submitting} className="bg-rose-600 hover:bg-rose-700 text-white text-sm px-4 py-2 rounded-lg disabled:opacity-50">{submitting ? '...' : 'Trigger'}</button>
          <button onClick={load} className="bg-white/10 hover:bg-white/20 text-white text-sm px-4 py-2 rounded-lg">Refresh</button>
        </div>
      </div>
    </div>
  )
}
