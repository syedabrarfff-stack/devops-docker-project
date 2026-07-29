import { useState, useEffect } from 'react'
import { getCFOBriefing, getFinancialHealthScore, computeFinancialSnapshot } from '../../services/api'

function MetricCard({ label, value, sub, color = 'text-white', large = false }) {
  return (
    <div className="bg-white/5 border border-white/10 rounded-xl p-4 text-center">
      <p className="text-gray-400 text-xs mb-1">{label}</p>
      <p className={`font-bold ${large ? 'text-3xl' : 'text-xl'} ${color}`}>{value}</p>
      {sub && <p className="text-gray-500 text-xs mt-0.5">{sub}</p>}
    </div>
  )
}

function GradeColor(grade) {
  return { A: 'text-emerald-400', B: 'text-blue-400', C: 'text-amber-400', D: 'text-rose-400' }[grade] || 'text-gray-400'
}

export default function FinancialIntelligence() {
  const [briefing, setBriefing] = useState(null)
  const [healthScore, setHealthScore] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [computing, setComputing] = useState(false)
  const [msg, setMsg] = useState(null)

  const load = async () => {
    setLoading(true)
    try {
      const [b, h] = await Promise.all([
        getCFOBriefing(),
        getFinancialHealthScore(),
      ])
      setBriefing(b); setHealthScore(h)
    } catch (e) { setError(e.message) }
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const computeSnapshot = async () => {
    setComputing(true)
    try {
      await computeFinancialSnapshot()
      setMsg('Financial snapshot computed.')
      load()
    } catch (e) { setMsg(`Error: ${e.message}`) }
    setComputing(false)
  }

  if (loading) return <div className="text-gray-400 p-8">Loading Financial Intelligence...</div>
  if (error) return <div className="text-rose-400 p-8">Error: {error}</div>

  const snap = briefing?.snapshot || {}
  const forecasts = briefing?.cashflow_forecasts || []
  const score = snap.financial_health_score || healthScore?.score || 0
  const grade = snap.grade || healthScore?.grade || 'D'
  const alerts = snap.risk_alerts || healthScore?.alerts || []
  const expansion = snap.expansion_alerts || []

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Financial Intelligence</h1>
        <p className="text-gray-400 text-sm mt-1">Virtual CFO — Real-Time Financial Health & Forecasting</p>
      </div>

      {msg && <div className="bg-blue-500/20 border border-blue-500/30 rounded-lg p-3 text-blue-300 text-sm">{msg}</div>}

      {/* Key Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <MetricCard label="MRR" value={`$${(snap.mrr || 0).toLocaleString()}`} color="text-emerald-400" large />
        <MetricCard label="ARR" value={`$${(snap.arr || 0).toLocaleString()}`} color="text-blue-400" />
        <MetricCard label="Gross Margin" value={`${(snap.gross_margin_pct || 0).toFixed(1)}%`} color={(snap.gross_margin_pct || 0) >= 50 ? 'text-emerald-400' : 'text-amber-400'} />
        <MetricCard
          label="Financial Health"
          value={`${score.toFixed(0)}/100`}
          sub={`Grade: ${grade}`}
          color={GradeColor(grade)}
          large
        />
        <MetricCard label="Runway" value={`${(snap.runway_months || 6).toFixed(1)} mo`} color={(snap.runway_months || 6) >= 6 ? 'text-blue-400' : 'text-rose-400'} />
        <MetricCard label="Concentration Risk" value={`${(snap.revenue_concentration_risk || 0).toFixed(1)}%`} color={(snap.revenue_concentration_risk || 0) < 40 ? 'text-emerald-400' : 'text-rose-400'} />
      </div>

      {/* Health Score Bar */}
      <div className="bg-white/5 border border-white/10 rounded-xl p-6">
        <div className="flex justify-between mb-2">
          <span className="text-white text-sm font-medium">Financial Health Score</span>
          <span className={`font-bold ${GradeColor(grade)}`}>{grade} — {score.toFixed(0)}/100</span>
        </div>
        <div className="w-full bg-white/10 rounded-full h-3">
          <div className={`h-3 rounded-full transition-all ${score >= 80 ? 'bg-emerald-500' : score >= 60 ? 'bg-blue-500' : score >= 40 ? 'bg-amber-500' : 'bg-rose-500'}`} style={{ width: `${score}%` }} />
        </div>
      </div>

      {/* Risk Alerts */}
      {alerts.length > 0 && (
        <div>
          <h2 className="text-white font-semibold mb-3">Risk Alerts</h2>
          {alerts.map((a, i) => (
            <div key={i} className="bg-rose-500/10 border border-rose-500/20 rounded-xl p-3 mb-2">
              <p className="text-rose-300 text-sm">⚠️ {a}</p>
            </div>
          ))}
        </div>
      )}

      {/* Expansion Alerts */}
      {expansion.length > 0 && (
        <div>
          <h2 className="text-white font-semibold mb-3">Expansion Opportunities</h2>
          {expansion.map((a, i) => (
            <div key={i} className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-3 mb-2">
              <p className="text-emerald-300 text-sm">🚀 {a}</p>
            </div>
          ))}
        </div>
      )}

      {/* CFO Briefing */}
      {snap.cfo_briefing && (
        <div className="bg-white/5 border border-white/10 rounded-xl p-5">
          <h2 className="text-white font-semibold mb-3">CFO Briefing</h2>
          <pre className="text-gray-300 text-xs whitespace-pre-wrap font-mono leading-relaxed">{snap.cfo_briefing}</pre>
        </div>
      )}

      {/* Cashflow Forecast */}
      {forecasts.length > 0 && (
        <div>
          <h2 className="text-white font-semibold mb-3">Cashflow Forecast</h2>
          <div className="grid grid-cols-3 gap-4">
            {forecasts.map(f => (
              <div key={f.horizon_days} className="bg-white/5 border border-white/10 rounded-xl p-4 text-center">
                <p className="text-gray-400 text-xs mb-1">{f.horizon_days}-Day Outlook</p>
                <p className={`text-xl font-bold ${(f.projected_net || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>${(f.projected_net || 0).toLocaleString()}</p>
                <p className="text-gray-500 text-xs mt-1">Revenue: ${(f.projected_revenue || 0).toLocaleString()}</p>
                {f.confidence_low != null && <p className="text-gray-600 text-xs">Range: ${f.confidence_low.toFixed(0)} – ${f.confidence_high?.toFixed(0)}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="flex gap-3">
        <button onClick={computeSnapshot} disabled={computing} className="bg-emerald-600 hover:bg-emerald-700 text-white text-sm px-6 py-2 rounded-lg disabled:opacity-50">{computing ? 'Computing...' : 'Compute Snapshot'}</button>
        <button onClick={load} className="bg-white/10 hover:bg-white/20 text-white text-sm px-6 py-2 rounded-lg">Refresh</button>
      </div>
    </div>
  )
}
