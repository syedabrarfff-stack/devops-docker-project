import { useState, useEffect } from "react"
import api from "../../services/api"

const STATUS_COLORS = {
  draft:       "text-gray-400 bg-gray-500/10 border-gray-600",
  sent:        "text-blue-400 bg-blue-500/10 border-blue-500/30",
  paid:        "text-green-400 bg-green-500/10 border-green-500/30",
  accepted:    "text-green-400 bg-green-500/10 border-green-500/30",
  overdue:     "text-red-400 bg-red-500/10 border-red-500/30",
  cancelled:   "text-red-400 bg-red-500/10 border-red-500/30",
  declined:    "text-red-400 bg-red-500/10 border-red-500/30",
  negotiating: "text-yellow-400 bg-yellow-500/10 border-yellow-500/30",
  open:        "text-red-400 bg-red-500/10 border-red-500/30",
  investigating:"text-orange-400 bg-orange-500/10 border-orange-500/30",
  resolved:    "text-green-400 bg-green-500/10 border-green-500/30",
}

const SEV_COLORS = {
  low:      "text-gray-400",
  medium:   "text-yellow-400",
  high:     "text-orange-400",
  critical: "text-red-400",
}

function StatusBadge({ status }) {
  const cls = STATUS_COLORS[status] || STATUS_COLORS.draft
  return (
    <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded border ${cls}`}>
      {status}
    </span>
  )
}

// ── Invoices Tab ─────────────────────────────────────────────────────────────
function InvoicesTab() {
  const [invoices, setInvoices] = useState([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({
    client_name: "", client_email: "", client_company: "",
    description: "", amount: "", tax_rate: "0", currency: "USD", notes: "", due_days: "14",
  })

  useEffect(() => { load() }, [])

  async function load() {
    setLoading(true)
    try {
      const data = await api.get("/api/v1/governance/invoices").then(r => r.data)
      setInvoices(data.invoices || [])
    } catch (e) { console.error(e) }
    setLoading(false)
  }

  async function createInvoice() {
    const amount = parseFloat(form.amount) || 0
    try {
      await api.post("/api/v1/governance/invoices", {
        client_name: form.client_name,
        client_email: form.client_email,
        client_company: form.client_company,
        items: [{ description: form.description, qty: 1, unit_price: amount, amount }],
        tax_rate: parseFloat(form.tax_rate) || 0,
        currency: form.currency,
        notes: form.notes,
        due_days: parseInt(form.due_days) || 14,
      })
      setShowCreate(false)
      setForm({ client_name: "", client_email: "", client_company: "", description: "", amount: "", tax_rate: "0", currency: "USD", notes: "", due_days: "14" })
      load()
    } catch (e) { alert(e.response?.data?.detail || e.message) }
  }

  async function updateStatus(id, status) {
    await api.post(`/api/v1/governance/invoices/${id}/status`, { status })
    load()
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <button onClick={() => setShowCreate(true)}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors">
          + New Invoice
        </button>
      </div>

      {showCreate && (
        <div className="glass rounded-xl p-5 border border-blue-500/20">
          <h3 className="text-sm font-semibold text-white mb-4">Create Invoice (requires Captain approval before sending)</h3>
          <div className="grid grid-cols-2 gap-3 mb-3">
            {[["client_name","Client Name"],["client_email","Client Email"],["client_company","Company"],["description","Service Description"]].map(([k,p]) => (
              <input key={k} value={form[k]} onChange={e => setForm(f => ({...f,[k]:e.target.value}))}
                placeholder={p}
                className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white placeholder-gray-500 text-sm focus:outline-none focus:border-blue-500/50" />
            ))}
          </div>
          <div className="grid grid-cols-4 gap-3 mb-4">
            {[["amount","Amount (USD)"],["tax_rate","Tax %"],["due_days","Due Days"],["currency","Currency"]].map(([k,p]) => (
              <input key={k} value={form[k]} onChange={e => setForm(f => ({...f,[k]:e.target.value}))}
                placeholder={p}
                className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white placeholder-gray-500 text-sm focus:outline-none" />
            ))}
          </div>
          <div className="flex gap-3">
            <button onClick={createInvoice}
              className="px-4 py-2 bg-green-600 hover:bg-green-500 text-white rounded-lg text-sm font-medium">
              Create Draft
            </button>
            <button onClick={() => setShowCreate(false)}
              className="px-4 py-2 bg-white/5 hover:bg-white/10 text-gray-400 rounded-lg text-sm">
              Cancel
            </button>
          </div>
        </div>
      )}

      {loading ? <div className="text-gray-500 text-sm p-4">Loading invoices...</div> :
        invoices.length === 0 ? (
          <div className="glass rounded-xl p-8 border border-white/5 text-center">
            <p className="text-gray-400 text-sm">No invoices yet.</p>
          </div>
        ) : invoices.map(inv => (
          <div key={inv.id} className="glass rounded-xl p-5 border border-white/5">
            <div className="flex items-start justify-between mb-2">
              <div>
                <p className="text-sm font-semibold text-white">{inv.invoice_number}</p>
                <p className="text-xs text-gray-400">{inv.client_name} · {inv.client_company}</p>
              </div>
              <div className="flex items-center gap-3">
                <p className="text-lg font-bold text-white">{inv.currency} {inv.total.toFixed(2)}</p>
                <StatusBadge status={inv.status} />
              </div>
            </div>
            <div className="flex items-center gap-2 mt-3">
              {inv.status === "draft" && (
                <button onClick={() => updateStatus(inv.id, "sent")}
                  className="px-3 py-1 bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 border border-blue-500/30 rounded text-xs">
                  Mark Sent
                </button>
              )}
              {inv.status === "sent" && (
                <button onClick={() => updateStatus(inv.id, "paid")}
                  className="px-3 py-1 bg-green-600/20 hover:bg-green-600/30 text-green-400 border border-green-500/30 rounded text-xs">
                  Mark Paid
                </button>
              )}
              {["draft","sent"].includes(inv.status) && (
                <button onClick={() => updateStatus(inv.id, "cancelled")}
                  className="px-3 py-1 bg-white/[0.05] hover:bg-white/[0.08] text-gray-500 rounded text-xs">
                  Cancel
                </button>
              )}
              {inv.due_date && (
                <span className="text-xs text-gray-600 ml-auto">Due: {new Date(inv.due_date).toLocaleDateString()}</span>
              )}
            </div>
          </div>
        ))
      }
    </div>
  )
}

// ── Proposals Tab ─────────────────────────────────────────────────────────────
function ProposalsTab() {
  const [proposals, setProposals] = useState([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [expanded, setExpanded] = useState(null)
  const [form, setForm] = useState({
    client_name: "", client_email: "", client_company: "",
    service_type: "", context: "", style: "standard",
    setup_fee: "", monthly_retainer: "",
  })

  useEffect(() => { load() }, [])

  async function load() {
    setLoading(true)
    try {
      const data = await api.get("/api/v1/governance/proposals").then(r => r.data)
      setProposals(data.proposals || [])
    } catch (e) { console.error(e) }
    setLoading(false)
  }

  async function generate() {
    if (!form.client_name || !form.service_type) return
    setGenerating(true)
    try {
      await api.post("/api/v1/governance/proposals/generate", {
        client_name: form.client_name,
        client_email: form.client_email,
        client_company: form.client_company,
        service_type: form.service_type,
        context: form.context,
        style: form.style,
        pricing: {
          setup_fee: form.setup_fee,
          monthly_retainer: form.monthly_retainer,
        },
      })
      load()
    } catch (e) { alert(e.response?.data?.detail || e.message) }
    setGenerating(false)
  }

  async function updateStatus(id, status) {
    await api.post(`/api/v1/governance/proposals/${id}/status`, { status })
    load()
  }

  return (
    <div className="space-y-4">
      <div className="glass rounded-xl p-5 border border-white/5">
        <h3 className="text-sm font-semibold text-white mb-3">Generate AI Proposal</h3>
        <div className="grid grid-cols-2 gap-3 mb-3">
          {[["client_name","Client Name *"],["client_company","Company"],["client_email","Email"],["service_type","Service Type *"]].map(([k,p]) => (
            <input key={k} value={form[k]} onChange={e => setForm(f => ({...f,[k]:e.target.value}))}
              placeholder={p}
              className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white placeholder-gray-500 text-sm focus:outline-none focus:border-blue-500/50" />
          ))}
        </div>
        <textarea value={form.context} onChange={e => setForm(f => ({...f,context:e.target.value}))}
          placeholder="Context: pain points, goals, industry, budget signals..."
          rows={2}
          className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white placeholder-gray-500 text-sm focus:outline-none mb-3 resize-none" />
        <div className="grid grid-cols-3 gap-3 mb-4">
          <select value={form.style} onChange={e => setForm(f => ({...f,style:e.target.value}))}
            className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none">
            {["standard","case_study","short_urgent","social_proof"].map(s => (
              <option key={s} value={s}>{s.replace(/_/g," ")}</option>
            ))}
          </select>
          <input value={form.setup_fee} onChange={e => setForm(f => ({...f,setup_fee:e.target.value}))}
            placeholder="Setup fee (USD)"
            className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white placeholder-gray-500 text-sm focus:outline-none" />
          <input value={form.monthly_retainer} onChange={e => setForm(f => ({...f,monthly_retainer:e.target.value}))}
            placeholder="Monthly retainer"
            className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white placeholder-gray-500 text-sm focus:outline-none" />
        </div>
        <button onClick={generate} disabled={!form.client_name || !form.service_type || generating}
          className="px-4 py-2 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-colors">
          {generating ? "Generating..." : "Generate Proposal (AI)"}
        </button>
      </div>

      {loading ? <div className="text-gray-500 text-sm p-4">Loading proposals...</div> :
        proposals.map(prop => (
          <div key={prop.id} className="glass rounded-xl border border-white/5">
            <button className="w-full flex items-start justify-between p-5 text-left"
              onClick={() => setExpanded(expanded === prop.id ? null : prop.id)}>
              <div>
                <p className="text-sm font-semibold text-white">{prop.title}</p>
                <p className="text-xs text-gray-400 mt-0.5">{prop.client_name} · {prop.service_type}</p>
              </div>
              <div className="flex items-center gap-2">
                <StatusBadge status={prop.status} />
                <span className="text-gray-600">{expanded === prop.id ? "▲" : "▼"}</span>
              </div>
            </button>
            {expanded === prop.id && (
              <div className="px-5 pb-5 border-t border-white/5 pt-4">
                <pre className="text-xs text-gray-300 whitespace-pre-wrap leading-relaxed font-sans mb-4 max-h-80 overflow-y-auto">
                  {prop.content}
                </pre>
                {prop.status === "draft" && (
                  <div className="flex gap-2">
                    <button onClick={() => updateStatus(prop.id, "sent")}
                      className="px-3 py-1.5 bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 border border-blue-500/30 rounded text-xs">
                      Mark Sent (needs Captain approval)
                    </button>
                    <button onClick={() => updateStatus(prop.id, "accepted")}
                      className="px-3 py-1.5 bg-green-600/20 hover:bg-green-600/30 text-green-400 border border-green-500/30 rounded text-xs">
                      Accepted
                    </button>
                    <button onClick={() => updateStatus(prop.id, "declined")}
                      className="px-3 py-1.5 bg-white/[0.05] hover:bg-white/[0.08] text-gray-500 rounded text-xs">
                      Declined
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        ))
      }
    </div>
  )
}

// ── Incidents Tab ─────────────────────────────────────────────────────────────
function IncidentsTab() {
  const [incidents, setIncidents] = useState([])
  const [health, setHealth] = useState(null)
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({ title: "", severity: "medium", category: "infrastructure", description: "" })

  useEffect(() => { load() }, [])

  async function load() {
    setLoading(true)
    const [inc, hlth] = await Promise.all([
      api.get("/api/v1/emergency/incidents").then(r => r.data).catch(() => ({ incidents: [] })),
      api.get("/api/v1/emergency/health").then(r => r.data).catch(() => null),
    ])
    setIncidents(inc.incidents || [])
    setHealth(hlth)
    setLoading(false)
  }

  async function declare() {
    if (!form.title || !form.description) return
    try {
      await api.post("/api/v1/emergency/incidents", {
        ...form,
        affected_systems: [],
      })
      setShowCreate(false)
      setForm({ title: "", severity: "medium", category: "infrastructure", description: "" })
      load()
    } catch (e) { alert(e.message) }
  }

  async function resolve(id) {
    await api.post(`/api/v1/emergency/incidents/${id}/resolve`, { actions_taken: ["Manually resolved by Captain"] })
    load()
  }

  const overallColor = health?.overall === "ok" ? "text-green-400" :
                       health?.overall === "degraded" ? "text-yellow-400" : "text-red-400"

  return (
    <div className="space-y-4">
      {/* Health panel */}
      {health && (
        <div className="glass rounded-xl p-5 border border-white/5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-white">System Health</h3>
            <span className={`text-sm font-bold uppercase ${overallColor}`}>{health.overall}</span>
          </div>
          <div className="grid grid-cols-3 gap-3">
            {Object.entries(health.subsystems || {}).map(([name, info]) => (
              <div key={name} className="p-3 bg-white/[0.03] rounded-lg border border-white/[0.05]">
                <p className="text-xs text-gray-500 capitalize">{name.replace(/_/g," ")}</p>
                <p className={`text-xs font-semibold mt-1 ${
                  info.status === "ok" ? "text-green-400" :
                  info.status === "degraded" ? "text-yellow-400" : "text-red-400"
                }`}>{info.status}</p>
                {info.providers !== undefined && (
                  <p className="text-[10px] text-gray-600">{info.providers} providers</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="flex justify-end">
        <button onClick={() => setShowCreate(true)}
          className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded-lg text-sm font-medium transition-colors">
          🚨 Declare Incident
        </button>
      </div>

      {showCreate && (
        <div className="glass rounded-xl p-5 border border-red-500/20">
          <h3 className="text-sm font-semibold text-white mb-3">Declare Incident</h3>
          <div className="space-y-3">
            <input value={form.title} onChange={e => setForm(f => ({...f,title:e.target.value}))}
              placeholder="Incident title" className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white placeholder-gray-500 text-sm focus:outline-none" />
            <div className="grid grid-cols-2 gap-3">
              <select value={form.severity} onChange={e => setForm(f => ({...f,severity:e.target.value}))}
                className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none">
                {["low","medium","high","critical"].map(s => <option key={s} value={s}>{s}</option>)}
              </select>
              <select value={form.category} onChange={e => setForm(f => ({...f,category:e.target.value}))}
                className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none">
                {["infrastructure","security","api","automation","billing"].map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <textarea value={form.description} onChange={e => setForm(f => ({...f,description:e.target.value}))}
              placeholder="Describe what happened..." rows={2}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white placeholder-gray-500 text-sm focus:outline-none resize-none" />
            <div className="flex gap-3">
              <button onClick={declare} className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded-lg text-sm font-medium">
                Declare + Notify Captain
              </button>
              <button onClick={() => setShowCreate(false)} className="px-4 py-2 bg-white/5 text-gray-400 rounded-lg text-sm">Cancel</button>
            </div>
          </div>
        </div>
      )}

      {loading ? <div className="text-gray-500 text-sm p-4">Loading incidents...</div> :
        incidents.length === 0 ? (
          <div className="glass rounded-xl p-8 border border-white/5 text-center">
            <p className="text-green-400 text-sm">✅ No active incidents</p>
          </div>
        ) : incidents.map(inc => (
          <div key={inc.id} className="glass rounded-xl p-5 border border-white/5">
            <div className="flex items-start justify-between mb-2">
              <div>
                <p className={`text-sm font-semibold ${SEV_COLORS[inc.severity] || "text-white"}`}>
                  {inc.severity === "critical" ? "🚨 " : ""}{inc.title}
                </p>
                <p className="text-xs text-gray-500 mt-0.5">{inc.category} · {new Date(inc.created_at).toLocaleString()}</p>
              </div>
              <StatusBadge status={inc.status} />
            </div>
            {inc.description && <p className="text-xs text-gray-400 mt-1">{inc.description}</p>}
            {inc.status !== "resolved" && (
              <button onClick={() => resolve(inc.id)} className="mt-3 px-3 py-1.5 bg-green-600/20 hover:bg-green-600/30 text-green-400 border border-green-500/30 rounded text-xs">
                Mark Resolved
              </button>
            )}
          </div>
        ))
      }
    </div>
  )
}

// ── Main Dashboard ─────────────────────────────────────────────────────────────
export default function GovernanceDashboard() {
  const [tab, setTab] = useState("invoices")
  const [stats, setStats] = useState(null)

  useEffect(() => {
    api.get("/api/v1/governance/stats").then(r => setStats(r.data)).catch(() => {})
  }, [])

  const TABS = [
    { id: "invoices",  label: "Invoices" },
    { id: "proposals", label: "Proposals" },
    { id: "incidents", label: "Incidents" },
  ]

  return (
    <div className="h-full min-h-0 overflow-y-auto p-6 pb-28 space-y-5">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Governance</h1>
          <p className="text-gray-400 text-sm">Invoices · Proposals · Agent permissions · Incident control</p>
        </div>
        {stats && (
          <div className="text-right">
            <p className="text-xs text-gray-500">Total invoiced: <span className="text-white font-semibold">${stats.total_invoiced?.toFixed(0)}</span></p>
            <p className="text-xs text-gray-500">Paid: <span className="text-green-400 font-semibold">${stats.total_paid?.toFixed(0)}</span></p>
          </div>
        )}
      </div>

      {stats && (
        <div className="grid grid-cols-4 gap-3">
          {[
            { label: "Total Invoiced",  value: `$${stats.total_invoiced?.toFixed(0)}`,    color: "text-white" },
            { label: "Total Paid",      value: `$${stats.total_paid?.toFixed(0)}`,        color: "text-green-400" },
            { label: "Draft Proposals", value: stats.draft_proposals,                      color: "text-blue-400" },
            { label: "Open Incidents",  value: stats.open_incidents,                       color: stats.open_incidents > 0 ? "text-red-400" : "text-gray-400" },
          ].map(s => (
            <div key={s.label} className="glass rounded-xl p-4 border border-white/5 text-center">
              <p className={`text-xl font-bold ${s.color}`}>{s.value}</p>
              <p className="text-xs text-gray-500 mt-1">{s.label}</p>
            </div>
          ))}
        </div>
      )}

      <div className="flex gap-1 bg-white/[0.03] rounded-lg p-1 border border-white/[0.05]">
        {TABS.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`flex-1 py-2 rounded-md text-sm font-medium transition-all ${
              tab === t.id ? "bg-blue-600 text-white" : "text-gray-400 hover:text-white"
            }`}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === "invoices"  && <InvoicesTab />}
      {tab === "proposals" && <ProposalsTab />}
      {tab === "incidents" && <IncidentsTab />}
    </div>
  )
}
