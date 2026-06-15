import React, { useCallback, useEffect, useMemo, useState } from 'react'
import {
  AlertTriangle,
  CheckCircle2,
  DollarSign,
  RefreshCw,
  Target,
  TrendingUp,
  Users,
} from 'lucide-react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import api from '../../services/api'
import {
  ActionCard,
  DEFAULT_TENANT,
  FrontierShell,
  Input,
  ResultBox,
  RunButton,
} from './FrontierShell'

const STAGE_COLORS = {
  PROPOSAL: '#22C55E',
  DEMO: '#3B82F6',
  REPLIED: '#8B5CF6',
  CONTACTED: '#F59E0B',
  NURTURE: '#F97316',
  NEW: '#6B7280',
  WON: '#10B981',
  LOST: '#EF4444',
}

function money(v) {
  const n = Number(v || 0)
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `$${(n / 1_000).toFixed(1)}K`
  return `$${n.toLocaleString()}`
}

function pct(v) { return `${Number(v || 0).toFixed(1)}%` }

function ScoreRing({ score, size = 80 }) {
  const r = 30
  const circ = 2 * Math.PI * r
  const fill = (score / 100) * circ
  const color = score >= 70 ? '#22C55E' : score >= 40 ? '#F59E0B' : '#EF4444'
  return (
    <svg width={size} height={size} viewBox="0 0 80 80">
      <circle cx="40" cy="40" r={r} fill="none" stroke="#ffffff10" strokeWidth="8" />
      <circle
        cx="40" cy="40" r={r} fill="none"
        stroke={color} strokeWidth="8"
        strokeDasharray={`${fill} ${circ - fill}`}
        strokeLinecap="round"
        transform="rotate(-90 40 40)"
      />
      <text x="40" y="44" textAnchor="middle" fontSize="14" fontWeight="bold" fill={color}>
        {Math.round(score)}
      </text>
    </svg>
  )
}

function MetricCard({ icon: Icon, label, value, sub, color = 'text-white' }) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/5 p-4 space-y-1">
      <div className="flex items-center gap-2 text-xs text-white/50 uppercase tracking-widest">
        {Icon && <Icon className="h-3.5 w-3.5" />}
        {label}
      </div>
      <p className={`text-2xl font-bold font-mono ${color}`}>{value}</p>
      {sub && <p className="text-xs text-white/40">{sub}</p>}
    </div>
  )
}

function AlertBanner({ alert }) {
  const styles = {
    high: 'border-red-500/40 bg-red-500/10 text-red-300',
    medium: 'border-amber-400/40 bg-amber-400/10 text-amber-200',
    info: 'border-green-400/40 bg-green-400/10 text-green-300',
  }
  const Icon = alert.severity === 'info' ? CheckCircle2 : AlertTriangle
  return (
    <div className={`flex items-start gap-2 rounded border px-3 py-2 text-xs ${styles[alert.severity] || styles.info}`}>
      <Icon className="mt-0.5 h-3.5 w-3.5 shrink-0" />
      <span>{alert.message}</span>
    </div>
  )
}

function WarRoomPanel({ data, loading, error, onRefresh }) {
  if (loading) return (
    <div className="flex items-center justify-center py-12 text-white/40 text-sm gap-2">
      <RefreshCw className="h-4 w-4 animate-spin" />
      Loading Revenue Command Center…
    </div>
  )
  if (error) return (
    <div className="rounded border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
      {error}
    </div>
  )
  if (!data) return null

  const { arr, pipeline, health, retention, alerts, executive_score } = data
  const forecastPoints = []

  return (
    <div className="space-y-5">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <ScoreRing score={executive_score || 0} />
          <div>
            <p className="text-sm font-semibold text-white">Executive Score</p>
            <p className="text-xs text-white/40">Composite revenue health index</p>
          </div>
        </div>
        <button
          onClick={onRefresh}
          className="flex items-center gap-1.5 rounded border border-white/10 px-3 py-1.5 text-xs text-white/60 hover:border-white/20 hover:text-white/80"
        >
          <RefreshCw className="h-3 w-3" />
          Refresh
        </button>
      </div>

      {/* Key metrics */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <MetricCard
          icon={DollarSign} label="MRR"
          value={money(arr?.mrr_usd)} sub={`ARR ${money(arr?.arr_usd)}`}
          color="text-green-300"
        />
        <MetricCard
          icon={Target} label="ARR Progress"
          value={pct(arr?.arr_progress_pct)} sub="toward $1M ARR target"
          color={arr?.arr_progress_pct >= 50 ? 'text-green-300' : 'text-amber-300'}
        />
        <MetricCard
          icon={TrendingUp} label="Pipeline"
          value={money(pipeline?.weighted_pipeline_usd)} sub={`${pipeline?.total_leads || 0} leads`}
          color="text-blue-300"
        />
        <MetricCard
          icon={Users} label="Active Clients"
          value={arr?.active_clients || 0}
          sub={`Retention ${pct(retention?.overall_retention_pct)}`}
          color="text-purple-300"
        />
      </div>

      {/* Cash health row */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <MetricCard
          icon={DollarSign} label="Collected"
          value={money(health?.total_collected_usd)} sub={`${pct(health?.collection_rate_pct)} rate`}
          color="text-green-400"
        />
        <MetricCard
          icon={AlertTriangle} label="Outstanding"
          value={money(health?.outstanding_usd)}
          sub={`${health?.overdue_count || 0} overdue`}
          color={health?.overdue_count > 0 ? 'text-red-400' : 'text-white'}
        />
        <MetricCard
          label="Cash Score"
          value={`${health?.cash_score || 0}/100`}
          sub="collection health"
          color={health?.cash_score >= 70 ? 'text-green-300' : 'text-amber-300'}
        />
      </div>

      {/* Pipeline chart */}
      {Array.isArray(pipeline?.stages) && pipeline.stages.length > 0 && (
        <div className="rounded-lg border border-white/10 bg-white/5 p-4">
          <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-white/50">
            Pipeline by Stage
          </p>
          <ResponsiveContainer width="100%" height={160}>
            <BarChart data={pipeline.stages} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" />
              <XAxis dataKey="stage" tick={{ fill: '#ffffff60', fontSize: 10 }} />
              <YAxis tick={{ fill: '#ffffff60', fontSize: 10 }} />
              <Tooltip
                contentStyle={{ background: '#0F172A', border: '1px solid #ffffff20', borderRadius: 8, fontSize: 12 }}
                formatter={(v, name) => [name === 'weighted_value_usd' ? money(v) : v, name === 'weighted_value_usd' ? 'Weighted $' : 'Leads']}
              />
              <Bar dataKey="count" name="Leads" radius={[3, 3, 0, 0]}>
                {pipeline.stages.map((entry) => (
                  <Cell key={entry.stage} fill={STAGE_COLORS[entry.stage] || '#6B7280'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Alerts */}
      {Array.isArray(alerts) && alerts.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-widest text-white/50">Alerts</p>
          {alerts.map((a, i) => <AlertBanner key={i} alert={a} />)}
        </div>
      )}
    </div>
  )
}

export default function RevenueIntelligence() {
  const [serviceType, setServiceType] = useState('ai_automation')
  const [pricingResult, setPricingResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [warRoom, setWarRoom] = useState(null)
  const [warRoomLoading, setWarRoomLoading] = useState(false)
  const [warRoomError, setWarRoomError] = useState(null)
  const [segmentBy, setSegmentBy] = useState('industry')

  const endpoints = useMemo(() => [
    { key: 'warRoom', label: 'War room (all metrics)', path: '/api/v1/revenue/war-room', params: { tenant_id: DEFAULT_TENANT } },
    { key: 'arr', label: 'ARR & $1M progress', path: '/api/v1/revenue/arr', params: { tenant_id: DEFAULT_TENANT } },
    { key: 'pipeline', label: 'Weighted pipeline', path: '/api/v1/revenue/pipeline', params: { tenant_id: DEFAULT_TENANT } },
    { key: 'forecast', label: '90-day forecast', path: '/api/v1/revenue/forecast', params: { tenant_id: DEFAULT_TENANT, days: 90 } },
    { key: 'health', label: 'Cash health', path: '/api/v1/revenue/health', params: { tenant_id: DEFAULT_TENANT } },
    { key: 'cohorts', label: 'Retention cohorts', path: '/api/v1/revenue/cohorts', params: { tenant_id: DEFAULT_TENANT } },
    { key: 'clients', label: 'Client breakdown', path: '/api/v1/revenue/clients', params: { tenant_id: DEFAULT_TENANT, status: 'ACTIVE' } },
    { key: 'segments', label: 'Revenue segments', path: '/api/v1/revenue/segments', params: { tenant_id: DEFAULT_TENANT, by: segmentBy } },
    { key: 'snapshot', label: 'Legacy snapshot', path: '/api/v1/revenue/snapshot', params: { tenant_id: DEFAULT_TENANT } },
    { key: 'mrr', label: 'MRR history', path: '/api/v1/revenue/mrr-chart', params: { tenant_id: DEFAULT_TENANT, days: 90 } },
  ], [segmentBy])

  const loadWarRoom = useCallback(async () => {
    setWarRoomLoading(true)
    setWarRoomError(null)
    try {
      const res = await api.get('/api/v1/revenue/war-room', { params: { tenant_id: DEFAULT_TENANT } })
      setWarRoom(res.data)
    } catch (err) {
      setWarRoomError(err.response?.data?.detail || err.message)
    }
    setWarRoomLoading(false)
  }, [])

  useEffect(() => { loadWarRoom() }, [loadWarRoom])

  async function calculatePricing(event) {
    event.preventDefault()
    setLoading(true)
    try {
      const response = await api.post('/api/v1/intelligence/dynamic-pricing', {
        tenant_id: DEFAULT_TENANT,
        service_type: serviceType,
        context: { source: 'revenue_intelligence_room' },
      })
      setPricingResult(response.data)
    } catch (error) {
      setPricingResult({ error: error.response?.data?.detail || error.message })
    }
    setLoading(false)
  }

  return (
    <FrontierShell
      eyebrow="Revenue"
      title="Revenue Command Center"
      description="ARR progress, weighted pipeline, cash health, retention cohorts, and segment breakdowns — all live from the JARVIS data layer."
      endpoints={endpoints}
    >
      {() => (
        <div className="space-y-6">
          {/* Live war room panel */}
          <WarRoomPanel
            data={warRoom}
            loading={warRoomLoading}
            error={warRoomError}
            onRefresh={loadWarRoom}
          />

          {/* Action cards */}
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            <ActionCard
              title="Dynamic Pricing Check"
              subtitle="Use after a prospect is serious. Not for first outreach."
            >
              <form onSubmit={calculatePricing} className="space-y-3">
                <Input value={serviceType} onChange={setServiceType} placeholder="Service type, e.g. ai_automation" />
                <RunButton loading={loading} disabled={!serviceType.trim()}>Calculate</RunButton>
              </form>
            </ActionCard>
            <ActionCard title="Latest Pricing Result" subtitle="Revenue result from the dynamic pricing engine.">
              <ResultBox result={pricingResult} />
            </ActionCard>
          </div>
        </div>
      )}
    </FrontierShell>
  )
}
