import { useState, useEffect } from 'react'
import { getTruthReport, getAccuracyDashboard, recordPrediction, runRealityCheck } from '../../services/api'

const PREDICTION_TYPES = ['lead_score','trust_score','proposal_acceptance','revenue_forecast','client_health','council_recommendation','dio_recommendation','delivery_estimate']

function AccuracyBar({ score }) {
  const color = score >= 75 ? 'bg-emerald-500' : score >= 50 ? 'bg-amber-500' : 'bg-rose-500'
  return (
    <div className="w-full bg-white/10 rounded-full h-2 mt-1">
      <div className={`${color} h-2 rounded-full transition-all`} style={{ width: `${Math.min(100, score || 0)}%` }} />
    </div>
  )
}

function TrendBadge({ trend }) {
  const cfg = { improving: 'bg-emerald-500/20 text-emerald-400', degrading: 'bg-rose-500/20 text-rose-400', stable: 'bg-blue-500/20 text-blue-400' }
  return <span className={`text-xs px-2 py-0.5 rounded-full ${cfg[trend] || cfg.stable}`}>{trend || 'stable'}</span>
}

export default function TruthEngine() {
  const [report, setReport] = useState(null)
  const [accuracy, setAccuracy] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [predForm, setPredForm] = useState({ prediction_type: 'lead_score', predicted_value: '', confidence_score: '', predicted_by: 'jarvis' })
  const [checkType, setCheckType] = useState('lead_score')
  const [submitting, setSubmitting] = useState(false)
  const [msg, setMsg] = useState(null)

  const load = async () => {
    setLoading(true)
    try {
      const [r, a] = await Promise.all([
        getTruthReport(),
        getAccuracyDashboard(),
      ])
      setReport(r)
      setAccuracy(Array.isArray(a) ? a : [])
    } catch (e) { setError(e.message) }
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const submitPrediction = async () => {
    setSubmitting(true)
    try {
      const data = await recordPrediction({ ...predForm, predicted_value: predForm.predicted_value ? parseFloat(predForm.predicted_value) : null, confidence_score: predForm.confidence_score ? parseFloat(predForm.confidence_score) : null, entity_type: 'general' })
      setMsg(`Prediction recorded: ID ${data.id}`)
      setTimeout(() => setMsg(null), 3000)
    } catch (e) { setMsg(`Error: ${e.message}`) }
    setSubmitting(false)
  }

  const runCheck = async () => {
    setSubmitting(true)
    try {
      const data = await runRealityCheck({ check_type: checkType })
      setMsg(`Reality check complete. Accuracy: ${data.accuracy_pct ? data.accuracy_pct.toFixed(1) + '%' : 'N/A'}`)
      load()
    } catch (e) { setMsg(`Error: ${e.message}`) }
    setSubmitting(false)
  }

  if (loading) return <div className="text-gray-400 p-8">Loading Truth Engine...</div>
  if (error) return <div className="text-rose-400 p-8">Error: {error}</div>

  const calibration = report?.overall_calibration_score ?? 0
  const calibColor = calibration >= 75 ? 'text-emerald-400' : calibration >= 50 ? 'text-amber-400' : 'text-rose-400'

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Truth Engine</h1>
        <p className="text-gray-400 text-sm mt-1">Prediction vs Reality — Continuous Calibration System</p>
      </div>

      {msg && <div className="bg-blue-500/20 border border-blue-500/30 rounded-lg p-3 text-blue-300 text-sm">{msg}</div>}

      {/* Overall Calibration */}
      <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl p-6 text-center">
        <p className="text-gray-400 text-sm mb-2">Overall System Calibration</p>
        <p className={`text-5xl font-bold ${calibColor}`}>{calibration.toFixed(1)}%</p>
        <p className="text-gray-500 text-xs mt-2">Across all prediction types</p>
      </div>

      {/* Accuracy by type */}
      {accuracy.length > 0 && (
        <div>
          <h2 className="text-white font-semibold mb-3">Accuracy by Prediction Type</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {accuracy.map(a => (
              <div key={a.prediction_type} className="bg-white/5 border border-white/10 rounded-xl p-4">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-white text-sm font-medium">{a.prediction_type.replace(/_/g, ' ')}</span>
                  <TrendBadge trend={a.trend} />
                </div>
                <div className="flex items-center gap-3">
                  <span className={`text-lg font-bold ${(a.accuracy_score || 0) >= 75 ? 'text-emerald-400' : (a.accuracy_score || 0) >= 50 ? 'text-amber-400' : 'text-rose-400'}`}>{a.accuracy_score ? a.accuracy_score.toFixed(1) : 'N/A'}%</span>
                  <div className="flex-1"><AccuracyBar score={a.accuracy_score} /></div>
                </div>
                <p className="text-gray-500 text-xs mt-1">{a.total_predictions} predictions | MAE: {a.mean_absolute_error ? a.mean_absolute_error.toFixed(3) : 'N/A'}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Top Failures */}
      {report?.top_failures?.length > 0 && (
        <div>
          <h2 className="text-white font-semibold mb-3">Calibration Issues</h2>
          {report.top_failures.map((f, i) => (
            <div key={i} className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-4 mb-2">
              <p className="text-amber-300 text-sm font-medium">{f.prediction_type?.replace(/_/g, ' ')}</p>
              <p className="text-amber-400/70 text-xs">Accuracy: {f.accuracy_score ? f.accuracy_score.toFixed(1) : 'N/A'}% | Trend: {f.trend}</p>
            </div>
          ))}
        </div>
      )}

      {/* Recommendations */}
      {report?.recommendations?.length > 0 && (
        <div>
          <h2 className="text-white font-semibold mb-3">JARVIS Recommendations</h2>
          {report.recommendations.map((r, i) => (
            <div key={i} className="bg-white/5 border border-white/10 rounded-xl p-3 mb-2">
              <p className="text-gray-300 text-sm">{r}</p>
            </div>
          ))}
        </div>
      )}

      {/* Recent Reality Checks */}
      {report?.recent_reality_checks?.length > 0 && (
        <div>
          <h2 className="text-white font-semibold mb-3">Recent Reality Checks</h2>
          {report.recent_reality_checks.slice(0, 3).map((rc, i) => (
            <div key={i} className="bg-white/5 border border-white/10 rounded-xl p-4 mb-2">
              <div className="flex justify-between">
                <span className="text-white text-sm">{rc.check_type?.replace(/_/g, ' ')}</span>
                <span className={`text-sm font-bold ${(rc.accuracy_pct || 0) >= 70 ? 'text-emerald-400' : 'text-amber-400'}`}>{rc.accuracy_pct ? rc.accuracy_pct.toFixed(1) + '%' : 'N/A'}</span>
              </div>
              <p className="text-gray-400 text-xs mt-1">{rc.gap_analysis}</p>
            </div>
          ))}
        </div>
      )}

      {/* Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white/5 border border-white/10 rounded-xl p-4">
          <h3 className="text-white text-sm font-semibold mb-3">Record Prediction</h3>
          <select className="w-full bg-white/10 border border-white/20 rounded-lg p-2 text-white text-sm mb-2" value={predForm.prediction_type} onChange={e => setPredForm(p => ({ ...p, prediction_type: e.target.value }))}>
            {PREDICTION_TYPES.map(t => <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>)}
          </select>
          <input className="w-full bg-white/10 border border-white/20 rounded-lg p-2 text-white text-sm mb-2" placeholder="Predicted value (number)" value={predForm.predicted_value} onChange={e => setPredForm(p => ({ ...p, predicted_value: e.target.value }))} />
          <input className="w-full bg-white/10 border border-white/20 rounded-lg p-2 text-white text-sm mb-3" placeholder="Confidence (0-1)" value={predForm.confidence_score} onChange={e => setPredForm(p => ({ ...p, confidence_score: e.target.value }))} />
          <button onClick={submitPrediction} disabled={submitting} className="w-full bg-blue-600 hover:bg-blue-700 text-white text-sm py-2 rounded-lg disabled:opacity-50">{submitting ? 'Recording...' : 'Record Prediction'}</button>
        </div>

        <div className="bg-white/5 border border-white/10 rounded-xl p-4">
          <h3 className="text-white text-sm font-semibold mb-3">Run Reality Check</h3>
          <select className="w-full bg-white/10 border border-white/20 rounded-lg p-2 text-white text-sm mb-3" value={checkType} onChange={e => setCheckType(e.target.value)}>
            {PREDICTION_TYPES.map(t => <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>)}
          </select>
          <button onClick={runCheck} disabled={submitting} className="w-full bg-purple-600 hover:bg-purple-700 text-white text-sm py-2 rounded-lg disabled:opacity-50">{submitting ? 'Running...' : 'Run Reality Check'}</button>
          <button onClick={load} className="w-full bg-white/10 hover:bg-white/20 text-white text-sm py-2 rounded-lg mt-2">Refresh</button>
        </div>
      </div>
    </div>
  )
}
