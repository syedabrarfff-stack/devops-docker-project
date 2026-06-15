import React, { useCallback, useEffect, useState } from 'react'
import { Activity, CheckCircle2, ChevronDown, ChevronRight, Loader2, RefreshCw, Radio, Radar, Sparkles, TrendingUp, X, Zap } from 'lucide-react'
import api from '../../services/api'

const REC_STATUS_CFG = {
  pending:     { cls: 'border-jarvis-gold/30 bg-jarvis-gold/10 text-jarvis-gold',    label: 'Pending' },
  approved:    { cls: 'border-blue-500/30 bg-blue-500/10 text-blue-300',             label: 'Approved' },
  implemented: { cls: 'border-green-500/30 bg-green-500/10 text-green-300',          label: 'Implemented' },
  dismissed:   { cls: 'border-gray-600/30 bg-gray-600/10 text-gray-500',             label: 'Dismissed' },
}

const RADAR_RING = {
  adopt:   { cls: 'border-green-500/30 bg-green-500/10 text-green-300',   label: 'Adopt' },
  trial:   { cls: 'border-blue-500/30 bg-blue-500/10 text-blue-300',      label: 'Trial' },
  assess:  { cls: 'border-jarvis-gold/30 bg-jarvis-gold/10 text-jarvis-gold', label: 'Assess' },
  hold:    { cls: 'border-red-500/30 bg-red-500/10 text-red-300',         label: 'Hold' },
}

function StatusBadge({ status, cfg }) {
  const c = cfg[status?.toLowerCase()] || cfg.pending || { cls: 'border-gray-500/30 bg-gray-500/10 text-gray-300', label: status }
  return <span className={`inline-flex rounded-full border px-2.5 py-0.5 text-[11px] font-semibold tracking-wide ${c.cls}`}>{c.label}</span>
}

function ExpandCard({ title, badge, children }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="rounded-xl border border-white/10 bg-white/5">
      <button type="button" onClick={() => setOpen(v => !v)} className="flex w-full items-center gap-3 p-4 text-left">
        {open ? <ChevronDown size={13} className="shrink-0 text-gray-400" /> : <ChevronRight size={13} className="shrink-0 text-gray-400" />}
        <span className="flex-1 text-sm font-medium text-white truncate min-w-0">{title}</span>
        {badge}
      </button>
      {open && <div className="border-t border-white/10 px-4 pb-4 pt-3">{children}</div>}
    </div>
  )
}

export default function IntelView() {
  const [tab, setTab] = useState('pulse')
  const [pulse, setPulse] = useState(null)
  const [radar, setRadar] = useState(null)
  const [recs, setRecs] = useState([])
  const [recStatus, setRecStatus] = useState('')
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState({})
  const [scanQueued, setScanQueued] = useState(false)
  const [analyzeQueued, setAnalyzeQueued] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    const [pulseRes, radarRes, recsRes] = await Promise.allSettled([
      api.get('/api/v1/intelligence/pulse'),
      api.get('/api/v1/intelligence/radar'),
      api.get('/api/v1/intelligence/recommendations'),
    ])
    if (pulseRes.status === 'fulfilled') setPulse(pulseRes.value.data)
    if (radarRes.status === 'fulfilled') setRadar(radarRes.value.data)
    if (recsRes.status === 'fulfilled') setRecs(recsRes.value.data?.recommendations || [])
    setLoading(false)
  }, [])

  useEffect(() => { load() }, [load])

  const loadRecs = async () => {
    const params = recStatus ? { status: recStatus } : {}
    const r = await api.get('/api/v1/intelligence/recommendations', { params }).catch(() => null)
    if (r) setRecs(r.data?.recommendations || [])
  }

  useEffect(() => { if (tab === 'recommendations') loadRecs() }, [tab, recStatus])

  const recAction = async (id, action) => {
    setActionLoading(p => ({ ...p, [id]: action }))
    try {
      await api.post(`/api/v1/intelligence/recommendations/${id}/${action}`)
      await loadRecs()
    } catch {}
    setActionLoading(p => { const n = { ...p }; delete n[id]; return n })
  }

  const triggerScan = async () => {
    setScanQueued(true)
    await api.post('/api/v1/intelligence/radar/scan').catch(() => {})
    setTimeout(() => setScanQueued(false), 4000)
  }

  const triggerAnalyze = async () => {
    setAnalyzeQueued(true)
    await api.post('/api/v1/intelligence/recommendations/analyze').catch(() => {})
    setTimeout(() => { setAnalyzeQueued(false); loadRecs() }, 5000)
  }

  const intel = pulse?.intelligence || {}
  const providers = pulse?.ai_providers || {}
  const availableProviders = pulse?.available_providers || []

  const TABS = [
    { id: 'pulse', label: 'System Pulse', icon: Activity },
    { id: 'radar', label: 'Tech Radar', icon: Radar },
    { id: 'recommendations', label: 'Recommendations', icon: TrendingUp, count: intel.pending_recommendations },
  ]

  return (
    <div className="min-h-[calc(100vh-3.5rem)] p-6 pb-10 space-y-6">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.22em] text-jarvis-cyan/70">Market Awareness</p>
          <h1 className="mt-2 text-3xl font-bold text-white">Market Intelligence</h1>
          <p className="mt-2 max-w-2xl text-sm text-gray-400">
            System pulse, technology radar, and optimization recommendations powering Aliyar Solutions' decisions.
          </p>
        </div>
        <button type="button" onClick={load} disabled={loading} className="btn-primary inline-flex items-center justify-center gap-2">
          {loading ? <Loader2 size={15} className="animate-spin" /> : <RefreshCw size={15} />}
          Refresh
        </button>
      </header>

      {/* Metric strip */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {[
          { label: 'Tech Radar Entries', value: intel.tech_radar_entries ?? '—', tone: 'text-jarvis-cyan' },
          { label: 'Recommendations', value: intel.optimization_recommendations ?? '—', tone: 'text-jarvis-gold' },
          { label: 'Pending Review', value: intel.pending_recommendations ?? '—', tone: intel.pending_recommendations > 0 ? 'text-orange-300' : 'text-green-300' },
          { label: 'Research Reports', value: intel.research_reports ?? '—', tone: 'text-purple-300' },
        ].map(m => (
          <div key={m.label} className="glass p-5">
            <p className="text-xs text-gray-400">{m.label}</p>
            <p className={`mt-2 text-2xl font-bold ${m.tone}`}>{m.value}</p>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-white/10">
        {TABS.map(t => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px ${
              tab === t.id ? 'border-jarvis-cyan text-jarvis-cyan' : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            <t.icon size={14} />
            {t.label}
            {t.count != null && t.count > 0 && (
              <span className="rounded-full bg-orange-400/20 text-orange-300 px-1.5 py-0.5 text-[10px] font-bold">{t.count}</span>
            )}
          </button>
        ))}
      </div>

      {/* Pulse Tab */}
      {tab === 'pulse' && (
        <div className="space-y-4">
          {/* AI Providers */}
          <section className="glass p-5">
            <h2 className="text-sm font-semibold text-white mb-4">AI Provider Status</h2>
            {loading ? (
              <div className="flex items-center justify-center py-6 text-gray-500"><Loader2 size={18} className="animate-spin mr-2" />Loading…</div>
            ) : (
              <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-4">
                {availableProviders.map(name => {
                  const p = providers[name] || {}
                  const ok = p.available !== false && !p.error
                  return (
                    <div key={name} className={`rounded-xl border p-3 ${ok ? 'border-green-500/20 bg-green-500/5' : 'border-red-500/20 bg-red-500/5'}`}>
                      <div className="flex items-center gap-2 mb-1">
                        <div className={`h-1.5 w-1.5 rounded-full ${ok ? 'bg-green-400' : 'bg-red-400'}`} />
                        <span className="text-xs font-semibold text-white capitalize">{name.replace(/_/g, ' ')}</span>
                      </div>
                      {p.model && <p className="text-[10px] text-gray-500 truncate">{p.model}</p>}
                      {p.error && <p className="text-[10px] text-red-400 truncate">{String(p.error).slice(0, 60)}</p>}
                    </div>
                  )
                })}
                {availableProviders.length === 0 && (
                  <p className="text-sm text-gray-500 col-span-full py-4 text-center">No provider data available.</p>
                )}
              </div>
            )}
          </section>

          {/* Scheduled jobs */}
          {pulse?.scheduled_jobs?.length > 0 && (
            <section className="glass p-5">
              <h2 className="text-sm font-semibold text-white mb-3">Scheduled Intelligence Jobs</h2>
              <div className="space-y-2">
                {pulse.scheduled_jobs.map((job, i) => (
                  <div key={i} className="flex items-center gap-3">
                    <div className="h-1.5 w-1.5 rounded-full bg-jarvis-cyan/60 shrink-0" />
                    <span className="text-xs text-gray-300 font-mono">{job}</span>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
      )}

      {/* Radar Tab */}
      {tab === 'radar' && (
        <section className="glass p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-white">Technology Radar</h2>
            <button
              type="button"
              onClick={triggerScan}
              disabled={scanQueued}
              className="inline-flex items-center gap-1.5 rounded border border-jarvis-cyan/40 bg-jarvis-cyan/10 px-3 py-1.5 text-xs font-medium text-jarvis-cyan hover:bg-jarvis-cyan/20 transition-colors disabled:opacity-50"
            >
              {scanQueued ? <Loader2 size={12} className="animate-spin" /> : <Radio size={12} />}
              {scanQueued ? 'Scanning…' : 'Trigger Scan'}
            </button>
          </div>
          {loading ? (
            <div className="flex items-center justify-center py-8 text-gray-500"><Loader2 size={18} className="animate-spin mr-2" />Loading…</div>
          ) : !radar || (radar.by_quadrant && Object.values(radar.by_quadrant).every(a => a.length === 0)) ? (
            <div className="flex flex-col items-center py-10 text-gray-500">
              <Radar size={32} className="mb-3 opacity-20" />
              <p className="text-sm">No radar entries yet — trigger a scan to populate.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {radar.by_quadrant && Object.entries(radar.by_quadrant).map(([quadrant, entries]) => (
                entries.length > 0 && (
                  <div key={quadrant}>
                    <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">{quadrant.replace(/_/g, ' ')}</p>
                    <div className="space-y-2">
                      {entries.map((entry, i) => (
                        <ExpandCard
                          key={i}
                          title={entry.name}
                          badge={
                            <div className="flex items-center gap-2 shrink-0">
                              <StatusBadge status={entry.ring} cfg={RADAR_RING} />
                              {entry.score != null && (
                                <span className="text-xs text-gray-400">{entry.score}%</span>
                              )}
                            </div>
                          }
                        >
                          <div className="space-y-2 text-xs text-gray-400">
                            {entry.summary && <p className="text-gray-300">{entry.summary}</p>}
                            {entry.use_cases?.length > 0 && (
                              <div>
                                <span className="text-jarvis-cyan font-medium">Use cases: </span>
                                {entry.use_cases.join(', ')}
                              </div>
                            )}
                            {entry.pros?.length > 0 && (
                              <div><span className="text-green-400 font-medium">Pros: </span>{entry.pros.join(', ')}</div>
                            )}
                            {entry.cons?.length > 0 && (
                              <div><span className="text-red-400 font-medium">Cons: </span>{entry.cons.join(', ')}</div>
                            )}
                          </div>
                        </ExpandCard>
                      ))}
                    </div>
                  </div>
                )
              ))}
            </div>
          )}
        </section>
      )}

      {/* Recommendations Tab */}
      {tab === 'recommendations' && (
        <section className="glass p-5 space-y-4">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <h2 className="text-sm font-semibold text-white">Optimization Recommendations</h2>
            <div className="flex items-center gap-2">
              <select
                value={recStatus}
                onChange={e => setRecStatus(e.target.value)}
                className="rounded-xl border border-white/10 bg-black/40 px-3 py-2 text-xs text-white outline-none focus:border-jarvis-cyan/60"
              >
                <option value="">All statuses</option>
                {Object.keys(REC_STATUS_CFG).map(s => <option key={s} value={s}>{s}</option>)}
              </select>
              <button
                type="button"
                onClick={triggerAnalyze}
                disabled={analyzeQueued}
                className="inline-flex items-center gap-1.5 rounded border border-jarvis-gold/40 bg-jarvis-gold/10 px-3 py-1.5 text-xs font-medium text-jarvis-gold hover:bg-jarvis-gold/20 transition-colors disabled:opacity-50"
              >
                {analyzeQueued ? <Loader2 size={12} className="animate-spin" /> : <Sparkles size={12} />}
                {analyzeQueued ? 'Analyzing…' : 'Run Analysis'}
              </button>
            </div>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-8 text-gray-500"><Loader2 size={18} className="animate-spin mr-2" />Loading…</div>
          ) : recs.length === 0 ? (
            <div className="flex flex-col items-center py-10 text-gray-500">
              <TrendingUp size={32} className="mb-3 opacity-20" />
              <p className="text-sm">No recommendations yet — run system analysis to generate.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {recs.map(rec => {
                const busy = actionLoading[rec.id]
                const isPending = rec.status === 'pending'
                const isApproved = rec.status === 'approved'
                return (
                  <ExpandCard
                    key={rec.id}
                    title={rec.title}
                    badge={
                      <div className="flex items-center gap-2 shrink-0">
                        <StatusBadge status={rec.status} cfg={REC_STATUS_CFG} />
                        {rec.impact_score != null && (
                          <span className="text-xs text-gray-400">Impact {rec.impact_score}/10</span>
                        )}
                      </div>
                    }
                  >
                    <div className="space-y-3">
                      {rec.description && <p className="text-xs text-gray-300">{rec.description}</p>}
                      {rec.category && <p className="text-[10px] text-gray-500 uppercase tracking-wider">{rec.category}</p>}
                      {(isPending || isApproved) && (
                        <div className="flex gap-2 flex-wrap">
                          {isPending && (
                            <button
                              type="button"
                              disabled={!!busy}
                              onClick={() => recAction(rec.id, 'approve')}
                              className="inline-flex items-center gap-1.5 rounded border border-green-500/40 bg-green-500/10 px-3 py-1 text-xs font-medium text-green-300 hover:bg-green-500/20 disabled:opacity-40 transition-colors"
                            >
                              {busy === 'approve' ? <Loader2 size={11} className="animate-spin" /> : <CheckCircle2 size={11} />}
                              Approve
                            </button>
                          )}
                          {isApproved && (
                            <button
                              type="button"
                              disabled={!!busy}
                              onClick={() => recAction(rec.id, 'implement')}
                              className="inline-flex items-center gap-1.5 rounded border border-jarvis-cyan/40 bg-jarvis-cyan/10 px-3 py-1 text-xs font-medium text-jarvis-cyan hover:bg-jarvis-cyan/20 disabled:opacity-40 transition-colors"
                            >
                              {busy === 'implement' ? <Loader2 size={11} className="animate-spin" /> : <Zap size={11} />}
                              Implement
                            </button>
                          )}
                          {isPending && (
                            <button
                              type="button"
                              disabled={!!busy}
                              onClick={() => recAction(rec.id, 'dismiss')}
                              className="inline-flex items-center gap-1.5 rounded border border-gray-600/40 bg-gray-600/10 px-3 py-1 text-xs font-medium text-gray-400 hover:bg-gray-600/20 disabled:opacity-40 transition-colors"
                            >
                              {busy === 'dismiss' ? <Loader2 size={11} className="animate-spin" /> : <X size={11} />}
                              Dismiss
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  </ExpandCard>
                )
              })}
            </div>
          )}
        </section>
      )}
    </div>
  )
}
