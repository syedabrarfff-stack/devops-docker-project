import { useState, useEffect } from "react"
import api from "../../services/api"

const STATUS_CONFIG = {
  adopt:  { label: "Adopt",  color: "text-green-400",  bg: "bg-green-500/10",  border: "border-green-500/30" },
  trial:  { label: "Trial",  color: "text-blue-400",   bg: "bg-blue-500/10",   border: "border-blue-500/30" },
  assess: { label: "Assess", color: "text-yellow-400", bg: "bg-yellow-500/10", border: "border-yellow-500/30" },
  hold:   { label: "Hold",   color: "text-red-400",    bg: "bg-red-500/10",    border: "border-red-500/30" },
}

const PRIORITY_CONFIG = {
  critical: { color: "text-red-400",    bg: "bg-red-500/10",    border: "border-red-500/30",    dot: "bg-red-400" },
  high:     { color: "text-orange-400", bg: "bg-orange-500/10", border: "border-orange-500/30", dot: "bg-orange-400" },
  medium:   { color: "text-yellow-400", bg: "bg-yellow-500/10", border: "border-yellow-500/30", dot: "bg-yellow-400" },
  low:      { color: "text-gray-400",   bg: "bg-gray-500/10",   border: "border-gray-600",      dot: "bg-gray-400" },
}

const CONF_CONFIG = {
  high:   { color: "text-green-400",  label: "High Confidence" },
  medium: { color: "text-yellow-400", label: "Medium Confidence" },
  low:    { color: "text-gray-400",   label: "Low Confidence" },
}

function TechRadarTab({ pulse }) {
  const [radar, setRadar] = useState(null)
  const [loading, setLoading] = useState(true)
  const [scanning, setScanning] = useState(false)

  useEffect(() => { loadRadar() }, [])

  async function loadRadar() {
    setLoading(true)
    try {
      const data = await api.get("/api/v1/intelligence/radar").then(r => r.data)
      setRadar(data)
    } catch (e) { console.error(e) }
    setLoading(false)
  }

  async function triggerScan() {
    setScanning(true)
    try {
      await api.post("/api/v1/intelligence/radar/scan")
      setTimeout(() => { loadRadar(); setScanning(false) }, 8000)
    } catch (e) { setScanning(false) }
  }

  if (loading) return <div className="p-6 text-gray-500 text-sm">Loading tech radar...</div>

  const categories = radar?.categories || {}
  const byStatus = radar?.by_status || {}

  return (
    <div className="space-y-5">
      {/* Summary + scan button */}
      <div className="flex items-center justify-between">
        <div className="flex gap-3">
          {Object.entries(STATUS_CONFIG).map(([status, cfg]) => (
            <div key={status} className={`px-3 py-1.5 rounded-lg text-xs font-medium ${cfg.bg} ${cfg.color} border ${cfg.border}`}>
              {cfg.label}: {byStatus[status] || 0}
            </div>
          ))}
        </div>
        <button
          onClick={triggerScan}
          disabled={scanning}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-colors"
        >
          {scanning ? "Scanning..." : "Run Tech Scan"}
        </button>
      </div>

      {Object.keys(categories).length === 0 ? (
        <div className="glass rounded-xl p-8 border border-white/5 text-center">
          <p className="text-gray-400 text-sm mb-3">No tech radar data yet.</p>
          <p className="text-gray-600 text-xs">Click "Run Tech Scan" to generate your first analysis.</p>
        </div>
      ) : (
        Object.entries(categories).map(([category, entries]) => (
          <div key={category} className="glass rounded-xl p-5 border border-white/5">
            <h3 className="text-sm font-semibold text-white/70 uppercase tracking-wider mb-3">{category}</h3>
            <div className="grid grid-cols-1 gap-3">
              {entries.map((entry) => {
                const cfg = STATUS_CONFIG[entry.status] || STATUS_CONFIG.assess
                return (
                  <div key={entry.id} className="flex items-start gap-4 p-3 bg-white/[0.03] rounded-lg border border-white/[0.05]">
                    <span className={`shrink-0 mt-0.5 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${cfg.bg} ${cfg.color} border ${cfg.border}`}>
                      {cfg.label}
                    </span>
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-white">{entry.name}</p>
                      <p className="text-xs text-gray-400 mt-0.5">{entry.summary}</p>
                      {entry.recommendation && (
                        <p className="text-xs text-blue-400/80 mt-1">{entry.recommendation}</p>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        ))
      )}
    </div>
  )
}

function RecommendationsTab() {
  const [recs, setRecs] = useState([])
  const [loading, setLoading] = useState(true)
  const [analyzing, setAnalyzing] = useState(false)
  const [filter, setFilter] = useState("pending")

  useEffect(() => { loadRecs() }, [filter])

  async function loadRecs() {
    setLoading(true)
    try {
      const data = await api.get("/api/v1/intelligence/recommendations", { params: { status: filter || undefined } }).then(r => r.data)
      setRecs(data.recommendations || [])
    } catch (e) { console.error(e) }
    setLoading(false)
  }

  async function triggerAnalysis() {
    setAnalyzing(true)
    try {
      await api.post("/api/v1/intelligence/recommendations/analyze")
      setTimeout(() => { loadRecs(); setAnalyzing(false) }, 8000)
    } catch (e) { setAnalyzing(false) }
  }

  async function updateStatus(id, status) {
    try {
      await api.post(`/api/v1/intelligence/recommendations/${id}/${status}`)
      loadRecs()
    } catch (e) { console.error(e) }
  }

  const FILTERS = ["pending", "approved", "implemented", "dismissed", ""]

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex gap-2">
          {FILTERS.map(f => (
            <button
              key={f || "all"}
              onClick={() => setFilter(f)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                filter === f ? "bg-blue-600 text-white" : "text-gray-400 hover:text-white bg-white/[0.05]"
              }`}
            >
              {f || "All"}
            </button>
          ))}
        </div>
        <button
          onClick={triggerAnalysis}
          disabled={analyzing}
          className="px-4 py-2 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-colors"
        >
          {analyzing ? "Analyzing..." : "Run Analysis"}
        </button>
      </div>

      {loading ? (
        <div className="text-gray-500 text-sm p-4">Loading recommendations...</div>
      ) : recs.length === 0 ? (
        <div className="glass rounded-xl p-8 border border-white/5 text-center">
          <p className="text-gray-400 text-sm mb-2">No recommendations found.</p>
          <p className="text-gray-600 text-xs">Click "Run Analysis" to generate system optimization recommendations.</p>
        </div>
      ) : (
        recs.map(rec => {
          const cfg = PRIORITY_CONFIG[rec.priority] || PRIORITY_CONFIG.medium
          return (
            <div key={rec.id} className="glass rounded-xl p-5 border border-white/5">
              <div className="flex items-start justify-between gap-3 mb-3">
                <div className="flex items-start gap-3">
                  <span className={`shrink-0 w-2 h-2 rounded-full mt-2 ${cfg.dot}`} />
                  <div>
                    <p className="text-sm font-semibold text-white">{rec.title}</p>
                    <p className="text-xs text-gray-500 mt-0.5 capitalize">{rec.area.replace(/_/g, " ")}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded border ${cfg.bg} ${cfg.color} ${cfg.border}`}>
                    {rec.priority}
                  </span>
                  <span className="text-[10px] text-gray-500 px-2 py-0.5 rounded border border-gray-700 bg-white/[0.03]">
                    {rec.status}
                  </span>
                </div>
              </div>

              <div className="space-y-2 text-xs text-gray-400 ml-5">
                {rec.current_state && <p><span className="text-gray-600">Now:</span> {rec.current_state}</p>}
                {rec.recommended_state && <p><span className="text-blue-500">Target:</span> {rec.recommended_state}</p>}
                {rec.estimated_impact && <p><span className="text-green-600">Impact:</span> {rec.estimated_impact}</p>}
              </div>

              {rec.action_steps?.length > 0 && (
                <ol className="mt-3 ml-5 space-y-1">
                  {rec.action_steps.map((step, i) => (
                    <li key={i} className="text-xs text-gray-500 flex gap-2">
                      <span className="text-gray-700 shrink-0">{i + 1}.</span>
                      <span>{step}</span>
                    </li>
                  ))}
                </ol>
              )}

              {rec.status === "pending" && (
                <div className="flex gap-2 mt-4">
                  <button
                    onClick={() => updateStatus(rec.id, "approve")}
                    className="px-3 py-1.5 bg-green-600/20 hover:bg-green-600/30 text-green-400 border border-green-500/30 rounded-lg text-xs font-medium transition-colors"
                  >
                    Approve
                  </button>
                  <button
                    onClick={() => updateStatus(rec.id, "implement")}
                    className="px-3 py-1.5 bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 border border-blue-500/30 rounded-lg text-xs font-medium transition-colors"
                  >
                    Implement
                  </button>
                  <button
                    onClick={() => updateStatus(rec.id, "dismiss")}
                    className="px-3 py-1.5 bg-white/[0.05] hover:bg-white/[0.08] text-gray-500 rounded-lg text-xs transition-colors"
                  >
                    Dismiss
                  </button>
                </div>
              )}
            </div>
          )
        })
      )}
    </div>
  )
}

function ResearchTab() {
  const [reports, setReports] = useState([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [expanded, setExpanded] = useState(null)
  const [topic, setTopic] = useState("")
  const [category, setCategory] = useState("market")

  useEffect(() => { loadReports() }, [])

  async function loadReports() {
    setLoading(true)
    try {
      const data = await api.get("/api/v1/intelligence/reports").then(r => r.data)
      setReports(data.reports || [])
    } catch (e) { console.error(e) }
    setLoading(false)
  }

  async function generateReport() {
    if (!topic.trim()) return
    setGenerating(true)
    try {
      await api.post("/api/v1/intelligence/reports/generate", { topic: topic.trim(), category })
      setTopic("")
      setTimeout(() => { loadReports(); setGenerating(false) }, 10000)
    } catch (e) { setGenerating(false) }
  }

  return (
    <div className="space-y-4">
      {/* Generate form */}
      <div className="glass rounded-xl p-5 border border-white/5">
        <h3 className="text-sm font-semibold text-white mb-3">Generate Research Report</h3>
        <div className="flex gap-3">
          <input
            value={topic}
            onChange={e => setTopic(e.target.value)}
            placeholder="Research topic (e.g. AI automation demand in hospitality)"
            className="flex-1 bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 text-sm focus:outline-none focus:border-blue-500/50"
          />
          <select
            value={category}
            onChange={e => setCategory(e.target.value)}
            className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none"
          >
            {["market", "technology", "competitor", "niche", "infrastructure"].map(c => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
          <button
            onClick={generateReport}
            disabled={!topic.trim() || generating}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-colors whitespace-nowrap"
          >
            {generating ? "Generating..." : "Generate"}
          </button>
        </div>
      </div>

      {loading ? (
        <div className="text-gray-500 text-sm p-4">Loading reports...</div>
      ) : reports.length === 0 ? (
        <div className="glass rounded-xl p-8 border border-white/5 text-center">
          <p className="text-gray-400 text-sm">No research reports yet.</p>
          <p className="text-gray-600 text-xs mt-1">Enter a topic above or wait for the Sunday automated report.</p>
        </div>
      ) : (
        reports.map(report => {
          const conf = CONF_CONFIG[report.confidence_level] || CONF_CONFIG.medium
          const isOpen = expanded === report.id
          return (
            <div key={report.id} className="glass rounded-xl border border-white/5">
              <button
                onClick={() => setExpanded(isOpen ? null : report.id)}
                className="w-full flex items-start gap-3 p-5 text-left"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-white/[0.05] text-gray-500 border border-gray-700">
                      {report.category}
                    </span>
                    <span className={`text-[10px] font-medium ${conf.color}`}>{conf.label}</span>
                  </div>
                  <p className="text-sm font-semibold text-white truncate">{report.title}</p>
                  {report.summary && (
                    <p className="text-xs text-gray-400 mt-1 line-clamp-2">{report.summary}</p>
                  )}
                </div>
                <span className="text-gray-600 shrink-0 mt-1">{isOpen ? "▲" : "▼"}</span>
              </button>

              {isOpen && (
                <div className="px-5 pb-5 space-y-4 border-t border-white/5 pt-4">
                  {report.findings?.length > 0 && (
                    <Section title="Findings" items={report.findings} color="text-white" />
                  )}
                  {report.opportunities?.length > 0 && (
                    <Section title="Opportunities" items={report.opportunities} color="text-green-400" />
                  )}
                  {report.risks?.length > 0 && (
                    <Section title="Risks" items={report.risks} color="text-red-400" />
                  )}
                  {report.action_items?.length > 0 && (
                    <Section title="Action Items" items={report.action_items} color="text-blue-400" />
                  )}
                  <p className="text-[10px] text-gray-600 mt-2">
                    Generated: {report.created_at ? new Date(report.created_at).toLocaleString() : "—"}
                  </p>
                </div>
              )}
            </div>
          )
        })
      )}
    </div>
  )
}

function Section({ title, items, color }) {
  return (
    <div>
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">{title}</p>
      <ul className="space-y-1">
        {items.map((item, i) => (
          <li key={i} className={`text-xs flex gap-2 ${color}`}>
            <span className="text-gray-700 shrink-0">•</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function IntelligenceDashboard() {
  const [tab, setTab] = useState("radar")
  const [pulse, setPulse] = useState(null)

  useEffect(() => {
    api.get("/api/v1/intelligence/pulse").then(r => setPulse(r.data)).catch(() => {})
  }, [])

  const TABS = [
    { id: "radar",    label: "Tech Radar" },
    { id: "recs",     label: "Recommendations" },
    { id: "research", label: "Research" },
  ]

  return (
    <div className="h-full overflow-y-auto p-6 space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Intelligence Layer</h1>
          <p className="text-gray-400 text-sm">Tech radar · Self-optimization · Autonomous research</p>
        </div>
        {pulse && (
          <div className="text-right">
            <p className="text-xs text-gray-500">
              {pulse.available_providers?.length || 0} AI providers active
            </p>
            <p className="text-xs text-gray-600 mt-0.5">
              {pulse.intelligence?.pending_recommendations || 0} pending recommendations
            </p>
          </div>
        )}
      </div>

      {/* Pulse stats */}
      {pulse && (
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: "Radar Entries",     value: pulse.intelligence?.tech_radar_entries || 0,        color: "text-blue-400" },
            { label: "Recommendations",   value: pulse.intelligence?.optimization_recommendations || 0, color: "text-purple-400" },
            { label: "Research Reports",  value: pulse.intelligence?.research_reports || 0,           color: "text-green-400" },
          ].map(s => (
            <div key={s.label} className="glass rounded-xl p-4 border border-white/5 text-center">
              <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
              <p className="text-xs text-gray-500 mt-1">{s.label}</p>
            </div>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 bg-white/[0.03] rounded-lg p-1 border border-white/[0.05]">
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex-1 py-2 rounded-md text-sm font-medium transition-all ${
              tab === t.id
                ? "bg-blue-600 text-white"
                : "text-gray-400 hover:text-white"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === "radar"    && <TechRadarTab pulse={pulse} />}
      {tab === "recs"     && <RecommendationsTab />}
      {tab === "research" && <ResearchTab />}
    </div>
  )
}
