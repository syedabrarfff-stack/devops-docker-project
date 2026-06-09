import React, { useCallback, useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import {
  Activity, AlertTriangle, Brain, CheckCircle2, ChevronRight,
  Cpu, Loader2, Mic, RefreshCw, Rocket, Shield, TrendingUp, Users, Zap,
} from 'lucide-react'
import api from '../../services/api'
import { DEFAULT_TENANT } from '../frontier/FrontierShell'

const TABS = [
  { id: 'axiom',      label: 'AXIOM OS',         icon: Shield },
  { id: 'overview',   label: 'Overview',         icon: Activity },
  { id: 'dios',       label: 'Intelligence Officers', icon: Users },
  { id: 'milestones', label: 'Milestones',        icon: CheckCircle2 },
  { id: 'tech',       label: 'Tech Evolution',    icon: Cpu },
  { id: 'calls',      label: 'Call Intelligence', icon: Mic },
  { id: 'strategy',   label: 'Strategy',          icon: Brain },
]

const STATUS_COLORS = {
  achieved:      'text-green-400 border-green-400/30 bg-green-400/10',
  in_review:     'text-yellow-400 border-yellow-400/30 bg-yellow-400/10',
  council_queue: 'text-cyan-400 border-cyan-400/30 bg-cyan-400/10',
  improving:     'text-blue-400 border-blue-400/30 bg-blue-400/10',
  implemented:   'text-emerald-400 border-emerald-400/30 bg-emerald-400/10',
  closed:        'text-gray-400 border-gray-400/30 bg-gray-400/10',
  discovered:    'text-purple-400 border-purple-400/30 bg-purple-400/10',
  evaluating:    'text-yellow-400 border-yellow-400/30 bg-yellow-400/10',
  approved:      'text-green-400 border-green-400/30 bg-green-400/10',
  implementing:  'text-blue-400 border-blue-400/30 bg-blue-400/10',
  deployed:      'text-emerald-400 border-emerald-400/30 bg-emerald-400/10',
  rejected:      'text-red-400 border-red-400/30 bg-red-400/10',
  scheduled:     'text-cyan-400 border-cyan-400/30 bg-cyan-400/10',
  ready:         'text-green-400 border-green-400/30 bg-green-400/10',
  completed:     'text-emerald-400 border-emerald-400/30 bg-emerald-400/10',
}

const PRIORITY_COLORS = {
  critical: 'text-red-400',
  high:     'text-orange-400',
  medium:   'text-yellow-400',
  low:      'text-gray-400',
}

function StatusBadge({ status }) {
  const cls = STATUS_COLORS[status] || 'text-gray-400 border-gray-400/30 bg-gray-400/10'
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide ${cls}`}>
      {status?.replace(/_/g, ' ')}
    </span>
  )
}

function ScoreBar({ value, max = 100 }) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100))
  const color = pct >= 80 ? 'bg-green-400' : pct >= 60 ? 'bg-yellow-400' : 'bg-red-400'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full bg-white/10">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[11px] text-gray-400 w-8 text-right">{Math.round(value)}</span>
    </div>
  )
}

function StatCard({ label, value, sub, color = 'text-jarvis-cyan', delay = 0 }) {
  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay }}
      className="glass p-4">
      <p className="text-xs text-gray-400">{label}</p>
      <p className={`mt-1.5 text-2xl font-bold ${color}`}>{value}</p>
      {sub && <p className="mt-1 text-[11px] text-gray-500">{sub}</p>}
    </motion.div>
  )
}

function EmptyState({ message }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <Shield size={32} className="text-gray-600 mb-3" />
      <p className="text-sm text-gray-500">{message}</p>
    </div>
  )
}

function AxiomTab({ axiom }) {
  const model = axiom?.model || {}
  const pulse = axiom?.pulse || {}
  const departments = model.departments || []
  const gateways = model.gateways || []
  const summary = pulse.summary || {}

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <StatCard label="Brand" value={model.brand?.commercial_name || 'AXIOM'} sub="Commercial operating system" delay={0} />
        <StatCard label="Departments" value={model.counts?.departments || departments.length} sub="One manager + consultant each" color="text-emerald-400" delay={0.04} />
        <StatCard label="Gateways" value={model.counts?.gateways || gateways.length} sub="Outreach, CloudOps, Council" color="text-jarvis-gold" delay={0.08} />
        <StatCard label="Pulse" value={`${pulse.pulse_interval_minutes || 15}m`} sub="Health monitoring cadence" color="text-blue-400" delay={0.12} />
        <StatCard label="Operational" value={summary.operational ?? departments.length} sub="Departments above alert threshold" color="text-green-400" delay={0.16} />
      </div>

      <div className="glass p-5">
        <p className="text-xs uppercase tracking-widest text-jarvis-cyan/70 mb-3">Commercial Gateways</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {gateways.map((gateway) => (
            <div key={gateway.code} className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
              <p className="text-sm font-semibold text-white">{gateway.name}</p>
              <p className="mt-2 text-xs text-gray-400 leading-relaxed">{gateway.entry_point}</p>
              <p className="mt-3 text-xs text-jarvis-gold">{gateway.retainer_range}</p>
              <p className="mt-1 text-[11px] text-gray-500">Success: {gateway.success_metric}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="glass p-5">
        <div className="flex items-center justify-between gap-3 mb-4">
          <div>
            <p className="text-xs uppercase tracking-widest text-jarvis-cyan/70">25 Departments</p>
            <p className="mt-1 text-xs text-gray-500">Internal capabilities stay invisible to clients; AXIOM sells diagnosis and outcomes.</p>
          </div>
          <StatusBadge status="operational" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {departments.map((department) => {
            const live = (pulse.departments || []).find((item) => item.code === department.code)
            return (
              <div key={department.code} className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-white">{department.name}</p>
                    <p className="text-xs text-gray-500">{department.group}</p>
                  </div>
                  <span className="rounded-full border border-jarvis-cyan/30 bg-jarvis-cyan/10 px-2 py-0.5 text-[10px] text-jarvis-cyan">
                    {department.number}/25
                  </span>
                </div>
                <p className="mt-3 text-xs text-gray-400 leading-relaxed">{department.service}</p>
                <div className="mt-3 grid grid-cols-2 gap-2 text-[11px] text-gray-500">
                  <span>Manager: <b className="text-gray-300">{department.manager}</b></span>
                  <span>Consultant: <b className="text-gray-300">{department.consultant}</b></span>
                </div>
                <div className="mt-3">
                  <p className="text-[11px] text-gray-500 mb-1">Health</p>
                  <ScoreBar value={live?.health_score || 0} />
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

// ── Overview Tab ──────────────────────────────────────────────────────────────
function OverviewTab({ health, dios, milestones, tech, calls, strategy }) {
  const activeDios    = (dios?.dios || []).filter(d => d.is_active).length
  const totalDios     = (dios?.dios || []).length
  const pendingMS     = (milestones?.milestones || []).filter(m => m.status !== 'implemented' && m.status !== 'closed').length
  const criticalTech  = (tech?.discoveries || []).filter(t => t.priority === 'critical').length
  const upcomingCalls = (calls?.calls || []).filter(c => c.status === 'scheduled' || c.status === 'ready').length
  const latestReport  = (strategy?.reports || [])[0]

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Active DIOs" value={`${activeDios}/${totalDios}`} sub="Intelligence officers online" delay={0} />
        <StatCard label="Pending Milestones" value={pendingMS} sub="Awaiting Council review" color="text-jarvis-gold" delay={0.04} />
        <StatCard label="Critical Tech" value={criticalTech} sub="Discoveries need action" color="text-red-400" delay={0.08} />
        <StatCard label="Upcoming Calls" value={upcomingCalls} sub="Client calls scheduled" color="text-emerald-400" delay={0.12} />
      </div>

      {latestReport && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="glass p-5">
          <p className="text-xs uppercase tracking-widest text-jarvis-cyan/70 mb-3">Latest Strategy Report</p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-xs text-gray-400">MRR</p>
              <p className="text-lg font-bold text-white">${(latestReport.mrr || 0).toLocaleString()}</p>
            </div>
            <div>
              <p className="text-xs text-gray-400">Pipeline</p>
              <p className="text-lg font-bold text-white">${(latestReport.pipeline_value || 0).toLocaleString()}</p>
            </div>
            <div>
              <p className="text-xs text-gray-400">Outreach Sent</p>
              <p className="text-lg font-bold text-white">{latestReport.outreach_sent || 0}</p>
            </div>
            <div>
              <p className="text-xs text-gray-400">Reply Rate</p>
              <p className="text-lg font-bold text-white">{(latestReport.reply_rate || 0).toFixed(1)}%</p>
            </div>
          </div>
          {(latestReport.alerts || []).length > 0 && (
            <div className="mt-4 space-y-1">
              {latestReport.alerts.slice(0, 3).map((alert, i) => (
                <div key={i} className="flex items-start gap-2 text-xs text-yellow-300">
                  <AlertTriangle size={12} className="mt-0.5 shrink-0" />
                  <span>{typeof alert === 'string' ? alert : JSON.stringify(alert)}</span>
                </div>
              ))}
            </div>
          )}
        </motion.div>
      )}

      {health && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="glass p-5">
          <p className="text-xs uppercase tracking-widest text-jarvis-cyan/70 mb-3">System Health</p>
          <pre className="text-xs text-gray-300 overflow-auto max-h-48">
            {JSON.stringify(health, null, 2)}
          </pre>
        </motion.div>
      )}
    </div>
  )
}

// ── DIOs Tab ─────────────────────────────────────────────────────────────────
function DiosTab({ dios, onInitialize, loading }) {
  const list = dios?.dios || []

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-400">{list.length} Department Intelligence Officers</p>
        {list.length === 0 && (
          <button onClick={onInitialize} disabled={loading}
            className="btn-primary inline-flex items-center gap-2 text-sm">
            {loading ? <Loader2 size={14} className="animate-spin" /> : <Zap size={14} />}
            Initialize All DIOs
          </button>
        )}
      </div>

      {list.length === 0
        ? <EmptyState message="No DIOs initialized yet. Click Initialize to deploy all 25 Department Intelligence Officers." />
        : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {list.map((dio, i) => (
              <motion.div key={dio.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.04 }} className="glass p-4">
                <div className="flex items-start justify-between gap-2 mb-3">
                  <div>
                    <p className="text-sm font-semibold text-white">{dio.agent_name}</p>
                    <p className="text-xs text-gray-400">{dio.department_name}</p>
                  </div>
                  <span className={`text-[10px] font-medium ${dio.is_active ? 'text-green-400' : 'text-gray-500'}`}>
                    {dio.is_active ? '● Online' : '○ Offline'}
                  </span>
                </div>
                <div className="space-y-2">
                  <div>
                    <p className="text-[11px] text-gray-500 mb-1">Performance</p>
                    <ScoreBar value={(dio.performance_score || 1) * 100} />
                  </div>
                  <div className="flex justify-between text-[11px] text-gray-500">
                    <span>{dio.milestones_submitted || 0} submitted</span>
                    <span>{dio.improvements_implemented || 0} implemented</span>
                  </div>
                  <p className="text-[10px] text-jarvis-cyan/70 truncate">{dio.agent_email}</p>
                </div>
              </motion.div>
            ))}
          </div>
        )
      }
    </div>
  )
}

// ── Milestones Tab ────────────────────────────────────────────────────────────
function MilestonesTab({ milestones, onBulkReview, loading }) {
  const list = milestones?.milestones || []
  const pending = list.filter(m => ['achieved', 'in_review', 'council_queue'].includes(m.status))
  const done    = list.filter(m => ['implemented', 'closed'].includes(m.status))

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-400">{list.length} total — {pending.length} pending review</p>
        <button onClick={onBulkReview} disabled={loading || pending.length === 0}
          className="btn-primary inline-flex items-center gap-2 text-sm">
          {loading ? <Loader2 size={14} className="animate-spin" /> : <Brain size={14} />}
          Run Council Review
        </button>
      </div>

      {list.length === 0
        ? <EmptyState message="No milestones submitted yet. DIOs submit milestones as departments achieve targets." />
        : (
          <div className="space-y-3">
            {list.map((ms, i) => (
              <motion.div key={ms.id} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.03 }} className="glass p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white truncate">{ms.title}</p>
                    <p className="text-xs text-gray-400 mt-0.5">{ms.department_code} · {ms.milestone_type}</p>
                    {ms.council_score != null && (
                      <div className="mt-2">
                        <p className="text-[11px] text-gray-500 mb-1">Council score</p>
                        <ScoreBar value={ms.council_score} />
                      </div>
                    )}
                    {ms.council_verdict && (
                      <p className="mt-2 text-xs text-gray-300 line-clamp-2">{ms.council_verdict}</p>
                    )}
                  </div>
                  <StatusBadge status={ms.status} />
                </div>
              </motion.div>
            ))}
          </div>
        )
      }
    </div>
  )
}

// ── Tech Evolution Tab ────────────────────────────────────────────────────────
function TechTab({ tech, onDiscover, loading }) {
  const list = tech?.discoveries || []

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-400">{list.length} technologies tracked</p>
        <button onClick={onDiscover} disabled={loading}
          className="btn-primary inline-flex items-center gap-2 text-sm">
          {loading ? <Loader2 size={14} className="animate-spin" /> : <Rocket size={14} />}
          Run Discovery Cycle
        </button>
      </div>

      {list.length === 0
        ? <EmptyState message="No technology discoveries yet. Run a discovery cycle to scan all sources." />
        : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {list.map((t, i) => (
              <motion.div key={t.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.04 }} className="glass p-4">
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-white">{t.technology_name}</p>
                    <p className="text-xs text-gray-400">{t.source} · {t.category}</p>
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    <StatusBadge status={t.status} />
                    <span className={`text-[10px] font-medium ${PRIORITY_COLORS[t.priority] || 'text-gray-400'}`}>
                      {t.priority}
                    </span>
                  </div>
                </div>
                <div className="space-y-1.5">
                  <div>
                    <p className="text-[11px] text-gray-500 mb-1">Relevance</p>
                    <ScoreBar value={t.relevance_score || 0} />
                  </div>
                  <div>
                    <p className="text-[11px] text-gray-500 mb-1">Feasibility</p>
                    <ScoreBar value={t.integration_feasibility || 0} />
                  </div>
                </div>
                {t.summary && (
                  <p className="mt-2 text-xs text-gray-400 line-clamp-2">{t.summary}</p>
                )}
              </motion.div>
            ))}
          </div>
        )
      }
    </div>
  )
}

// ── Call Intelligence Tab ─────────────────────────────────────────────────────
function CallsTab({ calls }) {
  const list = calls?.calls || []

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-400">{list.length} client calls</p>
      {list.length === 0
        ? <EmptyState message="No client calls scheduled. Calls are managed through the department intelligence API." />
        : (
          <div className="space-y-3">
            {list.map((call, i) => (
              <motion.div key={call.id} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.04 }} className="glass p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium text-white">{call.client_name}</p>
                      <span className="text-xs text-gray-500">·</span>
                      <p className="text-xs text-gray-400">{call.client_company}</p>
                    </div>
                    <p className="text-xs text-gray-500 mt-0.5">{call.call_topic}</p>
                    <div className="flex items-center gap-3 mt-2">
                      {call.council_approved && (
                        <span className="text-[10px] text-green-400">● Council Approved</span>
                      )}
                      {call.voice_agent_id && (
                        <span className="text-[10px] text-jarvis-cyan">● Voice Agent Deployed</span>
                      )}
                      {call.outcome && (
                        <span className="text-[10px] text-jarvis-gold">● {call.outcome.replace(/_/g, ' ')}</span>
                      )}
                    </div>
                  </div>
                  <StatusBadge status={call.status} />
                </div>
              </motion.div>
            ))}
          </div>
        )
      }
    </div>
  )
}

// ── Strategy Tab ──────────────────────────────────────────────────────────────
function StrategyTab({ strategy, onDailyReport, onWeeklyReport, loading }) {
  const list = strategy?.reports || []
  const latest = list[0]

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <button onClick={onDailyReport} disabled={loading}
          className="btn-primary inline-flex items-center gap-2 text-sm">
          {loading ? <Loader2 size={14} className="animate-spin" /> : <TrendingUp size={14} />}
          Daily Report
        </button>
        <button onClick={onWeeklyReport} disabled={loading}
          className="btn-secondary inline-flex items-center gap-2 text-sm">
          Weekly Report
        </button>
      </div>

      {!latest
        ? <EmptyState message="No strategy reports yet. Generate a daily or weekly report to start." />
        : (
          <div className="space-y-4">
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="glass p-5">
              <div className="flex items-center justify-between mb-4">
                <p className="text-sm font-semibold text-white">
                  {latest.report_type === 'daily' ? 'Daily' : 'Weekly'} Strategy Report
                </p>
                <span className="text-xs text-gray-500">
                  {new Date(latest.report_date).toLocaleDateString()}
                </span>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                <div>
                  <p className="text-[11px] text-gray-400">MRR</p>
                  <p className="text-lg font-bold text-white">${(latest.mrr || 0).toLocaleString()}</p>
                </div>
                <div>
                  <p className="text-[11px] text-gray-400">Pipeline</p>
                  <p className="text-lg font-bold text-white">${(latest.pipeline_value || 0).toLocaleString()}</p>
                </div>
                <div>
                  <p className="text-[11px] text-gray-400">Outreach</p>
                  <p className="text-lg font-bold text-white">{latest.outreach_sent || 0}</p>
                </div>
                <div>
                  <p className="text-[11px] text-gray-400">Reply Rate</p>
                  <p className="text-lg font-bold text-white">{(latest.reply_rate || 0).toFixed(1)}%</p>
                </div>
              </div>

              {latest.scaling_strategy && (
                <div className="border-t border-white/10 pt-4">
                  <p className="text-xs text-jarvis-cyan/70 mb-2">Council Scaling Strategy</p>
                  <p className="text-sm text-gray-300 leading-relaxed">{latest.scaling_strategy}</p>
                </div>
              )}

              {(latest.council_directives || []).length > 0 && (
                <div className="border-t border-white/10 pt-4 mt-4">
                  <p className="text-xs text-jarvis-cyan/70 mb-2">Council Directives</p>
                  <div className="space-y-2">
                    {latest.council_directives.slice(0, 5).map((d, i) => (
                      <div key={i} className="flex items-start gap-2 text-xs text-gray-300">
                        <ChevronRight size={12} className="mt-0.5 text-jarvis-cyan shrink-0" />
                        <span>{typeof d === 'string' ? d : JSON.stringify(d)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {(latest.achievements || []).length > 0 && (
                <div className="border-t border-white/10 pt-4 mt-4">
                  <p className="text-xs text-green-400/70 mb-2">Achievements</p>
                  <div className="space-y-1">
                    {latest.achievements.slice(0, 4).map((a, i) => (
                      <p key={i} className="text-xs text-gray-300">
                        ✓ {typeof a === 'string' ? a : JSON.stringify(a)}
                      </p>
                    ))}
                  </div>
                </div>
              )}
            </motion.div>

            {list.length > 1 && (
              <div className="glass p-4">
                <p className="text-xs text-gray-400 mb-3">Report History</p>
                <div className="space-y-2">
                  {list.slice(1, 6).map((r, i) => (
                    <div key={r.id} className="flex items-center justify-between text-xs">
                      <span className="text-gray-400">{new Date(r.report_date).toLocaleDateString()}</span>
                      <span className="text-gray-500 capitalize">{r.report_type}</span>
                      <span className="text-white">${(r.mrr || 0).toLocaleString()} MRR</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )
      }
    </div>
  )
}

// ── Main View ─────────────────────────────────────────────────────────────────
export default function DepartmentsView() {
  const [activeTab, setActiveTab] = useState('axiom')
  const [data, setData] = useState({ health: null, dios: null, milestones: null, tech: null, calls: null, strategy: null, axiom: null })
  const [loading, setLoading] = useState(false)
  const [actionLoading, setActionLoading] = useState(false)
  const [actionNotice, setActionNotice] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [health, dios, milestones, tech, calls, strategy, axiomModel, axiomPulse] = await Promise.allSettled([
        api.get('/api/v1/departments/health').then((r) => r.data),
        api.get('/api/v1/departments/dios', { params: { tenant_id: DEFAULT_TENANT } }).then((r) => r.data),
        api.get('/api/v1/departments/milestones', { params: { tenant_id: DEFAULT_TENANT } }).then((r) => r.data),
        api.get('/api/v1/departments/tech/discoveries', { params: { tenant_id: DEFAULT_TENANT } }).then((r) => r.data),
        api.get('/api/v1/departments/calls', { params: { tenant_id: DEFAULT_TENANT } }).then((r) => r.data),
        api.get('/api/v1/departments/strategy/reports', { params: { tenant_id: DEFAULT_TENANT } }).then((r) => r.data),
        api.get('/api/v1/departments/axiom/operating-model').then((r) => r.data),
        api.get('/api/v1/departments/axiom/pulse').then((r) => r.data),
      ])
      setData({
        health:     health.status    === 'fulfilled' ? health.value    : null,
        dios:       dios.status      === 'fulfilled' ? dios.value      : null,
        milestones: milestones.status === 'fulfilled' ? milestones.value : null,
        tech:       tech.status      === 'fulfilled' ? tech.value      : null,
        calls:      calls.status     === 'fulfilled' ? calls.value     : null,
        strategy:   strategy.status  === 'fulfilled' ? strategy.value  : null,
        axiom: {
          model: axiomModel.status === 'fulfilled' ? axiomModel.value : null,
          pulse: axiomPulse.status === 'fulfilled' ? axiomPulse.value : null,
        },
      })
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const withAction = (label, fn) => async (...args) => {
    setActionLoading(true)
    setActionNotice(null)
    try {
      const response = await fn(...args)
      const payload = response?.data || response || {}
      setActionNotice({
        kind: 'success',
        title: `${label} complete`,
        message: payload.message || payload.status || `${label} finished successfully.`,
      })
      await load()
    } catch (error) {
      const detail = error?.response?.data?.detail || error?.message || `${label} failed.`
      setActionNotice({
        kind: 'error',
        title: `${label} failed`,
        message: detail,
      })
      await load()
    } finally {
      setActionLoading(false)
    }
  }

  const initializeDios    = withAction('Initialize DIOs', () => api.post('/api/v1/departments/dios/initialize', { tenant_id: DEFAULT_TENANT }))
  const runBulkReview     = withAction('Bulk council review', () => api.post('/api/v1/departments/milestones/bulk-review', { tenant_id: DEFAULT_TENANT }))
  const runDiscovery      = withAction('Technology discovery', () => api.post('/api/v1/departments/tech/discover', { tenant_id: DEFAULT_TENANT }))
  const runDailyStrategy  = withAction('Daily strategy report', () => api.post('/api/v1/departments/strategy/daily-report', { tenant_id: DEFAULT_TENANT }))
  const runWeeklyStrategy = withAction('Weekly strategy report', () => api.post('/api/v1/departments/strategy/weekly-report', { tenant_id: DEFAULT_TENANT }))

  const busyLoading = loading || actionLoading

  return (
    <div className="h-full min-h-0 overflow-y-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.22em] text-jarvis-cyan/70">Autonomous Intelligence</p>
          <h1 className="mt-2 text-3xl font-bold text-white">Department Intelligence</h1>
          <p className="mt-2 max-w-3xl text-sm text-gray-400">
            25-module autonomous intelligence system — DIOs, Council milestone loop, 24/7 tech evolution, client call intelligence, and strategy oversight.
          </p>
        </div>
        <button onClick={load} disabled={busyLoading}
          className="btn-primary inline-flex items-center justify-center gap-2">
          {busyLoading ? <Loader2 size={15} className="animate-spin" /> : <RefreshCw size={15} />}
          Refresh
        </button>
      </div>

      {actionNotice && (
        <div className={`rounded-2xl border px-4 py-3 text-sm ${
          actionNotice.kind === 'success'
            ? 'border-green-400/30 bg-green-400/10 text-green-100'
            : 'border-red-400/30 bg-red-400/10 text-red-100'
        }`}>
          <p className="font-semibold">{actionNotice.title}</p>
          <p className="mt-1 text-xs leading-relaxed opacity-90">{actionNotice.message}</p>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b border-white/10 pb-0 overflow-x-auto">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button key={id} onClick={() => setActiveTab(id)}
            className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium transition-colors whitespace-nowrap border-b-2 -mb-px ${
              activeTab === id
                ? 'border-jarvis-cyan text-jarvis-cyan'
                : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}>
            <Icon size={14} />
            {label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <motion.div key={activeTab} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
        {activeTab === 'axiom'      && <AxiomTab      axiom={data.axiom} />}
        {activeTab === 'overview'   && <OverviewTab   {...data} />}
        {activeTab === 'dios'       && <DiosTab       dios={data.dios} onInitialize={initializeDios} loading={busyLoading} />}
        {activeTab === 'milestones' && <MilestonesTab milestones={data.milestones} onBulkReview={runBulkReview} loading={busyLoading} />}
        {activeTab === 'tech'       && <TechTab       tech={data.tech} onDiscover={runDiscovery} loading={busyLoading} />}
        {activeTab === 'calls'      && <CallsTab      calls={data.calls} />}
        {activeTab === 'strategy'   && <StrategyTab   strategy={data.strategy} onDailyReport={runDailyStrategy} onWeeklyReport={runWeeklyStrategy} loading={busyLoading} />}
      </motion.div>
    </div>
  )
}
