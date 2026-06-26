import React, { useCallback, useEffect, useState } from 'react'
import {
  AlertTriangle, CheckCircle2, ChevronDown, ChevronRight,
  Clock, DollarSign, Loader2, RefreshCw, Send, Shield,
  TrendingUp, Users, XCircle, Zap,
} from 'lucide-react'
import api from '../../services/api'

// ── Council type options ──────────────────────────────────────────────────────

const COUNCIL_TYPES = [
  { value: 'standard',   label: 'Standard — balanced multi-model reasoning' },
  { value: 'strategic',  label: 'Strategic — long-horizon business decisions' },
  { value: 'technical',  label: 'Technical — engineering and architecture' },
  { value: 'financial',  label: 'Financial — pricing, revenue, risk' },
  { value: 'rapid',      label: 'Rapid — fast single-model answer' },
]

const QUICK_PROMPTS = [
  { label: 'Price it',      prompt: 'What is the optimal pricing for our AI automation retainer package for a mid-size enterprise client?' },
  { label: 'Assess risk',   prompt: 'What are the top 3 operational risks Aliyar Solutions faces in the next 90 days?' },
  { label: 'Close strategy',prompt: 'What is the best strategy to close a prospect who went silent after the pricing call?' },
  { label: 'Build vs Buy',  prompt: 'Should Aliyar Solutions build its own CRM or use an existing platform like HubSpot?' },
]

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function fmtMs(ms) {
  if (!ms) return '—'
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

function fmtUsd(n) {
  if (!n) return '$0.00'
  return `$${Number(n).toFixed(4)}`
}

// ── Decision badge ────────────────────────────────────────────────────────────

function DecisionBadge({ decision }) {
  const cfg = {
    APPROVE:        { cls: 'border-green-500/40 bg-green-500/10 text-green-300', icon: <CheckCircle2 size={10} /> },
    CAPTAIN_REVIEW: { cls: 'border-yellow-500/40 bg-yellow-500/10 text-yellow-300', icon: <Shield size={10} /> },
    REJECT:         { cls: 'border-red-500/40 bg-red-500/10 text-red-300', icon: <XCircle size={10} /> },
  }[decision] || { cls: 'border-gray-500/30 bg-gray-500/10 text-gray-400', icon: null }

  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] font-bold ${cfg.cls}`}>
      {cfg.icon}{decision?.replace('_', ' ') || '—'}
    </span>
  )
}

// ── Vote badge (per member) ───────────────────────────────────────────────────

function VoteBadge({ rec }) {
  const cfg = {
    APPROVE:        'border-green-500/30 bg-green-500/10 text-green-300',
    CAPTAIN_REVIEW: 'border-yellow-500/30 bg-yellow-500/10 text-yellow-300',
    REJECT:         'border-red-500/30 bg-red-500/10 text-red-300',
  }[rec] || 'border-gray-500/30 bg-gray-500/10 text-gray-300'
  return (
    <span className={`inline-flex rounded-full border px-2 py-0.5 text-[9px] font-semibold uppercase ${cfg}`}>
      {rec?.replace('_', ' ') || '—'}
    </span>
  )
}

// ── Score bar ─────────────────────────────────────────────────────────────────

function ScoreBar({ score }) {
  const pct = Math.max(0, Math.min(100, Number(score || 0)))
  const color = pct >= 80 ? 'bg-green-400' : pct >= 60 ? 'bg-yellow-400' : 'bg-red-400'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full bg-white/10 overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-700 ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className={`text-[11px] font-bold tabular-nums ${pct >= 80 ? 'text-green-300' : pct >= 60 ? 'text-yellow-300' : 'text-red-300'}`}>
        {Math.round(pct)}
      </span>
    </div>
  )
}

// ── Member vote card ──────────────────────────────────────────────────────────

function MemberVoteCard({ vote }) {
  const [open, setOpen] = useState(false)
  const responded = vote?.responded
  return (
    <div className={`rounded-lg border p-2.5 ${responded ? 'border-white/10 bg-white/4' : 'border-red-500/15 bg-red-500/5 opacity-60'}`}>
      <div className="flex items-center gap-2 mb-1.5">
        <div className={`h-1.5 w-1.5 rounded-full shrink-0 ${responded ? 'bg-green-400' : 'bg-red-400'}`} />
        <span className="text-[11px] font-semibold text-white capitalize leading-tight flex-1 truncate">
          {vote.member_id}
        </span>
        {responded && <VoteBadge rec={vote.recommendation} />}
      </div>
      {responded && (
        <>
          <ScoreBar score={vote.vote_score} />
          <p className="text-[10px] text-gray-500 mt-1 truncate">{vote.provider}/{vote.model}</p>
          {vote.reasoning && (
            <button type="button" onClick={() => setOpen(v => !v)} className="flex items-center gap-1 mt-1.5 text-[10px] text-jarvis-cyan/70 hover:text-jarvis-cyan transition-colors">
              {open ? <ChevronDown size={9} /> : <ChevronRight size={9} />}
              {open ? 'hide' : 'reasoning'}
            </button>
          )}
          {open && (
            <p className="text-[11px] text-gray-300 mt-1.5 leading-relaxed line-clamp-6">{vote.reasoning}</p>
          )}
          {vote.risks?.length > 0 && open && (
            <div className="mt-2 space-y-0.5">
              {vote.risks.slice(0, 2).map((r, i) => (
                <p key={i} className="text-[10px] text-red-300 leading-tight">⚠ {r}</p>
              ))}
            </div>
          )}
        </>
      )}
      {!responded && (
        <p className="text-[10px] text-gray-500 mt-1">{vote.error || 'unavailable'}</p>
      )}
    </div>
  )
}

// ── Session card (history) ────────────────────────────────────────────────────

function SessionCard({ session }) {
  const [open, setOpen] = useState(false)
  const votes = session.member_votes || []
  const responded = votes.filter(v => v.responded)

  return (
    <div className="rounded-xl border border-white/10 bg-white/5">
      <button type="button" onClick={() => setOpen(v => !v)} className="flex w-full items-start gap-3 p-4 text-left hover:bg-white/3 transition-colors rounded-xl">
        {open ? <ChevronDown size={13} className="mt-0.5 shrink-0 text-gray-400" /> : <ChevronRight size={13} className="mt-0.5 shrink-0 text-gray-400" />}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-white line-clamp-2">{session.question}</p>
          <div className="flex items-center gap-3 mt-1.5 flex-wrap">
            <span className="text-[10px] text-gray-500">{fmtDate(session.created_at || session.convened_at)}</span>
            {session.council_type && (
              <span className="text-[10px] text-gray-600 uppercase tracking-wider">{session.council_type}</span>
            )}
            {session.decision && <DecisionBadge decision={session.decision} />}
            {session.score != null && (
              <span className={`text-[10px] font-semibold ${session.score >= 80 ? 'text-green-400' : session.score >= 60 ? 'text-yellow-400' : 'text-red-400'}`}>
                score {Math.round(session.score)}
              </span>
            )}
            {responded.length > 0 && (
              <span className="text-[10px] text-gray-600">{responded.length}/{votes.length} responded</span>
            )}
          </div>
        </div>
      </button>

      {open && (
        <div className="border-t border-white/10 px-4 pb-4 pt-3 space-y-4">
          {session.reasoning && (
            <div>
              <p className="text-[10px] font-semibold text-jarvis-cyan uppercase tracking-wider mb-1">Council Reasoning</p>
              <p className="text-xs text-gray-300 leading-relaxed whitespace-pre-line">{session.reasoning}</p>
            </div>
          )}
          {votes.length > 0 && (
            <div>
              <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2">Member Votes</p>
              <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
                {votes.map((v, i) => <MemberVoteCard key={i} vote={v} />)}
              </div>
            </div>
          )}
          <div className="flex items-center gap-4 text-[10px] text-gray-600">
            {session.duration_ms && <span>⏱ {fmtMs(session.duration_ms)}</span>}
            {session.cost_estimate_usd && <span>💰 {fmtUsd(session.cost_estimate_usd)}</span>}
            {session.winner_model && <span>🏆 {session.winner_model}</span>}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Live result panel ─────────────────────────────────────────────────────────

function CouncilResultPanel({ result }) {
  if (!result) return null
  if (result.error) {
    return (
      <div className="mt-4 rounded-xl border border-red-400/20 bg-red-400/10 p-4 text-sm text-red-200">
        <AlertTriangle size={14} className="inline mr-2 mb-0.5" />
        {result.error}
      </div>
    )
  }

  const votes  = result.member_votes || []
  const responded = votes.filter(v => v.responded)

  return (
    <div className="mt-4 space-y-4 rounded-xl border border-jarvis-cyan/20 bg-jarvis-cyan/5 p-5">
      {/* Header */}
      <div className="flex items-center gap-3 flex-wrap">
        <Zap size={14} className="text-jarvis-cyan shrink-0" />
        <p className="text-sm font-bold text-jarvis-cyan">Council Decision</p>
        <DecisionBadge decision={result.decision} />
        <span className="ml-auto text-xs text-gray-400">
          {responded.length}/{votes.length} responded · {fmtMs(result.duration_ms)} · {fmtUsd(result.cost_estimate_usd)}
        </span>
      </div>

      {/* Score bar */}
      <div>
        <div className="flex items-center justify-between mb-1.5">
          <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">Consensus Score</p>
          <span className="text-[11px] text-gray-400">quorum {result.quorum_met ? '✅' : '❌'}</span>
        </div>
        <ScoreBar score={result.score} />
      </div>

      {/* Reasoning */}
      {result.reasoning && (
        <div>
          <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-1">Reasoning</p>
          <p className="text-xs text-gray-300 leading-relaxed whitespace-pre-line max-h-40 overflow-y-auto">{result.reasoning}</p>
        </div>
      )}

      {/* Member votes grid */}
      {votes.length > 0 && (
        <div>
          <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2">Member Votes</p>
          <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
            {votes.map((v, i) => <MemberVoteCard key={i} vote={v} />)}
          </div>
        </div>
      )}

      {/* Winner */}
      {result.winner_model && (
        <p className="text-[10px] text-gray-500">
          🏆 <span className="text-gray-400">{result.winner_model}</span> — highest weighted vote
        </p>
      )}
    </div>
  )
}

// ── Main view ─────────────────────────────────────────────────────────────────

export default function CouncilView() {
  const [health,      setHealth]      = useState(null)
  const [sessions,    setSessions]    = useState([])
  const [loading,     setLoading]     = useState(true)
  const [question,    setQuestion]    = useState('')
  const [councilType, setCouncilType] = useState('standard')
  const [convening,   setConvening]   = useState(false)
  const [lastResult,  setLastResult]  = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    const [healthRes, sessionsRes] = await Promise.allSettled([
      api.get('/api/v1/council/health'),
      api.get('/api/v1/council/sessions'),
    ])
    if (healthRes.status === 'fulfilled')   setHealth(healthRes.value.data)
    if (sessionsRes.status === 'fulfilled') setSessions(sessionsRes.value.data?.sessions || [])
    setLoading(false)
  }, [])

  useEffect(() => { load() }, [load])

  const convene = async (e, overrideQ) => {
    e?.preventDefault()
    const q = (overrideQ || question).trim()
    if (!q) return
    setConvening(true)
    setLastResult(null)
    if (overrideQ) setQuestion(overrideQ)
    try {
      const r = await api.post('/api/v1/council/convene', { question: q, context: {}, council_type: councilType })
      setLastResult(r.data)
      setQuestion('')
      await load()
    } catch (err) {
      setLastResult({ error: err.response?.data?.detail || err.message })
    }
    setConvening(false)
  }

  const models = health?.members || health?.models || []
  const availableModels = models.filter(m => m.available !== false)
  const quorumRequired  = health?.quorum_required ?? 5

  return (
    <div className="min-h-[calc(100vh-3.5rem)] p-6 pb-10 space-y-6">

      {/* Header */}
      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.22em] text-jarvis-cyan/70">Decision Intelligence</p>
          <h1 className="mt-2 text-3xl font-bold text-white">AI Council</h1>
          <p className="mt-2 max-w-2xl text-sm text-gray-400">
            {models.length}-model council for pricing, proposals, risk, and strategic decisions.
            Quorum requires {quorumRequired}+ models. Captain review required before execution.
          </p>
        </div>
        <button type="button" onClick={load} disabled={loading} className="btn-primary inline-flex items-center justify-center gap-2">
          {loading ? <Loader2 size={15} className="animate-spin" /> : <RefreshCw size={15} />}
          Refresh
        </button>
      </header>

      {/* Metric strip */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {[
          { label: 'Sessions', value: sessions.length, icon: <Users size={14} />, tone: 'text-jarvis-cyan' },
          {
            label: 'Active Models',
            value: `${availableModels.length} / ${models.length}`,
            icon: <Zap size={14} />,
            tone: availableModels.length >= quorumRequired ? 'text-green-300' : 'text-red-400',
          },
          {
            label: 'Council Status',
            value: availableModels.length >= quorumRequired ? 'Quorum Ready' : 'Below Quorum',
            icon: <Shield size={14} />,
            tone: availableModels.length >= quorumRequired ? 'text-green-300' : 'text-red-400',
          },
          {
            label: 'Last Session',
            value: sessions[0] ? fmtDate(sessions[0].created_at || sessions[0].convened_at) : '—',
            icon: <Clock size={14} />,
            tone: 'text-jarvis-gold',
          },
        ].map(m => (
          <div key={m.label} className="glass p-4">
            <div className="flex items-center gap-1.5 text-gray-400 mb-2">
              {m.icon}
              <p className="text-xs">{m.label}</p>
            </div>
            <p className={`text-lg font-bold ${m.tone}`}>{m.value}</p>
          </div>
        ))}
      </div>

      {/* Council members grid */}
      {models.length > 0 && (
        <section className="glass p-5">
          <h2 className="text-sm font-semibold text-white mb-3">
            Council Members
            <span className="ml-2 text-[10px] font-normal text-gray-500 uppercase tracking-wider">
              {availableModels.length} active
            </span>
          </h2>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-4">
            {models.map(m => (
              <div key={m.id || m.name || m.model} className={`rounded-lg border p-3 ${m.available !== false ? 'border-green-500/20 bg-green-500/5' : 'border-red-500/20 bg-red-500/5 opacity-50'}`}>
                <div className="flex items-center gap-2">
                  <div className={`h-1.5 w-1.5 rounded-full shrink-0 ${m.available !== false ? 'bg-green-400' : 'bg-red-400'}`} />
                  <span className="text-xs font-semibold text-white capitalize truncate">{(m.id || m.name || m.model || '').replace(/_/g, ' ')}</span>
                </div>
                <p className="text-[10px] text-gray-500 mt-1 truncate">{m.provider} · {m.specialty}</p>
                {m.weight != null && <p className="text-[10px] text-gray-600 mt-0.5">weight {(m.weight * 100).toFixed(0)}%</p>}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Convene form */}
      <section className="glass p-5">
        <div className="flex items-start justify-between mb-1">
          <div>
            <h2 className="text-sm font-semibold text-white">Convene Council</h2>
            <p className="text-xs text-gray-500 mt-0.5">Use for pricing, proposal strategy, client objections, delivery risk, or any high-stakes decision.</p>
          </div>
        </div>

        {/* Quick prompt chips */}
        <div className="flex flex-wrap gap-2 mt-3 mb-4">
          {QUICK_PROMPTS.map(qp => (
            <button
              key={qp.label}
              type="button"
              disabled={convening}
              onClick={() => convene(null, qp.prompt)}
              className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[11px] text-gray-300 hover:border-jarvis-cyan/40 hover:text-jarvis-cyan transition-colors disabled:opacity-40"
            >
              {qp.label}
            </button>
          ))}
        </div>

        <form onSubmit={convene} className="space-y-3">
          <textarea
            value={question}
            onChange={e => setQuestion(e.target.value)}
            rows={4}
            placeholder="Ask the council. Include context: deal size, client type, competing options, constraints, risk tolerance…"
            className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none placeholder:text-gray-500 focus:border-jarvis-cyan/60 resize-none"
          />
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <select
              value={councilType}
              onChange={e => setCouncilType(e.target.value)}
              className="flex-1 rounded-xl border border-white/10 bg-black/40 px-4 py-3 text-sm text-white outline-none focus:border-jarvis-cyan/60"
            >
              {COUNCIL_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
            <button type="submit" disabled={convening || !question.trim()} className="btn-primary inline-flex min-w-44 items-center justify-center gap-2">
              {convening ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />}
              {convening ? 'Convening…' : 'Convene Council'}
            </button>
          </div>
        </form>

        <CouncilResultPanel result={lastResult} />
      </section>

      {/* Session history */}
      <section className="glass p-5 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-white">Session History</h2>
          <p className="text-xs text-gray-500">{sessions.length} sessions</p>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-8 text-gray-500">
            <Loader2 size={18} className="animate-spin mr-2" />Loading…
          </div>
        ) : sessions.length === 0 ? (
          <div className="flex flex-col items-center py-10 text-gray-500">
            <Users size={32} className="mb-3 opacity-20" />
            <p className="text-sm">No sessions yet — convene the council above.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {sessions.map((s, i) => <SessionCard key={s.id || i} session={s} />)}
          </div>
        )}
      </section>
    </div>
  )
}
