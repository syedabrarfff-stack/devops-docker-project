import React, { useCallback, useEffect, useState } from 'react'
import { Brain, ChevronDown, ChevronRight, Database, Loader2, Plus, RefreshCw, Search, Shield, Zap } from 'lucide-react'
import api from '../../services/api'

const MEMORY_TYPES = ['episodic', 'semantic', 'procedural', 'working', 'instruction']
const IMPORTANCE_COLORS = {
  10: 'text-red-300', 9: 'text-orange-300', 8: 'text-jarvis-gold', 7: 'text-jarvis-cyan',
  6: 'text-blue-300', 5: 'text-gray-300', 4: 'text-gray-400', 3: 'text-gray-500',
}

function MemoryTypeBadge({ type }) {
  const cfg = {
    episodic:    { cls: 'border-blue-500/30 bg-blue-500/10 text-blue-300' },
    semantic:    { cls: 'border-purple-500/30 bg-purple-500/10 text-purple-300' },
    procedural:  { cls: 'border-green-500/30 bg-green-500/10 text-green-300' },
    working:     { cls: 'border-jarvis-cyan/30 bg-jarvis-cyan/10 text-jarvis-cyan' },
    instruction: { cls: 'border-jarvis-gold/30 bg-jarvis-gold/10 text-jarvis-gold' },
  }[type] || { cls: 'border-gray-500/30 bg-gray-500/10 text-gray-300' }
  return <span className={`inline-flex rounded-full border px-2.5 py-0.5 text-[11px] font-semibold tracking-wide ${cfg.cls}`}>{type}</span>
}

function ExpandCard({ title, sub, children }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="rounded-xl border border-white/10 bg-white/5">
      <button type="button" onClick={() => setOpen(v => !v)} className="flex w-full items-center gap-3 p-4 text-left">
        {open ? <ChevronDown size={13} className="shrink-0 text-gray-400" /> : <ChevronRight size={13} className="shrink-0 text-gray-400" />}
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-white truncate">{title}</p>
          {sub && <p className="text-xs text-gray-500 mt-0.5">{sub}</p>}
        </div>
      </button>
      {open && <div className="border-t border-white/10 px-4 pb-4 pt-3">{children}</div>}
    </div>
  )
}

export default function MemoryView() {
  const [tab, setTab] = useState('recall')
  const [recallQuery, setRecallQuery] = useState('')
  const [recallType, setRecallType] = useState('')
  const [recallResults, setRecallResults] = useState(null)
  const [recallLoading, setRecallLoading] = useState(false)
  const [instructions, setInstructions] = useState([])
  const [context, setContext] = useState(null)
  const [humanIntel, setHumanIntel] = useState(null)
  const [loading, setLoading] = useState(true)
  const [storeForm, setStoreForm] = useState({ content: '', memory_type: 'episodic', importance: 7 })
  const [storeLoading, setStoreLoading] = useState(false)
  const [showStoreForm, setShowStoreForm] = useState(false)
  const [instrForm, setInstrForm] = useState({ content: '', category: 'general', priority: 5 })
  const [instrLoading, setInstrLoading] = useState(false)
  const [showInstrForm, setShowInstrForm] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    const [instrRes, ctxRes, hiRes] = await Promise.allSettled([
      api.get('/api/v1/memory/instructions'),
      api.get('/api/v1/memory/context'),
      api.get('/api/v1/memory/human-intelligence'),
    ])
    if (instrRes.status === 'fulfilled') setInstructions(instrRes.value.data || [])
    if (ctxRes.status === 'fulfilled') setContext(ctxRes.value.data || null)
    if (hiRes.status === 'fulfilled') setHumanIntel(hiRes.value.data || null)
    setLoading(false)
  }, [])

  useEffect(() => { load() }, [load])

  const recall = async () => {
    if (!recallQuery.trim()) return
    setRecallLoading(true)
    try {
      const params = { query: recallQuery, limit: 20 }
      if (recallType) params.memory_type = recallType
      const r = await api.get('/api/v1/memory/recall', { params })
      setRecallResults(r.data || [])
    } catch { setRecallResults([]) }
    setRecallLoading(false)
  }

  const storeMemory = async (e) => {
    e.preventDefault()
    if (!storeForm.content.trim()) return
    setStoreLoading(true)
    try {
      await api.post('/api/v1/memory/store', storeForm)
      setStoreForm({ content: '', memory_type: 'episodic', importance: 7 })
      setShowStoreForm(false)
    } catch {}
    setStoreLoading(false)
  }

  const storeInstruction = async (e) => {
    e.preventDefault()
    if (!instrForm.content.trim()) return
    setInstrLoading(true)
    try {
      await api.post('/api/v1/memory/instructions', instrForm)
      setInstrForm({ content: '', category: 'general', priority: 5 })
      setShowInstrForm(false)
      await load()
    } catch {}
    setInstrLoading(false)
  }

  const TABS = [
    { id: 'recall', label: 'Recall', icon: Search },
    { id: 'instructions', label: 'Instructions', icon: Shield, count: instructions.length },
    { id: 'context', label: 'Context', icon: Brain },
    { id: 'human-intel', label: 'Human Intel', icon: Zap },
  ]

  return (
    <div className="min-h-[calc(100vh-3.5rem)] p-6 pb-10 space-y-6">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.22em] text-jarvis-cyan/70">Organizational Memory</p>
          <h1 className="mt-2 text-3xl font-bold text-white">Memory Browser</h1>
          <p className="mt-2 max-w-2xl text-sm text-gray-400">
            Working, operational, and strategic memory — cross-agent context and long-term decision records.
          </p>
        </div>
        <button type="button" onClick={load} disabled={loading} className="btn-primary inline-flex items-center justify-center gap-2">
          {loading ? <Loader2 size={15} className="animate-spin" /> : <RefreshCw size={15} />}
          Refresh
        </button>
      </header>

      {/* Metric strip */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {[
          { label: 'Instructions', value: instructions.length, tone: 'text-jarvis-gold' },
          { label: 'Context blocks', value: context?.context ? Object.keys(context.context).length : '—', tone: 'text-jarvis-cyan' },
          { label: 'Memory types', value: MEMORY_TYPES.length, tone: 'text-purple-300' },
          { label: 'Human intel entries', value: humanIntel ? Object.keys(humanIntel).length : '—', tone: 'text-green-300' },
        ].map(m => (
          <div key={m.label} className="glass p-5">
            <p className="text-xs text-gray-400">{m.label}</p>
            <p className={`mt-2 text-2xl font-bold ${m.tone}`}>{m.value}</p>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-white/10">
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

      {/* Recall Tab */}
      {tab === 'recall' && (
        <section className="glass p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-white">Recall Memory</h2>
            <button
              type="button"
              onClick={() => setShowStoreForm(v => !v)}
              className="inline-flex items-center gap-1.5 rounded border border-jarvis-cyan/40 bg-jarvis-cyan/10 px-3 py-1.5 text-xs font-medium text-jarvis-cyan hover:bg-jarvis-cyan/20 transition-colors"
            >
              <Plus size={12} /> Store Memory
            </button>
          </div>

          {showStoreForm && (
            <form onSubmit={storeMemory} className="rounded-xl border border-white/10 bg-white/5 p-4 space-y-3">
              <p className="text-xs font-semibold text-jarvis-cyan">Store New Memory</p>
              <textarea
                value={storeForm.content}
                onChange={e => setStoreForm(p => ({ ...p, content: e.target.value }))}
                rows={3} placeholder="Memory content…"
                className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-white outline-none placeholder:text-gray-500 focus:border-jarvis-cyan/60"
              />
              <div className="flex gap-3">
                <select
                  value={storeForm.memory_type}
                  onChange={e => setStoreForm(p => ({ ...p, memory_type: e.target.value }))}
                  className="flex-1 rounded-xl border border-white/10 bg-black/40 px-3 py-2.5 text-sm text-white outline-none focus:border-jarvis-cyan/60"
                >
                  {MEMORY_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-400 shrink-0">Importance</span>
                  <input
                    type="number" min={1} max={10}
                    value={storeForm.importance}
                    onChange={e => setStoreForm(p => ({ ...p, importance: parseInt(e.target.value) || 5 }))}
                    className="w-16 rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white outline-none focus:border-jarvis-cyan/60"
                  />
                </div>
              </div>
              <div className="flex gap-2">
                <button type="submit" disabled={storeLoading} className="btn-primary inline-flex items-center gap-2">
                  {storeLoading ? <Loader2 size={13} className="animate-spin" /> : <Database size={13} />}
                  Store
                </button>
                <button type="button" onClick={() => setShowStoreForm(false)} className="px-3 py-1.5 text-xs text-gray-400 hover:text-gray-200">Cancel</button>
              </div>
            </form>
          )}

          <div className="flex gap-3">
            <input
              value={recallQuery}
              onChange={e => setRecallQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && recall()}
              placeholder="Search decisions, leads, clients, outcomes, or instructions…"
              className="flex-1 rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none placeholder:text-gray-500 focus:border-jarvis-cyan/60"
            />
            <select
              value={recallType}
              onChange={e => setRecallType(e.target.value)}
              className="rounded-xl border border-white/10 bg-black/40 px-3 py-3 text-sm text-white outline-none focus:border-jarvis-cyan/60"
            >
              <option value="">All types</option>
              {MEMORY_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
            <button onClick={recall} disabled={recallLoading} className="btn-primary inline-flex items-center gap-2">
              {recallLoading ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />}
              Recall
            </button>
          </div>

          {recallResults !== null && (
            <div>
              {recallResults.length === 0 ? (
                <p className="text-sm text-gray-500 py-4 text-center">No memories found for "{recallQuery}"</p>
              ) : (
                <div className="space-y-2">
                  {recallResults.map(m => (
                    <ExpandCard
                      key={m.id}
                      title={m.content?.slice(0, 80) + (m.content?.length > 80 ? '…' : '')}
                      sub={`${m.memory_type} • importance ${m.importance}`}
                    >
                      <div className="space-y-2">
                        <div className="flex items-center gap-2">
                          <MemoryTypeBadge type={m.memory_type} />
                          <span className={`text-sm font-bold ${IMPORTANCE_COLORS[m.importance] || 'text-gray-400'}`}>{m.importance}/10</span>
                          {m.tags?.length > 0 && m.tags.map(t => (
                            <span key={t} className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[10px] text-gray-400">{t}</span>
                          ))}
                        </div>
                        <p className="text-xs text-gray-300 leading-relaxed">{m.content}</p>
                        <p className="text-[10px] text-gray-600">{m.created_at}</p>
                      </div>
                    </ExpandCard>
                  ))}
                </div>
              )}
            </div>
          )}

          {recallResults === null && (
            <div className="flex flex-col items-center py-10 text-gray-500">
              <Brain size={32} className="mb-3 opacity-20" />
              <p className="text-sm">Search JARVIS operational memory</p>
            </div>
          )}
        </section>
      )}

      {/* Instructions Tab */}
      {tab === 'instructions' && (
        <section className="glass p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-white">Stored Instructions</h2>
            <button
              type="button"
              onClick={() => setShowInstrForm(v => !v)}
              className="inline-flex items-center gap-1.5 rounded border border-jarvis-gold/40 bg-jarvis-gold/10 px-3 py-1.5 text-xs font-medium text-jarvis-gold hover:bg-jarvis-gold/20 transition-colors"
            >
              <Plus size={12} /> Add Instruction
            </button>
          </div>

          {showInstrForm && (
            <form onSubmit={storeInstruction} className="rounded-xl border border-white/10 bg-white/5 p-4 space-y-3">
              <p className="text-xs font-semibold text-jarvis-gold">Store Captain Instruction</p>
              <textarea
                value={instrForm.content}
                onChange={e => setInstrForm(p => ({ ...p, content: e.target.value }))}
                rows={3} placeholder="Instruction content for JARVIS to follow…"
                className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-white outline-none placeholder:text-gray-500 focus:border-jarvis-cyan/60"
              />
              <div className="flex gap-3">
                <select
                  value={instrForm.category}
                  onChange={e => setInstrForm(p => ({ ...p, category: e.target.value }))}
                  className="flex-1 rounded-xl border border-white/10 bg-black/40 px-3 py-2.5 text-sm text-white outline-none focus:border-jarvis-cyan/60"
                >
                  {['general', 'sales', 'delivery', 'operations', 'communication', 'finance', 'technical'].map(c => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
                <input
                  type="number" min={1} max={10} placeholder="Priority"
                  value={instrForm.priority}
                  onChange={e => setInstrForm(p => ({ ...p, priority: parseInt(e.target.value) || 5 }))}
                  className="w-24 rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white outline-none focus:border-jarvis-cyan/60"
                />
              </div>
              <div className="flex gap-2">
                <button type="submit" disabled={instrLoading} className="btn-primary inline-flex items-center gap-2">
                  {instrLoading ? <Loader2 size={13} className="animate-spin" /> : <Shield size={13} />}
                  Store
                </button>
                <button type="button" onClick={() => setShowInstrForm(false)} className="px-3 py-1.5 text-xs text-gray-400 hover:text-gray-200">Cancel</button>
              </div>
            </form>
          )}

          {loading ? (
            <div className="flex items-center justify-center py-8 text-gray-500"><Loader2 size={18} className="animate-spin mr-2" />Loading…</div>
          ) : instructions.length === 0 ? (
            <div className="flex flex-col items-center py-10 text-gray-500">
              <Shield size={32} className="mb-3 opacity-20" />
              <p className="text-sm">No instructions stored yet.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {instructions.map(instr => (
                <div key={instr.id} className="rounded-xl border border-white/10 bg-white/5 p-4">
                  <div className="flex items-center gap-2 mb-2">
                    {instr.tags?.map(t => (
                      <span key={t} className="rounded-full border border-jarvis-gold/20 bg-jarvis-gold/10 px-2 py-0.5 text-[10px] text-jarvis-gold">{t}</span>
                    ))}
                    <span className={`ml-auto text-xs font-bold ${IMPORTANCE_COLORS[instr.priority] || 'text-gray-400'}`}>P{instr.priority}</span>
                  </div>
                  <p className="text-sm text-gray-300 leading-relaxed">{instr.content}</p>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {/* Context Tab */}
      {tab === 'context' && (
        <section className="glass p-5 space-y-4">
          <h2 className="text-sm font-semibold text-white">Memory Context</h2>
          {loading ? (
            <div className="flex items-center justify-center py-8 text-gray-500"><Loader2 size={18} className="animate-spin mr-2" />Loading…</div>
          ) : context ? (
            <pre className="max-h-[600px] overflow-auto rounded-lg border border-white/10 bg-black/20 p-4 text-xs text-gray-300 leading-relaxed">
              {JSON.stringify(context, null, 2)}
            </pre>
          ) : (
            <p className="text-sm text-gray-500 text-center py-8">No context available.</p>
          )}
        </section>
      )}

      {/* Human Intel Tab */}
      {tab === 'human-intel' && (
        <section className="glass p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-white">Human Intelligence KB</h2>
            <p className="text-xs text-gray-500">JARVIS psychology & persuasion model</p>
          </div>
          {loading ? (
            <div className="flex items-center justify-center py-8 text-gray-500"><Loader2 size={18} className="animate-spin mr-2" />Loading…</div>
          ) : humanIntel ? (
            <div className="space-y-3">
              {Object.entries(humanIntel).map(([key, value]) => (
                <ExpandCard key={key} title={key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}>
                  <pre className="text-xs text-gray-300 whitespace-pre-wrap leading-relaxed">
                    {typeof value === 'string' ? value : JSON.stringify(value, null, 2)}
                  </pre>
                </ExpandCard>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-500 text-center py-8">No human intelligence data available.</p>
          )}
        </section>
      )}
    </div>
  )
}
