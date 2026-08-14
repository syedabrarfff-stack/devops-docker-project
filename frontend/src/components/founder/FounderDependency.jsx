import { useState, useEffect } from 'react'
import { getFounderDependencyReport, getFounderDependencyScore, getAutomationOpportunities, runFounderAssessment } from '../../services/api'

function SubScoreBar({ label, score }) {
  const color = score > 80 ? 'bg-rose-500' : score > 60 ? 'bg-amber-500' : score > 20 ? 'bg-blue-500' : 'bg-emerald-500'
  return (
    <div className="mb-3">
      <div className="flex justify-between mb-1">
        <span className="text-gray-300 text-sm">{label}</span>
        <span className={`text-sm font-bold ${score > 80 ? 'text-rose-400' : score > 60 ? 'text-amber-400' : score <= 20 ? 'text-emerald-400' : 'text-blue-400'}`}>{score?.toFixed(1) ?? 0}</span>
      </div>
      <div className="w-full bg-white/10 rounded-full h-2">
        <div className={`${color} h-2 rounded-full transition-all`} style={{ width: `${Math.min(100, score || 0)}%` }} />
      </div>
    </div>
  )
}

export default function FounderDependency() {
  const [report, setReport] = useState(null)
  const [quickScore, setQuickScore] = useState(null)
  const [opps, setOpps] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [assessing, setAssessing] = useState(false)
  const [msg, setMsg] = useState(null)

  const load = async () => {
    setLoading(true)
    try {
      const [r, s, o] = await Promise.all([
        getFounderDependencyReport(),
        getFounderDependencyScore(),
        getAutomationOpportunities(),
      ])
      setReport(r); setQuickScore(s); setOpps(o)
    } catch (e) { setError(e.message) }
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const runAssessment = async () => {
    setAssessing(true)
    try {
      await runFounderAssessment()
      setMsg('Assessment complete.')
      load()
    } catch (e) { setMsg(`Error: ${e.message}`) }
    setAssessing(false)
  }

  if (loading) return <div className="text-gray-400 p-8">Loading Founder Dependency Engine...</div>
  if (error) return <div className="text-rose-400 p-8">Error: {error}</div>

  const score = quickScore?.score ?? report?.latest?.overall_dependency_score ?? 0
  const status = quickScore?.status ?? 'normal'
  const scoreColor = status === 'critical' ? 'text-rose-400' : status === 'high' ? 'text-amber-400' : status === 'target_met' ? 'text-emerald-400' : 'text-blue-400'
  const sub = report?.latest?.sub_scores || {}
  const latest = report?.latest || {}

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Founder Dependency</h1>
        <p className="text-gray-400 text-sm mt-1">Autonomy Score — Reducing Single-Point Dependency on Captain</p>
      </div>

      {msg && <div className="bg-blue-500/20 border border-blue-500/30 rounded-lg p-3 text-blue-300 text-sm">{msg}</div>}

      {/* Central Score */}
      <div className="bg-white/5 border border-white/10 rounded-xl p-8 text-center">
        <p className="text-gray-400 text-sm mb-2">Dependency Score</p>
        <p className={`text-6xl font-bold ${scoreColor}`}>{score.toFixed(0)}</p>
        <p className="text-gray-500 text-sm mt-1">Target: &lt;{quickScore?.target ?? 20} | Status: {status.replace('_', ' ').toUpperCase()}</p>
        <div className="mt-3 flex items-center justify-center gap-3">
          <span className="text-gray-400 text-xs">Gap to target: {Math.max(0, score - (quickScore?.target ?? 20)).toFixed(1)} points</span>
          {latest.trend && <span className={`text-xs px-2 py-0.5 rounded-full ${latest.trend === 'improving' ? 'bg-emerald-500/20 text-emerald-400' : latest.trend === 'worsening' ? 'bg-rose-500/20 text-rose-400' : 'bg-blue-500/20 text-blue-400'}`}>{latest.trend}</span>}
        </div>
      </div>

      {/* Sub Scores */}
      {Object.keys(sub).length > 0 && (
        <div className="bg-white/5 border border-white/10 rounded-xl p-6">
          <h2 className="text-white font-semibold mb-4">Dependency Breakdown</h2>
          <SubScoreBar label="Approval Dependency" score={sub.approval_dependency} />
          <SubScoreBar label="Revenue Dependency" score={sub.revenue_dependency} />
          <SubScoreBar label="Client Dependency" score={sub.client_dependency} />
          <SubScoreBar label="Decision Dependency" score={sub.decision_dependency} />
          <SubScoreBar label="Operational Dependency" score={sub.operational_dependency} />
          {latest.automation_coverage_pct != null && (
            <p className="text-gray-400 text-xs mt-2">Automation Coverage: {latest.automation_coverage_pct.toFixed(1)}% of operations automated</p>
          )}
        </div>
      )}

      {/* Alerts */}
      {(opps?.alerts || latest.single_point_alerts || []).filter(Boolean).length > 0 && (
        <div>
          <h2 className="text-white font-semibold mb-3">Single Point Alerts</h2>
          {(opps?.alerts || latest.single_point_alerts || []).map((a, i) => (
            <div key={i} className="bg-rose-500/10 border border-rose-500/20 rounded-xl p-3 mb-2">
              <p className="text-rose-300 text-sm">🚨 {a}</p>
            </div>
          ))}
        </div>
      )}

      {/* Automation Opportunities */}
      {(opps?.automation || latest.automation_opportunities || []).length > 0 && (
        <div className="bg-white/5 border border-white/10 rounded-xl p-5">
          <h2 className="text-white font-semibold mb-3">Automation Opportunities</h2>
          {(opps?.automation || latest.automation_opportunities || []).map((a, i) => (
            <div key={i} className="flex items-start gap-2 mb-2">
              <span className="text-blue-400 mt-0.5">🤖</span>
              <p className="text-gray-300 text-sm">{a}</p>
            </div>
          ))}
        </div>
      )}

      {/* Delegation Opportunities */}
      {(opps?.delegation || latest.delegation_opportunities || []).length > 0 && (
        <div className="bg-white/5 border border-white/10 rounded-xl p-5">
          <h2 className="text-white font-semibold mb-3">Delegation Opportunities</h2>
          {(opps?.delegation || latest.delegation_opportunities || []).map((a, i) => (
            <div key={i} className="flex items-start gap-2 mb-2">
              <span className="text-purple-400 mt-0.5">→</span>
              <p className="text-gray-300 text-sm">{a}</p>
            </div>
          ))}
        </div>
      )}

      <div className="flex gap-3">
        <button onClick={runAssessment} disabled={assessing} className="bg-blue-600 hover:bg-blue-700 text-white text-sm px-6 py-2 rounded-lg disabled:opacity-50">{assessing ? 'Assessing...' : 'Run Assessment'}</button>
        <button onClick={load} className="bg-white/10 hover:bg-white/20 text-white text-sm px-6 py-2 rounded-lg">Refresh</button>
      </div>
    </div>
  )
}
