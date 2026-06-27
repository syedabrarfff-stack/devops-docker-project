import React, { useState, useEffect, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import useJarvisStore from '../../store/useJarvisStore'
import {
  Infinity, Brain, Shield, Heart, Zap, Activity, AlertTriangle,
  CheckCircle, XCircle, Clock, ChevronDown, ChevronUp, Play,
  RefreshCw, Cpu, Radio, Ghost, Crosshair, Eye,
} from 'lucide-react'

const BASE_URL = import.meta.env.DEV ? 'http://localhost:8000' : ''

// ── Tier colours ──────────────────────────────────────────────────────────────
const STATUS_STYLE = {
  healthy:   { bg: 'bg-emerald-500/10', border: 'border-emerald-500/25', text: 'text-emerald-400', dot: 'bg-emerald-400' },
  degraded:  { bg: 'bg-amber-500/10',   border: 'border-amber-500/25',   text: 'text-amber-400',   dot: 'bg-amber-400' },
  warning:   { bg: 'bg-amber-500/10',   border: 'border-amber-500/25',   text: 'text-amber-400',   dot: 'bg-amber-400' },
  stopped:   { bg: 'bg-red-500/10',     border: 'border-red-500/25',     text: 'text-red-400',     dot: 'bg-red-500' },
  critical:  { bg: 'bg-red-500/10',     border: 'border-red-500/25',     text: 'text-red-400',     dot: 'bg-red-500' },
  missing_key: { bg: 'bg-red-500/10',   border: 'border-red-500/25',     text: 'text-red-400',     dot: 'bg-red-500' },
  configured:{ bg: 'bg-emerald-500/10', border: 'border-emerald-500/25', text: 'text-emerald-400', dot: 'bg-emerald-400' },
  unknown:   { bg: 'bg-slate-500/10',   border: 'border-slate-500/25',   text: 'text-slate-400',   dot: 'bg-slate-400' },
}
const getStyle = (s) => STATUS_STYLE[s] || STATUS_STYLE.unknown

const PHASE_ICONS = {
  PULSE:    <Activity size={14} />,
  THINK:    <Brain size={14} />,
  ACT:      <Zap size={14} />,
  HEAL:     <Heart size={14} />,
  COMPLETE: <CheckCircle size={14} />,
}

// ── Sub-components ────────────────────────────────────────────────────────────

function SubsystemCard({ name, status }) {
  const s = getStyle(status?.status || 'unknown')
  return (
    <div className={`p-3 rounded-lg border ${s.bg} ${s.border} flex items-start gap-3`}>
      <div className={`w-2 h-2 rounded-full mt-1 flex-shrink-0 ${s.dot} animate-pulse`} />
      <div className="min-w-0">
        <p className={`text-xs font-semibold uppercase tracking-wider ${s.text}`}>{name.replace('_', ' ')}</p>
        <p className="text-[11px] text-white/40 truncate mt-0.5">{status?.detail || '—'}</p>
        {status?.healable && (
          <span className="text-[10px] text-amber-400 mt-1 block">Healable</span>
        )}
      </div>
    </div>
  )
}

function ConstitutionArticle({ rule, idx }) {
  const [open, setOpen] = useState(false)
  const priorityColor = rule.priority === 1 ? 'text-red-400' : 'text-amber-400'
  return (
    <motion.div
      className="border border-white/[0.06] rounded-lg overflow-hidden"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: idx * 0.04 }}
    >
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-white/[0.03]"
      >
        <span className="text-[10px] font-mono text-white/30 w-14 flex-shrink-0">{rule.id}</span>
        <span className="text-sm text-white/80 flex-1">{rule.article}</span>
        <span className={`text-[10px] font-bold ${priorityColor} mr-2`}>P{rule.priority}</span>
        {open ? <ChevronUp size={14} className="text-white/30" /> : <ChevronDown size={14} className="text-white/30" />}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="px-4 pb-3 text-xs text-white/50 border-t border-white/[0.04]"
          >
            <p className="pt-2">{rule.description}</p>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

function DecisionCard({ d, idx }) {
  const actionColor = {
    send_outreach: 'text-emerald-400',
    standby: 'text-slate-400',
    escalate_to_captain: 'text-amber-400',
    nurture_sequence: 'text-blue-400',
  }[d.action] || 'text-white/60'

  return (
    <motion.div
      className="flex items-center gap-3 px-4 py-3 rounded-lg bg-white/[0.02] border border-white/[0.05]"
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: idx * 0.05 }}
    >
      <div className="w-8 h-8 rounded-lg bg-white/[0.04] border border-white/[0.08] flex items-center justify-center flex-shrink-0">
        <Brain size={14} className="text-jarvis-blue/60" />
      </div>
      <div className="flex-1 min-w-0">
        <p className={`text-xs font-semibold ${actionColor}`}>{d.action?.replace('_', ' ').toUpperCase()}</p>
        <p className="text-[11px] text-white/40 truncate">{d.situational_summary || '—'}</p>
      </div>
      <div className="text-right flex-shrink-0">
        <p className="text-[10px] text-white/30">{d.confidence ? `${d.confidence}%` : '—'}</p>
        <p className="text-[10px] text-white/20">{d.logged_at ? new Date(d.logged_at).toLocaleTimeString() : ''}</p>
      </div>
    </motion.div>
  )
}

// ── Main Dashboard ─────────────────────────────────────────────────────────────

export default function NexusCore() {
  const [status, setStatus] = useState(null)
  const [constitution, setConstitution] = useState(null)
  const [decisions, setDecisions] = useState([])
  const [healLog, setHealLog] = useState([])
  const [activeTab, setActiveTab] = useState('brain')

  const [running, setRunning] = useState(false)
  const [cyclePhase, setCyclePhase] = useState(null)
  const [thinkingText, setThinkingText] = useState('')
  const [cycleDecision, setCycleDecision] = useState(null)
  const [cycleLog, setCycleLog] = useState([])
  const abortRef = useRef(null)
  const thinkScrollRef = useRef(null)

  const wsNexusPulse = useJarvisStore(s => s.nexusPulse)
  const wsPendingDrafts = useJarvisStore(s => s.pendingDrafts)

  const load = useCallback(async () => {
    try {
      const [s, c, d] = await Promise.all([
        fetch(`${BASE_URL}/api/v1/nexus/status`).then(r => r.json()),
        fetch(`${BASE_URL}/api/v1/nexus/constitution`).then(r => r.json()),
        fetch(`${BASE_URL}/api/v1/nexus/decisions?limit=20`).then(r => r.json()),
      ])
      setStatus(s)
      setConstitution(c)
      setDecisions(d.decisions || [])
      setHealLog(d.heal_log || [])
    } catch (e) {
      console.error('[NEXUS] load error', e)
    }
  }, [])

  useEffect(() => {
    load()
    const t = setInterval(load, 60_000)
    return () => clearInterval(t)
  }, [load])

  useEffect(() => {
    if (thinkScrollRef.current) {
      thinkScrollRef.current.scrollTop = thinkScrollRef.current.scrollHeight
    }
  }, [thinkingText])

  async function runCycle() {
    if (running) {
      abortRef.current?.abort()
      setRunning(false)
      return
    }

    setRunning(true)
    setCyclePhase(null)
    setThinkingText('')
    setCycleDecision(null)
    setCycleLog([])

    const ctrl = new AbortController()
    abortRef.current = ctrl

    try {
      const resp = await fetch(`${BASE_URL}/api/v1/nexus/cycle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: ctrl.signal,
      })

      const reader = resp.body.getReader()
      const dec = new TextDecoder()
      let buf = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buf += dec.decode(value, { stream: true })
        const lines = buf.split('\n\n')
        buf = lines.pop() || ''

        for (const line of lines) {
          const data = line.replace(/^data: /, '').trim()
          if (!data) continue
          try {
            const evt = JSON.parse(data)
            if (evt.type === 'phase') {
              setCyclePhase(evt.phase)
              setCycleLog(prev => [...prev, { type: 'phase', phase: evt.phase, message: evt.message }])
            } else if (evt.type === 'thinking') {
              setThinkingText(prev => prev + evt.text)
            } else if (evt.type === 'decision') {
              setCycleDecision(evt.decision)
            } else if (evt.type === 'pulse') {
              setCycleLog(prev => [...prev, { type: 'pulse', data: evt.data }])
            } else if (evt.type === 'heal') {
              setCycleLog(prev => [...prev, { type: 'heal', results: evt.results }])
            } else if (evt.type === 'act_result') {
              setCycleLog(prev => [...prev, { type: 'act', result: evt.result }])
            } else if (evt.type === 'done') {
              break
            }
          } catch (_) {}
        }
      }
    } catch (e) {
      if (e.name !== 'AbortError') console.error('[NEXUS] cycle error', e)
    } finally {
      setRunning(false)
      load()
    }
  }

  // Pulse data — REST poll as baseline, WebSocket overrides for live fields
  const pulse = status?.latest_pulse
  const pipeline = pulse?.pipeline || {}
  const subsystems = status?.subsystem_health || {}
  const liveSignal = wsNexusPulse?.action_signal || pulse?.action_signal
  const liveHotLeads = wsNexusPulse != null ? wsNexusPulse.hot_leads : pipeline.hot_leads
  const liveDrafts = wsNexusPulse != null ? wsPendingDrafts : pulse?.autopilot_pending

  const TABS = [
    { id: 'brain',          label: 'Brain',         icon: <Brain size={14} /> },
    { id: 'constitution',   label: 'Constitution',  icon: <Shield size={14} /> },
    { id: 'health',         label: 'Health Matrix', icon: <Activity size={14} /> },
    { id: 'decisions',      label: 'Decisions',     icon: <Eye size={14} /> },
  ]

  return (
    <div className="flex flex-col h-full gap-6 p-6 overflow-y-auto no-scrollbar">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-violet-500/20 to-jarvis-blue/20
                          border border-violet-500/30 flex items-center justify-center">
            <Infinity size={22} className="text-violet-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-white tracking-tight">JARVIS NEXUS</h1>
              {wsNexusPulse && (
                <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/25 text-[10px] text-emerald-400 font-semibold">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse inline-block" />
                  LIVE
                </span>
              )}
            </div>
            <p className="text-xs text-white/40">Supreme Autonomous Intelligence Core · v{status?.version || '1.0.0'}</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button onClick={load} className="p-2 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] transition-all">
            <RefreshCw size={14} className="text-white/50" />
          </button>
          <motion.button
            onClick={runCycle}
            whileTap={{ scale: 0.97 }}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition-all ${
              running
                ? 'bg-red-500/15 border border-red-500/30 text-red-400'
                : 'bg-violet-500/15 border border-violet-500/30 text-violet-300 hover:bg-violet-500/25'
            }`}
          >
            {running ? <><XCircle size={14} /> ABORT</> : <><Play size={14} /> RUN CYCLE</>}
          </motion.button>
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-5 gap-3">
        {[
          { label: 'Total Leads',    value: pipeline.total_leads ?? '—',           color: 'text-white',       live: false },
          { label: 'HOT',            value: liveHotLeads ?? '—',                   color: 'text-red-400',     live: wsNexusPulse != null },
          { label: 'WARM',           value: pipeline.warm_leads ?? '—',            color: 'text-amber-400',   live: false },
          { label: 'Eligible',       value: pipeline.eligible_for_outreach ?? '—', color: 'text-emerald-400', live: false },
          { label: 'Drafts Pending', value: liveDrafts ?? '—',                     color: 'text-jarvis-blue', live: wsNexusPulse != null },
        ].map(({ label, value, color, live }) => (
          <div key={label} className="glass rounded-xl p-4 border border-white/[0.06] relative">
            {live && <div className="absolute top-2 right-2 w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />}
            <p className="text-[11px] text-white/40 uppercase tracking-wider">{label}</p>
            <p className={`text-2xl font-bold mt-1 ${color}`}>{value}</p>
          </div>
        ))}
      </div>

      {/* Cycle Activity Panel */}
      <AnimatePresence>
        {(running || cycleDecision || cycleLog.length > 0) && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="glass rounded-2xl border border-violet-500/20 overflow-hidden"
          >
            {/* Phase progress */}
            {cyclePhase && (
              <div className="px-5 py-3 border-b border-white/[0.06] flex items-center gap-3">
                <div className="flex items-center gap-2 text-violet-300 text-sm font-semibold">
                  {PHASE_ICONS[cyclePhase] || <Cpu size={14} />}
                  PHASE: {cyclePhase}
                </div>
                {running && <div className="w-2 h-2 rounded-full bg-violet-400 animate-ping ml-auto" />}
              </div>
            )}

            <div className="grid grid-cols-2 divide-x divide-white/[0.06]">
              {/* Thinking stream */}
              <div className="p-4">
                <p className="text-[11px] text-white/30 uppercase tracking-wider mb-2 flex items-center gap-1">
                  <Brain size={11} /> Brain Reasoning
                </p>
                <div ref={thinkScrollRef} className="h-48 overflow-y-auto text-xs text-white/60 font-mono whitespace-pre-wrap leading-relaxed no-scrollbar">
                  {thinkingText || <span className="text-white/20">Waiting for BRAIN activation...</span>}
                </div>
              </div>

              {/* Decision result */}
              <div className="p-4">
                <p className="text-[11px] text-white/30 uppercase tracking-wider mb-2 flex items-center gap-1">
                  <Crosshair size={11} /> Decision
                </p>
                {cycleDecision ? (
                  <div className="space-y-2">
                    <div className="p-3 rounded-lg bg-white/[0.03] border border-white/[0.06]">
                      <p className="text-[10px] text-white/40 uppercase">Primary Action</p>
                      <p className="text-sm font-bold text-violet-300 mt-0.5">
                        {cycleDecision.primary_decision?.action?.replace('_', ' ').toUpperCase()}
                      </p>
                      <p className="text-xs text-white/50 mt-1">{cycleDecision.primary_decision?.rationale}</p>
                    </div>
                    <p className="text-xs text-white/40 italic">{cycleDecision.situational_summary}</p>
                    {cycleDecision.captain_alerts?.length > 0 && (
                      <div className="p-2 rounded-lg bg-amber-500/10 border border-amber-500/20">
                        <p className="text-[10px] text-amber-400 font-bold">CAPTAIN ALERTS</p>
                        {cycleDecision.captain_alerts.map((a, i) => (
                          <p key={i} className="text-xs text-amber-300/80 mt-1">• {a}</p>
                        ))}
                      </div>
                    )}
                    {cycleDecision.constitution_verdict && (
                      <div className={`p-2 rounded-lg border text-xs ${
                        cycleDecision.constitution_verdict.allowed
                          ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300'
                          : 'bg-red-500/10 border-red-500/20 text-red-300'
                      }`}>
                        Constitution: {cycleDecision.constitution_verdict.allowed ? '✓ APPROVED' : '✗ BLOCKED'}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="h-48 flex items-center justify-center text-white/20 text-xs">
                    Awaiting brain output...
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Tabs */}
      <div className="flex gap-1 p-1 bg-white/[0.03] rounded-xl border border-white/[0.05] w-fit">
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium transition-all ${
              activeTab === t.id
                ? 'bg-violet-500/15 border border-violet-500/25 text-violet-300'
                : 'text-white/40 hover:text-white/70'
            }`}
          >
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <AnimatePresence mode="wait">
        {/* BRAIN TAB */}
        {activeTab === 'brain' && (
          <motion.div key="brain" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div className="grid grid-cols-2 gap-4">
              {/* Action signal */}
              <div className="glass rounded-2xl border border-white/[0.06] p-5">
                <p className="text-[11px] text-white/30 uppercase tracking-wider mb-3 flex items-center gap-1">
                  <Radio size={11} /> Action Signal
                </p>
                <div className="text-center py-4">
                  <p className={`text-3xl font-black tracking-widest ${
                    liveSignal === 'OUTREACH_READY' ? 'text-emerald-400' :
                    liveSignal === 'DRAFTS_PENDING' ? 'text-amber-400' : 'text-white/40'
                  }`}>
                    {liveSignal || 'STANDBY'}
                  </p>
                  <p className="text-xs text-white/30 mt-2">
                    {wsNexusPulse
                      ? <span className="text-emerald-400/70">⬤ Live via WebSocket</span>
                      : pulse?.timestamp
                        ? `Last pulse: ${new Date(pulse.timestamp).toLocaleTimeString()}`
                        : 'No pulse yet'}
                  </p>
                </div>
                <div className="grid grid-cols-3 gap-2 mt-2">
                  {[
                    ['OUTREACH_READY', 'Go signal — hot leads eligible for immediate outreach', 'emerald'],
                    ['DRAFTS_PENDING', 'Drafts queued for Captain approval', 'amber'],
                    ['MONITOR', 'No immediate action — continuing to monitor', 'slate'],
                  ].map(([sig, desc, col]) => (
                    <div key={sig} className={`p-2 rounded-lg bg-${col}-500/5 border border-${col}-500/10`}>
                      <p className={`text-[9px] font-bold text-${col}-400`}>{sig}</p>
                      <p className="text-[9px] text-white/30 mt-0.5">{desc}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Subsystems summary */}
              <div className="glass rounded-2xl border border-white/[0.06] p-5">
                <p className="text-[11px] text-white/30 uppercase tracking-wider mb-3 flex items-center gap-1">
                  <Cpu size={11} /> Subsystem Overview
                </p>
                <div className="space-y-2">
                  {Object.entries(subsystems).map(([name, s]) => {
                    const st = getStyle(s?.status || 'unknown')
                    return (
                      <div key={name} className="flex items-center gap-3">
                        <div className={`w-2 h-2 rounded-full flex-shrink-0 ${st.dot}`} />
                        <span className="text-xs text-white/60 flex-1 capitalize">{name.replace('_', ' ')}</span>
                        <span className={`text-[10px] font-semibold ${st.text}`}>{s?.status?.toUpperCase()}</span>
                      </div>
                    )
                  })}
                </div>
                <div className="mt-4 pt-3 border-t border-white/[0.05] flex items-center justify-between">
                  <span className="text-xs text-white/30">Healthy subsystems</span>
                  <span className="text-sm font-bold text-white">
                    {status?.healthy_subsystems ?? '—'}/{status?.total_subsystems ?? '—'}
                  </span>
                </div>
              </div>
            </div>
          </motion.div>
        )}

        {/* CONSTITUTION TAB */}
        {activeTab === 'constitution' && (
          <motion.div key="const" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div className="glass rounded-2xl border border-white/[0.06] p-5">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Shield size={16} className="text-violet-400" />
                  <p className="text-sm font-semibold text-white">NEXUS Constitution</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="px-2 py-1 rounded text-[10px] bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
                    IMMUTABLE
                  </span>
                  <span className="text-xs text-white/30">{constitution?.articles || 0} Articles</span>
                </div>
              </div>
              <div className="space-y-2">
                {(constitution?.constitution || []).map((rule, i) => (
                  <ConstitutionArticle key={rule.id} rule={rule} idx={i} />
                ))}
              </div>
            </div>
          </motion.div>
        )}

        {/* HEALTH MATRIX TAB */}
        {activeTab === 'health' && (
          <motion.div key="health" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div className="grid grid-cols-2 gap-3">
              {Object.entries(subsystems).map(([name, s]) => (
                <SubsystemCard key={name} name={name} status={s} />
              ))}
            </div>
            {Object.entries(subsystems).some(([, s]) => s?.healable) && (
              <div className="mt-4 p-4 rounded-xl bg-amber-500/5 border border-amber-500/15">
                <p className="text-xs text-amber-400 font-semibold">Healable subsystems detected.</p>
                <p className="text-xs text-white/40 mt-1">
                  Run a full NEXUS cycle to trigger automatic self-healing protocols.
                </p>
              </div>
            )}
          </motion.div>
        )}

        {/* DECISIONS TAB */}
        {activeTab === 'decisions' && (
          <motion.div key="decisions" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div className="space-y-4">
              <div className="glass rounded-2xl border border-white/[0.06] p-5">
                <p className="text-[11px] text-white/30 uppercase tracking-wider mb-3 flex items-center gap-1">
                  <Brain size={11} /> Autonomous Decision Log
                </p>
                {decisions.length === 0 ? (
                  <p className="text-xs text-white/30 text-center py-6">No decisions yet — run a NEXUS cycle.</p>
                ) : (
                  <div className="space-y-2">
                    {decisions.map((d, i) => <DecisionCard key={i} d={d} idx={i} />)}
                  </div>
                )}
              </div>

              {healLog.length > 0 && (
                <div className="glass rounded-2xl border border-white/[0.06] p-5">
                  <p className="text-[11px] text-white/30 uppercase tracking-wider mb-3 flex items-center gap-1">
                    <Heart size={11} /> Self-Heal Log
                  </p>
                  <div className="space-y-2">
                    {healLog.map((h, i) => (
                      <div key={i} className="flex items-center gap-3 px-3 py-2 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                        <div className={`w-2 h-2 rounded-full flex-shrink-0 ${h.success ? 'bg-emerald-400' : 'bg-red-400'}`} />
                        <span className="text-xs text-white/60 flex-1">{h.subsystem}</span>
                        <span className="text-[10px] text-white/30">{h.action}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
