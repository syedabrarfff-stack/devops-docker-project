import React, { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import {
  Activity,
  AlertTriangle,
  Brain,
  CheckSquare,
  Clock,
  DollarSign,
  FileText,
  Globe,
  Mail,
  RefreshCw,
  TrendingUp,
  Users,
  Zap,
} from 'lucide-react'
import {
  getHealth,
  getPendingCount,
  getRevenueDashboard,
  getSystemStatus,
  runRevenueEngine,
} from '../../services/api'
import useJarvisStore from '../../store/useJarvisStore'

const StatCard = ({ icon: Icon, label, value, sub, color = 'blue', delay = 0 }) => {
  const colors = {
    blue: { ring: 'border-jarvis-blue/20', bg: 'bg-jarvis-blue/10', text: 'text-jarvis-blue' },
    purple: { ring: 'border-jarvis-purple/20', bg: 'bg-jarvis-purple/10', text: 'text-purple-400' },
    green: { ring: 'border-green-400/20', bg: 'bg-green-400/10', text: 'text-green-400' },
    amber: { ring: 'border-amber-400/20', bg: 'bg-amber-400/10', text: 'text-amber-400' },
  }
  const c = colors[color]
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.4 }}
      className={`glass p-5 border ${c.ring}`}
    >
      <div className="flex items-start justify-between">
        <div className={`p-2.5 rounded-lg ${c.bg}`}>
          <Icon size={18} className={c.text} />
        </div>
        <span className="text-[10px] text-white/30 font-mono uppercase tracking-wider">{sub}</span>
      </div>
      <p className={`text-3xl font-bold mt-3 ${c.text}`}>{value}</p>
      <p className="text-xs text-white/40 mt-1">{label}</p>
    </motion.div>
  )
}

const ZONES = [
  { city: 'New York', tz: 'America/New_York' },
  { city: 'London', tz: 'Europe/London' },
  { city: 'Sydney', tz: 'Australia/Sydney' },
  { city: 'Dubai', tz: 'Asia/Dubai' },
]

export default function Dashboard() {
  const { setProviders, setPendingApprovals } = useJarvisStore()
  const [health, setHealth] = useState(null)
  const [status, setStatus] = useState(null)
  const [revenue, setRevenue] = useState(null)
  const [runningEngine, setRunningEngine] = useState(false)
  const [times, setTimes] = useState({})

  const fetchData = async () => {
    const [h, s, p, r] = await Promise.all([
      getHealth(),
      getSystemStatus(),
      getPendingCount(),
      getRevenueDashboard(),
    ])
    setHealth(h)
    setStatus(s)
    setRevenue(r)
    setPendingApprovals(p.pending || 0)
    setProviders(h.ai_providers || {})
  }

  useEffect(() => {
    fetchData().catch(() => {})

    const updateTimes = () => {
      const now = new Date()
      const t = {}
      ZONES.forEach(({ city, tz }) => {
        t[city] = now.toLocaleTimeString('en-US', {
          timeZone: tz,
          hour: '2-digit',
          minute: '2-digit',
          hour12: true,
        })
      })
      setTimes(t)
    }
    updateTimes()
    const ticker = setInterval(updateTimes, 10000)
    return () => clearInterval(ticker)
  }, [])

  const runEngine = async () => {
    setRunningEngine(true)
    try {
      await runRevenueEngine({ limit: 25, create_proposals: true })
      await fetchData()
    } finally {
      setRunningEngine(false)
    }
  }

  const aiAvailable = health?.ai_providers?.available ?? 0
  const aiTotal = health?.ai_providers?.total ?? 0
  const money = (n) => `$${Number(n || 0).toLocaleString()}`
  const activity = revenue?.engine?.overnight_activity?.length
    ? revenue.engine.overnight_activity
    : revenue?.engine?.activity_log || []

  return (
    <div className="p-3 sm:p-4 md:p-6 space-y-4 md:space-y-6 overflow-y-auto h-full no-scrollbar">
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass p-4 md:p-6 border border-jarvis-blue/15 glow-blue"
      >
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0">
            <h1 className="text-xl md:text-2xl font-bold text-white leading-tight">
              Good day, <span className="text-jarvis-blue text-glow">Captain.</span>
            </h1>
            <p className="text-white/50 text-sm mt-1">
              JARVIS is online. Revenue engine, approvals, and production systems are being watched.
            </p>
          </div>
          <div className="text-left sm:text-right">
            <div className="flex items-center gap-2 sm:justify-end">
              <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
              <span className="text-xs text-green-400 font-medium">OPERATIONAL</span>
            </div>
            <p className="text-xs text-white/30 mt-1 font-mono">
              {aiAvailable}/{aiTotal} AI providers active
            </p>
          </div>
        </div>
      </motion.div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3 md:gap-4">
        <StatCard icon={Users} label="Leads Discovered This Week" value={revenue?.leads?.this_week ?? '-'} sub={`${revenue?.leads?.total ?? 0} total`} color="blue" delay={0.05} />
        <StatCard icon={FileText} label="Draft Proposals" value={revenue?.proposals?.draft ?? '-'} sub={`${revenue?.proposals?.sent ?? 0} sent`} color="purple" delay={0.1} />
        <StatCard icon={Mail} label="Reply Rate" value={`${revenue?.outreach?.reply_rate ?? 0}%`} sub={`${revenue?.outreach?.sent ?? 0} sent`} color="green" delay={0.15} />
        <StatCard icon={DollarSign} label="Weighted Revenue Forecast" value={money(revenue?.revenue_forecast?.weighted_forecast)} sub="forecast" color="amber" delay={0.2} />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3 md:gap-4">
        <StatCard icon={TrendingUp} label="Pipeline Value" value={money(revenue?.revenue_forecast?.pipeline_value)} sub="open deals" color="green" delay={0.05} />
        <StatCard icon={CheckSquare} label="Pending Approvals" value={revenue?.approvals?.pending ?? status?.pending_approvals ?? '-'} sub="queue" color="amber" delay={0.1} />
        <StatCard icon={Activity} label="Outreach Drafts Ready" value={revenue?.outreach?.drafted ?? '-'} sub="review" color="blue" delay={0.15} />
        <StatCard icon={Brain} label="AI Providers Active" value={`${aiAvailable}/${aiTotal}`} sub="providers" color="purple" delay={0.2} />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.22 }}
        className="glass p-4 md:p-5 border border-white/[0.06]"
      >
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <Zap size={15} className="text-jarvis-blue" />
              <span className="text-sm font-semibold text-white/75">Revenue Engine Control</span>
            </div>
            <p className="text-xs text-white/40 mt-1">
              Apollo: {revenue?.engine?.apollo_ready ? 'ready' : 'blocked'} | Gmail: {revenue?.engine?.gmail_ready ? 'ready' : 'blocked'} | Approval gated
            </p>
          </div>
          <button
            onClick={runEngine}
            disabled={runningEngine}
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-jarvis-blue/15 hover:bg-jarvis-blue/25 disabled:opacity-50 border border-jarvis-blue/25 px-4 py-2 text-sm text-jarvis-blue"
          >
            <RefreshCw size={15} className={runningEngine ? 'animate-spin' : ''} />
            {runningEngine ? 'Running Engine' : 'Run Revenue Engine'}
          </button>
        </div>

        {!!revenue?.engine?.blockers?.length && (
          <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-2">
            {revenue.engine.blockers.map((blocker) => (
              <div key={blocker} className="flex gap-2 rounded-lg border border-amber-400/15 bg-amber-400/5 px-3 py-2">
                <AlertTriangle size={14} className="text-amber-400 mt-0.5 shrink-0" />
                <p className="text-xs leading-5 text-amber-100/75">{blocker}</p>
              </div>
            ))}
          </div>
        )}
      </motion.div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 md:gap-6">
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.25 }}
          className="glass p-4 md:p-5"
        >
          <div className="flex items-center gap-2 mb-4">
            <Brain size={15} className="text-jarvis-blue" />
            <span className="text-sm font-semibold text-white/70">AI Intelligence Network</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {(health?.ai_providers?.active || []).map((name) => (
              <div key={name} className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/[0.03] border border-white/[0.06]">
                <span className="w-1.5 h-1.5 rounded-full bg-green-400 shadow-[0_0_6px_#4ade80]" />
                <span className="text-xs text-white/60 font-mono">{name}</span>
              </div>
            ))}
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.3 }}
          className="glass p-4 md:p-5"
        >
          <div className="flex items-center gap-2 mb-4">
            <Globe size={15} className="text-jarvis-blue" />
            <span className="text-sm font-semibold text-white/70">Target Markets - Live Time</span>
          </div>
          <div className="space-y-3">
            {ZONES.map(({ city }) => (
              <div key={city} className="flex items-center justify-between px-3 py-2.5 rounded-lg bg-white/[0.03] border border-white/[0.04]">
                <div className="flex items-center gap-2">
                  <Clock size={13} className="text-white/30" />
                  <span className="text-sm text-white/60">{city}</span>
                </div>
                <span className="font-mono text-sm text-jarvis-blue">{times[city] || '-'}</span>
              </div>
            ))}
          </div>
        </motion.div>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.35 }}
        className="glass p-4 md:p-5"
      >
        <div className="flex items-center gap-2 mb-4">
          <Activity size={15} className="text-jarvis-blue" />
          <span className="text-sm font-semibold text-white/70">Overnight Engine Activity</span>
        </div>
        <div className="space-y-2">
          {activity.slice(0, 6).map((item) => (
            <div key={item.id} className="px-3 py-3 rounded-lg bg-white/[0.03] border border-white/[0.05]">
              <div className="flex items-start justify-between gap-3">
                <p className="text-sm text-white/70">{item.title}</p>
                <span className="text-[10px] text-white/30 font-mono shrink-0">{item.level}</span>
              </div>
              <p className="text-xs text-white/40 mt-1 leading-5">{item.body}</p>
            </div>
          ))}
          {!activity.length && (
            <div className="px-3 py-3 rounded-lg bg-white/[0.02] border border-white/[0.05]">
              <p className="text-xs text-white/40">No activity logged yet. Run the revenue engine once to create the first operating report.</p>
            </div>
          )}
        </div>
      </motion.div>
    </div>
  )
}
