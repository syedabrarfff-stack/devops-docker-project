import { useState, useEffect } from 'react'
import {
  getJarvisMemory, getJarvisMemoryStats, storeJarvisMemory,
  triggerEvolution, getEvolutionLog, getJarvisSelfImprovement,
  enhanceIdea, spawnAgentTeam, getJarvisAuthority,
  getJarvisBriefing, getJarvisGreeting, logOutcome, resolveOutcome,
} from '../../services/api'
import api from '../../services/api'

const MEMORY_TYPE_COLORS = {
  episodic:    { bg: 'bg-blue-500/20',   text: 'text-blue-400',   label: 'Episodic' },
  semantic:    { bg: 'bg-purple-500/20', text: 'text-purple-400', label: 'Semantic' },
  instruction: { bg: 'bg-yellow-500/20', text: 'text-yellow-400', label: 'Instruction' },
  learning:    { bg: 'bg-green-500/20',  text: 'text-green-400',  label: 'Learning' },
  working:     { bg: 'bg-slate-500/20',  text: 'text-slate-400',  label: 'Working' },
}

export default function EvolutionDashboard() {
  const [tab, setTab] = useState('memory') // memory | evolution | teach | capabilities
  const [memories, setMemories] = useState([])
  const [stats, setStats] = useState(null)
  const [evolutionLog, setEvolutionLog] = useState([])
  const [query, setQuery] = useState('')
  const [filterType, setFilterType] = useState('')
  const [loading, setLoading] = useState(false)
  const [evolving, setEvolving] = useState(false)
  const [evolveResult, setEvolveResult] = useState(null)
  const [teachInput, setTeachInput] = useState('')
  const [teachType, setTeachType] = useState('instruction')
  const [teachSaving, setTeachSaving] = useState(false)
  const [teachSuccess, setTeachSuccess] = useState(false)

  useEffect(() => {
    loadStats()
    if (tab === 'memory') loadMemories()
    if (tab === 'evolution') loadEvolutionLog()
  }, [tab])

  async function loadStats() {
    try {
      const data = await getJarvisMemoryStats()
      setStats(data)
    } catch (e) {}
  }

  async function loadMemories() {
    setLoading(true)
    try {
      const data = await getJarvisMemory(query, filterType || null, 30)
      setMemories(data.memories || [])
    } catch (e) {} finally {
      setLoading(false)
    }
  }

  async function loadEvolutionLog() {
    setLoading(true)
    try {
      const data = await getEvolutionLog(10)
      setEvolutionLog(data.history || [])
    } catch (e) {} finally {
      setLoading(false)
    }
  }

  async function handleSearch(e) {
    e.preventDefault()
    await loadMemories()
  }

  async function handleEvolve() {
    setEvolving(true)
    setEvolveResult(null)
    try {
      const result = await triggerEvolution()
      setEvolveResult(result)
      await loadEvolutionLog()
      await loadStats()
    } catch (e) {
      setEvolveResult({ error: e.message })
    } finally {
      setEvolving(false)
    }
  }

  async function handleTeach() {
    if (!teachInput.trim()) return
    setTeachSaving(true)
    try {
      await storeJarvisMemory(teachInput.trim(), teachType, teachType === 'instruction' ? 1.0 : 0.8, [teachType])
      setTeachInput('')
      setTeachSuccess(true)
      setTimeout(() => setTeachSuccess(false), 3000)
      await loadStats()
    } catch (e) {} finally {
      setTeachSaving(false)
    }
  }

  // Capabilities tab state and handlers
  const [capLoading, setCapLoading] = useState(false)
  const [capResult, setCapResult] = useState(null)
  const [selfImprovement, setSelfImprovement] = useState(null)
  const [authority, setAuthority] = useState(null)
  const [ideaText, setIdeaText] = useState('')
  const [spawnTask, setSpawnTask] = useState('')
  const [capError, setCapError] = useState(null)
  const [outcomeForm, setOutcomeForm] = useState({ action_type: 'decision', action_detail: '', action_ref: '', importance: '0.6' })
  const [resolveForm, setResolveForm] = useState({ outcome_id: '', outcome: '', note: '' })
  const setOF = k => v => setOutcomeForm(f => ({ ...f, [k]: v }))
  const setRF = k => v => setResolveForm(f => ({ ...f, [k]: v }))

  useEffect(() => {
    if (tab === 'capabilities' && !selfImprovement) {
      getJarvisSelfImprovement().then(d => setSelfImprovement(d)).catch(() => {})
      getJarvisAuthority().then(d => setAuthority(d)).catch(() => {})
    }
  }, [tab])

  async function runCapability(label, fn) {
    setCapLoading(true); setCapResult(null); setCapError(null)
    try {
      const r = await fn()
      setCapResult({ label, ...r })
    } catch (err) {
      setCapError({ label, error: err.message })
    }
    setCapLoading(false)
  }

  return (
    <div className="h-full flex flex-col overflow-hidden p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">JARVIS Self-Evolution</h1>
          <p className="text-slate-400 text-sm mt-1">
            Memory system · Daily learning · Continuous improvement
          </p>
        </div>
        {stats && (
          <div className="flex gap-4 text-right">
            <div>
              <p className="text-2xl font-bold text-blue-400">{stats.total || 0}</p>
              <p className="text-slate-500 text-xs">Total Memories</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-green-400">{stats.by_type?.learning || 0}</p>
              <p className="text-slate-500 text-xs">Learnings</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-yellow-400">{stats.by_type?.instruction || 0}</p>
              <p className="text-slate-500 text-xs">Instructions</p>
            </div>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-slate-800/50 p-1 rounded-xl w-fit">
        {[
          { id: 'memory', label: 'Memory Bank' },
          { id: 'evolution', label: 'Evolution Log' },
          { id: 'teach', label: 'Teach JARVIS' },
          { id: 'capabilities', label: 'Capabilities' },
        ].map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              tab === t.id
                ? 'bg-blue-600 text-white'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto no-scrollbar">

        {/* Memory Bank */}
        {tab === 'memory' && (
          <div className="space-y-4">
            <form onSubmit={handleSearch} className="flex gap-3">
              <input
                value={query}
                onChange={e => setQuery(e.target.value)}
                placeholder="Search JARVIS memory..."
                className="flex-1 bg-slate-800/60 border border-slate-700/50 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:border-blue-500/50 placeholder-slate-500"
              />
              <select
                value={filterType}
                onChange={e => setFilterType(e.target.value)}
                className="bg-slate-800/60 border border-slate-700/50 rounded-xl px-4 py-3 text-slate-300 text-sm focus:outline-none"
              >
                <option value="">All Types</option>
                <option value="episodic">Episodic</option>
                <option value="semantic">Semantic</option>
                <option value="instruction">Instructions</option>
                <option value="learning">Learnings</option>
              </select>
              <button
                type="submit"
                className="px-5 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-sm font-medium transition-colors"
              >
                Search
              </button>
            </form>

            {loading ? (
              <div className="space-y-3">
                {[1,2,3,4,5].map(i => (
                  <div key={i} className="h-20 bg-slate-800/40 rounded-xl animate-pulse" />
                ))}
              </div>
            ) : memories.length === 0 ? (
              <div className="text-center py-16">
                <p className="text-slate-500 text-lg">No memories yet</p>
                <p className="text-slate-600 text-sm mt-2">Start chatting with JARVIS — every conversation is remembered</p>
              </div>
            ) : (
              <div className="space-y-3">
                {memories.map(m => {
                  const typeStyle = MEMORY_TYPE_COLORS[m.type] || MEMORY_TYPE_COLORS.working
                  return (
                    <div key={m.id} className="bg-slate-800/60 border border-slate-700/30 rounded-xl p-4">
                      <div className="flex items-start justify-between gap-3 mb-2">
                        <span className={`text-xs px-2 py-0.5 rounded-full ${typeStyle.bg} ${typeStyle.text} flex-shrink-0`}>
                          {typeStyle.label}
                        </span>
                        <div className="flex items-center gap-3 text-xs text-slate-600">
                          <span>importance: {(m.importance * 100).toFixed(0)}%</span>
                          <span>accessed: {m.access_count}x</span>
                          <span>{new Date(m.created_at).toLocaleDateString()}</span>
                        </div>
                      </div>
                      <p className="text-slate-200 text-sm leading-relaxed">{m.content}</p>
                      {m.tags?.length > 0 && (
                        <div className="flex gap-1.5 mt-2 flex-wrap">
                          {m.tags.map((tag, i) => (
                            <span key={i} className="text-xs text-slate-500 bg-slate-700/50 px-2 py-0.5 rounded">
                              {tag}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )}

        {/* Evolution Log */}
        {tab === 'evolution' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <p className="text-slate-400 text-sm">
                JARVIS runs a self-learning cycle daily at midnight. Each cycle reviews the day's activity, extracts insights, and stores learnings permanently.
              </p>
              <button
                onClick={handleEvolve}
                disabled={evolving}
                className="px-5 py-2.5 bg-green-600 hover:bg-green-500 disabled:opacity-50 text-white rounded-xl text-sm font-medium transition-colors flex-shrink-0 ml-4"
              >
                {evolving ? 'Evolving...' : 'Run Now'}
              </button>
            </div>

            {evolveResult && (
              <div className={`p-4 rounded-xl border text-sm ${evolveResult.error ? 'bg-red-500/10 border-red-500/30 text-red-300' : 'bg-green-500/10 border-green-500/30 text-green-300'}`}>
                {evolveResult.error ? (
                  <p>Evolution failed: {evolveResult.error}</p>
                ) : (
                  <div className="space-y-1">
                    <p className="font-medium">Evolution cycle complete</p>
                    <p>Conversations reviewed: {evolveResult.conversations_reviewed}</p>
                    <p>Facts extracted: {evolveResult.facts_extracted}</p>
                    <p>Learnings stored: {evolveResult.learnings_stored}</p>
                  </div>
                )}
              </div>
            )}

            {loading ? (
              <div className="space-y-4">
                {[1,2,3].map(i => <div key={i} className="h-40 bg-slate-800/40 rounded-xl animate-pulse" />)}
              </div>
            ) : evolutionLog.length === 0 ? (
              <div className="text-center py-16">
                <p className="text-slate-500 text-lg">No evolution reports yet</p>
                <p className="text-slate-600 text-sm mt-2">Click "Run Now" to trigger the first learning cycle</p>
              </div>
            ) : (
              <div className="space-y-4">
                {evolutionLog.map((entry, i) => (
                  <div key={i} className="bg-slate-800/60 border border-green-500/20 rounded-xl p-5">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-green-400 text-sm font-medium">JARVIS Self-Learning Report</span>
                      <span className="text-slate-500 text-xs">{new Date(entry.date).toLocaleString()}</span>
                    </div>
                    <p className="text-slate-200 text-sm leading-relaxed whitespace-pre-wrap">{entry.report}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Teach JARVIS */}
        {tab === 'teach' && (
          <div className="max-w-2xl space-y-6">
            <div className="bg-slate-800/60 border border-yellow-500/20 rounded-xl p-5">
              <h3 className="text-yellow-400 font-semibold mb-2">Teach JARVIS</h3>
              <p className="text-slate-400 text-sm leading-relaxed">
                Give JARVIS a standing order, a preference, or a fact about Aliyar Solutions. It will remember this permanently and use it in every future response.
              </p>
            </div>

            <div className="space-y-4">
              <div>
                <label className="text-slate-400 text-sm mb-2 block">Memory Type</label>
                <div className="flex gap-2">
                  {[
                    { id: 'instruction', label: 'Standing Order', desc: 'A rule JARVIS must always follow' },
                    { id: 'semantic', label: 'Company Fact', desc: 'Knowledge about Aliyar Solutions' },
                    { id: 'learning', label: 'Lesson Learned', desc: 'Something that happened and what to do next time' },
                  ].map(type => (
                    <button
                      key={type.id}
                      onClick={() => setTeachType(type.id)}
                      className={`flex-1 p-3 rounded-xl border text-left transition-colors ${
                        teachType === type.id
                          ? 'border-blue-500/50 bg-blue-500/10'
                          : 'border-slate-700/50 bg-slate-800/40 hover:border-slate-600'
                      }`}
                    >
                      <p className="text-white text-sm font-medium">{type.label}</p>
                      <p className="text-slate-500 text-xs mt-0.5">{type.desc}</p>
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-slate-400 text-sm mb-2 block">What to remember</label>
                <textarea
                  value={teachInput}
                  onChange={e => setTeachInput(e.target.value)}
                  placeholder={
                    teachType === 'instruction'
                      ? 'e.g. "Always prioritise retainer clients over one-off projects"'
                      : teachType === 'semantic'
                      ? 'e.g. "Our main target market is SaaS companies with 10-100 employees"'
                      : 'e.g. "When proposing at $8k, healthcare clients always negotiate down. Start at $10k."'
                  }
                  rows={4}
                  className="w-full bg-slate-900/60 border border-slate-600/50 rounded-xl px-4 py-3 text-white text-sm resize-none focus:outline-none focus:border-blue-500/50 placeholder-slate-500"
                />
              </div>

              <button
                onClick={handleTeach}
                disabled={!teachInput.trim() || teachSaving}
                className="px-6 py-3 bg-yellow-600 hover:bg-yellow-500 disabled:opacity-40 text-white rounded-xl text-sm font-medium transition-colors"
              >
                {teachSaving ? 'Storing...' : teachSuccess ? 'Stored in JARVIS Memory ✓' : 'Teach JARVIS'}
              </button>
            </div>

            <div className="bg-slate-800/40 border border-slate-700/30 rounded-xl p-4">
              <p className="text-slate-500 text-xs leading-relaxed">
                <strong className="text-slate-400">How it works:</strong> Every time JARVIS responds to you, it first searches its memory bank for relevant context. Instructions are always included. Semantic facts are included when relevant. Learnings are surfaced when a similar situation arises.
              </p>
            </div>
          </div>
        )}

        {/* Capabilities Tab */}
        {tab === 'capabilities' && (
          <div className="space-y-5">
            {/* Authority */}
            {authority && (
              <div className="rounded-xl border border-slate-700/40 bg-slate-800/40 p-4">
                <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">JARVIS Authority Level</p>
                <pre className="text-xs text-slate-300 overflow-auto max-h-40">{JSON.stringify(authority, null, 2)}</pre>
              </div>
            )}

            {/* Self-Improvement */}
            {selfImprovement && (
              <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-4">
                <p className="text-xs font-bold uppercase tracking-wider text-blue-400/70 mb-2">Self-Improvement Recommendations</p>
                <pre className="text-xs text-slate-300 overflow-auto max-h-40">{JSON.stringify(selfImprovement, null, 2)}</pre>
              </div>
            )}

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              {/* Enhance Idea */}
              <div className="rounded-xl border border-slate-700/40 bg-slate-800/40 p-4 space-y-3">
                <p className="text-xs font-bold uppercase tracking-wider text-purple-400/70">Enhance Idea with AI</p>
                <textarea
                  value={ideaText}
                  onChange={e => setIdeaText(e.target.value)}
                  placeholder="Paste any idea, strategy, or concept to enhance…"
                  rows={3}
                  className="w-full bg-slate-900/50 border border-slate-600/40 rounded-xl px-4 py-3 text-white text-xs focus:outline-none focus:border-purple-500/50 resize-none placeholder-slate-600"
                />
                <button
                  onClick={() => runCapability('Enhanced Idea', () => enhanceIdea(ideaText))}
                  disabled={capLoading || !ideaText.trim()}
                  className="w-full py-2 rounded-xl bg-purple-600/80 hover:bg-purple-500 disabled:opacity-40 text-white text-xs font-medium transition-colors"
                >
                  {capLoading ? 'Processing…' : '✨ Enhance'}
                </button>
              </div>

              {/* Spawn Agent Team */}
              <div className="rounded-xl border border-slate-700/40 bg-slate-800/40 p-4 space-y-3">
                <p className="text-xs font-bold uppercase tracking-wider text-cyan-400/70">Spawn Agent Team</p>
                <textarea
                  value={spawnTask}
                  onChange={e => setSpawnTask(e.target.value)}
                  placeholder="Describe the task for the agent team to execute…"
                  rows={3}
                  className="w-full bg-slate-900/50 border border-slate-600/40 rounded-xl px-4 py-3 text-white text-xs focus:outline-none focus:border-cyan-500/50 resize-none placeholder-slate-600"
                />
                <button
                  onClick={() => runCapability('Agent Team', () => spawnAgentTeam(spawnTask))}
                  disabled={capLoading || !spawnTask.trim()}
                  className="w-full py-2 rounded-xl bg-cyan-600/80 hover:bg-cyan-500 disabled:opacity-40 text-white text-xs font-medium transition-colors"
                >
                  {capLoading ? 'Spawning…' : '⚡ Spawn Team'}
                </button>
              </div>
            </div>

            {/* Quick reads */}
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div className="rounded-xl border border-slate-700/40 bg-slate-800/40 p-4 space-y-3">
                <p className="text-xs font-bold uppercase tracking-wider text-yellow-400/70">JARVIS Briefing</p>
                <p className="text-xs text-slate-400">Morning intelligence brief — pipeline, threats, scheduled tasks.</p>
                <button
                  onClick={() => runCapability('JARVIS Briefing', getJarvisBriefing)}
                  disabled={capLoading}
                  className="w-full py-2 rounded-xl bg-yellow-600/80 hover:bg-yellow-500 disabled:opacity-40 text-white text-xs font-medium transition-colors"
                >
                  {capLoading ? 'Loading…' : 'Get Briefing'}
                </button>
              </div>
              <div className="rounded-xl border border-slate-700/40 bg-slate-800/40 p-4 space-y-3">
                <p className="text-xs font-bold uppercase tracking-wider text-green-400/70">JARVIS Greeting</p>
                <p className="text-xs text-slate-400">Context-aware greeting from JARVIS for the current session.</p>
                <button
                  onClick={() => runCapability('JARVIS Greeting', getJarvisGreeting)}
                  disabled={capLoading}
                  className="w-full py-2 rounded-xl bg-green-600/80 hover:bg-green-500 disabled:opacity-40 text-white text-xs font-medium transition-colors"
                >
                  {capLoading ? 'Loading…' : 'Get Greeting'}
                </button>
              </div>
            </div>

            {/* Outcome tracking */}
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div className="rounded-xl border border-slate-700/40 bg-slate-800/40 p-4 space-y-3">
                <p className="text-xs font-bold uppercase tracking-wider text-orange-400/70">Log JARVIS Outcome</p>
                <select
                  value={outcomeForm.action_type}
                  onChange={e => setOF('action_type')(e.target.value)}
                  className="w-full bg-slate-900/50 border border-slate-600/40 rounded-xl px-3 py-2 text-white text-xs outline-none"
                >
                  {['decision', 'outreach', 'proposal', 'research', 'automation', 'escalation', 'client_action', 'system_action'].map(t => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
                <textarea
                  value={outcomeForm.action_detail}
                  onChange={e => setOF('action_detail')(e.target.value)}
                  placeholder="What action did JARVIS take?"
                  rows={2}
                  className="w-full bg-slate-900/50 border border-slate-600/40 rounded-xl px-3 py-2 text-white text-xs outline-none resize-none placeholder-slate-600"
                />
                <div className="grid grid-cols-2 gap-2">
                  <input
                    value={outcomeForm.action_ref}
                    onChange={e => setOF('action_ref')(e.target.value)}
                    placeholder="Reference ID (opt)"
                    className="bg-slate-900/50 border border-slate-600/40 rounded-xl px-3 py-2 text-white text-xs outline-none placeholder-slate-600"
                  />
                  <input
                    type="number" step="0.1" min="0" max="1"
                    value={outcomeForm.importance}
                    onChange={e => setOF('importance')(e.target.value)}
                    placeholder="Importance 0-1"
                    className="bg-slate-900/50 border border-slate-600/40 rounded-xl px-3 py-2 text-white text-xs outline-none placeholder-slate-600"
                  />
                </div>
                <button
                  onClick={() => runCapability('Log Outcome', () => logOutcome(
                    outcomeForm.action_type,
                    outcomeForm.action_detail,
                    outcomeForm.action_ref || null,
                    parseFloat(outcomeForm.importance) || 0.6,
                  ))}
                  disabled={capLoading || !outcomeForm.action_detail.trim()}
                  className="w-full py-2 rounded-xl bg-orange-600/80 hover:bg-orange-500 disabled:opacity-40 text-white text-xs font-medium transition-colors"
                >
                  {capLoading ? 'Logging…' : 'Log Outcome'}
                </button>
              </div>

              <div className="rounded-xl border border-slate-700/40 bg-slate-800/40 p-4 space-y-3">
                <p className="text-xs font-bold uppercase tracking-wider text-rose-400/70">Resolve Outcome</p>
                <p className="text-xs text-slate-400">Mark what actually happened so JARVIS learns from this action.</p>
                <input
                  value={resolveForm.outcome_id}
                  onChange={e => setRF('outcome_id')(e.target.value)}
                  placeholder="Outcome ID (from Log response)"
                  className="w-full bg-slate-900/50 border border-slate-600/40 rounded-xl px-3 py-2 text-white text-xs outline-none placeholder-slate-600"
                />
                <input
                  value={resolveForm.outcome}
                  onChange={e => setRF('outcome')(e.target.value)}
                  placeholder="What happened? (e.g. 'won', 'declined', 'no response')"
                  className="w-full bg-slate-900/50 border border-slate-600/40 rounded-xl px-3 py-2 text-white text-xs outline-none placeholder-slate-600"
                />
                <textarea
                  value={resolveForm.note}
                  onChange={e => setRF('note')(e.target.value)}
                  placeholder="Captain's note (optional — why this happened)"
                  rows={2}
                  className="w-full bg-slate-900/50 border border-slate-600/40 rounded-xl px-3 py-2 text-white text-xs outline-none resize-none placeholder-slate-600"
                />
                <button
                  onClick={() => runCapability('Resolve Outcome', () => resolveOutcome(
                    resolveForm.outcome_id.trim(),
                    resolveForm.outcome.trim(),
                    resolveForm.note.trim() || null,
                  ))}
                  disabled={capLoading || !resolveForm.outcome_id.trim() || !resolveForm.outcome.trim()}
                  className="w-full py-2 rounded-xl bg-rose-600/80 hover:bg-rose-500 disabled:opacity-40 text-white text-xs font-medium transition-colors"
                >
                  {capLoading ? 'Resolving…' : 'Resolve & Teach JARVIS'}
                </button>
              </div>
            </div>

            {(capResult || capError) && (
              <div className={`rounded-xl border p-4 ${capError ? 'border-red-500/25 bg-red-500/10' : 'border-slate-700/40 bg-slate-800/40'}`}>
                <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                  {capError ? `Error — ${capError.label}` : `Result — ${capResult?.label}`}
                </p>
                <pre className="text-xs text-slate-300 overflow-auto max-h-60">
                  {JSON.stringify(capResult || capError, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  )
}
