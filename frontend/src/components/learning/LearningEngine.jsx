import { useState, useEffect } from 'react'
import { getLearningDashboard, getLearningRecommendations, extractDeliveryLessons, applyRecommendation, optimizeProposal, optimizeOutreach } from '../../services/api'

const PRIORITY_COLORS = { critical: 'bg-rose-500/20 text-rose-400', high: 'bg-amber-500/20 text-amber-400', medium: 'bg-blue-500/20 text-blue-400', low: 'bg-gray-500/20 text-gray-400' }
const REC_TYPES = ['All','sop','proposal','outreach','delivery','institutional_wisdom']

export default function LearningEngine() {
  const [dashboard, setDashboard] = useState(null)
  const [recs, setRecs] = useState([])
  const [filter, setFilter] = useState('All')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [msg, setMsg] = useState(null)
  const [submitting, setSubmitting] = useState(null)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ project_type: '', client_industry: '', what_worked: '', what_failed: '', estimated_days: '', actual_days: '', client_feedback: '' })

  const load = async () => {
    setLoading(true)
    try {
      const [d, r] = await Promise.all([
        getLearningDashboard(),
        getLearningRecommendations(filter !== 'All' ? filter : null),
      ])
      setDashboard(d); setRecs(Array.isArray(r) ? r : [])
    } catch (e) { setError(e.message) }
    setLoading(false)
  }

  useEffect(() => { load() }, [filter])

  const extractLessons = async () => {
    setSubmitting('extract')
    try {
      const data = await extractDeliveryLessons({ project_type: form.project_type, client_industry: form.client_industry || null, delivery_data: { what_worked: form.what_worked, what_failed: form.what_failed, estimated_days: form.estimated_days ? parseFloat(form.estimated_days) : null, actual_days: form.actual_days ? parseFloat(form.actual_days) : null, client_feedback: form.client_feedback } })
      setMsg(`Extracted: ${data.lessons_created} lessons, ${data.recommendations_created} recommendations`)
      setShowForm(false); load()
    } catch (e) { setMsg(`Error: ${e.message}`) }
    setSubmitting(null)
  }

  const applyRec = async (id) => {
    setSubmitting(id)
    try {
      await applyRecommendation(id, { applied_by: 'Captain' })
      setMsg('Recommendation applied.')
      load()
    } catch (e) { setMsg(`Error: ${e.message}`) }
    setSubmitting(null)
  }

  const quickAction = async (apiFn, key) => {
    setSubmitting(key)
    try {
      const data = await apiFn()
      setMsg(data.title || 'Done')
      load()
    } catch (e) { setMsg(`Error: ${e.message}`) }
    setSubmitting(null)
  }

  if (loading) return <div className="text-gray-400 p-8">Loading Learning Engine...</div>
  if (error) return <div className="text-rose-400 p-8">Error: {error}</div>

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Learning Engine</h1>
        <p className="text-gray-400 text-sm mt-1">Every Delivery Compounds — Institutional Intelligence Growth</p>
      </div>

      {msg && <div className="bg-blue-500/20 border border-blue-500/30 rounded-lg p-3 text-blue-300 text-sm">{msg}<button onClick={() => setMsg(null)} className="ml-2 text-blue-400 text-xs">✕</button></div>}

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Total Lessons', value: dashboard?.lessons_count ?? 0, color: 'text-blue-400' },
          { label: 'Pending Recommendations', value: dashboard?.pending_recommendations ?? 0, color: 'text-amber-400' },
          { label: 'Applied Recommendations', value: dashboard?.applied_recommendations ?? 0, color: 'text-emerald-400' },
          { label: 'Avg Effort Accuracy', value: dashboard?.avg_effort_accuracy ? `${dashboard.avg_effort_accuracy.toFixed(1)}%` : 'N/A', color: (dashboard?.avg_effort_accuracy || 0) >= 80 ? 'text-emerald-400' : 'text-amber-400' },
        ].map(s => (
          <div key={s.label} className="bg-white/5 border border-white/10 rounded-xl p-4 text-center">
            <p className="text-gray-400 text-xs mb-1">{s.label}</p>
            <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
          </div>
        ))}
      </div>

      {/* Recent Lessons */}
      {dashboard?.recent_lessons?.length > 0 && (
        <div>
          <h2 className="text-white font-semibold mb-3">Recent Delivery Lessons</h2>
          {dashboard.recent_lessons.map((l, i) => (
            <div key={i} className="bg-white/5 border border-white/10 rounded-xl p-4 mb-2">
              <div className="flex justify-between items-start">
                <div>
                  <p className="text-white text-sm font-medium">{l.lesson_title}</p>
                  <p className="text-gray-400 text-xs mt-0.5">{l.project_type} · {l.lesson_category}</p>
                </div>
                {l.effort_accuracy_pct != null && (
                  <span className={`text-xs px-2 py-0.5 rounded-full ${l.effort_accuracy_pct >= 80 ? 'bg-emerald-500/20 text-emerald-400' : l.effort_accuracy_pct >= 60 ? 'bg-amber-500/20 text-amber-400' : 'bg-rose-500/20 text-rose-400'}`}>{l.effort_accuracy_pct.toFixed(0)}% accuracy</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Recommendations */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-white font-semibold">Improvement Recommendations</h2>
          <div className="flex gap-2">
            {REC_TYPES.map(t => (
              <button key={t} onClick={() => setFilter(t)} className={`text-xs px-3 py-1 rounded-full border transition-colors ${filter === t ? 'bg-blue-600 border-blue-500 text-white' : 'bg-white/5 border-white/10 text-gray-400'}`}>{t}</button>
            ))}
          </div>
        </div>
        {recs.length === 0 ? <p className="text-gray-500 text-sm">No pending recommendations.</p> : recs.map(r => (
          <div key={r.id} className="bg-white/5 border border-white/10 rounded-xl p-4 mb-2">
            <div className="flex justify-between items-start">
              <div className="flex-1 mr-3">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${PRIORITY_COLORS[r.priority] || PRIORITY_COLORS.medium}`}>{r.priority}</span>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-white/10 text-gray-300">{r.recommendation_type}</span>
                </div>
                <p className="text-white text-sm font-medium">{r.title}</p>
                <p className="text-gray-400 text-xs mt-1 line-clamp-2">{r.description}</p>
                {r.estimated_impact && <p className="text-blue-400 text-xs mt-1">Impact: {r.estimated_impact}</p>}
              </div>
              <button onClick={() => applyRec(r.id)} disabled={submitting === r.id} className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs px-3 py-1.5 rounded-lg disabled:opacity-50 whitespace-nowrap">{submitting === r.id ? '...' : 'Apply'}</button>
            </div>
          </div>
        ))}
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        <button onClick={() => setShowForm(!showForm)} className="bg-purple-600 hover:bg-purple-700 text-white text-sm py-2 rounded-lg">Extract Lessons</button>
        <button onClick={() => quickAction(optimizeProposal, 'optimize-proposal')} disabled={submitting === 'optimize-proposal'} className="bg-blue-600 hover:bg-blue-700 text-white text-sm py-2 rounded-lg disabled:opacity-50">{submitting === 'optimize-proposal' ? '...' : 'Optimize Proposal'}</button>
        <button onClick={() => quickAction(optimizeOutreach, 'optimize-outreach')} disabled={submitting === 'optimize-outreach'} className="bg-amber-600 hover:bg-amber-700 text-white text-sm py-2 rounded-lg disabled:opacity-50">{submitting === 'optimize-outreach' ? '...' : 'Optimize Outreach'}</button>
      </div>

      {/* Extract Form */}
      {showForm && (
        <div className="bg-white/5 border border-white/10 rounded-xl p-5 space-y-3">
          <h3 className="text-white font-semibold">Extract Delivery Lessons</h3>
          <input className="w-full bg-white/10 border border-white/20 rounded-lg p-2 text-white text-sm" placeholder="Project type (e.g. AWS Migration)" value={form.project_type} onChange={e => setForm(f => ({ ...f, project_type: e.target.value }))} />
          <input className="w-full bg-white/10 border border-white/20 rounded-lg p-2 text-white text-sm" placeholder="Client industry" value={form.client_industry} onChange={e => setForm(f => ({ ...f, client_industry: e.target.value }))} />
          <textarea className="w-full bg-white/10 border border-white/20 rounded-lg p-2 text-white text-sm h-20" placeholder="What worked well?" value={form.what_worked} onChange={e => setForm(f => ({ ...f, what_worked: e.target.value }))} />
          <textarea className="w-full bg-white/10 border border-white/20 rounded-lg p-2 text-white text-sm h-20" placeholder="What failed or caused issues?" value={form.what_failed} onChange={e => setForm(f => ({ ...f, what_failed: e.target.value }))} />
          <div className="grid grid-cols-2 gap-3">
            <input className="bg-white/10 border border-white/20 rounded-lg p-2 text-white text-sm" placeholder="Estimated days" value={form.estimated_days} onChange={e => setForm(f => ({ ...f, estimated_days: e.target.value }))} />
            <input className="bg-white/10 border border-white/20 rounded-lg p-2 text-white text-sm" placeholder="Actual days" value={form.actual_days} onChange={e => setForm(f => ({ ...f, actual_days: e.target.value }))} />
          </div>
          <textarea className="w-full bg-white/10 border border-white/20 rounded-lg p-2 text-white text-sm h-16" placeholder="Client feedback" value={form.client_feedback} onChange={e => setForm(f => ({ ...f, client_feedback: e.target.value }))} />
          <button onClick={extractLessons} disabled={submitting === 'extract' || !form.project_type} className="w-full bg-purple-600 hover:bg-purple-700 text-white text-sm py-2 rounded-lg disabled:opacity-50">{submitting === 'extract' ? 'Extracting...' : 'Extract Lessons'}</button>
        </div>
      )}

      <button onClick={load} className="bg-white/10 hover:bg-white/20 text-white text-sm px-6 py-2 rounded-lg">Refresh</button>
    </div>
  )
}
