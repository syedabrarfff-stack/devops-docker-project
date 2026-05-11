import { useState, useEffect } from 'react'
import {
  getJarvisMemory, getJarvisMemoryStats, storeJarvisMemory,
  triggerEvolution, getEvolutionLog,
} from '../../services/api'

const MEMORY_TYPE_COLORS = {
  episodic:    { bg: 'bg-blue-500/20',   text: 'text-blue-400',   label: 'Episodic' },
  semantic:    { bg: 'bg-purple-500/20', text: 'text-purple-400', label: 'Semantic' },
  instruction: { bg: 'bg-yellow-500/20', text: 'text-yellow-400', label: 'Instruction' },
  learning:    { bg: 'bg-green-500/20',  text: 'text-green-400',  label: 'Learning' },
  working:     { bg: 'bg-slate-500/20',  text: 'text-slate-400',  label: 'Working' },
}

export default function EvolutionDashboard() {
  const [tab, setTab] = useState('memory') // memory | evolution | teach
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

      </div>
    </div>
  )
}
