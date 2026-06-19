import React, { useCallback, useEffect, useState } from 'react'
import { getMorningBriefing, getSystemHUD, getSystemStatus, triggerOpportunityRadar } from '../../services/api'

const TENANT = '794d9b02-2dd6-49f0-b5c1-9f7c0b3af4b1'

// ── Shared primitives ───────────────────────────────────────────────────────

function Card({ children, className = '' }) {
  return (
    <div className={`rounded-2xl border border-white/10 bg-white/5 backdrop-blur-md p-5 ${className}`}>
      {children}
    </div>
  )
}

function Label({ children }) {
  return <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-white/40 mb-1">{children}</p>
}

function BigStat({ label, value, sub, color = 'text-white' }) {
  return (
    <div>
      <Label>{label}</Label>
      <p className={`text-3xl font-bold tabular-nums ${color}`}>{value}</p>
      {sub && <p className="text-xs text-white/40 mt-0.5">{sub}</p>}
    </div>
  )
}

function StatusDot({ status }) {
  const map = { green: 'bg-emerald-400', amber: 'bg-amber-400', red: 'bg-red-400', ok: 'bg-emerald-400' }
  return <span className={`inline-block h-2 w-2 rounded-full ${map[status] || 'bg-white/20'}`} />
}

function PriorityBadge({ label }) {
  const isHot = label === 'HOT'
  return (
    <span className={`inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-bold
      ${isHot ? 'bg-orange-500/20 text-orange-300' : 'bg-blue-500/20 text-blue-300'}`}>
      {isHot ? '🔥' : '⚡'} {label}
    </span>
  )
}

// ── Revenue strip ───────────────────────────────────────────────────────────

function RevenueStrip({ metrics }) {
  const fmt = (n) => n >= 1000 ? `$${(n / 1000).toFixed(1)}k` : `$${n}`
  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
      <Card>
        <BigStat label="MRR" value={fmt(metrics.mrr || 0)} sub="monthly recurring revenue" color="text-emerald-300" />
      </Card>
      <Card>
        <BigStat label="Pipeline" value={fmt(metrics.pipeline || 0)} sub="active opportunities" color="text-cyan-300" />
      </Card>
      <Card>
        <BigStat label="Hot Leads" value={metrics.hot_lead_count || 0} sub="score ≥ 60, ready for proposal" color="text-orange-300" />
      </Card>
      <Card>
        <BigStat label="New Today" value={metrics.new_leads || 0} sub="leads added today" color="text-purple-300" />
      </Card>
    </div>
  )
}

// ── Hot leads panel ─────────────────────────────────────────────────────────

function HotLeadsPanel({ leads }) {
  if (!leads?.length) {
    return (
      <Card>
        <Label>Hot Leads (Score ≥ 60)</Label>
        <p className="text-xs text-white/30 mt-3 text-center py-4">No hot leads yet. Run discovery or add leads to start scoring.</p>
      </Card>
    )
  }
  return (
    <Card>
      <Label>Hot Leads — Ready for Proposal</Label>
      <div className="mt-3 space-y-2">
        {leads.map((lead, i) => (
          <div key={lead.id || i} className="flex items-center justify-between gap-2 rounded-xl border border-white/5 bg-white/5 px-3 py-2">
            <div className="min-w-0">
              <p className="text-sm font-semibold text-white truncate">{lead.company || 'Unknown'}</p>
              <p className="text-xs text-white/40">{lead.industry || '—'} · {lead.country || '—'}</p>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <div className="text-right">
                <p className="text-sm font-bold text-orange-300">{Math.round(lead.score)}</p>
                <p className="text-[10px] text-white/30">/ 100</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </Card>
  )
}

// ── Proposals / contracts strip ─────────────────────────────────────────────

function PipelineAlerts({ metrics }) {
  const overdue = metrics.overdue_proposals || []
  const contracts = metrics.pending_contracts || []
  const accepted = metrics.accepted_proposals_awaiting_contract || 0

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
      {/* Overdue proposals */}
      <Card>
        <Label>Overdue Proposals</Label>
        {overdue.length === 0 ? (
          <p className="text-xs text-white/30 mt-2">None overdue ✓</p>
        ) : overdue.map((p, i) => (
          <div key={i} className="mt-2 rounded-lg border border-red-500/20 bg-red-500/5 px-3 py-2">
            <p className="text-sm font-semibold text-red-300 truncate">{p.client}</p>
            <p className="text-xs text-white/40">{p.days_overdue}d no response · follow up now</p>
          </div>
        ))}
      </Card>

      {/* Accepted → awaiting contract */}
      <Card>
        <Label>Accepted → Contract Pending</Label>
        <div className="mt-2 flex items-center gap-3">
          <p className={`text-3xl font-bold ${accepted > 0 ? 'text-amber-300' : 'text-white/30'}`}>
            {accepted}
          </p>
          <p className="text-xs text-white/40">
            {accepted > 0 ? 'proposal(s) accepted — generate contracts' : 'No pending contracts to generate'}
          </p>
        </div>
      </Card>

      {/* Pending contracts */}
      <Card>
        <Label>Pending Contracts</Label>
        {contracts.length === 0 ? (
          <p className="text-xs text-white/30 mt-2">None pending ✓</p>
        ) : contracts.map((c, i) => (
          <div key={i} className="mt-2 rounded-lg border border-amber-500/20 bg-amber-500/5 px-3 py-2">
            <p className="text-sm font-semibold text-amber-300 truncate">{c.client}</p>
            <p className="text-xs text-white/40">{c.service || '—'} · [{c.status}]</p>
          </div>
        ))}
      </Card>
    </div>
  )
}

// ── System health panel ─────────────────────────────────────────────────────

function SystemHealthPanel({ hud, providers }) {
  const health = hud?.system_health || {}
  const systems = [
    { key: 'backend', label: 'Backend' },
    { key: 'database', label: 'Database' },
    { key: 'redis', label: 'Redis' },
    { key: 'scheduler', label: 'Scheduler' },
    { key: 'aionx', label: 'AIONx' },
    { key: 'email_engine', label: 'Email Engine' },
  ]

  const active = providers?.ai_providers?.active || []

  return (
    <Card>
      <Label>System Health</Label>
      <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
        {systems.map(({ key, label }) => (
          <div key={key} className="flex items-center gap-2">
            <StatusDot status={health[key] || 'red'} />
            <span className="text-xs text-white/60">{label}</span>
            <span className={`ml-auto text-[10px] font-bold uppercase ${
              health[key] === 'green' ? 'text-emerald-400' :
              health[key] === 'amber' ? 'text-amber-400' : 'text-red-400'
            }`}>{health[key] || 'unknown'}</span>
          </div>
        ))}
      </div>
      {active.length > 0 && (
        <div className="mt-4">
          <Label>AI Providers Active</Label>
          <div className="flex flex-wrap gap-1.5 mt-1">
            {active.map(p => (
              <span key={p} className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-300">
                {p}
              </span>
            ))}
          </div>
        </div>
      )}
    </Card>
  )
}

// ── Outreach snapshot ───────────────────────────────────────────────────────

function OutreachSnapshot({ metrics }) {
  return (
    <Card>
      <Label>Outreach Activity</Label>
      <div className="mt-3 space-y-3">
        <div className="flex justify-between text-sm">
          <span className="text-white/50">Scheduled today</span>
          <span className="font-bold text-white">{metrics.outreach_count || 0}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-white/50">Replies this week</span>
          <span className="font-bold text-white">{metrics.reply_count || 0}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-white/50">Trust briefs this week</span>
          <span className="font-bold text-white">{metrics.briefs_this_week || 0}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-white/50">Pending approvals</span>
          <span className={`font-bold ${(metrics.pending_approvals || 0) > 0 ? 'text-amber-300' : 'text-white'}`}>
            {metrics.pending_approvals || 0}
          </span>
        </div>
      </div>
    </Card>
  )
}

// ── Opportunity Radar panel ─────────────────────────────────────────────────

function OpportunityRadarPanel() {
  const [radar, setRadar] = useState(null)
  const [loading, setLoading] = useState(false)

  async function runRadar() {
    setLoading(true)
    try {
      const data = await triggerOpportunityRadar()
      setRadar(data)
    } catch {}
    setLoading(false)
  }

  return (
    <Card>
      <div className="flex items-center justify-between mb-3">
        <Label>Opportunity Radar</Label>
        <button
          onClick={runRadar}
          disabled={loading}
          className="rounded border border-blue-400/30 bg-blue-400/10 px-2.5 py-1 text-[11px] font-bold text-blue-300 hover:bg-blue-400/20 disabled:opacity-40 transition-colors"
        >
          {loading ? '…Scanning' : '🎯 Scan Now'}
        </button>
      </div>

      {!radar ? (
        <p className="text-xs text-white/30 text-center py-4">
          Click Scan Now to find idle hot leads ready to re-engage.
        </p>
      ) : (
        <div className="space-y-2">
          <div className="flex gap-4 text-xs mb-3">
            <span className="text-orange-300 font-bold">🔥 {radar.summary?.hot} HOT</span>
            <span className="text-blue-300 font-bold">⚡ {radar.summary?.warm} WARM</span>
          </div>
          {radar.leads?.length === 0 ? (
            <p className="text-xs text-white/30">No idle opportunities found. Pipeline is active ✓</p>
          ) : radar.leads?.map((lead, i) => (
            <div key={i} className="rounded-lg border border-white/5 bg-white/5 px-3 py-2">
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm font-semibold text-white truncate">{lead.company}</p>
                <PriorityBadge label={lead.priority} />
              </div>
              <p className="text-xs text-white/40 mt-0.5">{lead.recommended_action}</p>
              <p className="text-[10px] text-white/30 mt-0.5">{lead.days_silent}d silent · score {Math.round(lead.score)}</p>
            </div>
          ))}
        </div>
      )}
    </Card>
  )
}

// ── Main WarRoom ─────────────────────────────────────────────────────────────

export default function WarRoom() {
  const [metrics, setMetrics] = useState({})
  const [hud, setHud] = useState(null)
  const [providers, setProviders] = useState(null)
  const [loading, setLoading] = useState(true)
  const [lastRefresh, setLastRefresh] = useState(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const [briefingData, hudData, statusData] = await Promise.allSettled([
        getMorningBriefing(TENANT),
        getSystemHUD(),
        getSystemStatus(),
      ])
      if (briefingData.status === 'fulfilled') setMetrics(briefingData.value?.metrics || {})
      if (hudData.status === 'fulfilled') setHud(hudData.value)
      if (statusData.status === 'fulfilled') setProviders(statusData.value)
      setLastRefresh(new Date().toLocaleTimeString())
    } catch {}
    setLoading(false)
  }, [])

  useEffect(() => {
    refresh()
    const id = setInterval(refresh, 60_000)
    return () => clearInterval(id)
  }, [refresh])

  return (
    <div className="min-h-screen bg-[#0a0a0f] p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-white/30">Aliyar Solutions</p>
          <h1 className="text-2xl font-bold text-white mt-0.5">War Room</h1>
          <p className="text-sm text-white/40 mt-0.5">Live pipeline intelligence · refreshes every 60s</p>
        </div>
        <div className="flex items-center gap-3">
          {lastRefresh && <span className="text-xs text-white/30">Updated {lastRefresh}</span>}
          <button
            onClick={refresh}
            disabled={loading}
            className="rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm font-semibold text-white hover:bg-white/10 disabled:opacity-40 transition-colors"
          >
            {loading ? '…' : '↻ Refresh'}
          </button>
        </div>
      </div>

      {loading && !metrics.mrr ? (
        <div className="flex items-center justify-center py-24">
          <div className="text-center space-y-3">
            <div className="h-8 w-8 rounded-full border-2 border-white/20 border-t-white/80 animate-spin mx-auto" />
            <p className="text-sm text-white/40">Loading intelligence…</p>
          </div>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Revenue KPIs */}
          <RevenueStrip metrics={metrics} />

          {/* Pipeline alerts row */}
          <PipelineAlerts metrics={metrics} />

          {/* Main content: hot leads + radar + outreach + health */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <div className="lg:col-span-1">
              <HotLeadsPanel leads={metrics.hot_leads} />
            </div>
            <div className="lg:col-span-1 space-y-6">
              <OutreachSnapshot metrics={metrics} />
              <SystemHealthPanel hud={hud} providers={providers} />
            </div>
            <div className="lg:col-span-1">
              <OpportunityRadarPanel />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
