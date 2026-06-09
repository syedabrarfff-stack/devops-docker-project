import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import {
  AlertTriangle,
  BarChart3,
  Brain,
  BriefcaseBusiness,
  CheckCircle2,
  CheckSquare,
  ChevronDown,
  Clock,
  Cpu,
  Database,
  DollarSign,
  FileText,
  Layers,
  Loader2,
  MessageCircle,
  Network,
  RefreshCw,
  Shield,
  Target,
  Users,
  Zap,
} from 'lucide-react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import api from '../../services/api'
import useJarvisStore from '../../store/useJarvisStore'

const FUNNEL_STATUSES = ['NEW', 'CONTACTED', 'REPLIED', 'DEMO', 'PROPOSAL', 'WON']
const COST_COLORS = ['#00C8FF', '#0057FF', '#FFB700', '#22C55E', '#A855F7', '#F97316', '#EF4444']

function money(value) {
  const n = Number(value || 0)
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `$${(n / 1_000).toFixed(1)}K`
  return `$${n.toLocaleString(undefined, { maximumFractionDigits: 0 })}`
}

function number(value) {
  return Number(value || 0).toLocaleString()
}

function safeArray(value, key) {
  if (Array.isArray(value)) return value
  if (Array.isArray(value?.[key])) return value[key]
  return []
}

function statusIsOk(value) {
  if (!value) return false
  const normalized = String(value.status || value).toLowerCase()
  return ['ok', 'ready', 'operational', 'healthy', 'up'].includes(normalized)
}

function TruthBadge({ source = 'live' }) {
  const styles = {
    live: 'border-green-400/25 bg-green-400/10 text-green-300',
    metric: 'border-jarvis-cyan/25 bg-jarvis-cyan/10 text-jarvis-cyan',
    mixed: 'border-blue-400/25 bg-blue-400/10 text-blue-300',
    doctrine: 'border-amber-300/25 bg-amber-400/10 text-amber-200',
    blocked: 'border-red-400/25 bg-red-400/10 text-red-300',
  }
  const labels = {
    live: 'LIVE DATA',
    metric: 'LIVE METRIC',
    mixed: 'MIXED',
    doctrine: 'DOCTRINE',
    blocked: 'BLOCKED',
  }
  return (
    <span className={`rounded-full border px-2 py-0.5 text-[10px] font-bold tracking-[0.14em] ${styles[source] || styles.live}`}>
      {labels[source] || labels.live}
    </span>
  )
}

function MetricCard({ icon: Icon, label, value, detail, tone = 'cyan', source = 'live', onClick }) {
  const tones = {
    gold: 'border-jarvis-gold/30 text-jarvis-gold bg-jarvis-gold/10',
    cyan: 'border-jarvis-cyan/30 text-jarvis-cyan bg-jarvis-cyan/10',
    blue: 'border-jarvis-blue/30 text-jarvis-blue bg-jarvis-blue/10',
    green: 'border-green-400/30 text-green-300 bg-green-400/10',
    red: 'border-red-400/30 text-red-300 bg-red-400/10',
  }[tone]

  return (
    <motion.button
      type="button"
      onClick={onClick}
      disabled={!onClick}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className={`glass p-5 text-left transition-all ${onClick ? 'hover:border-white/20' : ''}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className={`rounded-xl border p-2.5 ${tones}`}>
          <Icon size={18} />
        </div>
        <div className="flex flex-col items-end gap-2">
          <p className="text-right text-[11px] uppercase tracking-[0.18em] text-gray-500">{label}</p>
          <TruthBadge source={source} />
        </div>
      </div>
      <p className="mt-5 text-3xl font-bold text-white">{value}</p>
      <p className={`mt-2 text-xs ${tone === 'red' ? 'text-red-300' : 'text-gray-400'}`}>{detail}</p>
    </motion.button>
  )
}

function Panel({ title, subtitle, icon: Icon, action, children }) {
  return (
    <section className="glass p-5">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          {Icon && (
            <div className="rounded-lg border border-white/10 bg-white/5 p-2 text-jarvis-cyan">
              <Icon size={15} />
            </div>
          )}
          <div>
            <h2 className="text-sm font-semibold text-white">{title}</h2>
            {subtitle && <p className="mt-1 text-xs text-gray-500">{subtitle}</p>}
          </div>
        </div>
        {action}
      </div>
      {children}
    </section>
  )
}

function EmptyState({ text }) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.03] p-5 text-center text-sm text-gray-500">
      {text}
    </div>
  )
}

function HealthRow({ label, ok, detail, source }) {
  return (
    <div className="flex items-center justify-between rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2.5">
      <div className="flex items-center gap-2">
        {ok ? <CheckCircle2 size={14} className="text-green-400" /> : <AlertTriangle size={14} className="text-red-300" />}
        <span className="text-sm text-white/70">{label}</span>
      </div>
      <div className="flex items-center gap-2">
        {source && <TruthBadge source={source} />}
        <span className={`text-xs ${ok ? 'text-green-300' : 'text-red-300'}`}>{detail}</span>
      </div>
    </div>
  )
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-lg border border-white/10 bg-[#08111f]/95 px-3 py-2 text-xs shadow-xl">
      <p className="mb-1 text-gray-400">{label}</p>
      {payload.map((item) => (
        <p key={item.name} style={{ color: item.color }}>
          {item.name}: {typeof item.value === 'number' ? number(item.value) : item.value}
        </p>
      ))}
    </div>
  )
}

export default function Dashboard() {
  const {
    setActiveView,
    pendingApprovals,
    setPendingApprovals,
    notifications,
    captainQueue,
    systemHealth,
    setSystemHealth,
  } = useJarvisStore()

  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [briefExpanded, setBriefExpanded] = useState(false)
  const [criticalAlert, setCriticalAlert] = useState(null)
  const [dashboardIssues, setDashboardIssues] = useState([])
  const [data, setData] = useState({
    revenue: null,
    mrrChart: [],
    pipeline: null,
    approvals: [],
    leads: [],
    briefing: null,
    ready: null,
    aiHealth: null,
    aiCost: null,
    audit: [],
    catalog: null,
    departments: null,
    council: null,
    aionx: null,
    consciousness: null,
    civilization: null,
    agentOps: null,
    scheduler: null,
    batch1Workflow: null,
    batch1Board: null,
    axiom: null,
    operatingIntelligence: null,
    communication: null,
  })

  const fetchDashboard = useCallback(async ({ soft = false } = {}) => {
    if (soft) setRefreshing(true)
    else setLoading(true)
    setDashboardIssues([])
    try {
      const requests = [
        { key: 'revenue', run: () => api.get('/api/v1/revenue/snapshot') },
        { key: 'mrrChart', run: () => api.get('/api/v1/revenue/mrr-chart', { params: { days: 365 } }) },
        { key: 'pipeline', run: () => api.get('/api/v1/crm/deals/pipeline') },
        { key: 'approvals', run: () => api.get('/api/v1/approvals', { params: { status: 'pending' } }) },
        { key: 'leads', run: () => api.get('/api/v1/leads/', { params: { limit: 50 } }) },
        { key: 'leadStats', run: () => api.get('/api/v1/leads/stats') },
        { key: 'briefing', run: () => api.get('/api/v1/briefing/morning') },
        { key: 'ready', run: () => api.get('/readyz') },
        { key: 'aiHealth', run: () => api.get('/api/v1/ai-ops/health') },
        { key: 'aiCost', run: () => api.get('/api/v1/ai-ops/cost/summary', { params: { days: 7 } }) },
        { key: 'audit', run: () => api.get('/api/v1/ai-ops/audit', { params: { limit: 10 } }) },
        { key: 'catalog', run: () => api.get('/api/v1/catalog/capability-modules') },
        { key: 'departments', run: () => api.get('/api/v1/departments/health') },
        { key: 'council', run: () => api.get('/api/v1/council/status') },
        { key: 'aionx', run: () => api.get('/api/v1/aionx/cortex/operational-iq') },
        { key: 'consciousness', run: () => api.get('/api/v1/consciousness/snapshot') },
        { key: 'civilization', run: () => api.get('/api/v1/civilization/ledger') },
        { key: 'agentOps', run: () => api.get('/api/v1/agent-ops/status') },
        { key: 'scheduler', run: () => api.get('/api/v1/scheduler/jobs') },
        { key: 'batch1Workflow', run: () => api.get('/api/v1/batch1/workflow') },
        { key: 'batch1Board', run: () => api.get('/api/v1/batch1/board') },
        { key: 'axiom', run: () => api.get('/api/v1/departments/axiom/operating-model') },
        { key: 'operatingIntelligence', run: () => api.get('/api/v1/aionx/operating-intelligence') },
        { key: 'communication', run: () => api.get('/api/v1/communication/status') },
      ]

      const results = await Promise.allSettled(requests.map((request) => request.run()))
      const issues = results.flatMap((result, index) => {
        if (result.status === 'fulfilled') return []
        const name = requests[index]?.key || `request-${index + 1}`
        const reason = result.reason?.response?.data?.detail
          || result.reason?.response?.data?.message
          || result.reason?.message
          || 'failed to load'
        return [{ name, reason }]
      })

      const value = (index, fallback = null) => (
        results[index].status === 'fulfilled' ? results[index].value.data : fallback
      )

      const approvals = safeArray(value(3, []), 'approvals')
      setPendingApprovals(approvals.length)
      setSystemHealth(value(7, null))
      setDashboardIssues(issues)

      setData({
        revenue: value(0, null),
        mrrChart: safeArray(value(1, {}), 'points'),
        pipeline: value(2, null),
        approvals,
        leads: safeArray(value(4, []), 'leads'),
        briefing: value(6, null),
        ready: value(7, null),
        aiHealth: value(8, null),
        aiCost: value(9, null),
        audit: safeArray(value(10, {}), 'logs'),
        catalog: value(11, null),
        departments: value(12, null),
        council: value(13, null),
        aionx: value(14, null),
        consciousness: value(15, null),
        civilization: value(16, null),
        agentOps: value(17, null),
        scheduler: value(18, null),
        batch1Workflow: value(19, null),
        batch1Board: value(20, null),
        axiom: value(21, null),
        operatingIntelligence: value(22, null),
        communication: value(23, null),
      })
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [setPendingApprovals, setSystemHealth])

  useEffect(() => {
    fetchDashboard()
    const interval = setInterval(() => fetchDashboard({ soft: true }), 30_000)
    return () => clearInterval(interval)
  }, [fetchDashboard])

  useEffect(() => {
    const newest = notifications.find((item) => ['critical', 'error', 'warning'].includes(item.level))
    if (newest) setCriticalAlert(newest)
  }, [notifications])

  const mrrGrowth = useMemo(() => {
    const points = data.mrrChart.filter((point) => Number(point.mrr_usd || 0) >= 0)
    if (points.length < 2) return 0
    const previous = Number(points[points.length - 2].mrr_usd || 0)
    const current = Number(points[points.length - 1].mrr_usd || 0)
    if (!previous) return current ? 100 : 0
    return ((current - previous) / previous) * 100
  }, [data.mrrChart])

  const topLeads = useMemo(() => (
    [...data.leads]
      .sort((a, b) => Number(b.score || 0) - Number(a.score || 0))
      .slice(0, 5)
  ), [data.leads])

  const funnelData = useMemo(() => {
    const byStatus = data.leads.reduce((acc, lead) => {
      const status = String(lead.status || 'NEW').toUpperCase()
      acc[status] = (acc[status] || 0) + 1
      return acc
    }, {})
    return FUNNEL_STATUSES.map((status) => ({ status, count: byStatus[status] || 0 }))
  }, [data.leads])

  const mrrData = useMemo(() => {
    const points = data.mrrChart.slice(-12).map((point) => ({
      month: String(point.snapshot_date || point.date || '').slice(0, 7) || 'now',
      mrr: Number(point.mrr_usd || 0),
    }))
    if (points.length) return points
    return [{ month: 'current', mrr: Number(data.revenue?.mrr_usd || 0) }]
  }, [data.mrrChart, data.revenue])

  const costData = useMemo(() => {
    const raw = data.aiCost?.by_provider || data.aiCost?.providers || data.aiCost?.provider_costs || {}
    const entries = Object.entries(raw).map(([name, value]) => {
      const amount = typeof value === 'object'
        ? value?.total_cost_usd ?? value?.cost_usd ?? value?.total ?? 0
        : value
      return { name, value: Number(amount || 0) }
    }).filter((item) => item.value > 0)
    return entries.length ? entries : [{ name: 'No spend logged', value: 1, placeholder: true }]
  }, [data.aiCost])

  const apiOk = statusIsOk(data.ready || systemHealth)
  const checks = data.ready?.checks || systemHealth?.checks || {}
  const dbOk = statusIsOk(checks.database)
  const redisOk = statusIsOk(checks.redis) || statusIsOk(systemHealth?.redis) || false
  const aiOk = statusIsOk(checks.ai_providers) || Number(data.aiHealth?.available || 0) > 0
  const queueCount = pendingApprovals || data.approvals.length || captainQueue.length
  const moduleCount = data.catalog?.modules?.length || data.catalog?.capability_modules?.length || data.catalog?.total_modules || 0
  const osLayerCount = data.catalog?.operating_system?.operational_integrity_layers?.length || 0
  const operationalIq = data.aionx?.operational_iq ?? data.aionx?.score ?? data.aionx?.iq ?? 0
  const schedulerJobs = safeArray(data.scheduler, 'jobs')
  const aionxJobCount = schedulerJobs.filter((job) => String(job.id || job.name || '').includes('aionx')).length
  const batch1StageCount = data.batch1Workflow?.stage_count || 0
  const batch1PhaseCount = data.batch1Workflow?.phase_count || 0
  const activePipelines = data.batch1Board?.counts?.active_pipelines || 0
  const axiomDepartmentCount = data.axiom?.counts?.departments || 0
  const adaptiveCycleCount = data.operatingIntelligence?.adaptive_intelligence?.cycle_count || 0
  const techSourceCount = data.operatingIntelligence?.technology_exploration?.source_count || 0
  const dependencyModuleCount = data.operatingIntelligence?.module_dependencies?.module_count || 0
  const liveTableCount = data.operatingIntelligence?.data_backbone?.total_live_tables || 0
  const integrityTeamCount = data.operatingIntelligence?.operational_integrity?.team_count || 0
  const integrityPipelineCount = data.operatingIntelligence?.operational_integrity?.pipeline_stage_count || 0
  const sovereignOrganCount = data.operatingIntelligence?.sovereign_organs?.organ_count || 0
  const ultimateJourneyCount = data.operatingIntelligence?.ultimate_journey?.stage_count || 0
  const sesConnected = !!data.communication?.ses?.connected
  const whatsappConnected = !!data.communication?.whatsapp?.connected
  const communicationLiveCount = [sesConnected, whatsappConnected].filter(Boolean).length

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="glass flex items-center gap-3 px-5 py-4 text-sm text-gray-300">
          <Loader2 size={18} className="animate-spin text-jarvis-cyan" />
          Loading executive dashboard
        </div>
      </div>
    )
  }

  return (
    <div className="h-full min-h-0 overflow-y-auto p-6 pb-24 space-y-6">
      <AnimatePresence>
        {criticalAlert && (
          <motion.div
            initial={{ opacity: 0, y: -12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            className="glass border-red-400/30 bg-red-500/10 p-4"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-start gap-3">
                <AlertTriangle size={18} className="mt-0.5 text-red-300" />
                <div>
                  <p className="text-sm font-semibold text-red-100">Critical event</p>
                  <p className="mt-1 text-sm text-red-100/80">{criticalAlert.message}</p>
                </div>
              </div>
              <button onClick={() => setCriticalAlert(null)} className="text-xs text-red-100/60 hover:text-red-100">
                Dismiss
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {dashboardIssues.length > 0 && (
        <div className="glass border border-amber-400/30 bg-amber-500/10 p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle size={18} className="mt-0.5 text-amber-300" />
            <div>
              <p className="text-sm font-semibold text-amber-100">Partial dashboard load</p>
              <p className="mt-1 text-sm text-amber-100/80">
                {dashboardIssues.length} subsystem{dashboardIssues.length === 1 ? '' : 's'} failed to load, but the dashboard stayed online.
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                {dashboardIssues.slice(0, 6).map((issue) => (
                  <span
                    key={issue.name}
                    className="rounded-full border border-amber-300/20 bg-black/20 px-3 py-1 text-xs text-amber-100/80"
                  >
                    {issue.name}: {issue.reason}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.22em] text-jarvis-cyan/70">Captain Command</p>
          <h1 className="mt-2 text-3xl font-bold text-white">Executive Dashboard</h1>
          <p className="mt-2 max-w-3xl text-sm text-gray-400">
            Revenue, pipeline, alerts, briefing, and system readiness in one operating view.
          </p>
        </div>
        <button
          onClick={() => fetchDashboard({ soft: true })}
          disabled={refreshing}
          className="btn-primary inline-flex items-center gap-2"
        >
          {refreshing ? <Loader2 size={15} className="animate-spin" /> : <RefreshCw size={15} />}
          Refresh
        </button>
      </header>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          icon={DollarSign}
          label="MRR"
          value={money(data.revenue?.mrr_usd)}
          detail={`${mrrGrowth >= 0 ? '+' : ''}${mrrGrowth.toFixed(1)}% vs previous snapshot`}
          tone="gold"
          source="live"
          onClick={() => setActiveView('invoices')}
        />
        <MetricCard
          icon={Users}
          label="Active Clients"
          value={number(data.revenue?.active_clients)}
          detail={`${number(data.revenue?.paid_invoices)} paid invoices`}
          tone="cyan"
          source="live"
          onClick={() => setActiveView('crm')}
        />
        <MetricCard
          icon={BriefcaseBusiness}
          label="Pipeline Value"
          value={money(data.pipeline?.pipeline_value || data.pipeline?.total_value || data.pipeline?.open_value)}
          detail="Open opportunities from CRM"
          tone="blue"
          source="live"
          onClick={() => setActiveView('leads')}
        />
        <MetricCard
          icon={CheckSquare}
          label="Pending Approvals"
          value={number(queueCount)}
          detail={queueCount ? 'Captain decision required' : 'No blocking queue items'}
          tone={queueCount ? 'red' : 'green'}
          source="live"
          onClick={() => setActiveView('approvals')}
        />
        <MetricCard
          icon={Layers}
          label="AIONX Modules"
          value={number(moduleCount)}
          detail={`${osLayerCount} operating layers mapped`}
          tone={moduleCount === 25 ? 'green' : 'red'}
          source="doctrine"
          onClick={() => setActiveView('catalog')}
        />
        <MetricCard
          icon={Brain}
          label="Operational IQ"
          value={Number(operationalIq || 0).toFixed(1)}
          detail={`${aionxJobCount} AIONX heartbeat jobs visible`}
          tone={aionxJobCount ? 'green' : 'red'}
          source="metric"
          onClick={() => setActiveView('aionxArchitecture')}
        />
        <MetricCard
          icon={Zap}
          label="Client Engine"
          value={number(batch1StageCount)}
          detail={`${batch1PhaseCount} phases - ${activePipelines} active pipelines`}
          tone={batch1StageCount === 33 ? 'green' : 'red'}
          source="mixed"
          onClick={() => setActiveView('aionxArchitecture')}
        />
        <MetricCard
          icon={Cpu}
          label="Adaptive Layer"
          value={`${adaptiveCycleCount}/5`}
          detail={`${techSourceCount} watchtower sources | ${dependencyModuleCount} dependency rules`}
          tone={adaptiveCycleCount === 5 ? 'green' : 'red'}
          source="doctrine"
          onClick={() => setActiveView('aionxArchitecture')}
        />
        <MetricCard
          icon={Shield}
          label="Integrity Teams"
          value={number(integrityTeamCount)}
          detail={`${integrityPipelineCount} full pipeline stages guarded`}
          tone={integrityTeamCount === 8 ? 'green' : 'red'}
          source="doctrine"
          onClick={() => setActiveView('aionxArchitecture')}
        />
        <MetricCard
          icon={Network}
          label="Sovereign Organs"
          value={number(sovereignOrganCount)}
          detail={`${ultimateJourneyCount} monitored client journey stages`}
          tone={sovereignOrganCount === 9 ? 'green' : 'red'}
          source="doctrine"
          onClick={() => setActiveView('aionxArchitecture')}
        />
        <MetricCard
          icon={MessageCircle}
          label="Comms"
          value={`${communicationLiveCount}/2`}
          detail={`SES ${sesConnected ? 'live' : 'blocked'} | WhatsApp ${whatsappConnected ? 'paired' : 'pairing'}`}
          tone={communicationLiveCount === 2 ? 'green' : communicationLiveCount === 1 ? 'gold' : 'red'}
          source={communicationLiveCount === 2 ? 'live' : 'blocked'}
          onClick={() => setActiveView('communications')}
        />
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,3fr)_minmax(320px,2fr)]">
        <div className="space-y-6">
          <Panel
            title="JARVIS Operating System"
            subtitle="Canonical 25 modules, departments, councils, consciousness, and automation surfaces"
            icon={Network}
            action={<button onClick={() => setActiveView('catalog')} className="text-xs text-jarvis-cyan hover:text-white">Open catalog</button>}
          >
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
              <HealthRow label="Catalog" ok={moduleCount === 25} detail={`${moduleCount}/25 modules`} source="doctrine" />
              <HealthRow label="Departments" ok={statusIsOk(data.departments)} detail={`${data.departments?.departments_monitored || 0} DIOs`} source="live" />
              <HealthRow label="Council" ok={statusIsOk(data.council)} detail={data.council?.status || 'unknown'} source="live" />
              <HealthRow label="AIONX Cortex" ok={Number(operationalIq) >= 0 && data.aionx} detail={`IQ ${Number(operationalIq || 0).toFixed(1)}`} source="metric" />
              <HealthRow label="Consciousness" ok={statusIsOk(data.consciousness)} detail={`${data.consciousness?.giants_online || 0} giants`} source="doctrine" />
              <HealthRow label="Civilization" ok={!!data.civilization} detail={`${safeArray(data.civilization, 'ledger').length} records`} source="live" />
              <HealthRow label="Agent Ops" ok={statusIsOk(data.agentOps)} detail={data.agentOps?.status || 'unknown'} source="live" />
              <HealthRow label="Scheduler" ok={aionxJobCount > 0} detail={`${aionxJobCount} AIONX jobs`} source="live" />
              <HealthRow label="Client Engine" ok={batch1StageCount === 33} detail={`${batch1StageCount}/33 stages`} source="mixed" />
              <HealthRow label="AXIOM" ok={axiomDepartmentCount === 25} detail={`${axiomDepartmentCount}/25 departments`} source="doctrine" />
              <HealthRow label="Adaptive Intelligence" ok={adaptiveCycleCount === 5} detail={`${adaptiveCycleCount}/5 cycles`} source="doctrine" />
              <HealthRow label="Tech Watchtower" ok={techSourceCount >= 10} detail={`${techSourceCount} sources`} source="doctrine" />
              <HealthRow label="Dependency Resolver" ok={dependencyModuleCount >= 25} detail={`${dependencyModuleCount} modules`} source="doctrine" />
              <HealthRow label="Data Backbone" ok={liveTableCount > 0} detail={`${liveTableCount} tables`} source="live" />
              <HealthRow label="Operational Integrity" ok={integrityTeamCount === 8} detail={`${integrityTeamCount}/8 teams`} source="doctrine" />
              <HealthRow label="18-Stage Pipeline" ok={integrityPipelineCount === 18} detail={`${integrityPipelineCount}/18 stages`} source="doctrine" />
              <HealthRow label="Sovereign Organs" ok={sovereignOrganCount === 9} detail={`${sovereignOrganCount}/9 organs`} source="doctrine" />
              <HealthRow label="Ultimate Journey" ok={ultimateJourneyCount === 33} detail={`${ultimateJourneyCount}/33 stages`} source="doctrine" />
              <HealthRow label="SES Email" ok={sesConnected} detail={data.communication?.ses?.blocker_code || data.communication?.ses?.send_mode || 'unknown'} source={sesConnected ? 'live' : 'blocked'} />
              <HealthRow label="WhatsApp" ok={whatsappConnected} detail={data.communication?.whatsapp?.blocker_code || data.communication?.whatsapp?.status || 'unknown'} source={whatsappConnected ? 'live' : 'blocked'} />
            </div>
          </Panel>

          <Panel
            title="Communication Transport"
            subtitle="AWS SES primary outreach and Bahrain WhatsApp Business relationship layer. Both feed the same AIONX organism."
            icon={MessageCircle}
            action={<button onClick={() => setActiveView('communications')} className="text-xs text-jarvis-cyan hover:text-white">Open Comms</button>}
          >
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <HealthRow
                label="AWS SES"
                ok={sesConnected}
                detail={data.communication?.ses?.required_action || data.communication?.ses?.send_mode || 'unknown'}
                source={sesConnected ? 'live' : 'blocked'}
              />
              <HealthRow
                label="Bahrain WhatsApp"
                ok={whatsappConnected}
                detail={data.communication?.whatsapp?.required_action || data.communication?.whatsapp?.status || 'unknown'}
                source={whatsappConnected ? 'live' : 'blocked'}
              />
            </div>
            <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
              <HealthRow label="Email out" ok={true} detail={`${data.communication?.counts?.EMAIL?.OUTBOUND || 0}`} source="live" />
              <HealthRow label="Email in" ok={true} detail={`${data.communication?.counts?.EMAIL?.INBOUND || 0}`} source="live" />
              <HealthRow label="WA out" ok={true} detail={`${data.communication?.counts?.WHATSAPP?.OUTBOUND || 0}`} source="live" />
              <HealthRow label="WA in" ok={true} detail={`${data.communication?.counts?.WHATSAPP?.INBOUND || 0}`} source="live" />
            </div>
          </Panel>

          <Panel
            title="Living Operating Intelligence"
            subtitle="Adaptive layer, technology watchtower, data backbone, gateway UX, and Captain boundary"
            icon={Cpu}
            action={<button onClick={() => setActiveView('aionxArchitecture')} className="text-xs text-jarvis-cyan hover:text-white">Open full map</button>}
          >
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              {(data.operatingIntelligence?.adaptive_intelligence?.cycles || []).map((cycle) => (
                <div key={cycle.code} className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-white">{cycle.name}</p>
                      <p className="mt-1 text-xs uppercase tracking-[0.18em] text-jarvis-cyan/70">{cycle.cadence}</p>
                    </div>
                    <span className="rounded-full border border-green-400/30 bg-green-400/10 px-2 py-1 text-xs text-green-300">
                      {cycle.authority}
                    </span>
                  </div>
                  <p className="mt-3 line-clamp-2 text-xs text-gray-400">{cycle.purpose}</p>
                </div>
              ))}
            </div>
            <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
              <HealthRow label="Cycles" ok={adaptiveCycleCount === 5} detail={`${adaptiveCycleCount}/5`} />
              <HealthRow label="Watchtower" ok={techSourceCount >= 10} detail={`${techSourceCount} feeds`} />
              <HealthRow label="12-stage pipe" ok={(data.operatingIntelligence?.revenue_pipeline?.stage_count || 0) === 12} detail={`${data.operatingIntelligence?.revenue_pipeline?.stage_count || 0}/12`} />
              <HealthRow label="DB backbone" ok={liveTableCount > 0} detail={`${liveTableCount} tables`} />
              <HealthRow label="Integrity" ok={integrityTeamCount === 8} detail={`${integrityTeamCount}/8 teams`} />
              <HealthRow label="Full pipe" ok={integrityPipelineCount === 18} detail={`${integrityPipelineCount}/18`} />
              <HealthRow label="Organs" ok={sovereignOrganCount === 9} detail={`${sovereignOrganCount}/9`} />
              <HealthRow label="Journey" ok={ultimateJourneyCount === 33} detail={`${ultimateJourneyCount}/33`} />
            </div>
          </Panel>

          <Panel
            title="33-Stage Client Engine"
            subtitle="Discovery, outreach, proposal, onboarding, delivery, success, reputation, and learning"
            icon={Zap}
            action={<button onClick={() => setActiveView('aionxArchitecture')} className="text-xs text-jarvis-cyan hover:text-white">Open AIONX map</button>}
          >
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              {(data.batch1Workflow?.phases || []).map((phase) => (
                <div key={phase.name} className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-white">{phase.name}</p>
                      <p className="mt-1 text-xs text-gray-500">{phase.stage_count} stages live in doctrine</p>
                    </div>
                    <span className="rounded-full border border-jarvis-cyan/30 bg-jarvis-cyan/10 px-2 py-1 text-xs text-jarvis-cyan">
                      {phase.stages?.[0]?.stage}-{phase.stages?.[phase.stages.length - 1]?.stage}
                    </span>
                  </div>
                  <p className="mt-3 line-clamp-2 text-xs text-gray-400">
                    {(phase.stages || []).slice(0, 3).map((stage) => stage.name).join(' - ')}
                  </p>
                </div>
              ))}
            </div>
            <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
              <HealthRow label="Stages" ok={batch1StageCount === 33} detail={`${batch1StageCount}/33`} />
              <HealthRow label="Pipelines" ok={!!data.batch1Board} detail={`${activePipelines} active`} />
              <HealthRow label="Overdue" ok={(data.batch1Board?.counts?.overdue_milestones || 0) === 0} detail={`${data.batch1Board?.counts?.overdue_milestones || 0}`} />
              <HealthRow label="Captain gates" ok={true} detail={(data.batch1Workflow?.authority_boundaries?.captain_required || []).join(', ') || 'none'} />
            </div>
          </Panel>

          <Panel
            title="Today's Pipeline"
            subtitle="Top 5 leads by score with quick actions"
            icon={Target}
            action={<button onClick={() => setActiveView('leads')} className="text-xs text-jarvis-cyan hover:text-white">Open leads</button>}
          >
            {topLeads.length === 0 ? (
              <EmptyState text="No lead records are visible yet." />
            ) : (
              <div className="space-y-3">
                {topLeads.map((lead) => (
                  <div key={lead.id} className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
                    <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                      <div>
                        <p className="font-semibold text-white">{lead.company || lead.company_name || 'Unnamed company'}</p>
                        <p className="mt-1 text-xs text-gray-400">
                          {[lead.industry, lead.country, lead.contact_name].filter(Boolean).join(' | ') || 'No enrichment summary yet'}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="rounded-full border border-jarvis-gold/30 bg-jarvis-gold/10 px-3 py-1 text-xs font-semibold text-jarvis-gold">
                          Score {Number(lead.score || 0).toFixed(0)}
                        </span>
                        <button onClick={() => setActiveView('proposals')} className="btn-primary py-1.5 text-xs">
                          Proposal
                        </button>
                        <button onClick={() => setActiveView('outreach')} className="btn-primary py-1.5 text-xs">
                          Outreach
                        </button>
                      </div>
                    </div>
                    {lead.pain_points?.length > 0 && (
                      <p className="mt-3 text-xs text-gray-400">Pain points: {lead.pain_points.slice(0, 3).join(', ')}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </Panel>

          <Panel
            title="Recent Activity"
            subtitle="Last 10 AI/audit events available to the frontend"
            icon={Clock}
          >
            {data.audit.length === 0 ? (
              <EmptyState text="No recent audit records returned yet." />
            ) : (
              <div className="space-y-2">
                {data.audit.slice(0, 10).map((item, index) => (
                  <div key={item.id || index} className="flex items-start justify-between gap-4 rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3">
                    <div>
                      <p className="text-sm text-white/80">{item.task_type || item.provider || item.action || 'System activity'}</p>
                      <p className="mt-1 text-xs text-gray-500">
                        {item.model || item.endpoint || item.status || 'No details'} {item.latency_ms ? `| ${item.latency_ms}ms` : ''}
                      </p>
                    </div>
                    <span className={`text-xs ${item.success === false ? 'text-red-300' : 'text-green-300'}`}>
                      {item.success === false ? 'failed' : 'ok'}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </Panel>
        </div>

        <div className="space-y-6">
          <Panel
            title="Morning Briefing"
            subtitle={data.briefing?.generated_at ? `Generated ${new Date(data.briefing.generated_at).toLocaleString()}` : 'Latest briefing'}
            icon={FileText}
            action={
              <button onClick={() => setBriefExpanded((current) => !current)} className="text-gray-400 hover:text-white">
                <ChevronDown size={16} className={`transition-transform ${briefExpanded ? 'rotate-180' : ''}`} />
              </button>
            }
          >
            <div className={`overflow-hidden text-sm leading-6 text-gray-300 ${briefExpanded ? '' : 'max-h-40'}`}>
              {data.briefing?.briefing || 'Morning briefing is not available yet.'}
            </div>
            {!briefExpanded && data.briefing?.briefing && (
              <button onClick={() => setBriefExpanded(true)} className="mt-3 text-xs text-jarvis-cyan hover:text-white">
                Expand briefing
              </button>
            )}
          </Panel>

          <Panel title="System Health" subtitle="API, database, Redis, and AI readiness" icon={Shield}>
            <div className="space-y-2">
              <HealthRow label="API" ok={apiOk} detail={data.ready?.status || 'unknown'} />
              <HealthRow label="Database" ok={dbOk} detail={checks.database?.latency_ms ? `${checks.database.latency_ms}ms` : checks.database?.status || 'unknown'} />
              <HealthRow label="Redis" ok={redisOk} detail={checks.redis?.status || systemHealth?.redis?.status || 'not reported'} />
              <HealthRow
                label="AI Providers"
                ok={aiOk}
                detail={`${data.aiHealth?.available ?? checks.ai_providers?.available ?? 0}/${data.aiHealth?.total_providers ?? checks.ai_providers?.total ?? 0}`}
              />
            </div>
          </Panel>

          <Panel
            title="Captain Queue"
            subtitle="Pending approvals and high-authority decisions"
            icon={CheckSquare}
            action={<button onClick={() => setActiveView('approvals')} className="text-xs text-jarvis-cyan hover:text-white">Open queue</button>}
          >
            <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
              <p className={`text-4xl font-bold ${queueCount ? 'text-red-300' : 'text-green-300'}`}>{queueCount}</p>
              <p className="mt-2 text-sm text-gray-400">
                {queueCount ? 'Items are waiting for Captain review.' : 'No approvals are blocking execution.'}
              </p>
            </div>
            {data.approvals.slice(0, 3).map((approval) => (
              <div key={approval.id} className="mt-3 rounded-xl border border-white/10 bg-white/[0.03] p-3">
                <p className="text-sm font-medium text-white">{approval.title}</p>
                <p className="mt-1 line-clamp-2 text-xs text-gray-500">{approval.summary}</p>
              </div>
            ))}
          </Panel>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <Panel title="MRR Trend" subtitle="Last 12 available snapshots" icon={BarChart3}>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={mrrData}>
                <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
                <XAxis dataKey="month" tick={{ fill: '#94A3B8', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#94A3B8', fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={money} />
                <Tooltip content={<CustomTooltip />} />
                <Line type="monotone" dataKey="mrr" name="MRR" stroke="#FFB700" strokeWidth={3} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Panel>

        <Panel title="Lead Funnel" subtitle="Visible lead stages" icon={Target}>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={funnelData}>
                <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
                <XAxis dataKey="status" tick={{ fill: '#94A3B8', fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#94A3B8', fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="count" name="Leads" radius={[6, 6, 0, 0]} fill="#00C8FF" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>

        <Panel title="AI Cost Breakdown" subtitle="Provider spend, last 7 days" icon={Database}>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={costData}
                  dataKey="value"
                  nameKey="name"
                  innerRadius={52}
                  outerRadius={86}
                  paddingAngle={3}
                >
                  {costData.map((entry, index) => (
                    <Cell key={entry.name} fill={entry.placeholder ? 'rgba(255,255,255,0.16)' : COST_COLORS[index % COST_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {costData.map((entry, index) => (
              <span key={entry.name} className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-xs text-gray-300">
                <span className="mr-1 inline-block h-2 w-2 rounded-full" style={{ background: entry.placeholder ? 'rgba(255,255,255,0.16)' : COST_COLORS[index % COST_COLORS.length] }} />
                {entry.name}: {entry.placeholder ? '$0' : money(entry.value)}
              </span>
            ))}
          </div>
        </Panel>
      </div>
    </div>
  )
}
