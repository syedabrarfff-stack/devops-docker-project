import React, { useEffect, useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Brain, CheckSquare, TrendingUp, Globe, Clock, Zap,
  Mail, Users, Target, Activity, RefreshCw, Volume2,
  AlertCircle, CheckCircle, XCircle, Loader
} from 'lucide-react'
import {
  getHealth, getPendingCount, getLeadStats,
  getGmailStats, getJarvisGreeting, getJarvisAIHealth,
  getJarvisVoiceBrief,
} from '../../services/api'
import voiceService from '../../services/voice'
import useJarvisStore from '../../store/useJarvisStore'

const ZONES = [
  { city: 'New York',   tz: 'America/New_York',  flag: '🇺🇸' },
  { city: 'London',     tz: 'Europe/London',      flag: '🇬🇧' },
  { city: 'Dubai',      tz: 'Asia/Dubai',         flag: '🇦🇪' },
  { city: 'Sydney',     tz: 'Australia/Sydney',   flag: '🇦🇺' },
  { city: 'Mumbai',     tz: 'Asia/Kolkata',       flag: '🇮🇳' },
]

const AI_PROVIDER_DISPLAY = {
  anthropic: 'Claude',
  openai:    'GPT-4o',
  google:    'Gemini',
  deepseek:  'DeepSeek',
  groq:      'Groq / Llama',
  mistral:   'Mistral',
}

// ── Stat card ─────────────────────────────────────────────────────────────────

const StatCard = ({ icon: Icon, label, value, sub, color = 'blue', onClick, delay = 0 }) => {
  const C = {
    blue:   { border: 'border-jarvis-blue/20',   bg: 'bg-jarvis-blue/10',   text: 'text-jarvis-blue',   glow: 'glow-blue' },
    purple: { border: 'border-purple-400/20',     bg: 'bg-purple-500/10',    text: 'text-purple-400',    glow: '' },
    green:  { border: 'border-green-400/20',      bg: 'bg-green-500/10',     text: 'text-green-400',     glow: '' },
    amber:  { border: 'border-amber-400/20',      bg: 'bg-amber-400/10',     text: 'text-amber-400',     glow: '' },
    red:    { border: 'border-red-400/20',        bg: 'bg-red-500/10',       text: 'text-red-400',       glow: '' },
  }[color]

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.35 }}
      onClick={onClick}
      className={`glass p-5 border ${C.border} ${C.glow} ${onClick ? 'cursor-pointer hover:border-opacity-60' : ''} transition-all`}
    >
      <div className="flex items-start justify-between mb-3">
        <div className={`p-2.5 rounded-xl ${C.bg}`}>
          <Icon size={17} className={C.text} />
        </div>
        <span className="text-[10px] text-white/25 font-mono uppercase tracking-wider">{sub}</span>
      </div>
      <p className={`text-3xl font-bold ${C.text}`}>{value ?? '—'}</p>
      <p className="text-xs text-white/40 mt-1 font-medium">{label}</p>
    </motion.div>
  )
}

// ── AI Provider status dot ─────────────────────────────────────────────────────

const ProviderRow = ({ name, data, delay }) => {
  const display = AI_PROVIDER_DISPLAY[name] || name
  const online = data?.status === 'online'
  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay }}
      className="flex items-center justify-between px-3 py-2.5 rounded-xl bg-white/[0.03] border border-white/[0.05]"
    >
      <div className="flex items-center gap-2.5">
        <span className={`w-2 h-2 rounded-full flex-shrink-0 ${
          online ? 'bg-green-400 shadow-[0_0_6px_#4ade80]' : 'bg-red-400 shadow-[0_0_6px_#f87171]'
        }`} />
        <span className="text-sm text-white/65 font-medium">{display}</span>
      </div>
      <div className="flex items-center gap-2">
        {data?.latency_ms && (
          <span className="text-[10px] text-white/25 font-mono">{data.latency_ms}ms</span>
        )}
        {online
          ? <CheckCircle size={13} className="text-green-400/70" />
          : <XCircle size={13} className="text-red-400/70" />}
      </div>
    </motion.div>
  )
}

// ── Main dashboard ─────────────────────────────────────────────────────────────

export default function Dashboard() {
  const { setActiveView, setPendingApprovals } = useJarvisStore()

  const [greeting, setGreeting]       = useState(null)
  const [health, setHealth]           = useState(null)
  const [aiHealth, setAiHealth]       = useState(null)
  const [leadStats, setLeadStats]     = useState(null)
  const [gmailStats, setGmailStats]   = useState(null)
  const [approvals, setApprovals]     = useState(0)
  const [times, setTimes]             = useState({})
  const [loadingAI, setLoadingAI]     = useState(false)
  const [speaking, setSpeaking]       = useState(false)
  const [greeted, setGreeted]         = useState(false)
  const [now, setNow]                 = useState(new Date())

  // Fetch all dashboard data in parallel
  const fetchAll = useCallback(async () => {
    try {
      const [h, p, ls, gs] = await Promise.allSettled([
        getHealth(),
        getPendingCount(),
        getLeadStats(),
        getGmailStats(),
      ])
      if (h.status === 'fulfilled') setHealth(h.value)
      if (p.status === 'fulfilled') {
        const count = p.value?.pending || 0
        setApprovals(count)
        setPendingApprovals(count)
      }
      if (ls.status === 'fulfilled') setLeadStats(ls.value)
      if (gs.status === 'fulfilled') setGmailStats(gs.value)
    } catch {}
  }, [setPendingApprovals])

  // Fetch AI health check
  const runAIHealthCheck = useCallback(async () => {
    setLoadingAI(true)
    try {
      const data = await getJarvisAIHealth()
      setAiHealth(data)
    } catch {}
    setLoadingAI(false)
  }, [])

  // Contextual greeting
  const fetchAndSpeak = useCallback(async () => {
    if (greeted) return
    setGreeted(true)
    try {
      const data = await getJarvisGreeting()
      setGreeting(data.greeting)
    } catch {
      const hour = new Date().getHours()
      setGreeting(
        hour < 12 ? "Good morning, Captain. JARVIS is operational." :
        hour < 17 ? "Good afternoon, Captain. All systems running." :
        "Good evening, Captain. Standing by."
      )
    }
  }, [greeted])

  const speakGreeting = () => {
    if (!greeting) return
    setSpeaking(true)
    voiceService.speak(greeting, { onEnd: () => setSpeaking(false) })
  }

  const speakVoiceBrief = async () => {
    setSpeaking(true)
    try {
      const data = await getJarvisVoiceBrief()
      await voiceService.speak(data.brief, { onEnd: () => setSpeaking(false) })
    } catch {
      setSpeaking(false)
    }
  }

  useEffect(() => {
    fetchAll()
    fetchAndSpeak()
    runAIHealthCheck()

    // Refresh stats every 60s
    const interval = setInterval(fetchAll, 60_000)
    return () => clearInterval(interval)
  }, [])

  // World clocks
  useEffect(() => {
    const update = () => {
      const t = {}
      ZONES.forEach(({ city, tz }) => {
        t[city] = new Date().toLocaleTimeString('en-US', {
          timeZone: tz, hour: '2-digit', minute: '2-digit', hour12: true,
        })
      })
      setTimes(t)
      setNow(new Date())
    }
    update()
    const ticker = setInterval(update, 10_000)
    return () => clearInterval(ticker)
  }, [])

  const hour = now.getHours()
  const timeLabel = hour < 12 ? 'morning' : hour < 17 ? 'afternoon' : hour < 21 ? 'evening' : 'night'
  const aiOnline = aiHealth?.online ?? 0
  const aiTotal  = aiHealth?.total ?? 6

  return (
    <div className="p-5 space-y-5 overflow-y-auto h-full no-scrollbar">

      {/* ── JARVIS Greeting banner ── */}
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass p-5 border border-jarvis-blue/15 glow-blue relative overflow-hidden"
      >
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse shadow-[0_0_8px_#4ade80]" />
              <span className="text-xs text-green-400 font-semibold tracking-wider uppercase">JARVIS Online</span>
            </div>
            <p className="text-white/80 text-sm leading-relaxed mt-2">
              {greeting || `Good ${timeLabel}, Captain. Loading status…`}
            </p>
          </div>
          <div className="flex flex-col items-end gap-2 flex-shrink-0">
            <button
              onClick={speaking ? () => voiceService.stopSpeaking() : speakGreeting}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium border transition-all ${
                speaking
                  ? 'bg-jarvis-blue/20 border-jarvis-blue/40 text-jarvis-blue'
                  : 'glass border-white/15 text-white/45 hover:text-white/80'
              }`}
            >
              <Volume2 size={12} className={speaking ? 'animate-pulse' : ''} />
              {speaking ? 'Stop' : 'Play'}
            </button>
            <button
              onClick={speakVoiceBrief}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium glass border border-white/10 text-white/40 hover:text-white/70 transition-all"
            >
              <Zap size={12} />
              Full Brief
            </button>
          </div>
        </div>
      </motion.div>

      {/* ── Stats row ── */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard
          icon={Brain}
          label="AI Providers Online"
          value={`${aiOnline}/${aiTotal}`}
          sub="intelligence"
          color={aiOnline > 0 ? 'blue' : 'red'}
          onClick={() => runAIHealthCheck()}
          delay={0.04}
        />
        <StatCard
          icon={CheckSquare}
          label="Pending Approvals"
          value={approvals}
          sub="queue"
          color={approvals > 0 ? 'amber' : 'green'}
          onClick={() => setActiveView('approvals')}
          delay={0.08}
        />
        <StatCard
          icon={Target}
          label="Total Leads"
          value={leadStats?.total ?? '—'}
          sub="pipeline"
          color="purple"
          onClick={() => setActiveView('leads')}
          delay={0.12}
        />
        <StatCard
          icon={Mail}
          label="Emails — Needs Action"
          value={gmailStats?.needs_action ?? '—'}
          sub="inbox"
          color={gmailStats?.needs_action > 0 ? 'amber' : 'green'}
          onClick={() => setActiveView('gmail')}
          delay={0.16}
        />
      </div>

      {/* ── AI Health + World clocks ── */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">

        {/* AI Intelligence Network */}
        <motion.div
          initial={{ opacity: 0, x: -16 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2 }}
          className="glass p-5"
        >
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Brain size={15} className="text-jarvis-blue" />
              <span className="text-sm font-semibold text-white/70">AI Intelligence Network</span>
            </div>
            <button
              onClick={runAIHealthCheck}
              disabled={loadingAI}
              className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs text-white/35 hover:text-white/60 glass border border-white/10 transition-all disabled:opacity-40"
            >
              <RefreshCw size={11} className={loadingAI ? 'animate-spin' : ''} />
              {loadingAI ? 'Checking…' : 'Test All'}
            </button>
          </div>

          {loadingAI && !aiHealth ? (
            <div className="flex items-center justify-center py-8 gap-2">
              <Loader size={16} className="animate-spin text-jarvis-blue/60" />
              <span className="text-sm text-white/30">Testing all providers…</span>
            </div>
          ) : aiHealth?.providers ? (
            <div className="space-y-2">
              {Object.entries(aiHealth.providers).map(([name, data], i) => (
                <ProviderRow key={name} name={name} data={data} delay={i * 0.05} />
              ))}
            </div>
          ) : (
            <div className="space-y-2">
              {['anthropic','openai','google','deepseek','groq','mistral'].map((n, i) => (
                <div key={n} className="flex items-center gap-2.5 px-3 py-2.5 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                  <span className="w-2 h-2 rounded-full bg-white/20" />
                  <span className="text-sm text-white/35">{AI_PROVIDER_DISPLAY[n]}</span>
                </div>
              ))}
            </div>
          )}

          {aiHealth && (
            <div className="mt-3 pt-3 border-t border-white/[0.06] flex items-center justify-between">
              <span className="text-xs text-white/30">{aiOnline} of {aiTotal} providers responding</span>
              <span className={`text-xs font-medium ${aiOnline === aiTotal ? 'text-green-400' : aiOnline > 0 ? 'text-amber-400' : 'text-red-400'}`}>
                {aiOnline === aiTotal ? 'All Operational' : aiOnline > 0 ? 'Partially Degraded' : 'Critical'}
              </span>
            </div>
          )}
        </motion.div>

        {/* World clock */}
        <motion.div
          initial={{ opacity: 0, x: 16 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.25 }}
          className="glass p-5"
        >
          <div className="flex items-center gap-2 mb-4">
            <Globe size={15} className="text-jarvis-blue" />
            <span className="text-sm font-semibold text-white/70">Target Markets — Live Time</span>
          </div>
          <div className="space-y-2.5">
            {ZONES.map(({ city, flag }) => {
              const t = times[city]
              const [hhmm, ampm] = (t || '').split(' ')
              const isBusinessHours = (() => {
                if (!t) return false
                const h = parseInt(hhmm?.split(':')[0] || '0')
                const isPM = ampm === 'PM'
                const hour24 = isPM && h !== 12 ? h + 12 : (!isPM && h === 12 ? 0 : h)
                return hour24 >= 9 && hour24 < 18
              })()
              return (
                <div key={city} className="flex items-center justify-between px-3 py-2.5 rounded-xl bg-white/[0.03] border border-white/[0.04]">
                  <div className="flex items-center gap-2.5">
                    <span>{flag}</span>
                    <span className="text-sm text-white/60 font-medium">{city}</span>
                    {isBusinessHours && (
                      <span className="text-[9px] text-green-400 bg-green-400/10 px-1.5 py-0.5 rounded-full font-medium">OPEN</span>
                    )}
                  </div>
                  <span className="font-mono text-sm text-jarvis-blue">{t || '—'}</span>
                </div>
              )
            })}
          </div>
        </motion.div>
      </div>

      {/* ── Lead pipeline + Gmail quick stats ── */}
      {(leadStats || gmailStats) && (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
          {leadStats && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="glass p-5"
            >
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Target size={15} className="text-purple-400" />
                  <span className="text-sm font-semibold text-white/70">Lead Pipeline</span>
                </div>
                <button onClick={() => setActiveView('leads')} className="text-xs text-jarvis-blue/60 hover:text-jarvis-blue">View all →</button>
              </div>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { label: 'New', value: leadStats.by_status?.new ?? '—', color: 'text-white/60' },
                  { label: 'Hot (8+)', value: leadStats.hot_leads ?? '—', color: 'text-red-400' },
                  { label: 'Proposals', value: leadStats.by_status?.proposal_sent ?? '—', color: 'text-amber-400' },
                ].map(({ label, value, color }) => (
                  <div key={label} className="text-center p-3 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                    <p className={`text-2xl font-bold ${color}`}>{value}</p>
                    <p className="text-[11px] text-white/35 mt-0.5">{label}</p>
                  </div>
                ))}
              </div>
            </motion.div>
          )}

          {gmailStats && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.35 }}
              className="glass p-5"
            >
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Mail size={15} className="text-green-400" />
                  <span className="text-sm font-semibold text-white/70">Gmail Operations</span>
                </div>
                <button onClick={() => setActiveView('gmail')} className="text-xs text-jarvis-blue/60 hover:text-jarvis-blue">Open inbox →</button>
              </div>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { label: 'Unread', value: gmailStats.unread ?? '—', color: 'text-jarvis-blue' },
                  { label: 'Client Replies', value: gmailStats.client_replies ?? '—', color: 'text-green-400' },
                  { label: 'Needs Action', value: gmailStats.needs_action ?? '—', color: 'text-amber-400' },
                ].map(({ label, value, color }) => (
                  <div key={label} className="text-center p-3 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                    <p className={`text-2xl font-bold ${color}`}>{value}</p>
                    <p className="text-[11px] text-white/35 mt-0.5">{label}</p>
                  </div>
                ))}
              </div>
            </motion.div>
          )}
        </div>
      )}

      {/* ── Overnight engine status ── */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="glass p-5"
      >
        <div className="flex items-center gap-2 mb-4">
          <Activity size={15} className="text-jarvis-blue" />
          <span className="text-sm font-semibold text-white/70">Overnight Revenue Engine — Schedule (IST)</span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          {[
            { time: '11:30 PM', label: 'Lead Discovery',    status: 'active' },
            { time: '12:00 AM', label: 'Intel Analysis',    status: 'active' },
            { time: '01:00 AM', label: 'Proposal Engine',   status: 'active' },
            { time: '02:00 AM', label: 'Cold Outreach',     status: 'active' },
            { time: '03:00 AM', label: 'Upwork / PPH Bids', status: 'active' },
            { time: '05:00 AM', label: 'Follow-ups',        status: 'active' },
            { time: '06:30 AM', label: 'Pipeline Health',   status: 'active' },
            { time: '08:00 AM', label: 'Ops Report',        status: 'active' },
          ].map(({ time, label }) => (
            <div key={label} className="flex items-center gap-2 px-3 py-2.5 rounded-xl bg-white/[0.03] border border-white/[0.05]">
              <span className="w-1.5 h-1.5 rounded-full bg-jarvis-blue/70 flex-shrink-0" />
              <div className="min-w-0">
                <p className="text-[10px] text-jarvis-blue/70 font-mono">{time}</p>
                <p className="text-xs text-white/50 truncate">{label}</p>
              </div>
            </div>
          ))}
        </div>
      </motion.div>

    </div>
  )
}
