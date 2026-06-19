import React, { useCallback, useEffect, useState } from 'react'
import { BookOpen, ChevronDown, ChevronRight, FileText, Lightbulb, Loader2, Plus, RefreshCw, Search, Sparkles, TrendingUp, X } from 'lucide-react'
import api from '../../services/api'

const SOP_CATEGORIES = ['general', 'client_onboarding', 'proposal', 'delivery', 'invoicing', 'outreach', 'security', 'infrastructure', 'ai_operations']
const LEARNING_TYPES = ['success', 'failure', 'near_miss', 'insight']
const IMPACT_COLORS = { 9: 'text-green-300', 8: 'text-green-400', 7: 'text-jarvis-cyan', 6: 'text-jarvis-gold', 5: 'text-gray-300', 4: 'text-gray-400', 3: 'text-orange-400', 2: 'text-red-400', 1: 'text-red-500' }

function EventBadge({ type }) {
  const cfg = {
    success:   { cls: 'border-green-500/30 bg-green-500/10 text-green-300',  label: 'Success' },
    failure:   { cls: 'border-red-500/30 bg-red-500/10 text-red-300',        label: 'Failure' },
    near_miss: { cls: 'border-orange-500/30 bg-orange-500/10 text-orange-300', label: 'Near Miss' },
    insight:   { cls: 'border-blue-500/30 bg-blue-500/10 text-blue-300',     label: 'Insight' },
  }[type] || { cls: 'border-gray-500/30 bg-gray-500/10 text-gray-300', label: type }
  return <span className={`inline-flex rounded-full border px-2.5 py-0.5 text-[11px] font-semibold tracking-wide ${cfg.cls}`}>{cfg.label}</span>
}

function ExpandableCard({ title, children, badge }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="rounded-xl border border-white/10 bg-white/5">
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        className="flex w-full items-center justify-between p-4 text-left"
      >
        <div className="flex items-center gap-3 min-w-0">
          {open ? <ChevronDown size={14} className="shrink-0 text-gray-400" /> : <ChevronRight size={14} className="shrink-0 text-gray-400" />}
          <span className="text-sm font-medium text-white truncate">{title}</span>
          {badge}
        </div>
      </button>
      {open && <div className="border-t border-white/10 px-4 pb-4 pt-3">{children}</div>}
    </div>
  )
}

export default function KnowledgeView() {
  const [tab, setTab] = useState('sops')
  const [stats, setStats] = useState(null)
  const [sops, setSops] = useState([])
  const [learnings, setLearnings] = useState([])
  const [searchResults, setSearchResults] = useState(null)
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchLoading, setSearchLoading] = useState(false)
  const [sopForm, setSopForm] = useState({ title: '', category: 'general', context: '' })
  const [sopGenerating, setSopGenerating] = useState(false)
  const [learnForm, setLearnForm] = useState({ title: '', category: 'delivery', event_type: 'success', what_happened: '', lesson: '', what_worked: '', what_failed: '', impact_score: 7 })
  const [learnLoading, setLearnLoading] = useState(false)
  const [showLearnForm, setShowLearnForm] = useState(false)
  const [showSopForm, setShowSopForm] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    const [statsRes, sopsRes, learnRes] = await Promise.allSettled([
      api.get('/api/v1/knowledge/stats'),
      api.get('/api/v1/knowledge/sops'),
      api.get('/api/v1/knowledge/learnings', { params: { limit: 50 } }),
    ])
    if (statsRes.status === 'fulfilled') setStats(statsRes.value.data)
    if (sopsRes.status === 'fulfilled') setSops(sopsRes.value.data?.sops || [])
    if (learnRes.status === 'fulfilled') setLearnings(learnRes.value.data?.learnings || [])
    setLoading(false)
  }, [])

  useEffect(() => { load() }, [load])

  const search = async () => {
    if (!searchQuery.trim()) return
    setSearchLoading(true)
    try {
      const r = await api.get('/api/v1/knowledge/search', { params: { q: searchQuery } })
      setSearchResults(r.data?.results || [])
    } catch { setSearchResults([]) }
    setSearchLoading(false)
  }

  const generateSop = async (e) => {
    e.preventDefault()
    if (!sopForm.title.trim()) return
    setSopGenerating(true)
    try {
      await api.post('/api/v1/knowledge/sops/generate', sopForm)
      setSopForm({ title: '', category: 'general', context: '' })
      setShowSopForm(false)
      await load()
    } catch {}
    setSopGenerating(false)
  }

  const logLearning = async (e) => {
    e.preventDefault()
    if (!learnForm.title.trim() || !learnForm.what_happened.trim()) return
    setLearnLoading(true)
    try {
      await api.post('/api/v1/knowledge/learnings', learnForm)
      setLearnForm({ title: '', category: 'delivery', event_type: 'success', what_happened: '', lesson: '', what_worked: '', what_failed: '', impact_score: 7 })
      setShowLearnForm(false)
      await load()
    } catch {}
    setLearnLoading(false)
  }

  const [entryForm, setEntryForm] = useState({ title: '', category: 'general', content: '', tags: '', source: '' })
  const [entryLoading, setEntryLoading] = useState(false)
  const [showEntryForm, setShowEntryForm] = useState(false)

  const addEntry = async (e) => {
    e.preventDefault()
    if (!entryForm.title.trim() || !entryForm.content.trim()) return
    setEntryLoading(true)
    try {
      await api.post('/api/v1/knowledge/entries', {
        ...entryForm,
        tags: entryForm.tags.split(',').map(s => s.trim()).filter(Boolean),
      })
      setEntryForm({ title: '', category: 'general', content: '', tags: '', source: '' })
      setShowEntryForm(false)
      await load()
    } catch {}
    setEntryLoading(false)
  }

  const TABS = [
    { id: 'sops', label: 'SOPs', icon: FileText, count: stats?.active_sops },
    { id: 'learnings', label: 'Learnings', icon: Lightbulb, count: stats?.learning_records },
    { id: 'entries', label: 'Entries', icon: BookOpen, count: stats?.knowledge_entries },
    { id: 'search', label: 'Search', icon: Search },
  ]

  return (
    <div className="min-h-[calc(100vh-3.5rem)] p-6 pb-10 space-y-6">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.22em] text-jarvis-cyan/70">Operating Knowledge</p>
          <h1 className="mt-2 text-3xl font-bold text-white">Knowledge Base</h1>
          <p className="mt-2 max-w-2xl text-sm text-gray-400">
            SOPs, operational learnings, and reusable delivery patterns for Aliyar Solutions.
          </p>
        </div>
        <button type="button" onClick={load} disabled={loading} className="btn-primary inline-flex items-center justify-center gap-2">
          {loading ? <Loader2 size={15} className="animate-spin" /> : <RefreshCw size={15} />}
          Refresh
        </button>
      </header>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {[
          { label: 'Active SOPs', value: stats?.active_sops ?? '—', tone: 'text-jarvis-cyan' },
          { label: 'Learnings', value: stats?.learning_records ?? '—', tone: 'text-jarvis-gold' },
          { label: 'Knowledge Entries', value: stats?.knowledge_entries ?? '—', tone: 'text-purple-300' },
          { label: 'Top Impact', value: stats?.top_lessons?.[0]?.score ?? '—', tone: 'text-green-300' },
        ].map(m => (
          <div key={m.label} className="glass p-5">
            <p className="text-xs text-gray-400">{m.label}</p>
            <p className={`mt-2 text-2xl font-bold ${m.tone}`}>{m.value}</p>
          </div>
        ))}
      </div>

      {/* Top lessons */}
      {stats?.top_lessons?.length > 0 && (
        <section className="glass p-5">
          <p className="text-xs font-semibold text-jarvis-gold mb-3">Top Impact Lessons</p>
          <div className="space-y-2">
            {stats.top_lessons.map((l, i) => (
              <div key={i} className="flex items-start gap-3">
                <span className={`text-lg font-bold ${IMPACT_COLORS[l.score] || 'text-gray-400'} shrink-0 w-6 text-center`}>{l.score}</span>
                <div>
                  <p className="text-sm font-medium text-white">{l.title}</p>
                  <p className="text-xs text-gray-400 mt-0.5">{l.lesson}</p>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b border-white/10 pb-0">
        {TABS.map(t => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px ${
              tab === t.id ? 'border-jarvis-cyan text-jarvis-cyan' : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            <t.icon size={14} />
            {t.label}
            {t.count != null && (
              <span className="rounded-full bg-white/10 px-1.5 py-0.5 text-[10px] font-bold">{t.count}</span>
            )}
          </button>
        ))}
      </div>

      {/* SOPs Tab */}
      {tab === 'sops' && (
        <section className="glass p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-white">Standard Operating Procedures</h2>
            <button
              type="button"
              onClick={() => setShowSopForm(v => !v)}
              className="inline-flex items-center gap-1.5 rounded border border-jarvis-cyan/40 bg-jarvis-cyan/10 px-3 py-1.5 text-xs font-medium text-jarvis-cyan hover:bg-jarvis-cyan/20 transition-colors"
            >
              <Sparkles size={12} /> Generate SOP
            </button>
          </div>

          {showSopForm && (
            <form onSubmit={generateSop} className="rounded-xl border border-white/10 bg-white/5 p-4 space-y-3">
              <p className="text-xs font-semibold text-jarvis-cyan">AI-Generate New SOP</p>
              <input
                value={sopForm.title}
                onChange={e => setSopForm(p => ({ ...p, title: e.target.value }))}
                placeholder="SOP title (e.g. 'Client onboarding for AI automation projects')"
                maxLength={300}
                className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-white outline-none placeholder:text-gray-500 focus:border-jarvis-cyan/60"
              />
              <div className="flex gap-3">
                <select
                  value={sopForm.category}
                  onChange={e => setSopForm(p => ({ ...p, category: e.target.value }))}
                  className="flex-1 rounded-xl border border-white/10 bg-black/40 px-4 py-2.5 text-sm text-white outline-none focus:border-jarvis-cyan/60"
                >
                  {SOP_CATEGORIES.map(c => <option key={c} value={c}>{c.replace(/_/g, ' ')}</option>)}
                </select>
              </div>
              <textarea
                value={sopForm.context}
                onChange={e => setSopForm(p => ({ ...p, context: e.target.value }))}
                rows={2}
                placeholder="Additional context (optional)"
                maxLength={5000}
                className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-white outline-none placeholder:text-gray-500 focus:border-jarvis-cyan/60"
              />
              <div className="flex gap-2">
                <button type="submit" disabled={sopGenerating} className="btn-primary inline-flex items-center gap-2">
                  {sopGenerating ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={13} />}
                  {sopGenerating ? 'Generating…' : 'Generate'}
                </button>
                <button type="button" onClick={() => setShowSopForm(false)} className="px-3 py-1.5 text-xs text-gray-400 hover:text-gray-200">
                  Cancel
                </button>
              </div>
            </form>
          )}

          {loading ? (
            <div className="flex items-center justify-center py-8 text-gray-500"><Loader2 size={18} className="animate-spin mr-2" /> Loading…</div>
          ) : sops.length === 0 ? (
            <div className="flex flex-col items-center py-10 text-gray-500">
              <FileText size={32} className="mb-3 opacity-20" />
              <p className="text-sm">No SOPs yet — click Generate SOP to create one.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {sops.map(sop => (
                <ExpandableCard
                  key={sop.id}
                  title={sop.title}
                  badge={<span className="ml-2 rounded-full border border-jarvis-cyan/20 bg-jarvis-cyan/10 px-2 py-0.5 text-[10px] text-jarvis-cyan shrink-0">{sop.category}</span>}
                >
                  <p className="text-xs text-gray-300 whitespace-pre-wrap leading-relaxed">{sop.content}</p>
                </ExpandableCard>
              ))}
            </div>
          )}
        </section>
      )}

      {/* Learnings Tab */}
      {tab === 'learnings' && (
        <section className="glass p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-white">Operational Learnings</h2>
            <button
              type="button"
              onClick={() => setShowLearnForm(v => !v)}
              className="inline-flex items-center gap-1.5 rounded border border-jarvis-gold/40 bg-jarvis-gold/10 px-3 py-1.5 text-xs font-medium text-jarvis-gold hover:bg-jarvis-gold/20 transition-colors"
            >
              <Plus size={12} /> Log Learning
            </button>
          </div>

          {showLearnForm && (
            <form onSubmit={logLearning} className="rounded-xl border border-white/10 bg-white/5 p-4 space-y-3">
              <p className="text-xs font-semibold text-jarvis-gold">Log New Learning</p>
              <input
                value={learnForm.title}
                onChange={e => setLearnForm(p => ({ ...p, title: e.target.value }))}
                placeholder="Learning title"
                maxLength={300}
                className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-white outline-none placeholder:text-gray-500 focus:border-jarvis-cyan/60"
              />
              <div className="grid grid-cols-3 gap-3">
                <select
                  value={learnForm.event_type}
                  onChange={e => setLearnForm(p => ({ ...p, event_type: e.target.value }))}
                  className="rounded-xl border border-white/10 bg-black/40 px-3 py-2.5 text-sm text-white outline-none focus:border-jarvis-cyan/60"
                >
                  {LEARNING_TYPES.map(t => <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>)}
                </select>
                <select
                  value={learnForm.category}
                  onChange={e => setLearnForm(p => ({ ...p, category: e.target.value }))}
                  className="rounded-xl border border-white/10 bg-black/40 px-3 py-2.5 text-sm text-white outline-none focus:border-jarvis-cyan/60"
                >
                  {['delivery', 'sales', 'operations', 'client', 'technical', 'outreach', 'finance'].map(c => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-400 shrink-0">Impact</span>
                  <input
                    type="number" min={1} max={10}
                    value={learnForm.impact_score}
                    onChange={e => setLearnForm(p => ({ ...p, impact_score: parseInt(e.target.value) || 5 }))}
                    className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white outline-none focus:border-jarvis-cyan/60"
                  />
                </div>
              </div>
              <textarea
                value={learnForm.what_happened}
                onChange={e => setLearnForm(p => ({ ...p, what_happened: e.target.value }))}
                rows={2} placeholder="What happened?"
                maxLength={10000}
                className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-white outline-none placeholder:text-gray-500 focus:border-jarvis-cyan/60"
              />
              <textarea
                value={learnForm.lesson}
                onChange={e => setLearnForm(p => ({ ...p, lesson: e.target.value }))}
                rows={2} placeholder="Key lesson learned"
                maxLength={5000}
                className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-white outline-none placeholder:text-gray-500 focus:border-jarvis-cyan/60"
              />
              <div className="flex gap-2">
                <button type="submit" disabled={learnLoading} className="btn-primary inline-flex items-center gap-2">
                  {learnLoading ? <Loader2 size={13} className="animate-spin" /> : <Plus size={13} />}
                  Log
                </button>
                <button type="button" onClick={() => setShowLearnForm(false)} className="px-3 py-1.5 text-xs text-gray-400 hover:text-gray-200">Cancel</button>
              </div>
            </form>
          )}

          {loading ? (
            <div className="flex items-center justify-center py-8 text-gray-500"><Loader2 size={18} className="animate-spin mr-2" /> Loading…</div>
          ) : learnings.length === 0 ? (
            <div className="flex flex-col items-center py-10 text-gray-500">
              <Lightbulb size={32} className="mb-3 opacity-20" />
              <p className="text-sm">No learnings logged yet.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {learnings.map(l => (
                <ExpandableCard
                  key={l.id}
                  title={l.title}
                  badge={
                    <div className="flex items-center gap-2 ml-2 shrink-0">
                      <EventBadge type={l.event_type} />
                      <span className={`text-sm font-bold ${IMPACT_COLORS[l.impact_score] || 'text-gray-400'}`}>{l.impact_score}/10</span>
                    </div>
                  }
                >
                  <div className="space-y-2 text-xs text-gray-400">
                    {l.what_happened && <div><span className="text-gray-500 font-medium">What happened: </span>{l.what_happened}</div>}
                    {l.lesson && <div><span className="text-green-400 font-medium">Lesson: </span><span className="text-gray-300">{l.lesson}</span></div>}
                    {l.what_worked && <div><span className="text-jarvis-cyan font-medium">What worked: </span>{l.what_worked}</div>}
                    {l.what_failed && <div><span className="text-red-400 font-medium">What failed: </span>{l.what_failed}</div>}
                  </div>
                </ExpandableCard>
              ))}
            </div>
          )}
        </section>
      )}

      {/* Entries Tab */}
      {tab === 'entries' && (
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-white">Knowledge Entries</h2>
            <button onClick={() => setShowEntryForm(v => !v)} className="btn-primary inline-flex items-center gap-1.5 text-sm">
              <Plus size={13} /> Add Entry
            </button>
          </div>

          {showEntryForm && (
            <div className="glass p-5 border border-jarvis-cyan/20 space-y-3">
              <h3 className="text-xs font-semibold text-white uppercase tracking-wider">New Knowledge Entry</h3>
              <form onSubmit={addEntry} className="space-y-3">
                <input value={entryForm.title} onChange={e => setEntryForm(f => ({ ...f, title: e.target.value }))}
                  placeholder="Title *"
                  maxLength={300}
                  className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none placeholder:text-gray-500 focus:border-jarvis-cyan/60" />
                <div className="grid grid-cols-2 gap-3">
                  <select value={entryForm.category} onChange={e => setEntryForm(f => ({ ...f, category: e.target.value }))}
                    className="rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none">
                    {SOP_CATEGORIES.map(c => <option key={c} value={c}>{c.replace(/_/g, ' ')}</option>)}
                  </select>
                  <input value={entryForm.source} onChange={e => setEntryForm(f => ({ ...f, source: e.target.value }))}
                    placeholder="Source (e.g. Captain, client call)"
                    maxLength={200}
                    className="rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none placeholder:text-gray-500" />
                </div>
                <textarea value={entryForm.content} onChange={e => setEntryForm(f => ({ ...f, content: e.target.value }))}
                  placeholder="Knowledge content *" rows={4}
                  maxLength={100000}
                  className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none placeholder:text-gray-500 focus:border-jarvis-cyan/60 resize-none" />
                <input value={entryForm.tags} onChange={e => setEntryForm(f => ({ ...f, tags: e.target.value }))}
                  placeholder="Tags — comma separated (e.g. pricing, dental, objection)"
                  maxLength={500}
                  className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none placeholder:text-gray-500" />
                <div className="flex gap-3">
                  <button type="submit" disabled={entryLoading || !entryForm.title.trim() || !entryForm.content.trim()}
                    className="btn-primary inline-flex items-center gap-2">
                    {entryLoading ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={13} />}
                    Save Entry
                  </button>
                  <button type="button" onClick={() => setShowEntryForm(false)} className="px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors">
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          )}

          <div className="glass p-8 flex flex-col items-center justify-center text-center text-gray-500">
            <BookOpen size={28} className="mb-3 opacity-20" />
            <p className="text-sm">Knowledge entries are searchable via the Search tab.</p>
            <p className="text-xs mt-1 text-gray-600">Use this to store client-specific notes, market insights, and institutional knowledge.</p>
          </div>
        </section>
      )}

      {/* Search Tab */}
      {tab === 'search' && (
        <section className="glass p-5 space-y-4">
          <h2 className="text-sm font-semibold text-white">Search Knowledge</h2>
          <div className="flex gap-3">
            <input
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && search()}
              placeholder="Search SOPs, learnings, delivery lessons, client notes…"
              maxLength={500}
              className="flex-1 rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none placeholder:text-gray-500 focus:border-jarvis-cyan/60"
            />
            <button onClick={search} disabled={searchLoading} className="btn-primary inline-flex items-center gap-2">
              {searchLoading ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />}
              Search
            </button>
          </div>

          {searchResults !== null && (
            <div>
              {searchResults.length === 0 ? (
                <p className="text-sm text-gray-500 py-4 text-center">No results for "{searchQuery}"</p>
              ) : (
                <div className="space-y-2">
                  {searchResults.map((r, i) => (
                    <div key={i} className="rounded-xl border border-white/10 bg-white/5 p-4">
                      <div className="flex items-center gap-2 mb-1">
                        <p className="text-sm font-medium text-white">{r.title}</p>
                        <span className="text-[10px] text-gray-500 uppercase tracking-wider">{r.type || r.source}</span>
                      </div>
                      <p className="text-xs text-gray-400 line-clamp-3">{r.content || r.lesson || r.summary}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {searchResults === null && (
            <div className="flex flex-col items-center py-10 text-gray-500">
              <BookOpen size={32} className="mb-3 opacity-20" />
              <p className="text-sm">Search across all SOPs, learnings, and knowledge entries</p>
            </div>
          )}
        </section>
      )}
    </div>
  )
}
