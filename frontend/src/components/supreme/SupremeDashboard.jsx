import React, { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Scale, Brain, DollarSign, Server, Target, ChevronDown, ChevronUp,
  RefreshCw, CheckCircle, AlertTriangle, XCircle, TrendingUp, Shield,
  Zap, Activity, Users, ArrowRight, BarChart2, Layers, Lock,
} from 'lucide-react'
import {
  supremeSnapshot, supremeConstitutionLaws, supremeAuthorityMatrix,
  supremeEscalationTriggers, supremeCEODashboard, supremeCEOPriorities,
  supremeCEOCompetitive, supremeRevenueDashboard, supremePipelineHealth,
  supremePlatformDashboard, supremeTechDebt, supremeSalesDashboard,
  supremeObjectionPlaybook, getRevenueARR, getLeadStats,
} from '../../services/api'

// ── Shared styles ─────────────────────────────────────────────────────────────

const TABS = [
  { id: 'overview',      label: 'Overview',      icon: Layers },
  { id: 'constitution',  label: 'Constitution',   icon: Scale },
  { id: 'ceo',           label: 'CEO Brain',      icon: Brain },
  { id: 'revenue',       label: 'Revenue',        icon: DollarSign },
  { id: 'platform',      label: 'Platform',       icon: Server },
  { id: 'sales',         label: 'Sales',          icon: Target },
]

const STATUS_STYLE = {
  HEALTHY:        { bg: 'bg-emerald-500/10', border: 'border-emerald-500/25', text: 'text-emerald-400', dot: 'bg-emerald-400' },
  FULLY_OPERATIONAL: { bg: 'bg-emerald-500/10', border: 'border-emerald-500/25', text: 'text-emerald-400', dot: 'bg-emerald-400' },
  NEEDS_ATTENTION:{ bg: 'bg-amber-500/10',   border: 'border-amber-500/25',   text: 'text-amber-400',   dot: 'bg-amber-400' },
  AT_RISK:        { bg: 'bg-amber-500/10',   border: 'border-amber-500/25',   text: 'text-amber-400',   dot: 'bg-amber-400' },
  CRITICAL:       { bg: 'bg-red-500/10',     border: 'border-red-500/25',     text: 'text-red-400',     dot: 'bg-red-500' },
  STRONG:         { bg: 'bg-emerald-500/10', border: 'border-emerald-500/25', text: 'text-emerald-400', dot: 'bg-emerald-400' },
}
const getStyle = (s) => STATUS_STYLE[s] || { bg: 'bg-slate-500/10', border: 'border-slate-500/20', text: 'text-slate-400', dot: 'bg-slate-400' }

function Card({ children, className = '' }) {
  return (
    <div className={`rounded-xl border border-white/[0.07] bg-white/[0.03] p-4 ${className}`}>
      {children}
    </div>
  )
}

function SectionTitle({ icon: Icon, label }) {
  return (
    <div className="flex items-center gap-2 mb-4">
      <Icon size={14} className="text-jarvis-blue" />
      <h3 className="text-xs font-semibold uppercase tracking-widest text-white/50">{label}</h3>
    </div>
  )
}

function StatusBadge({ status }) {
  const s = getStyle(status)
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold ${s.bg} ${s.text} border ${s.border}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${s.dot}`} />
      {status?.replace(/_/g, ' ')}
    </span>
  )
}

function Spinner() {
  return <RefreshCw size={14} className="animate-spin text-white/30" />
}

// ── OVERVIEW TAB ─────────────────────────────────────────────────────────────

function Overview({ snapshot }) {
  if (!snapshot) return <div className="flex justify-center py-20"><Spinner /></div>
  const subsystems = snapshot.subsystems || {}
  return (
    <div className="space-y-4">
      <Card>
        <SectionTitle icon={Layers} label="Supreme Intelligence Layer — Active Subsystems" />
        <div className="grid grid-cols-1 gap-3">
          {Object.entries(subsystems).map(([key, desc]) => (
            <div key={key} className="flex items-start gap-3 p-3 rounded-lg bg-white/[0.02] border border-white/[0.05]">
              <CheckCircle size={14} className="text-emerald-400 mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-xs font-semibold text-white/80 capitalize">{key.replace(/_/g, ' ')}</p>
                <p className="text-[11px] text-white/40 mt-0.5">{desc}</p>
              </div>
            </div>
          ))}
        </div>
      </Card>
      <div className="grid grid-cols-2 gap-3">
        <Card>
          <p className="text-[10px] text-white/40 uppercase tracking-wider mb-1">CEO Phase</p>
          <p className="text-sm font-semibold text-white">{snapshot.ceo_phase || '—'}</p>
        </Card>
        <Card>
          <p className="text-[10px] text-white/40 uppercase tracking-wider mb-1">Sales Tiers Active</p>
          <p className="text-sm font-semibold text-white">{(snapshot.sales_tiers || []).join(' · ')}</p>
        </Card>
      </div>
      {(snapshot.constitution_summary?.total_laws) && (
        <Card>
          <SectionTitle icon={Scale} label="Constitution" />
          <div className="grid grid-cols-3 gap-3">
            <div className="text-center">
              <p className="text-2xl font-black text-jarvis-blue">{snapshot.constitution_summary.total_laws}</p>
              <p className="text-[10px] text-white/40 mt-0.5">Constitutional Laws</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-black text-amber-400">{snapshot.constitution_summary.total_escalation_triggers}</p>
              <p className="text-[10px] text-white/40 mt-0.5">Escalation Triggers</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-black text-emerald-400">3</p>
              <p className="text-[10px] text-white/40 mt-0.5">Authority Tiers</p>
            </div>
          </div>
        </Card>
      )}
    </div>
  )
}

// ── CONSTITUTION TAB ─────────────────────────────────────────────────────────

function ConstitutionLaw({ law, idx }) {
  const [open, setOpen] = useState(false)
  return (
    <motion.div
      className="border border-white/[0.06] rounded-lg overflow-hidden"
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: idx * 0.03 }}
    >
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-white/[0.03]"
      >
        <span className="text-[10px] font-mono text-jarvis-blue w-8 flex-shrink-0">#{law.law}</span>
        <span className="text-sm text-white/80 flex-1">{law.title}</span>
        <span className="text-[10px] text-white/30 mr-2">{law.authority?.replace(/_/g, ' ')}</span>
        {open ? <ChevronUp size={13} className="text-white/30" /> : <ChevronDown size={13} className="text-white/30" />}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="px-4 pb-3 border-t border-white/[0.04]"
          >
            <p className="pt-2 text-xs text-white/50 leading-relaxed">{law.mandate}</p>
            <p className="mt-2 text-[11px] text-jarvis-blue/70 italic">{law.test}</p>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

function Constitution() {
  const [laws, setLaws] = useState(null)
  const [matrix, setMatrix] = useState(null)
  const [triggers, setTriggers] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([supremeConstitutionLaws(), supremeAuthorityMatrix(), supremeEscalationTriggers()])
      .then(([l, m, t]) => { setLaws(l.laws || []); setMatrix(m); setTriggers(t.triggers || []) })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="flex justify-center py-20"><Spinner /></div>

  return (
    <div className="space-y-4">
      {matrix && (
        <Card>
          <SectionTitle icon={Lock} label="Authority Matrix" />
          <div className="grid grid-cols-1 gap-2">
            {Object.entries(matrix.tiers || {}).map(([tier, config]) => (
              <div key={tier} className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.05]">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-semibold text-white/80">{tier.replace(/_/g, ' ')}</span>
                  {config.financial_ceiling && (
                    <span className="text-[11px] text-emerald-400 font-mono">≤ ${config.financial_ceiling?.toLocaleString()}</span>
                  )}
                  {!config.financial_ceiling && config.financial_ceiling !== 0 && (
                    <span className="text-[11px] text-amber-400 font-mono">Captain decides</span>
                  )}
                </div>
                <p className="text-[11px] text-white/40">{config.description}</p>
              </div>
            ))}
          </div>
        </Card>
      )}

      {laws && (
        <Card>
          <SectionTitle icon={Scale} label={`${laws.length} Constitutional Laws`} />
          <div className="space-y-1.5">
            {laws.map((law, i) => <ConstitutionLaw key={law.law} law={law} idx={i} />)}
          </div>
        </Card>
      )}

      {triggers && triggers.length > 0 && (
        <Card>
          <SectionTitle icon={AlertTriangle} label="Escalation Triggers" />
          <div className="space-y-1.5">
            {triggers.map((t, i) => (
              <div key={i} className="flex items-start gap-2 p-2 rounded bg-amber-500/5 border border-amber-500/10">
                <AlertTriangle size={12} className="text-amber-400 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-xs text-white/70">{t.trigger}</p>
                  <p className="text-[10px] text-amber-400/70 mt-0.5">{t.escalate_to?.replace(/_/g, ' ')} · {t.reason}</p>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}

// ── CEO BRAIN TAB ─────────────────────────────────────────────────────────────

function CEOBrain() {
  const [data, setData] = useState(null)
  const [priorities, setPriorities] = useState(null)
  const [competitive, setCompetitive] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Pull real business figures first — the constitutional math here is real,
    // it was just always being fed hardcoded zeros regardless of actual state.
    Promise.all([
      getRevenueARR().catch(() => ({ mrr_usd: 0, active_clients: 0 })),
      getLeadStats().catch(() => ({ high_score: 0 })),
    ]).then(([arr, leadStats]) => {
      const mrr = arr.mrr_usd || 0
      const clientCount = arr.active_clients || 0
      const hotLeads = leadStats.high_score || 0

      Promise.all([supremeCEODashboard(mrr), supremeCEOCompetitive()])
        .then(([d, c]) => { setData(d); setCompetitive(c) })
        .catch(() => {})
        .finally(() => setLoading(false))
      supremeCEOPriorities({
        mrr, client_count: clientCount, hot_leads: hotLeads,
        // Not yet backed by a per-client concentration metric — left at 0
        // rather than a fabricated figure until that's wired up.
        top_client_revenue_pct: 0,
      }).then(setPriorities).catch(() => {})
    })
  }, [])

  if (loading) return <div className="flex justify-center py-20"><Spinner /></div>

  const phase = data?.expansion_phase
  return (
    <div className="space-y-4">
      {phase && (
        <Card>
          <SectionTitle icon={TrendingUp} label="Expansion Phase" />
          <div className="flex items-center justify-between mb-3">
            <p className="text-base font-bold text-white">{phase.phase_title}</p>
            <span className="text-[10px] text-jarvis-blue/70 font-mono">{phase.active_phase?.toUpperCase()}</span>
          </div>
          <p className="text-xs text-white/50 mb-3">Milestone: {phase.milestone}</p>
          <div className="space-y-1">
            {(phase.focus_areas || []).map((f, i) => (
              <div key={i} className="flex items-center gap-2 text-xs text-white/60">
                <ArrowRight size={11} className="text-jarvis-blue" />
                {f}
              </div>
            ))}
          </div>
        </Card>
      )}

      {priorities && (
        <Card>
          <SectionTitle icon={Zap} label="Strategic Priorities" />
          <div className="space-y-2">
            {(priorities.strategic_priorities || []).map((p, i) => (
              <div key={i} className="p-3 rounded-lg border border-white/[0.06] bg-white/[0.02]">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-semibold text-white/80">{p.priority?.replace(/_/g, ' ')}</span>
                  <span className={`text-[10px] font-bold ${p.urgency === 'CRITICAL' || p.urgency === 'IMMEDIATE' ? 'text-red-400' : p.urgency === 'HIGH' ? 'text-amber-400' : 'text-white/40'}`}>
                    {p.urgency}
                  </span>
                </div>
                <p className="text-[11px] text-white/50">{p.action}</p>
              </div>
            ))}
          </div>
          {(priorities.warnings || []).length > 0 && (
            <div className="mt-3 space-y-1">
              {priorities.warnings.map((w, i) => (
                <div key={i} className="flex items-start gap-2 text-[11px] text-amber-400/80">
                  <AlertTriangle size={11} className="mt-0.5 flex-shrink-0" />
                  {w}
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {competitive && (
        <Card>
          <SectionTitle icon={Shield} label="Competitive Position" />
          <p className="text-xs text-white/70 mb-3 leading-relaxed">{competitive.our_position}</p>
          <div className="space-y-1.5">
            {(competitive.key_differentiators || []).map((d, i) => (
              <div key={i} className="flex items-start gap-2 text-[11px] text-white/50">
                <CheckCircle size={11} className="text-emerald-400 mt-0.5 flex-shrink-0" />
                {d}
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}

// ── REVENUE TAB ───────────────────────────────────────────────────────────────

function Revenue() {
  const [data, setData] = useState(null)
  const [health, setHealth] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    supremeRevenueDashboard().then(setData).catch(() => {}).finally(() => setLoading(false))
    supremePipelineHealth({ mrr: 0, monthly_growth_pct: 0, hot_leads: 0, proposals_sent: 0, proposals_won: 0 })
      .then(setHealth).catch(() => {})
  }, [])

  if (loading) return <div className="flex justify-center py-20"><Spinner /></div>

  const tiers = data?.tier_details || {}
  const milestones = data?.milestones || []
  const metrics = data?.healthy_metrics || {}

  return (
    <div className="space-y-4">
      <Card>
        <SectionTitle icon={DollarSign} label="Pricing Tiers" />
        <div className="grid grid-cols-2 gap-2">
          {Object.entries(tiers).map(([name, tier]) => (
            <div key={name} className="p-3 rounded-lg border border-white/[0.06] bg-white/[0.02]">
              <p className="text-xs font-bold text-jarvis-blue mb-1">{name}</p>
              <p className="text-base font-black text-white">${tier.monthly_retainer?.toLocaleString()}<span className="text-[10px] text-white/30 font-normal">/mo</span></p>
              <p className="text-[10px] text-white/40 mt-1">LTV target: ${tier.target_ltv?.toLocaleString()}</p>
              <p className="text-[10px] text-white/30 mt-0.5">{tier.churn_risk} churn risk</p>
            </div>
          ))}
        </div>
      </Card>

      {milestones.length > 0 && (
        <Card>
          <SectionTitle icon={BarChart2} label="MRR Milestones" />
          <div className="space-y-2">
            {milestones.map((m, i) => (
              <div key={i} className="flex items-center gap-3">
                <span className="text-xs font-mono text-emerald-400 w-16 flex-shrink-0">${(m.milestone/1000).toFixed(0)}K</span>
                <span className="text-xs text-white/60 flex-1">{m.phase}</span>
                <span className="text-[10px] text-white/30">{m.target_clients} clients</span>
              </div>
            ))}
          </div>
        </Card>
      )}

      {Object.keys(metrics).length > 0 && (
        <Card>
          <SectionTitle icon={Activity} label="Health Benchmarks" />
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(metrics).map(([k, v]) => (
              <div key={k} className="p-2 rounded bg-white/[0.02] border border-white/[0.05]">
                <p className="text-[10px] text-white/40 capitalize">{k.replace(/_/g, ' ')}</p>
                <p className="text-xs font-semibold text-white/80 mt-0.5">{typeof v === 'number' ? v : String(v)}</p>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}

// ── PLATFORM TAB ─────────────────────────────────────────────────────────────

function Platform() {
  const [data, setData] = useState(null)
  const [debt, setDebt] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([supremePlatformDashboard(), supremeTechDebt()])
      .then(([d, t]) => { setData(d); setDebt(t) })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="flex justify-center py-20"><Spinner /></div>

  const infra = data?.infrastructure || {}
  const sla = data?.sla_standards || {}
  const items = debt?.immediate_priorities || []
  const liveDebt = debt?.live_debt_index

  return (
    <div className="space-y-4">
      {liveDebt ? (
        <Card>
          <SectionTitle icon={AlertTriangle} label={`Live Debt Index — week of ${liveDebt.week_of}`} />
          <div className="grid grid-cols-3 gap-2">
            <div className="p-2 rounded bg-white/[0.02] border border-white/[0.05]">
              <p className="text-[10px] text-white/40">Total debt score</p>
              <p className="text-sm font-semibold text-white/80 mt-0.5">{liveDebt.total_debt_score}</p>
            </div>
            <div className="p-2 rounded bg-white/[0.02] border border-white/[0.05]">
              <p className="text-[10px] text-white/40">Trend</p>
              <p className="text-sm font-semibold text-white/80 mt-0.5">{liveDebt.trend}</p>
            </div>
            <div className="p-2 rounded bg-white/[0.02] border border-white/[0.05]">
              <p className="text-[10px] text-white/40">Est. repayment</p>
              <p className="text-sm font-semibold text-white/80 mt-0.5">{liveDebt.estimated_repayment_weeks}w</p>
            </div>
            <div className="p-2 rounded bg-white/[0.02] border border-white/[0.05]">
              <p className="text-[10px] text-white/40">Critical items</p>
              <p className="text-sm font-semibold text-red-400 mt-0.5">{liveDebt.critical_count}</p>
            </div>
            <div className="p-2 rounded bg-white/[0.02] border border-white/[0.05]">
              <p className="text-[10px] text-white/40">High items</p>
              <p className="text-sm font-semibold text-amber-400 mt-0.5">{liveDebt.high_count}</p>
            </div>
            <div className="p-2 rounded bg-white/[0.02] border border-white/[0.05]">
              <p className="text-[10px] text-white/40">Refactor triggered</p>
              <p className="text-sm font-semibold text-white/80 mt-0.5">{liveDebt.refactoring_triggered ? 'Yes' : 'No'}</p>
            </div>
          </div>
        </Card>
      ) : (
        <div className="text-[11px] text-white/40 px-1">
          No debt index computed yet — the weekly aionx_debt_assessment job populates this.
        </div>
      )}
      <Card>
        <SectionTitle icon={Server} label="Infrastructure" />
        <div className="grid grid-cols-2 gap-2">
          {Object.entries(infra).filter(([, v]) => typeof v === 'string').map(([k, v]) => (
            <div key={k} className="p-2 rounded bg-white/[0.02] border border-white/[0.05]">
              <p className="text-[10px] text-white/40 capitalize">{k.replace(/_/g, ' ')}</p>
              <p className="text-[11px] font-medium text-white/70 mt-0.5 truncate">{v}</p>
            </div>
          ))}
        </div>
      </Card>

      <Card>
        <SectionTitle icon={Activity} label="SLA Standards" />
        <div className="grid grid-cols-2 gap-2">
          {Object.entries(sla).map(([k, v]) => (
            <div key={k} className="p-2 rounded bg-white/[0.02] border border-white/[0.05]">
              <p className="text-[10px] text-white/40 capitalize">{k.replace(/_/g, ' ')}</p>
              <p className="text-xs font-semibold text-emerald-400 mt-0.5">{v}</p>
            </div>
          ))}
        </div>
      </Card>

      {items.length > 0 && (
        <Card>
          <SectionTitle icon={AlertTriangle} label={`Tech Improvements (${debt?.total_improvements} total)`} />
          <div className="space-y-2">
            {items.map((item) => (
              <div key={item.id} className="p-3 rounded-lg border border-white/[0.06] bg-white/[0.02]">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[10px] font-mono text-white/30">{item.id}</span>
                  <span className={`text-[10px] font-bold ${item.category === 'CRITICAL' ? 'text-red-400' : item.category === 'HIGH' ? 'text-amber-400' : 'text-white/40'}`}>
                    {item.category}
                  </span>
                </div>
                <p className="text-xs font-semibold text-white/80">{item.title}</p>
                <p className="text-[11px] text-white/40 mt-0.5">{item.revenue_impact}</p>
                <p className="text-[10px] text-white/30 mt-1">{item.estimated_hours}h estimated</p>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}

// ── SALES TAB ─────────────────────────────────────────────────────────────────

function Sales() {
  const [data, setData] = useState(null)
  const [objection, setObjection] = useState(null)
  const [selectedObj, setSelectedObj] = useState('too_expensive')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    supremeSalesDashboard().then(setData).catch(() => {}).finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    supremeObjectionPlaybook(selectedObj).then(setObjection).catch(() => {})
  }, [selectedObj])

  if (loading) return <div className="flex justify-center py-20"><Spinner /></div>

  const tiers = data?.tier_definitions || {}
  const winP = data?.win_patterns || []
  const lossP = data?.loss_patterns || []
  const objTypes = data?.objection_types || []

  return (
    <div className="space-y-4">
      <Card>
        <SectionTitle icon={Users} label="Lead Tiers" />
        <div className="grid grid-cols-2 gap-2">
          {Object.entries(tiers).map(([name, tier]) => (
            <div key={name} className="p-3 rounded-lg border border-white/[0.06] bg-white/[0.02]">
              <p className={`text-xs font-bold mb-1 ${name === 'HOT' ? 'text-red-400' : name === 'WARM' ? 'text-amber-400' : name === 'NURTURE' ? 'text-jarvis-blue' : 'text-white/40'}`}>{name}</p>
              <p className="text-[11px] text-white/60">Follow-up: {tier.follow_up_hours}h</p>
              <p className="text-[11px] text-white/40">{tier.owner}</p>
              <p className="text-[10px] text-white/30 mt-1">{tier.action?.replace(/_/g, ' ')}</p>
            </div>
          ))}
        </div>
      </Card>

      <Card>
        <SectionTitle icon={Target} label="Objection Playbook" />
        <div className="flex flex-wrap gap-1.5 mb-3">
          {objTypes.map((t) => (
            <button
              key={t}
              onClick={() => setSelectedObj(t)}
              className={`px-2.5 py-1 rounded-full text-[10px] font-semibold transition-all ${selectedObj === t ? 'bg-jarvis-blue/20 text-jarvis-blue border border-jarvis-blue/30' : 'bg-white/[0.04] text-white/40 border border-white/[0.06] hover:text-white/60'}`}
            >
              {t.replace(/_/g, ' ')}
            </button>
          ))}
        </div>
        {objection && (
          <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.06]">
            <p className="text-[10px] text-jarvis-blue/70 uppercase tracking-wider mb-1">{objection.framing}</p>
            <p className="text-xs text-white/70 leading-relaxed">{objection.response_template}</p>
            <div className="flex items-center justify-between mt-2 pt-2 border-t border-white/[0.05]">
              <span className="text-[10px] text-white/40">Owner: {objection.assigned_owner}</span>
              <span className="text-[10px] text-white/30 italic">{objection.escalation_option}</span>
            </div>
          </div>
        )}
      </Card>

      <div className="grid grid-cols-2 gap-3">
        <Card>
          <SectionTitle icon={CheckCircle} label="Win Patterns" />
          <div className="space-y-1.5">
            {winP.slice(0, 5).map((p, i) => (
              <div key={i} className="flex items-start gap-1.5 text-[11px] text-white/50">
                <CheckCircle size={10} className="text-emerald-400 mt-0.5 flex-shrink-0" />
                {p}
              </div>
            ))}
          </div>
        </Card>
        <Card>
          <SectionTitle icon={XCircle} label="Loss Patterns" />
          <div className="space-y-1.5">
            {lossP.slice(0, 5).map((p, i) => (
              <div key={i} className="flex items-start gap-1.5 text-[11px] text-white/50">
                <XCircle size={10} className="text-red-400 mt-0.5 flex-shrink-0" />
                {p}
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  )
}

// ── MAIN COMPONENT ────────────────────────────────────────────────────────────

export default function SupremeDashboard() {
  const [tab, setTab] = useState('overview')
  const [snapshot, setSnapshot] = useState(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(() => {
    setLoading(true)
    supremeSnapshot(0).then(setSnapshot).catch(() => {}).finally(() => setLoading(false))
  }, [])

  useEffect(() => { load() }, [load])

  return (
    <div className="h-full flex flex-col bg-black/20 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-white/[0.06]">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-jarvis-blue/30 to-purple-500/30 border border-jarvis-blue/30 flex items-center justify-center">
            <Layers size={16} className="text-jarvis-blue" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-white tracking-wide">Supreme Intelligence</h1>
            <p className="text-[10px] text-white/40">Layer 19 — Constitution · CEO · Revenue · Platform · Sales</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {loading ? <Spinner /> : (
            <StatusBadge status="FULLY_OPERATIONAL" />
          )}
          <button onClick={load} className="p-1.5 rounded-lg hover:bg-white/[0.06] transition-colors">
            <RefreshCw size={13} className="text-white/40" />
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 px-4 py-2 border-b border-white/[0.04] overflow-x-auto no-scrollbar">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all
              ${tab === id ? 'bg-jarvis-blue/15 text-jarvis-blue border border-jarvis-blue/25' : 'text-white/40 hover:text-white/60 hover:bg-white/[0.04]'}`}
          >
            <Icon size={12} />
            {label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        <AnimatePresence mode="wait">
          <motion.div
            key={tab}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.15 }}
          >
            {tab === 'overview'     && <Overview snapshot={snapshot} />}
            {tab === 'constitution' && <Constitution />}
            {tab === 'ceo'          && <CEOBrain />}
            {tab === 'revenue'      && <Revenue />}
            {tab === 'platform'     && <Platform />}
            {tab === 'sales'        && <Sales />}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  )
}
