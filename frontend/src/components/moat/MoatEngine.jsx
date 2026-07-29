import { useState, useEffect } from 'react'
import { getMoatReport, getMoatDimensions, getMoatThreats, runMoatScan } from '../../services/api'

const DIMENSIONS = [
  { key: 'proprietary_data', label: 'Proprietary Data', desc: 'Lead database + client intelligence accumulated' },
  { key: 'case_studies', label: 'Case Studies', desc: 'Delivered projects as referenceable proof' },
  { key: 'delivery_intelligence', label: 'Delivery Intelligence', desc: 'Lessons from every completed project' },
  { key: 'relationship_graph', label: 'Relationship Graph', desc: 'Network of engaged clients and prospects' },
  { key: 'institutional_wisdom', label: 'Institutional Wisdom', desc: 'Knowledge base + SOPs + AIONx memory' },
  { key: 'automation_advantage', label: 'Automation Advantage', desc: '33 scheduled jobs + 57 routes running 24/7' },
  { key: 'operational_speed', label: 'Operational Speed', desc: 'Delivery speed vs industry average' },
]

function DefensibilityColor(label) {
  return { fortress: 'text-emerald-400', strong: 'text-blue-400', building: 'text-amber-400', vulnerable: 'text-rose-400' }[label] || 'text-gray-400'
}

export default function MoatEngine() {
  const [report, setReport] = useState(null)
  const [dims, setDims] = useState(null)
  const [threats, setThreats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [scanning, setScanning] = useState(false)
  const [msg, setMsg] = useState(null)

  const load = async () => {
    setLoading(true)
    try {
      const [r, d, t] = await Promise.all([
        getMoatReport(),
        getMoatDimensions(),
        getMoatThreats(),
      ])
      setReport(r); setDims(d); setThreats(t)
    } catch (e) { setError(e.message) }
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const runScan = async () => {
    setScanning(true)
    try {
      await runMoatScan()
      setMsg('Moat scan complete.')
      load()
    } catch (e) { setMsg(`Error: ${e.message}`) }
    setScanning(false)
  }

  if (loading) return <div className="text-gray-400 p-8">Loading Competitive Moat Engine...</div>
  if (error) return <div className="text-rose-400 p-8">Error: {error}</div>

  const latest = report?.latest || {}
  const moatScore = latest.moat_score ?? 0
  const threatScore = latest.competitive_threat_score ?? 100
  const defensibility = latest.defensibility || 'vulnerable'
  const dimData = dims?.dimensions || latest.dimensions || {}

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Competitive Moat</h1>
        <p className="text-gray-400 text-sm mt-1">Strategic Defensibility — Building an Unassailable Position</p>
      </div>

      {msg && <div className="bg-blue-500/20 border border-blue-500/30 rounded-lg p-3 text-blue-300 text-sm">{msg}</div>}

      {/* Top Scores */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-white/5 border border-white/10 rounded-xl p-6 text-center">
          <p className="text-gray-400 text-sm mb-2">Moat Score</p>
          <p className={`text-5xl font-bold ${DefensibilityColor(defensibility)}`}>{moatScore.toFixed(0)}</p>
          <p className={`text-sm mt-2 font-medium ${DefensibilityColor(defensibility)}`}>{defensibility.toUpperCase()}</p>
        </div>
        <div className="bg-white/5 border border-white/10 rounded-xl p-6 text-center">
          <p className="text-gray-400 text-sm mb-2">Competitive Threat</p>
          <p className={`text-5xl font-bold ${threatScore > 60 ? 'text-rose-400' : threatScore > 40 ? 'text-amber-400' : 'text-emerald-400'}`}>{threatScore.toFixed(0)}</p>
          <p className="text-gray-500 text-sm mt-2">Higher = more vulnerable</p>
        </div>
      </div>

      {/* Moat Score Bar */}
      <div className="bg-white/5 border border-white/10 rounded-xl p-5">
        <div className="flex justify-between mb-2">
          <span className="text-white text-sm font-medium">Moat Progress</span>
          <span className={DefensibilityColor(defensibility)}>{moatScore.toFixed(1)}/100</span>
        </div>
        <div className="w-full bg-white/10 rounded-full h-3">
          <div className={`h-3 rounded-full transition-all ${moatScore >= 80 ? 'bg-emerald-500' : moatScore >= 60 ? 'bg-blue-500' : moatScore >= 40 ? 'bg-amber-500' : 'bg-rose-500'}`} style={{ width: `${moatScore}%` }} />
        </div>
        <div className="flex justify-between mt-1 text-gray-600 text-xs">
          <span>Vulnerable</span><span>Building</span><span>Strong</span><span>Fortress</span>
        </div>
      </div>

      {/* 7 Dimensions */}
      <div>
        <h2 className="text-white font-semibold mb-3">7 Moat Dimensions</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {DIMENSIONS.map(d => {
            const val = dimData[d.key] ?? 0
            return (
              <div key={d.key} className="bg-white/5 border border-white/10 rounded-xl p-4">
                <div className="flex justify-between mb-1">
                  <span className="text-white text-sm font-medium">{d.label}</span>
                  <span className={`text-sm font-bold ${val >= 60 ? 'text-emerald-400' : val >= 30 ? 'text-amber-400' : 'text-rose-400'}`}>{val.toFixed(0)}</span>
                </div>
                <div className="w-full bg-white/10 rounded-full h-1.5 mb-1">
                  <div className={`h-1.5 rounded-full ${val >= 60 ? 'bg-emerald-500' : val >= 30 ? 'bg-amber-500' : 'bg-rose-500'}`} style={{ width: `${val}%` }} />
                </div>
                <p className="text-gray-500 text-xs">{d.desc}</p>
              </div>
            )
          })}
        </div>
      </div>

      {/* Strengths */}
      {(latest.strengths_identified || threats?.strengths || []).length > 0 && (
        <div>
          <h2 className="text-white font-semibold mb-3">Strategic Strengths</h2>
          {(latest.strengths_identified || threats?.strengths || []).map((s, i) => (
            <div key={i} className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-3 mb-2">
              <p className="text-emerald-300 text-sm">✓ {s}</p>
            </div>
          ))}
        </div>
      )}

      {/* Threats */}
      {(latest.threats_identified || threats?.threats || []).length > 0 && (
        <div>
          <h2 className="text-white font-semibold mb-3">Competitive Threats</h2>
          {(latest.threats_identified || threats?.threats || []).map((t, i) => (
            <div key={i} className="bg-rose-500/10 border border-rose-500/20 rounded-xl p-3 mb-2">
              <p className="text-rose-300 text-sm">✗ {t}</p>
            </div>
          ))}
        </div>
      )}

      {/* Strategic Actions */}
      {(latest.strategic_actions || threats?.strategic_actions || []).length > 0 && (
        <div className="bg-white/5 border border-white/10 rounded-xl p-5">
          <h2 className="text-white font-semibold mb-3">Strategic Actions</h2>
          {(latest.strategic_actions || threats?.strategic_actions || []).map((a, i) => (
            <div key={i} className="flex items-start gap-2 mb-2">
              <span className="text-blue-400 font-bold text-sm mt-0.5">{i + 1}.</span>
              <p className="text-gray-300 text-sm">{a}</p>
            </div>
          ))}
        </div>
      )}

      {/* Defensibility Report */}
      {latest.defensibility_report && (
        <div className="bg-white/5 border border-white/10 rounded-xl p-5">
          <h2 className="text-white font-semibold mb-3">Defensibility Report</h2>
          <pre className="text-gray-300 text-xs whitespace-pre-wrap font-mono">{latest.defensibility_report}</pre>
        </div>
      )}

      <div className="flex gap-3">
        <button onClick={runScan} disabled={scanning} className="bg-emerald-600 hover:bg-emerald-700 text-white text-sm px-6 py-2 rounded-lg disabled:opacity-50">{scanning ? 'Scanning...' : 'Run Moat Scan'}</button>
        <button onClick={load} className="bg-white/10 hover:bg-white/20 text-white text-sm px-6 py-2 rounded-lg">Refresh</button>
      </div>
    </div>
  )
}
