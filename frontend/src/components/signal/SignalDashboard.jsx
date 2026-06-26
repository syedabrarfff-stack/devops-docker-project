import React, { useCallback, useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Radio, Zap, TrendingUp, AlertTriangle, Eye, ChevronRight,
  Loader, RefreshCw, Ghost, Cpu, User, Building2, Globe,
  CheckCircle, AlertCircle, Layers, Sparkles, Target, Activity,
} from 'lucide-react'
import { api } from '../../services/api'

const BASE_URL = import.meta.env.DEV ? 'http://localhost:8000' : ''

const TIER_STYLE = {
  HOT:  { bg: 'bg-red-500/10',     border: 'border-red-500/30',     text: 'text-red-400',     dot: 'bg-red-400' },
  WARM: { bg: 'bg-amber-500/10',   border: 'border-amber-500/30',   text: 'text-amber-400',   dot: 'bg-amber-400' },
  COOL: { bg: 'bg-blue-500/10',    border: 'border-blue-500/30',    text: 'text-blue-400',    dot: 'bg-blue-400' },
  COLD: { bg: 'bg-slate-500/10',   border: 'border-slate-500/30',   text: 'text-slate-400',   dot: 'bg-slate-300' },
}

function TierBadge({ tier }) {
  const s = TIER_STYLE[tier] || TIER_STYLE.COLD
  return (
    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${s.bg} ${s.border} ${s.text}`}>
      {tier}
    </span>
  )
}

function SignalBar({ score }) {
  const color = score >= 75 ? 'bg-red-400' : score >= 50 ? 'bg-amber-400' : score >= 25 ? 'bg-blue-400' : 'bg-slate-500'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-white/[0.05] rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${score}%` }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
          className={`h-full rounded-full ${color}`}
        />
      </div>
      <span className="text-[11px] text-white/50 w-6 text-right">{score}</span>
    </div>
  )
}

function SignalCard({ signal, onViewDetail }) {
  const tier = signal.intent_tier || 'COLD'
  const s = TIER_STYLE[tier] || TIER_STYLE.COLD

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={`rounded-xl border p-4 cursor-pointer transition-all hover:scale-[1.01]
        ${s.bg} ${s.border}`}
      onClick={() => onViewDetail(signal)}
    >
      <div className="flex items-start justify-between mb-2">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-white truncate">
              {signal.lead_company || '—'}
            </span>
            <TierBadge tier={tier} />
          </div>
          <div className="flex items-center gap-2 mt-0.5 text-[11px] text-white/40">
            {signal.lead_contact && <span>{signal.lead_contact}</span>}
            {signal.lead_industry && <span className="opacity-60">{signal.lead_industry}</span>}
          </div>
        </div>
        <div className={`flex-shrink-0 w-2 h-2 rounded-full mt-1.5 ml-2 ${s.dot}
                        ${tier === 'HOT' ? 'animate-pulse' : ''}`} />
      </div>

      <SignalBar score={signal.signal_score || 0} />

      {signal.why_now && (
        <p className="mt-2 text-[11px] text-white/60 leading-relaxed line-clamp-2 italic">
          "{signal.why_now}"
        </p>
      )}

      {signal.recommended_persona && (
        <div className="mt-2 flex items-center gap-1.5 text-[10px] text-white/35">
          <User size={10} />
          {signal.recommended_persona}
          {signal.recommended_tone && <span className="opacity-60">· {signal.recommended_tone}</span>}
        </div>
      )}
    </motion.div>
  )
}

function SignalModal({ signal, onClose, onGhost, onAutopilot }) {
  if (!signal) return null
  const tier = signal.intent_tier || 'COLD'
  const s = TIER_STYLE[tier] || TIER_STYLE.COLD

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
      onClick={e => e.target === e.currentTarget && onClose()}
    >
      <motion.div
        initial={{ scale: 0.95, y: 12 }}
        animate={{ scale: 1, y: 0 }}
        exit={{ scale: 0.95, opacity: 0 }}
        className="w-full max-w-lg rounded-2xl border border-white/[0.1] bg-[#0d0d14]
                   shadow-2xl overflow-hidden"
      >
        <div className={`px-6 py-4 border-b border-white/[0.06] ${s.bg}`}>
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-semibold text-white">{signal.lead_company}</h3>
                <TierBadge tier={tier} />
              </div>
              <p className="text-xs text-white/40 mt-0.5">
                {signal.lead_contact}{signal.lead_industry ? ` · ${signal.lead_industry}` : ''}
                {signal.lead_country ? ` · ${signal.lead_country}` : ''}
              </p>
            </div>
            <div className="text-right">
              <div className={`text-2xl font-bold ${s.text}`}>{signal.signal_score}</div>
              <div className="text-[10px] text-white/30">signal score</div>
            </div>
          </div>
        </div>

        <div className="p-6 space-y-4">
          <div>
            <div className="text-[10px] text-white/30 uppercase tracking-wider mb-2">Why Now</div>
            <p className="text-sm text-white/80 italic">"{signal.why_now}"</p>
          </div>

          {(signal.signals || []).length > 0 && (
            <div>
              <div className="text-[10px] text-white/30 uppercase tracking-wider mb-2">Buying Signals</div>
              <ul className="space-y-1.5">
                {signal.signals.map((sig, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-white/65">
                    <Zap size={10} className={`mt-0.5 flex-shrink-0 ${s.text}`} />
                    {sig}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <div className="text-[10px] text-white/30 uppercase tracking-wider mb-1">Best Persona</div>
              <div className="flex items-center gap-1.5 text-sm text-white/80">
                <User size={12} className="text-white/30" />
                {signal.recommended_persona}
              </div>
              {signal.persona_reason && (
                <p className="text-[10px] text-white/35 mt-1">{signal.persona_reason}</p>
              )}
            </div>
            <div>
              <div className="text-[10px] text-white/30 uppercase tracking-wider mb-1">Confidence</div>
              <div className="text-sm text-white/80 font-medium">{signal.confidence || '—'}%</div>
              <div className="text-[10px] text-white/30">AI confidence score</div>
            </div>
          </div>

          {(signal.risk_flags || []).length > 0 && (
            <div className="px-3 py-2.5 rounded-lg bg-amber-500/5 border border-amber-500/20">
              <div className="text-[10px] text-amber-400/70 uppercase tracking-wider mb-1">Risk Flags</div>
              {signal.risk_flags.map((f, i) => (
                <div key={i} className="text-[11px] text-amber-400/60 flex items-center gap-1.5">
                  <AlertTriangle size={10} />
                  {f}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="px-6 pb-6 flex gap-2">
          <button
            onClick={() => { onGhost(signal); onClose() }}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium border
                       border-jarvis-purple/30 bg-jarvis-purple/10 text-white/80
                       hover:bg-jarvis-purple/20 transition-all"
          >
            <Ghost size={13} /> Compose with GHOST
          </button>
          <button
            onClick={onClose}
            className="px-3 py-2 rounded-lg text-sm border border-white/[0.08]
                       text-white/40 hover:text-white/70 transition-all"
          >
            Close
          </button>
        </div>
      </motion.div>
    </motion.div>
  )
}

export default function SignalDashboard() {
  const [pipelineStats, setPipelineStats] = useState(null)
  const [signals, setSignals]             = useState([])
  const [scanning, setScanning]           = useState(false)
  const [scanProgress, setScanProgress]   = useState({ done: 0, total: 0 })
  const [briefText, setBriefText]         = useState('')
  const [briefing, setBriefing]           = useState(false)
  const [briefPhase, setBriefPhase]       = useState('idle')
  const [selectedSignal, setSelectedSignal] = useState(null)
  const [filter, setFilter]               = useState('ALL')
  const [errorMsg, setErrorMsg]           = useState('')
  const [scanSettings, setScanSettings]   = useState({ limit: 20, min_score: 0 })
  const abortRef = useRef(null)

  useEffect(() => { fetchStats() }, [])

  async function fetchStats() {
    try {
      const r = await api.get('/api/v1/signal/status')
      setPipelineStats(r.data)
    } catch { /* ignore */ }
  }

  const runPipelineScan = useCallback(async () => {
    if (abortRef.current) abortRef.current.abort()
    const ctrl = new AbortController()
    abortRef.current = ctrl

    setScanning(true)
    setSignals([])
    setScanProgress({ done: 0, total: 0 })
    setErrorMsg('')
    setBriefText('')
    setBriefPhase('idle')

    try {
      const res = await fetch(`${BASE_URL}/api/v1/signal/scan/pipeline`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ limit: scanSettings.limit, min_score: scanSettings.min_score }),
        signal: ctrl.signal,
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)

      const reader = res.body.getReader()
      const dec = new TextDecoder()
      let buf = ''
      let allSignals = []

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buf += dec.decode(value, { stream: true })
        const parts = buf.split('\n\n')
        buf = parts.pop() ?? ''
        for (const part of parts) {
          const line = part.trim()
          if (!line.startsWith('data: ')) continue
          try {
            const evt = JSON.parse(line.slice(6))
            if (evt.type === 'pipeline_start') {
              setScanProgress({ done: 0, total: evt.total })
            } else if (evt.type === 'scan_result') {
              allSignals = [...allSignals, evt.signal]
              allSignals.sort((a, b) => (b.signal_score || 0) - (a.signal_score || 0))
              setSignals([...allSignals])
              setScanProgress(p => ({ ...p, done: evt.done }))
            } else if (evt.type === 'pipeline_complete') {
              allSignals = evt.results
              setSignals([...allSignals])
            }
          } catch { /* skip */ }
        }
      }
    } catch (err) {
      if (err.name === 'AbortError') return
      setErrorMsg(err.message || 'Scan failed')
    } finally {
      setScanning(false)
    }
  }, [scanSettings])

  async function generateBrief() {
    if (!signals.length) return
    if (abortRef.current) abortRef.current.abort()
    const ctrl = new AbortController()
    abortRef.current = ctrl

    setBriefing(true)
    setBriefText('')
    setBriefPhase('streaming')

    try {
      const res = await fetch(`${BASE_URL}/api/v1/signal/brief/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ signals }),
        signal: ctrl.signal,
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)

      const reader = res.body.getReader()
      const dec = new TextDecoder()
      let buf = ''
      let full = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buf += dec.decode(value, { stream: true })
        const parts = buf.split('\n\n')
        buf = parts.pop() ?? ''
        for (const part of parts) {
          const line = part.trim()
          if (!line.startsWith('data: ')) continue
          try {
            const evt = JSON.parse(line.slice(6))
            if (evt.type === 'token') {
              full += evt.text
              setBriefText(full)
            } else if (evt.type === 'complete') {
              setBriefPhase('done')
            } else if (evt.type === 'error') {
              setErrorMsg(evt.message)
              setBriefPhase('idle')
            }
          } catch { /* skip */ }
        }
      }
    } catch (err) {
      if (err.name === 'AbortError') return
      setErrorMsg(err.message || 'Brief generation failed')
      setBriefPhase('idle')
    } finally {
      setBriefing(false)
    }
  }

  const filteredSignals = signals.filter(s =>
    filter === 'ALL' || s.intent_tier === filter
  )

  const counts = signals.reduce((acc, s) => {
    acc[s.intent_tier] = (acc[s.intent_tier] || 0) + 1
    return acc
  }, {})

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-white/[0.06] flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-red-500/20 to-amber-500/10
                          border border-red-500/25 flex items-center justify-center">
            <Radio size={16} className="text-red-400" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-white">JARVIS SIGNAL</h2>
            <p className="text-[11px] text-white/40">AI Pipeline Intelligence Scanner</p>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <div className="flex items-center gap-2 text-xs">
            <input
              type="number" min={1} max={50} value={scanSettings.limit}
              onChange={e => setScanSettings(s => ({ ...s, limit: Number(e.target.value) }))}
              className="w-14 px-2 py-1 bg-white/[0.05] border border-white/[0.08] rounded text-white outline-none"
              title="Max leads"
            />
            <span className="text-white/30">leads</span>
          </div>
          <motion.button
            whileTap={{ scale: 0.97 }}
            onClick={runPipelineScan}
            disabled={scanning}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold border
              transition-all
              ${scanning
                ? 'opacity-60 cursor-wait border-red-500/20 bg-red-500/5 text-red-400/60'
                : 'border-red-500/30 bg-red-500/10 text-white hover:bg-red-500/20'}`}
          >
            {scanning ? <Loader size={14} className="animate-spin" /> : <Radio size={14} />}
            {scanning ? `Scanning… ${scanProgress.done}/${scanProgress.total}` : 'Scan Pipeline'}
          </motion.button>
          {signals.length > 0 && !scanning && (
            <motion.button
              whileTap={{ scale: 0.97 }}
              onClick={generateBrief}
              disabled={briefing}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold border
                transition-all
                ${briefing
                  ? 'opacity-60 cursor-wait border-jarvis-blue/20 bg-jarvis-blue/5 text-jarvis-blue/60'
                  : 'border-jarvis-blue/30 bg-jarvis-blue/10 text-white hover:bg-jarvis-blue/20'}`}
            >
              {briefing ? <Loader size={14} className="animate-spin" /> : <Sparkles size={14} />}
              {briefing ? 'Generating Brief…' : 'Intelligence Brief'}
            </motion.button>
          )}
        </div>
      </div>

      {/* Stats bar */}
      {pipelineStats && (
        <div className="flex gap-0 border-b border-white/[0.06] divide-x divide-white/[0.04]">
          {[
            { label: 'Total Leads', value: pipelineStats.total_leads, icon: Target, color: 'text-white/60' },
            { label: 'Hot', value: pipelineStats.hot_leads, icon: Zap, color: 'text-red-400' },
            { label: 'Warm', value: pipelineStats.warm_leads, icon: TrendingUp, color: 'text-amber-400' },
            { label: 'Eligible', value: pipelineStats.eligible_for_outreach, icon: CheckCircle, color: 'text-emerald-400' },
          ].map(stat => (
            <div key={stat.label} className="flex-1 px-4 py-2.5 flex items-center gap-2">
              <stat.icon size={13} className={stat.color} />
              <div>
                <div className="text-sm font-bold text-white">{stat.value}</div>
                <div className="text-[10px] text-white/30">{stat.label}</div>
              </div>
            </div>
          ))}
          {signals.length > 0 && (
            <>
              {['HOT', 'WARM', 'COOL', 'COLD'].map(tier => counts[tier] ? (
                <div key={tier} className="px-4 py-2.5 flex items-center gap-1.5">
                  <div className={`w-2 h-2 rounded-full ${TIER_STYLE[tier].dot}`} />
                  <div className="text-[11px] text-white/40">{counts[tier]} {tier}</div>
                </div>
              ) : null)}
            </>
          )}
        </div>
      )}

      {/* Error */}
      <AnimatePresence>
        {errorMsg && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="mx-6 mt-3 flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm
                       bg-red-500/10 border border-red-500/20 text-red-400"
          >
            <AlertCircle size={14} /> {errorMsg}
          </motion.div>
        )}
      </AnimatePresence>

      <div className="flex-1 overflow-hidden flex">
        {/* Signal grid */}
        <div className={`overflow-y-auto no-scrollbar p-5 space-y-4 transition-all
          ${briefText ? 'w-1/2 border-r border-white/[0.06]' : 'flex-1'}`}>

          {/* Progress bar */}
          {scanning && scanProgress.total > 0 && (
            <div className="space-y-1">
              <div className="flex items-center justify-between text-[11px] text-white/40">
                <span className="flex items-center gap-1.5"><Activity size={11} /> Scanning leads…</span>
                <span>{scanProgress.done} / {scanProgress.total}</span>
              </div>
              <div className="h-1 bg-white/[0.05] rounded-full overflow-hidden">
                <motion.div
                  animate={{ width: `${(scanProgress.done / scanProgress.total) * 100}%` }}
                  className="h-full bg-gradient-to-r from-red-500 to-amber-400 rounded-full"
                />
              </div>
            </div>
          )}

          {/* Filter tabs */}
          {signals.length > 0 && !scanning && (
            <div className="flex gap-1 bg-white/[0.03] rounded-lg p-1 border border-white/[0.06] w-fit">
              {['ALL', 'HOT', 'WARM', 'COOL', 'COLD'].map(f => (
                <button key={f} onClick={() => setFilter(f)}
                  className={`px-3 py-1 rounded-md text-xs font-medium transition-all
                    ${filter === f ? 'bg-white/[0.08] text-white' : 'text-white/35 hover:text-white/60'}`}>
                  {f} {f !== 'ALL' && counts[f] ? `(${counts[f]})` : ''}
                </button>
              ))}
            </div>
          )}

          {signals.length === 0 && !scanning ? (
            <div className="flex flex-col items-center justify-center h-full min-h-[300px] text-white/20">
              <Radio size={40} className="mb-4 opacity-30" />
              <p className="text-sm font-medium">Pipeline not scanned</p>
              <p className="text-xs mt-1 opacity-70">Press Scan Pipeline to analyse your leads with AI</p>
            </div>
          ) : (
            <motion.div layout className="grid grid-cols-1 lg:grid-cols-2 gap-3">
              <AnimatePresence mode="popLayout">
                {filteredSignals.map(signal => (
                  <SignalCard key={signal.lead_id + signal.signal_score}
                    signal={signal} onViewDetail={setSelectedSignal} />
                ))}
              </AnimatePresence>
            </motion.div>
          )}
        </div>

        {/* Intelligence Brief panel */}
        <AnimatePresence>
          {briefText && (
            <motion.div
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: '50%', opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              className="overflow-y-auto no-scrollbar p-5"
            >
              <div className="flex items-center gap-2 mb-4">
                <Sparkles size={14} className="text-jarvis-blue" />
                <span className="text-xs font-semibold text-white/60 uppercase tracking-wider">
                  Intelligence Brief
                </span>
                {briefPhase === 'streaming' && (
                  <span className="text-[10px] text-jarvis-blue animate-pulse">Generating…</span>
                )}
              </div>
              <div className="text-sm text-white/80 whitespace-pre-wrap leading-relaxed">
                {briefText}
                {briefPhase === 'streaming' && (
                  <span className="inline-block w-[2px] h-[1em] bg-jarvis-blue align-middle ml-0.5 animate-pulse" />
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Signal detail modal */}
      <AnimatePresence>
        {selectedSignal && (
          <SignalModal
            signal={selectedSignal}
            onClose={() => setSelectedSignal(null)}
            onGhost={signal => {
              window.location.hash = '#/control-room/ghost'
            }}
            onAutopilot={() => {}}
          />
        )}
      </AnimatePresence>
    </div>
  )
}
