import React, { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Zap, Brain, CheckSquare, Users, TrendingUp, Activity, Globe, Clock } from 'lucide-react'
import { getHealth, getSystemStatus, getPendingCount } from '../../services/api'
import useJarvisStore from '../../store/useJarvisStore'

const StatCard = ({ icon: Icon, label, value, sub, color = 'blue', delay = 0 }) => {
  const colors = {
    blue:   { ring: 'border-jarvis-blue/20',  bg: 'bg-jarvis-blue/10',   text: 'text-jarvis-blue' },
    purple: { ring: 'border-jarvis-purple/20', bg: 'bg-jarvis-purple/10', text: 'text-purple-400' },
    green:  { ring: 'border-green-400/20',     bg: 'bg-green-400/10',     text: 'text-green-400' },
    amber:  { ring: 'border-amber-400/20',     bg: 'bg-amber-400/10',     text: 'text-amber-400' },
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
  { city: 'New York',  tz: 'America/New_York' },
  { city: 'London',    tz: 'Europe/London' },
  { city: 'Sydney',    tz: 'Australia/Sydney' },
  { city: 'Dubai',     tz: 'Asia/Dubai' },
]

export default function Dashboard() {
  const { setProviders, setPendingApprovals } = useJarvisStore()
  const [health, setHealth] = useState(null)
  const [status, setStatus] = useState(null)
  const [times, setTimes]   = useState({})

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [h, s, p] = await Promise.all([getHealth(), getSystemStatus(), getPendingCount()])
        setHealth(h)
        setStatus(s)
        setPendingApprovals(p.pending || 0)
        setProviders(h.ai_providers || {})
      } catch {}
    }
    fetchData()

    const updateTimes = () => {
      const now = new Date()
      const t = {}
      ZONES.forEach(({ city, tz }) => {
        t[city] = now.toLocaleTimeString('en-US', { timeZone: tz, hour: '2-digit', minute: '2-digit', hour12: true })
      })
      setTimes(t)
    }
    updateTimes()
    const ticker = setInterval(updateTimes, 10000)
    return () => clearInterval(ticker)
  }, [])

  const aiAvailable = health?.ai_providers?.available ?? 0
  const aiTotal     = health?.ai_providers?.total ?? 0

  return (
    <div className="p-6 space-y-6 overflow-y-auto h-full no-scrollbar">
      {/* Hero greeting */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass p-6 border border-jarvis-blue/15 glow-blue"
      >
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">
              Good day, <span className="text-jarvis-blue text-glow">Captain.</span>
            </h1>
            <p className="text-white/50 text-sm mt-1">
              JARVIS is online — all systems operational. Aliyar Solutions AI OS v1.0
            </p>
          </div>
          <div className="text-right">
            <div className="flex items-center gap-2 justify-end">
              <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
              <span className="text-xs text-green-400 font-medium">OPERATIONAL</span>
            </div>
            <p className="text-xs text-white/30 mt-1 font-mono">
              {aiAvailable}/{aiTotal} AI providers active
            </p>
          </div>
        </div>
      </motion.div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard icon={Brain}       label="AI Providers Active"  value={`${aiAvailable}/${aiTotal}`} sub="providers" color="blue"   delay={0.05} />
        <StatCard icon={CheckSquare} label="Pending Approvals"    value={status?.pending_approvals ?? '—'} sub="queue"    color="amber"  delay={0.10} />
        <StatCard icon={Users}       label="AI Agents Available"  value="22"  sub="agents"    color="purple" delay={0.15} />
        <StatCard icon={TrendingUp}  label="Workflows Automated"  value="∞"   sub="capability" color="green"  delay={0.20} />
      </div>

      {/* Providers + World clock */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* AI Providers */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.25 }}
          className="glass p-5"
        >
          <div className="flex items-center gap-2 mb-4">
            <Brain size={15} className="text-jarvis-blue" />
            <span className="text-sm font-semibold text-white/70">AI Intelligence Network</span>
          </div>
          <div className="grid grid-cols-2 gap-2">
            {(health?.ai_providers?.active || [
              'Claude Sonnet', 'GPT-4o', 'Gemini Pro', 'DeepSeek', 'Llama 3.3', 'Groq',
            ]).map((name) => (
              <div key={name} className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/[0.03] border border-white/[0.06]">
                <span className="w-1.5 h-1.5 rounded-full bg-green-400 shadow-[0_0_6px_#4ade80]" />
                <span className="text-xs text-white/60 font-mono">{name}</span>
              </div>
            ))}
          </div>
        </motion.div>

        {/* World clock */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.30 }}
          className="glass p-5"
        >
          <div className="flex items-center gap-2 mb-4">
            <Globe size={15} className="text-jarvis-blue" />
            <span className="text-sm font-semibold text-white/70">Target Markets — Live Time</span>
          </div>
          <div className="space-y-3">
            {ZONES.map(({ city }) => (
              <div key={city} className="flex items-center justify-between px-3 py-2.5
                                         rounded-lg bg-white/[0.03] border border-white/[0.04]">
                <div className="flex items-center gap-2">
                  <Clock size={13} className="text-white/30" />
                  <span className="text-sm text-white/60">{city}</span>
                </div>
                <span className="font-mono text-sm text-jarvis-blue">{times[city] || '—'}</span>
              </div>
            ))}
          </div>
        </motion.div>
      </div>

      {/* Quick actions */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.35 }}
        className="glass p-5"
      >
        <div className="flex items-center gap-2 mb-4">
          <Zap size={15} className="text-jarvis-blue" />
          <span className="text-sm font-semibold text-white/70">Phase 2 Preview — Coming Soon</span>
        </div>
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: 'Lead Generation Engine',     sub: 'Phase 2' },
            { label: 'CRM Integration Hub',        sub: 'Phase 2' },
            { label: 'Outreach Automation',        sub: 'Phase 2' },
            { label: 'Reporting Dashboard',        sub: 'Phase 2' },
            { label: 'Contract Management',        sub: 'Phase 2' },
            { label: 'Revenue Intelligence',       sub: 'Phase 2' },
          ].map(({ label, sub }) => (
            <div key={label}
                 className="px-4 py-3 rounded-lg bg-white/[0.02] border border-white/[0.06]
                            text-center opacity-50 cursor-not-allowed">
              <p className="text-xs text-white/50">{label}</p>
              <p className="text-[10px] text-white/25 mt-1 font-mono">{sub}</p>
            </div>
          ))}
        </div>
      </motion.div>
    </div>
  )
}
