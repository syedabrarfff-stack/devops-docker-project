import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { api } from "../../services/api";

const TIER_COLORS = { A: "text-red-400 bg-red-500/10 border-red-500/30", B: "text-orange-400 bg-orange-500/10 border-orange-500/30", C: "text-yellow-400 bg-yellow-500/10 border-yellow-500/30", D: "text-gray-400 bg-gray-500/10 border-gray-500/30" };
const STATUS_COLORS = { new: "text-blue-400", qualified: "text-green-400", contacted: "text-yellow-400", replied: "text-purple-400", interested: "text-teal-400", proposal: "text-orange-400", closed: "text-green-500", disqualified: "text-red-400" };

function asArray(value, key) {
  if (Array.isArray(value)) return value;
  if (Array.isArray(value?.[key])) return value[key];
  return [];
}

function leadCompany(lead) {
  return lead.company_name || lead.company || lead.enrichment_data?.company_name || lead.email?.split("@")[1] || "Unnamed company";
}

function normaliseStatus(status) {
  return String(status || "new").toLowerCase();
}

function errorText(error, fallback) {
  return error?.response?.data?.detail || error?.response?.data?.message || error?.message || fallback;
}

function Notice({ notice, onDismiss }) {
  if (!notice) return null;
  const error = notice.tone === "error";
  return (
    <div className={`rounded-xl border p-3 text-sm ${error ? "border-red-300/25 bg-red-500/10 text-red-100" : "border-emerald-300/25 bg-emerald-500/10 text-emerald-100"}`}>
      <div className="flex items-start justify-between gap-3">
        <p>{notice.text}</p>
        <button onClick={onDismiss} className="text-xs opacity-60 hover:opacity-100">Dismiss</button>
      </div>
    </div>
  );
}

function ScoreBar({ score }) {
  const color = score >= 80 ? "bg-red-500" : score >= 60 ? "bg-orange-500" : score >= 40 ? "bg-yellow-500" : "bg-gray-500";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-white/10 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${score}%` }} />
      </div>
      <span className="text-xs text-gray-400 w-8 text-right">{score}</span>
    </div>
  );
}

function LeadRow({ lead, onScore }) {
  const [scoring, setScoring] = useState(false);

  async function handleScore() {
    setScoring(true);
    try { await onScore(lead.id); } finally { setScoring(false); }
  }

  return (
    <motion.div
      layout
      className="glass rounded-xl p-4 border border-white/5 hover:border-blue-500/20 transition-all"
    >
      <div className="flex items-start justify-between mb-3">
        <div>
          <p className="font-semibold text-white">{leadCompany(lead)}</p>
          <p className="text-sm text-gray-400">{lead.contact_name || "-"}</p>
        </div>
        <div className="flex items-center gap-2">
          {lead.tier && (
            <span className={`text-xs px-2 py-0.5 rounded-full border font-bold ${TIER_COLORS[lead.tier] || TIER_COLORS.D}`}>
              {lead.tier}
            </span>
          )}
          <span className={`text-xs ${STATUS_COLORS[normaliseStatus(lead.status)] || "text-gray-400"}`}>{normaliseStatus(lead.status)}</span>
        </div>
      </div>

      <ScoreBar score={lead.score || 0} />

      <div className="flex items-center gap-4 mt-3 text-xs text-gray-500">
        <span>{lead.industry || "Unknown"}</span>
        <span>{lead.country || "Unknown"}</span>
        {lead.email && <span className="truncate max-w-32">{lead.email}</span>}
      </div>

      {/* Contact channels */}
      {(lead.whatsapp_number || lead.phone || lead.linkedin_url) && (
        <div className="flex items-center gap-3 mt-2">
          {(lead.whatsapp_number || lead.phone) && (
            <a
              href={`https://wa.me/${(lead.whatsapp_number || lead.phone).replace(/[^\d]/g, '')}`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-xs text-green-400 hover:text-green-300"
            >
              <span>📱</span>
              <span>{lead.whatsapp_number || lead.phone}</span>
            </a>
          )}
          {lead.linkedin_url && (
            <a
              href={lead.linkedin_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-blue-400 hover:text-blue-300"
            >
              🔗 LinkedIn
            </a>
          )}
        </div>
      )}

      {lead.pain_points?.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {lead.pain_points.slice(0, 3).map(pp => (
            <span key={pp} className="text-xs px-1.5 py-0.5 rounded bg-white/5 text-gray-400">{pp}</span>
          ))}
        </div>
      )}

      <div className="flex items-center justify-between mt-3">
        <span className="text-xs text-gray-600">Source: {lead.source}</span>
        {lead.score === 0 && (
          <button
            onClick={handleScore}
            disabled={scoring}
            className="text-xs px-3 py-1 rounded-lg bg-blue-600/20 hover:bg-blue-600/40 text-blue-400 border border-blue-500/20 transition-colors disabled:opacity-50"
          >
            {scoring ? "Scoring..." : "Score with AI"}
          </button>
        )}
      </div>
    </motion.div>
  );
}

export default function LeadsDashboard() {
  const [leads, setLeads] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [showAdd, setShowAdd] = useState(false);
  const [newLead, setNewLead] = useState({ company: "", contact_name: "", email: "", industry: "", country: "" });
  const [bulkScoring, setBulkScoring] = useState(false);
  const [notice, setNotice] = useState(null);

  useEffect(() => { loadAll(); }, []);

  async function loadAll() {
    setLoading(true);
    try {
      const [l, s] = await Promise.all([
        api.get("/api/v1/leads/?limit=100").then(r => r.data),
        api.get("/api/v1/leads/stats").then(r => r.data),
      ]);
      setLeads(asArray(l, "leads"));
      setStats(s);
    } catch (e) {
      setLeads([]);
      setStats({});
      setNotice({ tone: "error", text: errorText(e, "Lead pipeline failed to load.") });
    }
    setLoading(false);
  }

  async function scoreLead(id) {
    try {
      await api.post(`/api/v1/leads/${id}/score`);
      setNotice({ tone: "success", text: "Lead scoring completed." });
      await loadAll();
    } catch (e) {
      setNotice({ tone: "error", text: errorText(e, "Lead scoring failed.") });
    }
  }

  async function bulkScore() {
    setBulkScoring(true);
    try {
      const response = await api.post("/api/v1/leads/bulk-score?limit=20");
      setNotice({ tone: "success", text: response.data?.message || "Bulk lead scoring started." });
      await loadAll();
    } catch (e) {
      setNotice({ tone: "error", text: errorText(e, "Bulk lead scoring failed.") });
    }
    finally { setBulkScoring(false); }
  }

  async function addLead() {
    try {
      await api.post("/api/v1/leads/?auto_score=true", newLead);
      setShowAdd(false);
      setNewLead({ company: "", contact_name: "", email: "", industry: "", country: "" });
      setNotice({ tone: "success", text: "Lead added. AI scoring will run in the background." });
      setTimeout(loadAll, 2000); // brief delay for background scoring
    } catch (e) {
      setNotice({ tone: "error", text: errorText(e, "Lead creation failed.") });
    }
  }

  const filtered = filter === "all" ? leads :
    filter === "unscored" ? leads.filter(l => l.score === 0) :
    leads.filter(l => normaliseStatus(l.status) === filter);

  return (
    <div className="min-h-full p-6 pb-28 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Lead Generation</h1>
          <p className="text-gray-400 text-sm">AI-scored prospects for Aliyar Solutions</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={bulkScore}
            disabled={bulkScoring}
            className="px-4 py-2 border border-blue-500/30 text-blue-400 hover:bg-blue-500/10 rounded-lg text-sm transition-colors disabled:opacity-50"
          >
            {bulkScoring ? "Scoring..." : "Bulk Score AI"}
          </button>
          <button
            onClick={() => setShowAdd(true)}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors"
          >
            + Add Lead
          </button>
        </div>
      </div>

      <Notice notice={notice} onDismiss={() => setNotice(null)} />

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {[
          { label: "Total", value: stats.total || 0, color: "text-white" },
          { label: "Qualified", value: stats.qualified || 0, color: "text-green-400" },
          { label: "Contacted", value: stats.contacted || 0, color: "text-blue-400" },
          { label: "Avg Score", value: `${stats.avg_score || 0}`, color: "text-yellow-400" },
          { label: "Conversion", value: `${stats.conversion_rate || 0}%`, color: "text-purple-400" },
        ].map(s => (
          <div key={s.label} className="glass rounded-xl p-4 border border-white/5">
            <p className="text-gray-400 text-xs mb-1">{s.label}</p>
            <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
          </div>
        ))}
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-1 bg-white/5 rounded-lg p-1 w-fit flex-wrap">
        {["all", "unscored", "new", "qualified", "contacted", "interested"].map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all capitalize ${
              filter === f ? "bg-blue-600 text-white" : "text-gray-400 hover:text-white"
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      {/* Lead Grid */}
      {loading ? (
        <div className="text-center text-gray-500 py-12">Loading leads...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.length === 0 ? (
            <p className="text-gray-500 col-span-3 text-center py-8">No leads found. Add your first lead.</p>
          ) : (
            filtered.map(l => <LeadRow key={l.id} lead={l} onScore={scoreLead} />)
          )}
        </div>
      )}

      {/* Add Lead Modal */}
      {showAdd && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 overflow-y-auto p-4"
          onClick={() => setShowAdd(false)}
        >
          <div
            className="glass rounded-2xl border border-white/10 p-6 w-full max-w-md"
            onClick={e => e.stopPropagation()}
          >
            <h2 className="text-lg font-bold text-white mb-4">New Lead</h2>
            <div className="space-y-3">
              {[
                { key: "company", placeholder: "Company name *" },
                { key: "contact_name", placeholder: "Contact name" },
                { key: "email", placeholder: "Email address" },
                { key: "industry", placeholder: "Industry (saas, hotel, clinic...)" },
                { key: "country", placeholder: "Country (usa, uk, canada...)" },
              ].map(f => (
                <input
                  key={f.key}
                  value={newLead[f.key]}
                  onChange={e => setNewLead(p => ({ ...p, [f.key]: e.target.value }))}
                  placeholder={f.placeholder}
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 text-sm focus:outline-none focus:border-blue-500/50"
                />
              ))}
            </div>
            <p className="text-xs text-gray-500 mt-2">AI scoring will run automatically in the background.</p>
            <div className="flex gap-3 mt-4">
              <button onClick={() => setShowAdd(false)} className="flex-1 py-2 rounded-lg border border-white/10 text-gray-400 hover:text-white text-sm transition-colors">Cancel</button>
              <button onClick={addLead} disabled={!newLead.company} className="flex-1 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-40 text-white text-sm font-medium transition-colors">Add Lead</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
