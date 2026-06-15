import React, { useCallback, useEffect, useState } from 'react'
import { CheckCircle2, ChevronDown, ChevronRight, Loader2, RefreshCw, Send, Users, Zap } from 'lucide-react'
import api from '../../services/api'

const COUNCIL_TYPES = [
  { value: 'standard', label: 'Standard — balanced multi-model reasoning' },
  { value: 'strategic', label: 'Strategic — long-horizon business decisions' },
  { value: 'technical', label: 'Technical — engineering and architecture' },
  { value: 'financial', label: 'Financial — pricing, revenue, risk' },
  { value: 'rapid', label: 'Rapid — fast single-model answer' },
]

function fmtDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function VoteBadge({ vote }) {
  const cfg = {
    agree:     'border-green-500/30 bg-green-500/10 text-green-300',
    disagree:  'border-red-500/30 bg-red-500/10 text-red-300',
    abstain:   'border-gray-500/30 bg-gray-500/10 text-gray-400',
    uncertain: 'border-yellow-500/30 bg-yellow-500/10 text-yellow-300',
  }[vote?.toLowerCase()] || 'border-gray-500/30 bg-gray-500/10 text-gray-300'
  return <span className={`inline-flex rounded-full border px-2 py-0.5 text-[10px] font-semibold ${cfg}`}>{vote}</span>
}

function SessionCard({ session }) {
  const [open, setOpen] = useState(false)
  const confidence = session.confidence != null ? Math.round(session.confidence * 100) : null
  return (
    <div className="rounded-xl border border-white/10 bg-white/5">
      <button type="button" onClick={() => setOpen(v => !v)} className="flex w-full items-start gap-3 p-4 text-left">
        {open ? <ChevronDown size={13} className="mt-0.5 shrink-0 text-gray-400" /> : <ChevronRight size={13} className="mt-0.5 shrink-0 text-gray-400" />}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-white line-clamp-2">{session.question}</p>
          <div className="flex items-center gap-3 mt-1 flex-wrap">
            <span className="text-[10px] text-gray-500">{fmtDate(session.created_at || session.convened_at)}</span>
            {session.council_type && (
              <span className="text-[10px] text-gray-600 uppercase tracking-wider">{session.council_type}</span>
            )}
            {confidence != null && (
              <span className={`text-[10px] font-medium ${confidence >= 70 ? 'text-green-400' : confidence >= 50 ? 'text-jarvis-gold' : 'text-red-400'}`}>
                {confidence}% confidence
              </span>
            )}
          </div>
        </div>
      </button>
      {open && (
        <div className="border-t border-white/10 px-4 pb-4 pt-3 space-y-3">
          {session.consensus_answer && (
            <div>
              <p className="text-[10px] font-semibold text-jarvis-cyan uppercase tracking-wider mb-1">Council Decision</p>
              <p className="text-sm text-gray-200 leading-relaxed">{session.consensus_answer}</p>
            </div>
          )}
          {session.reasoning && (
            <div>
              <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1">Reasoning</p>
              <p className="text-xs text-gray-400 leading-relaxed">{session.reasoning}</p>
            </div>
          )}
          {session.member_votes?.length > 0 && (
            <div>
              <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2">Member Votes</p>
              <div className="space-y-2">
                {session.member_votes.map((v, i) => (
                  <div key={i} className="flex items-start gap-3">
                    <VoteBadge vote={v.vote} />
                    <div>
                      <span className="text-xs font-medium text-gray-300">{v.model}</span>
                      {v.rationale && <p className="text-xs text-gray-500 mt-0.5">{v.rationale}</p>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
          {session.action_items?.length > 0 && (
            <div>
              <p className="text-[10px] font-semibold text-green-400 uppercase tracking-wider mb-1">Action Items</p>
              <ul className="space-y-1">
                {session.action_items.map((a, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-gray-300">
                    <CheckCircle2 size={10} className="mt-0.5 shrink-0 text-green-400" />{a}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function CouncilView() {
  const [health, setHealth] = useState(null)
  const [sessions, setSessions] = useState([])
  const [loading, setLoading] = useState(true)
  const [question, setQuestion] = useState('')
  const [councilType, setCouncilType] = useState('standard')
  const [convening, setConvening] = useState(false)
  const [lastResult, setLastResult] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    const [healthRes, sessionsRes] = await Promise.allSettled([
      api.get('/api/v1/council/health'),
      api.get('/api/v1/council/sessions'),
    ])
    if (healthRes.status === 'fulfilled') setHealth(healthRes.value.data)
    if (sessionsRes.status === 'fulfilled') setSessions(sessionsRes.value.data?.sessions || [])
    setLoading(false)
  }, [])

  useEffect(() => { load() }, [load])

  const convene = async (e) => {
    e.preventDefault()
    if (!question.trim()) return
    setConvening(true)
    setLastResult(null)
    try {
      const r = await api.post('/api/v1/council/convene', { question, context: {}, council_type: councilType })
      setLastResult(r.data)
      setQuestion('')
      await load()
    } catch (err) {
      setLastResult({ error: err.response?.data?.detail || err.message })
    }
    setConvening(false)
  }

  const models = health?.models || []
  const availableModels = models.filter(m => m.available !== false)

  return (
    <div className="min-h-[calc(100vh-3.5rem)] p-6 pb-10 space-y-6">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.22em] text-jarvis-cyan/70">Decision Intelligence</p>
          <h1 className="mt-2 text-3xl font-bold text-white">Council Sessions</h1>
          <p className="mt-2 max-w-2xl text-sm text-gray-400">
            Multi-model AI council for pricing, proposal, risk, and strategic decisions — Captain review required for execution.
          </p>
        </div>
        <button type="button" onClick={load} disabled={loading} className="btn-primary inline-flex items-center justify-center gap-2">
          {loading ? <Loader2 size={15} className="animate-spin" /> : <RefreshCw size={15} />}
          Refresh
        </button>
      </header>

      {/* Metrics */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {[
          { label: 'Total Sessions', value: sessions.length, tone: 'text-jarvis-cyan' },
          { label: 'Active Models', value: availableModels.length, tone: 'text-green-300' },
          { label: 'Council Status', value: health?.status === 'operational' ? 'Online' : (health?.status || '—'), tone: health?.status === 'operational' ? 'text-green-300' : 'text-red-400' },
          { label: 'Last Session', value: sessions[0] ? fmtDate(sessions[0].created_at || sessions[0].convened_at) : '—', tone: 'text-jarvis-gold' },
        ].map(m => (
          <div key={m.label} className="glass p-5">
            <p className="text-xs text-gray-400">{m.label}</p>
            <p className={`mt-2 text-lg font-bold ${m.tone}`}>{m.value}</p>
          </div>
        ))}
      </div>

      {/* Model health grid */}
      {models.length > 0 && (
        <section className="glass p-5">
          <h2 className="text-sm font-semibold text-white mb-3">Council Members</h2>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-4">
            {models.map(m => (
              <div key={m.name || m.model} className={`rounded-xl border p-3 ${m.available !== false ? 'border-green-500/20 bg-green-500/5' : 'border-red-500/20 bg-red-500/5'}`}>
                <div className="flex items-center gap-2">
                  <div className={`h-1.5 w-1.5 rounded-full ${m.available !== false ? 'bg-green-400' : 'bg-red-400'}`} />
                  <span className="text-xs font-semibold text-white capitalize">{(m.name || m.model || '').replace(/_/g, ' ')}</span>
                </div>
                {m.weight != null && <p className="text-[10px] text-gray-500 mt-1">weight {m.weight}</p>}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Convene form */}
      <section className="glass p-5">
        <h2 className="text-sm font-semibold text-white mb-1">New Council Question</h2>
        <p className="text-xs text-gray-500 mb-4">Use for pricing, proposal strategy, client objections, delivery risk, or any high-stakes decision.</p>
        <form onSubmit={convene} className="space-y-3">
          <textarea
            value={question}
            onChange={e => setQuestion(e.target.value)}
            rows={4}
            placeholder="Ask the council what decision should be made. Include context: deal size, client type, competing options, constraints…"
            className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none placeholder:text-gray-500 focus:border-jarvis-cyan/60"
          />
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <select
              value={councilType}
              onChange={e => setCouncilType(e.target.value)}
              className="flex-1 rounded-xl border border-white/10 bg-black/40 px-4 py-3 text-sm text-white outline-none focus:border-jarvis-cyan/60"
            >
              {COUNCIL_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
            <button type="submit" disabled={convening || !question.trim()} className="btn-primary inline-flex min-w-40 items-center justify-center gap-2">
              {convening ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />}
              {convening ? 'Convening…' : 'Convene Council'}
            </button>
          </div>
        </form>

        {lastResult && !lastResult.error && (
          <div className="mt-4 rounded-xl border border-jarvis-cyan/20 bg-jarvis-cyan/5 p-4">
            <div className="flex items-center gap-2 mb-2">
              <Zap size={13} className="text-jarvis-cyan" />
              <p className="text-xs font-semibold text-jarvis-cyan">Council Decision</p>
              {lastResult.confidence != null && (
                <span className="ml-auto text-xs text-gray-400">{Math.round(lastResult.confidence * 100)}% confidence</span>
              )}
            </div>
            <p className="text-sm text-gray-200 leading-relaxed">{lastResult.consensus_answer}</p>
            {lastResult.action_items?.length > 0 && (
              <div className="mt-3">
                <p className="text-[10px] font-semibold text-green-400 uppercase tracking-wider mb-1">Action Items</p>
                <ul className="space-y-1">
                  {lastResult.action_items.map((a, i) => (
                    <li key={i} className="flex items-start gap-2 text-xs text-gray-300">
                      <CheckCircle2 size={10} className="mt-0.5 shrink-0 text-green-400" />{a}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {lastResult?.error && (
          <div className="mt-4 rounded-lg border border-red-400/20 bg-red-400/10 p-3 text-sm text-red-200">
            {lastResult.error}
          </div>
        )}
      </section>

      {/* Session history */}
      <section className="glass p-5 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-white">Session History</h2>
          <p className="text-xs text-gray-500">{sessions.length} sessions</p>
        </div>
        {loading ? (
          <div className="flex items-center justify-center py-8 text-gray-500"><Loader2 size={18} className="animate-spin mr-2" />Loading…</div>
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
