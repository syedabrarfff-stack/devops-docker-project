import React, { useCallback, useEffect, useState } from 'react'
import { ChevronDown, ChevronRight, FileText, Loader2, RefreshCw, Sparkles } from 'lucide-react'
import api from '../../services/api'

const REPORT_CATEGORIES = ['market', 'technology', 'competitor', 'industry', 'opportunity', 'risk', 'regulatory', 'general']
const CATEGORY_COLORS = {
  market:     'border-jarvis-cyan/30 bg-jarvis-cyan/10 text-jarvis-cyan',
  technology: 'border-blue-500/30 bg-blue-500/10 text-blue-300',
  competitor: 'border-orange-500/30 bg-orange-500/10 text-orange-300',
  industry:   'border-purple-500/30 bg-purple-500/10 text-purple-300',
  opportunity:'border-green-500/30 bg-green-500/10 text-green-300',
  risk:       'border-red-500/30 bg-red-500/10 text-red-300',
  regulatory: 'border-yellow-500/30 bg-yellow-500/10 text-yellow-300',
  general:    'border-gray-500/30 bg-gray-500/10 text-gray-300',
}

function fmtDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function ReportCard({ report }) {
  const [open, setOpen] = useState(false)
  const cls = CATEGORY_COLORS[report.category] || CATEGORY_COLORS.general
  return (
    <div className="rounded-xl border border-white/10 bg-white/5">
      <button type="button" onClick={() => setOpen(v => !v)} className="flex w-full items-start gap-3 p-4 text-left">
        {open ? <ChevronDown size={13} className="mt-0.5 shrink-0 text-gray-400" /> : <ChevronRight size={13} className="mt-0.5 shrink-0 text-gray-400" />}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-sm font-medium text-white">{report.title || report.topic}</p>
            <span className={`inline-flex rounded-full border px-2 py-0.5 text-[10px] font-semibold ${cls}`}>{report.category}</span>
          </div>
          <p className="text-xs text-gray-500 mt-0.5">{fmtDate(report.created_at)}</p>
        </div>
      </button>
      {open && (
        <div className="border-t border-white/10 px-4 pb-4 pt-3">
          {report.summary && (
            <div className="mb-3">
              <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1">Summary</p>
              <p className="text-xs text-gray-300 leading-relaxed">{report.summary}</p>
            </div>
          )}
          {report.content && (
            <div>
              <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1">Full Report</p>
              <p className="text-xs text-gray-400 whitespace-pre-wrap leading-relaxed max-h-80 overflow-auto">{report.content}</p>
            </div>
          )}
          {report.key_findings?.length > 0 && (
            <div className="mt-3">
              <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2">Key Findings</p>
              <ul className="space-y-1">
                {report.key_findings.map((f, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-gray-300">
                    <span className="text-jarvis-cyan mt-0.5 shrink-0">→</span>{f}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {report.recommendations?.length > 0 && (
            <div className="mt-3">
              <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2">Recommendations</p>
              <ul className="space-y-1">
                {report.recommendations.map((r, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-green-300">
                    <span className="mt-0.5 shrink-0">✓</span>{r}
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

export default function ResearchView() {
  const [reports, setReports] = useState([])
  const [loading, setLoading] = useState(true)
  const [topic, setTopic] = useState('')
  const [category, setCategory] = useState('market')
  const [generating, setGenerating] = useState(false)
  const [queued, setQueued] = useState(null)
  const [filterCategory, setFilterCategory] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    const r = await api.get('/api/v1/intelligence/reports', { params: { limit: 30 } }).catch(() => null)
    if (r) setReports(r.data?.reports || [])
    setLoading(false)
  }, [])

  useEffect(() => { load() }, [load])

  const generate = async (e) => {
    e.preventDefault()
    if (!topic.trim()) return
    setGenerating(true)
    try {
      const r = await api.post('/api/v1/intelligence/reports/generate', { topic, category })
      setQueued({ topic, message: r.data?.message })
      setTopic('')
      setTimeout(() => { setQueued(null); load() }, 8000)
    } catch (err) {
      setQueued({ error: err.response?.data?.detail || err.message })
      setTimeout(() => setQueued(null), 5000)
    }
    setGenerating(false)
  }

  const filtered = filterCategory ? reports.filter(r => r.category === filterCategory) : reports

  return (
    <div className="min-h-[calc(100vh-3.5rem)] p-6 pb-10 space-y-6">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.22em] text-jarvis-cyan/70">Research</p>
          <h1 className="mt-2 text-3xl font-bold text-white">Research Reports</h1>
          <p className="mt-2 max-w-2xl text-sm text-gray-400">
            AI-generated market and technology research informing Aliyar Solutions strategy and proposals.
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
          { label: 'Total Reports', value: reports.length, tone: 'text-jarvis-cyan' },
          { label: 'Market Reports', value: reports.filter(r => r.category === 'market').length, tone: 'text-jarvis-gold' },
          { label: 'Technology', value: reports.filter(r => r.category === 'technology').length, tone: 'text-blue-300' },
          { label: 'Competitor', value: reports.filter(r => r.category === 'competitor').length, tone: 'text-orange-300' },
        ].map(m => (
          <div key={m.label} className="glass p-5">
            <p className="text-xs text-gray-400">{m.label}</p>
            <p className={`mt-2 text-2xl font-bold ${m.tone}`}>{m.value}</p>
          </div>
        ))}
      </div>

      {/* Generate form */}
      <section className="glass p-5">
        <h2 className="text-sm font-semibold text-white mb-4">Generate Research Report</h2>
        <form onSubmit={generate} className="flex flex-col gap-3 md:flex-row md:items-end">
          <div className="flex-1">
            <label className="text-xs text-gray-500 mb-1 block">Research Topic</label>
            <input
              value={topic}
              onChange={e => setTopic(e.target.value)}
              placeholder="e.g. AI automation market for SMBs in Southeast Asia, 2026"
              className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none placeholder:text-gray-500 focus:border-jarvis-cyan/60"
            />
          </div>
          <div className="md:w-48">
            <label className="text-xs text-gray-500 mb-1 block">Category</label>
            <select
              value={category}
              onChange={e => setCategory(e.target.value)}
              className="w-full rounded-xl border border-white/10 bg-black/40 px-4 py-3 text-sm text-white outline-none focus:border-jarvis-cyan/60"
            >
              {REPORT_CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <button type="submit" disabled={generating || !topic.trim()} className="btn-primary inline-flex items-center gap-2 md:mb-0">
            {generating ? <Loader2 size={15} className="animate-spin" /> : <Sparkles size={15} />}
            {generating ? 'Queuing…' : 'Generate'}
          </button>
        </form>

        {queued && (
          <div className={`mt-3 rounded-lg border p-3 text-sm ${
            queued.error
              ? 'border-red-400/20 bg-red-400/10 text-red-200'
              : 'border-jarvis-cyan/20 bg-jarvis-cyan/10 text-jarvis-cyan'
          }`}>
            {queued.error || `${queued.message || 'Report queued.'} Refreshing in ~8s…`}
          </div>
        )}
      </section>

      {/* Reports list */}
      <section className="glass p-5 space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <h2 className="text-sm font-semibold text-white">
            {loading ? 'Loading…' : `${filtered.length} report${filtered.length !== 1 ? 's' : ''}`}
          </h2>
          <select
            value={filterCategory}
            onChange={e => setFilterCategory(e.target.value)}
            className="rounded-xl border border-white/10 bg-black/40 px-3 py-2 text-xs text-white outline-none focus:border-jarvis-cyan/60"
          >
            <option value="">All categories</option>
            {REPORT_CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-8 text-gray-500">
            <Loader2 size={18} className="animate-spin mr-2" />Loading reports…
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center py-10 text-gray-500">
            <FileText size={32} className="mb-3 opacity-20" />
            <p className="text-sm font-medium text-gray-400">No reports yet</p>
            <p className="mt-1 text-xs">Generate your first research report above.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {filtered.map(report => <ReportCard key={report.id} report={report} />)}
          </div>
        )}
      </section>
    </div>
  )
}
