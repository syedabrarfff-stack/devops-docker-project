import React, { useCallback, useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Ghost, Zap, Send, Copy, RefreshCw, ChevronDown, ChevronUp,
  User, Building2, Globe, Target, Star, Layers, CheckCircle,
  AlertCircle, Loader, Mail, Sparkles, PenLine, Clock, TrendingUp,
} from 'lucide-react'
import { api } from '../../services/api'

// ── Constants ───────────────────────────────────────────────────────────────

const TONES = [
  { value: 'professional', label: 'Professional', desc: 'Formal, confident, enterprise-grade', icon: '🎩' },
  { value: 'warm',         label: 'Warm & Human', desc: 'Friendly, conversational, genuinely helpful', icon: '🤝' },
  { value: 'direct',       label: 'Direct',        desc: 'Blunt, value-first, max 4 sentences', icon: '⚡' },
]

const EMAIL_LABELS = ['Cold Intro', 'Follow-Up 1', 'Follow-Up 2']

const PERSONA_COLORS = {
  'Darren Mitchell':  { bg: 'from-amber-500/20 to-orange-500/10', border: 'border-amber-500/30', dot: 'bg-amber-400' },
  'David Carter':     { bg: 'from-blue-500/20 to-cyan-500/10',    border: 'border-blue-500/30',   dot: 'bg-blue-400' },
  'Sophia Reynolds':  { bg: 'from-purple-500/20 to-pink-500/10',  border: 'border-purple-500/30', dot: 'bg-purple-400' },
  'Nathan Scott':     { bg: 'from-emerald-500/20 to-teal-500/10', border: 'border-emerald-500/30',dot: 'bg-emerald-400' },
  'Emma Collins':     { bg: 'from-rose-500/20 to-red-500/10',     border: 'border-rose-500/30',   dot: 'bg-rose-400' },
  'Daniel Brooks':    { bg: 'from-slate-500/20 to-zinc-500/10',   border: 'border-slate-500/30',  dot: 'bg-slate-400' },
  'Michael Hayes':    { bg: 'from-indigo-500/20 to-blue-500/10',  border: 'border-indigo-500/30', dot: 'bg-indigo-400' },
  'Lucas Reed':       { bg: 'from-green-500/20 to-lime-500/10',   border: 'border-green-500/30',  dot: 'bg-green-400' },
  'Olivia Bennett':   { bg: 'from-pink-500/20 to-rose-500/10',    border: 'border-pink-500/30',   dot: 'bg-pink-400' },
}

const BASE_URL = import.meta.env.DEV ? 'http://localhost:8000' : ''

// ── Sub-components ──────────────────────────────────────────────────────────

function ScoreBadge({ score }) {
  const color = score >= 70 ? 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10'
              : score >= 40 ? 'text-amber-400 border-amber-500/30 bg-amber-500/10'
              : 'text-red-400 border-red-500/30 bg-red-500/10'
  return (
    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${color}`}>
      {score.toFixed(0)}
    </span>
  )
}

function PersonaCard({ persona, selected, onSelect }) {
  const theme = PERSONA_COLORS[persona.name] || { bg: 'from-white/5 to-white/0', border: 'border-white/10', dot: 'bg-white/40' }
  return (
    <motion.button
      whileTap={{ scale: 0.97 }}
      onClick={() => onSelect(persona.name)}
      className={`w-full text-left p-3 rounded-xl border transition-all duration-200
        bg-gradient-to-br ${theme.bg} ${theme.border}
        ${selected ? 'ring-1 ring-white/20 shadow-lg' : 'opacity-70 hover:opacity-100'}`}
    >
      <div className="flex items-start gap-2">
        <div className={`mt-1 w-2 h-2 rounded-full flex-shrink-0 ${theme.dot} ${selected ? 'animate-pulse' : ''}`} />
        <div className="min-w-0">
          <p className="text-sm font-semibold text-white truncate">{persona.name}</p>
          <p className="text-[11px] text-white/50 truncate">{persona.role}</p>
          <div className="mt-1 flex flex-wrap gap-1">
            {(persona.tone_keywords || []).slice(0, 3).map(kw => (
              <span key={kw} className="text-[9px] px-1.5 py-0.5 rounded bg-white/5 text-white/40">{kw}</span>
            ))}
          </div>
        </div>
        {selected && <CheckCircle size={14} className="ml-auto flex-shrink-0 text-white/50 mt-0.5" />}
      </div>
    </motion.button>
  )
}

function LeadCard({ lead, onSelect }) {
  const pain = Array.isArray(lead.pain_points) ? lead.pain_points.slice(0, 2).join(', ') : ''
  return (
    <motion.button
      whileTap={{ scale: 0.98 }}
      onClick={() => onSelect(lead)}
      className="w-full text-left p-3 rounded-lg border border-white/[0.08] bg-white/[0.03]
                 hover:bg-white/[0.06] hover:border-white/[0.14] transition-all"
    >
      <div className="flex items-center gap-2">
        <Building2 size={13} className="text-white/30 flex-shrink-0" />
        <span className="text-sm font-medium text-white truncate flex-1">
          {lead.company_name || lead.company || '—'}
        </span>
        <ScoreBadge score={lead.score || 0} />
      </div>
      <div className="mt-1 flex items-center gap-3 text-[11px] text-white/40">
        {lead.contact_name && <span className="truncate">{lead.contact_name}</span>}
        {lead.industry && <span className="truncate opacity-60">{lead.industry}</span>}
      </div>
      {pain && <p className="mt-1 text-[10px] text-white/30 truncate">{pain}</p>}
    </motion.button>
  )
}

function EmailCanvas({ lines, streaming, phase }) {
  const endRef = useRef(null)
  useEffect(() => {
    if (streaming) endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [lines, streaming])

  return (
    <div className="relative min-h-[220px] font-mono text-sm leading-relaxed text-white/85
                    whitespace-pre-wrap break-words">
      {phase === 'idle' && (
        <div className="absolute inset-0 flex flex-col items-center justify-center text-white/20 select-none">
          <Ghost size={36} className="mb-3 opacity-30" />
          <p className="text-xs">Configure above and press Compose</p>
        </div>
      )}
      {phase === 'thinking' && (
        <div className="absolute inset-0 flex flex-col items-center justify-center text-white/40">
          <Sparkles size={24} className="mb-2 animate-pulse text-jarvis-purple" />
          <p className="text-xs animate-pulse">Ghost is reading the intelligence…</p>
        </div>
      )}
      {lines}
      {streaming && (
        <span className="inline-block w-[2px] h-[1em] bg-jarvis-blue align-middle ml-0.5 animate-pulse" />
      )}
      <div ref={endRef} />
    </div>
  )
}

// ── Main component ──────────────────────────────────────────────────────────

export default function GhostWriter() {
  // Lead state
  const [leads, setLeads]           = useState([])
  const [leadsLoading, setLeadsLoading] = useState(false)
  const [leadSearch, setLeadSearch] = useState('')
  const [selectedLead, setSelectedLead] = useState(null)
  const [leadPanelOpen, setLeadPanelOpen] = useState(true)

  // Persona state
  const [personas, setPersonas]     = useState([])
  const [selectedPersona, setSelectedPersona] = useState(null)
  const [personaPanelOpen, setPersonaPanelOpen] = useState(false)

  // Compose controls
  const [tone, setTone]             = useState('professional')
  const [emailNum, setEmailNum]     = useState(1)
  const [sequenceMode, setSequenceMode] = useState(false)

  // Composition state
  const [phase, setPhase]           = useState('idle') // idle | thinking | streaming | done | error
  const [streamedText, setStreamedText] = useState('')
  const [parsedSubject, setParsedSubject] = useState('')
  const [parsedBody, setParsedBody] = useState('')
  const [charCount, setCharCount]   = useState(0)
  const [errorMsg, setErrorMsg]     = useState('')
  const [copied, setCopied]         = useState(false)

  // Sequence state
  const [sequenceEmails, setSequenceEmails] = useState([])
  const [seqLoading, setSeqLoading] = useState(false)

  // Send state
  const [sending, setSending]       = useState(false)
  const [sentOk, setSentOk]         = useState(false)

  const abortRef = useRef(null)

  // ── Load data ─────────────────────────────────────────────────────────────

  useEffect(() => {
    fetchLeads()
    fetchPersonas()
  }, [])

  async function fetchLeads(q = '') {
    setLeadsLoading(true)
    try {
      const params = { limit: 50, min_score: 0 }
      const r = await api.get('/api/v1/leads/', { params })
      const all = r.data?.leads || r.data || []
      setLeads(all)
    } catch {
      setLeads([])
    } finally {
      setLeadsLoading(false)
    }
  }

  async function fetchPersonas() {
    try {
      const r = await api.get('/api/v1/ghost/personas')
      setPersonas(r.data?.personas || [])
    } catch {
      setPersonas([])
    }
  }

  // ── Lead selection ────────────────────────────────────────────────────────

  async function handleSelectLead(lead) {
    setSelectedLead(lead)
    setLeadPanelOpen(false)
    setStreamedText('')
    setParsedSubject('')
    setParsedBody('')
    setPhase('idle')
    setSequenceEmails([])
    setSentOk(false)

    // Auto-suggest persona
    try {
      const r = await api.get('/api/v1/ghost/persona/suggest', {
        params: {
          industry: lead.industry,
          pain_points: Array.isArray(lead.pain_points) ? lead.pain_points.join(',') : '',
        },
      })
      const suggested = r.data?.suggested_persona
      if (suggested) setSelectedPersona(suggested)
    } catch {/* ignore */}
  }

  // ── Compose (streaming) ───────────────────────────────────────────────────

  const compose = useCallback(async () => {
    if (!selectedLead) return
    if (abortRef.current) abortRef.current.abort()

    const ctrl = new AbortController()
    abortRef.current = ctrl

    setPhase('thinking')
    setStreamedText('')
    setParsedSubject('')
    setParsedBody('')
    setCharCount(0)
    setErrorMsg('')
    setSentOk(false)

    const body = {
      lead_id: selectedLead.id || null,
      lead_data: selectedLead.id ? null : selectedLead,
      persona_name: selectedPersona || null,
      tone,
      email_num: emailNum,
      total_emails: sequenceMode ? 3 : 1,
    }

    try {
      const res = await fetch(`${BASE_URL}/api/v1/ghost/compose/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: ctrl.signal,
      })

      if (!res.ok) {
        const err = await res.text()
        throw new Error(err || `HTTP ${res.status}`)
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buf = ''
      let full = ''

      setPhase('streaming')

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buf += decoder.decode(value, { stream: true })

        const parts = buf.split('\n\n')
        buf = parts.pop() ?? ''

        for (const part of parts) {
          const line = part.trim()
          if (!line.startsWith('data: ')) continue
          try {
            const evt = JSON.parse(line.slice(6))
            if (evt.type === 'token') {
              full += evt.text
              setStreamedText(full)
            } else if (evt.type === 'complete') {
              setCharCount(evt.char_count || full.length)
              // parse subject / body
              const [subj, bdy] = parseEmail(full)
              setParsedSubject(subj)
              setParsedBody(bdy)
            } else if (evt.type === 'error') {
              setErrorMsg(evt.message || 'Composition failed')
              setPhase('error')
              return
            } else if (evt.type === 'done') {
              setPhase('done')
            }
          } catch {/* malformed SSE line */}
        }
      }

      if (phase !== 'error') setPhase('done')
    } catch (err) {
      if (err.name === 'AbortError') return
      setErrorMsg(err.message || 'Network error')
      setPhase('error')
    }
  }, [selectedLead, selectedPersona, tone, emailNum, sequenceMode])

  // ── Sequence (non-streaming) ──────────────────────────────────────────────

  async function generateSequence() {
    if (!selectedLead) return
    setSeqLoading(true)
    setSequenceEmails([])
    setSentOk(false)

    try {
      const r = await api.post('/api/v1/ghost/sequence', {
        lead_id: selectedLead.id || null,
        lead_data: selectedLead.id ? null : selectedLead,
        persona_name: selectedPersona || null,
        tone,
        email_count: 3,
      })
      setSequenceEmails(r.data?.emails || [])
    } catch (err) {
      setErrorMsg(err?.response?.data?.detail || err.message || 'Sequence generation failed')
    } finally {
      setSeqLoading(false)
    }
  }

  // ── Send ──────────────────────────────────────────────────────────────────

  async function sendEmail() {
    if (!selectedLead?.id) {
      setErrorMsg('Select a lead from the CRM to send directly')
      return
    }
    setSending(true)
    try {
      await api.post('/api/v1/ghost/send', {
        lead_id: selectedLead.id,
        persona_name: selectedPersona || null,
        tone,
      })
      setSentOk(true)
    } catch (err) {
      setErrorMsg(err?.response?.data?.detail || err.message || 'Send failed')
    } finally {
      setSending(false)
    }
  }

  // ── Copy ─────────────────────────────────────────────────────────────────

  function copyToClipboard(text) {
    navigator.clipboard.writeText(text || streamedText).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  // ── Filtered leads ────────────────────────────────────────────────────────

  const filteredLeads = leads.filter(l => {
    if (!leadSearch) return true
    const q = leadSearch.toLowerCase()
    return (
      (l.company_name || l.company || '').toLowerCase().includes(q) ||
      (l.contact_name || '').toLowerCase().includes(q) ||
      (l.industry || '').toLowerCase().includes(q)
    )
  }).slice(0, 12)

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-white/[0.06] flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-jarvis-purple/30 to-jarvis-blue/20
                          border border-jarvis-purple/30 flex items-center justify-center">
            <Ghost size={16} className="text-jarvis-purple" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-white">JARVIS GHOST</h2>
            <p className="text-[11px] text-white/40">AI Outreach Intelligence Engine</p>
          </div>
        </div>
        <div className="flex items-center gap-2 text-[11px] text-white/30">
          <Sparkles size={12} className="text-jarvis-purple" />
          <span>Claude Opus · Live Composition</span>
        </div>
      </div>

      <div className="flex-1 overflow-hidden flex">
        {/* ── Left Panel ── */}
        <div className="w-72 flex-shrink-0 border-r border-white/[0.06] flex flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto no-scrollbar px-3 py-3 space-y-3">

            {/* Lead Selector */}
            <div className="rounded-xl border border-white/[0.08] bg-white/[0.02] overflow-hidden">
              <button
                onClick={() => setLeadPanelOpen(!leadPanelOpen)}
                className="w-full flex items-center justify-between px-3 py-2.5 text-xs font-semibold
                           text-white/60 hover:text-white/90 transition-colors"
              >
                <span className="flex items-center gap-2">
                  <Target size={12} className="text-jarvis-blue" />
                  {selectedLead
                    ? `${selectedLead.company_name || selectedLead.company || '—'}`
                    : 'Select Target Lead'}
                </span>
                {leadPanelOpen ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
              </button>

              <AnimatePresence>
                {leadPanelOpen && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className="border-t border-white/[0.06]"
                  >
                    <div className="p-2">
                      <input
                        value={leadSearch}
                        onChange={e => setLeadSearch(e.target.value)}
                        placeholder="Search leads…"
                        className="w-full px-3 py-1.5 text-xs bg-white/[0.05] border border-white/[0.08]
                                   rounded-lg text-white placeholder-white/30 outline-none
                                   focus:border-jarvis-blue/40 transition-colors"
                      />
                    </div>
                    <div className="px-2 pb-2 space-y-1 max-h-52 overflow-y-auto no-scrollbar">
                      {leadsLoading
                        ? <div className="text-center py-4 text-xs text-white/30">Loading…</div>
                        : filteredLeads.length === 0
                        ? <div className="text-center py-4 text-xs text-white/30">No leads found</div>
                        : filteredLeads.map(l => (
                          <LeadCard key={l.id} lead={l} onSelect={handleSelectLead} />
                        ))
                      }
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Selected lead intel */}
            <AnimatePresence>
              {selectedLead && (
                <motion.div
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="rounded-xl border border-white/[0.08] bg-gradient-to-br
                             from-jarvis-blue/5 to-jarvis-purple/5 p-3 space-y-2"
                >
                  <div className="text-[10px] text-white/40 font-semibold uppercase tracking-wider">
                    Lead Intel
                  </div>
                  {selectedLead.contact_name && (
                    <div className="flex items-center gap-2 text-xs text-white/70">
                      <User size={11} className="text-white/30" />
                      {selectedLead.contact_name}
                    </div>
                  )}
                  {selectedLead.industry && (
                    <div className="flex items-center gap-2 text-xs text-white/70">
                      <TrendingUp size={11} className="text-white/30" />
                      {selectedLead.industry}
                    </div>
                  )}
                  {selectedLead.country && (
                    <div className="flex items-center gap-2 text-xs text-white/70">
                      <Globe size={11} className="text-white/30" />
                      {selectedLead.country}
                    </div>
                  )}
                  {selectedLead.email && (
                    <div className="flex items-center gap-2 text-xs text-white/70">
                      <Mail size={11} className="text-white/30" />
                      {selectedLead.email}
                    </div>
                  )}
                  {Array.isArray(selectedLead.pain_points) && selectedLead.pain_points.length > 0 && (
                    <div className="pt-1 border-t border-white/[0.05]">
                      <div className="text-[10px] text-white/30 mb-1">Pain Points</div>
                      <div className="flex flex-wrap gap-1">
                        {selectedLead.pain_points.slice(0, 4).map((pp, i) => (
                          <span key={i} className="text-[9px] px-1.5 py-0.5 rounded bg-jarvis-purple/10
                                                    border border-jarvis-purple/20 text-jarvis-purple/80">
                            {String(pp).slice(0, 30)}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  <div className="flex items-center gap-2 pt-1 border-t border-white/[0.05]">
                    <Star size={11} className="text-amber-400" />
                    <span className="text-xs text-white/60">Score</span>
                    <ScoreBadge score={selectedLead.score || 0} />
                    <span className={`ml-auto text-[10px] px-1.5 py-0.5 rounded border
                      ${selectedLead.status === 'WON'   ? 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10'
                      : selectedLead.status === 'LOST'  ? 'text-red-400 border-red-500/30 bg-red-500/10'
                      : 'text-amber-400 border-amber-500/30 bg-amber-500/10'}`}>
                      {selectedLead.status || 'NEW'}
                    </span>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Persona Selector */}
            <div className="rounded-xl border border-white/[0.08] bg-white/[0.02] overflow-hidden">
              <button
                onClick={() => setPersonaPanelOpen(!personaPanelOpen)}
                className="w-full flex items-center justify-between px-3 py-2.5 text-xs font-semibold
                           text-white/60 hover:text-white/90 transition-colors"
              >
                <span className="flex items-center gap-2">
                  <Layers size={12} className="text-jarvis-purple" />
                  {selectedPersona ? `${selectedPersona}` : 'Auto-Select Persona'}
                </span>
                {personaPanelOpen ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
              </button>

              <AnimatePresence>
                {personaPanelOpen && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className="border-t border-white/[0.06] p-2 space-y-1.5 max-h-72 overflow-y-auto no-scrollbar"
                  >
                    <button
                      onClick={() => { setSelectedPersona(null); setPersonaPanelOpen(false) }}
                      className={`w-full text-left px-3 py-2 rounded-lg text-xs transition-all border
                        ${!selectedPersona
                          ? 'bg-jarvis-purple/10 border-jarvis-purple/30 text-jarvis-purple'
                          : 'border-white/[0.06] text-white/40 hover:text-white/70'}`}
                    >
                      <span className="flex items-center gap-2">
                        <Sparkles size={10} />
                        Auto-Select (AI chooses)
                      </span>
                    </button>
                    {personas.map(p => (
                      <PersonaCard
                        key={p.name}
                        persona={p}
                        selected={selectedPersona === p.name}
                        onSelect={name => { setSelectedPersona(name); setPersonaPanelOpen(false) }}
                      />
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Tone + Email Type */}
            <div className="space-y-2">
              <div className="text-[10px] text-white/40 font-semibold uppercase tracking-wider px-1">Tone</div>
              {TONES.map(t => (
                <button
                  key={t.value}
                  onClick={() => setTone(t.value)}
                  className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs
                    border transition-all duration-200
                    ${tone === t.value
                      ? 'bg-jarvis-blue/10 border-jarvis-blue/30 text-white'
                      : 'border-white/[0.06] text-white/40 hover:text-white/70 hover:border-white/[0.12]'}`}
                >
                  <span>{t.icon}</span>
                  <span className="font-medium">{t.label}</span>
                  <span className="ml-auto text-[10px] opacity-50">{t.desc}</span>
                </button>
              ))}
            </div>

            {/* Email number + sequence toggle */}
            <div className="space-y-2">
              <div className="text-[10px] text-white/40 font-semibold uppercase tracking-wider px-1">Email Type</div>
              <div className="flex gap-1">
                {EMAIL_LABELS.map((label, i) => (
                  <button
                    key={i}
                    onClick={() => setEmailNum(i + 1)}
                    className={`flex-1 py-1.5 rounded-lg text-[11px] font-medium border transition-all
                      ${emailNum === i + 1
                        ? 'bg-jarvis-blue/15 border-jarvis-blue/30 text-jarvis-blue'
                        : 'border-white/[0.06] text-white/30 hover:text-white/60'}`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>

          </div>
        </div>

        {/* ── Right Panel — Canvas ── */}
        <div className="flex-1 flex flex-col overflow-hidden">

          {/* Action Bar */}
          <div className="px-4 py-3 border-b border-white/[0.06] flex items-center gap-2 flex-wrap">
            <motion.button
              whileTap={{ scale: 0.96 }}
              onClick={compose}
              disabled={!selectedLead || phase === 'streaming' || phase === 'thinking'}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold
                transition-all
                ${!selectedLead || phase === 'streaming' || phase === 'thinking'
                  ? 'opacity-40 cursor-not-allowed bg-jarvis-purple/10 border border-jarvis-purple/20 text-jarvis-purple'
                  : 'bg-jarvis-purple/20 border border-jarvis-purple/30 text-white hover:bg-jarvis-purple/30'}`}
            >
              {phase === 'thinking' || phase === 'streaming'
                ? <Loader size={14} className="animate-spin" />
                : <Ghost size={14} />}
              {phase === 'thinking' ? 'Thinking…'
               : phase === 'streaming' ? 'Composing…'
               : 'Compose'}
            </motion.button>

            <motion.button
              whileTap={{ scale: 0.96 }}
              onClick={generateSequence}
              disabled={!selectedLead || seqLoading}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm border transition-all
                ${!selectedLead || seqLoading
                  ? 'opacity-40 cursor-not-allowed border-white/[0.06] text-white/30'
                  : 'border-white/[0.12] text-white/60 hover:text-white/90 hover:border-white/[0.25]'}`}
            >
              {seqLoading ? <Loader size={13} className="animate-spin" /> : <Layers size={13} />}
              3-Email Sequence
            </motion.button>

            <div className="flex-1" />

            {(phase === 'done' || streamedText) && (
              <>
                <motion.button
                  whileTap={{ scale: 0.96 }}
                  onClick={() => copyToClipboard()}
                  className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs border
                             border-white/[0.08] text-white/50 hover:text-white/80 transition-all"
                >
                  {copied ? <CheckCircle size={13} className="text-emerald-400" /> : <Copy size={13} />}
                  {copied ? 'Copied!' : 'Copy'}
                </motion.button>

                <motion.button
                  whileTap={{ scale: 0.96 }}
                  onClick={compose}
                  className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs border
                             border-white/[0.08] text-white/50 hover:text-white/80 transition-all"
                >
                  <RefreshCw size={13} />
                  Regenerate
                </motion.button>
              </>
            )}

            {phase === 'done' && selectedLead?.email && (
              <motion.button
                whileTap={{ scale: 0.96 }}
                onClick={sendEmail}
                disabled={sending || sentOk}
                className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold border
                  transition-all
                  ${sentOk
                    ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400'
                    : sending
                    ? 'opacity-60 cursor-wait border-white/[0.08] text-white/40'
                    : 'border-jarvis-blue/30 bg-jarvis-blue/10 text-jarvis-blue hover:bg-jarvis-blue/20'}`}
              >
                {sentOk
                  ? <><CheckCircle size={13} /> Sent!</>
                  : sending
                  ? <><Loader size={13} className="animate-spin" /> Sending…</>
                  : <><Send size={13} /> Send Email</>}
              </motion.button>
            )}
          </div>

          {/* Canvas body */}
          <div className="flex-1 overflow-y-auto no-scrollbar p-5">

            {/* Error banner */}
            <AnimatePresence>
              {(phase === 'error' || errorMsg) && (
                <motion.div
                  initial={{ opacity: 0, y: -8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="mb-4 flex items-start gap-2 px-4 py-3 rounded-xl
                             bg-red-500/10 border border-red-500/20 text-red-400 text-sm"
                >
                  <AlertCircle size={15} className="flex-shrink-0 mt-0.5" />
                  <span>{errorMsg || 'Composition failed — check API key and try again'}</span>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Sequence results */}
            <AnimatePresence>
              {sequenceEmails.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mb-6 space-y-4"
                >
                  <div className="text-xs font-semibold text-white/40 uppercase tracking-wider flex items-center gap-2">
                    <Layers size={12} />
                    3-Email Sequence Ready
                  </div>
                  {sequenceEmails.map((email, i) => (
                    <div key={i} className="rounded-xl border border-white/[0.08] bg-white/[0.02] overflow-hidden">
                      <div className="flex items-center justify-between px-4 py-2.5
                                      border-b border-white/[0.06] bg-white/[0.02]">
                        <span className="text-xs font-semibold text-white/60">
                          {EMAIL_LABELS[i]} {email.status === 'error' ? '— Failed' : ''}
                        </span>
                        <div className="flex items-center gap-2">
                          {email.status === 'ok' && (
                            <>
                              <span className="text-[10px] text-white/30">
                                {(email.full_text || '').length} chars
                              </span>
                              <button
                                onClick={() => copyToClipboard(email.full_text)}
                                className="text-white/30 hover:text-white/70 transition-colors"
                              >
                                <Copy size={12} />
                              </button>
                            </>
                          )}
                        </div>
                      </div>
                      {email.status === 'ok' ? (
                        <div className="p-4">
                          {email.subject && (
                            <div className="mb-3 pb-3 border-b border-white/[0.06]">
                              <span className="text-[10px] text-white/30 uppercase tracking-wider">Subject</span>
                              <p className="mt-1 text-sm font-semibold text-white">{email.subject}</p>
                            </div>
                          )}
                          <div className="text-sm text-white/70 whitespace-pre-wrap leading-relaxed font-mono">
                            {email.body || email.full_text}
                          </div>
                        </div>
                      ) : (
                        <div className="p-4 text-xs text-red-400">{email.error}</div>
                      )}
                    </div>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>

            {/* Parsed subject / body preview */}
            <AnimatePresence>
              {parsedSubject && phase !== 'streaming' && (
                <motion.div
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mb-4 px-4 py-3 rounded-xl border border-jarvis-blue/20
                             bg-jarvis-blue/5"
                >
                  <div className="text-[10px] text-jarvis-blue/60 uppercase tracking-wider mb-1">Subject Line</div>
                  <div className="text-sm font-semibold text-white">{parsedSubject}</div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Email canvas — live streaming text */}
            <div className={`rounded-xl border p-5 transition-all duration-300
              ${phase === 'streaming'
                ? 'border-jarvis-purple/30 bg-jarvis-purple/5'
                : phase === 'done'
                ? 'border-white/[0.08] bg-white/[0.02]'
                : 'border-white/[0.05] bg-transparent'}`}
            >
              <EmailCanvas
                lines={streamedText}
                streaming={phase === 'streaming'}
                phase={phase === 'idle' ? 'idle' : phase === 'thinking' ? 'thinking' : phase}
              />
            </div>

            {/* Meta footer */}
            {phase === 'done' && charCount > 0 && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="mt-3 flex items-center gap-4 text-[11px] text-white/25"
              >
                <span className="flex items-center gap-1">
                  <PenLine size={11} />
                  {charCount} characters
                </span>
                <span className="flex items-center gap-1">
                  <Clock size={11} />
                  ~{Math.ceil(charCount / 200)} min read
                </span>
                {selectedPersona && (
                  <span className="flex items-center gap-1">
                    <User size={11} />
                    Written as {selectedPersona}
                  </span>
                )}
              </motion.div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Helpers ─────────────────────────────────────────────────────────────────

function parseEmail(text) {
  const lines = (text || '').trim().split('\n')
  let subject = ''
  const body = []
  let inBody = false
  for (const line of lines) {
    if (!inBody && line.toLowerCase().startsWith('subject:')) {
      subject = line.slice(8).trim()
      inBody = true
    } else if (inBody) {
      body.push(line)
    }
  }
  return [subject, body.join('\n').trim()]
}
