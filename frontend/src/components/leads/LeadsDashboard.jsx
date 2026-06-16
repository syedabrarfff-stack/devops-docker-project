import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { api } from "../../services/api";
import useJarvisStore from "../../store/useJarvisStore";

const DEFAULT_TENANT = '794d9b02-2dd6-49f0-b5c1-9f7c0b3af4b1'

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

function CallBriefModal({ lead, onClose }) {
  const [tab, setTab] = useState('brief')
  const [brief, setBrief] = useState(null)
  const [support, setSupport] = useState(null)
  const [briefLoading, setBriefLoading] = useState(true)
  const [debrief, setDebrief] = useState({ call_outcome: 'follow-up', notes: '', next_action: '' })
  const [debriefSent, setDebriefSent] = useState(false)
  const [debriefErr, setDebriefErr] = useState(null)
  const [debriefing, setDebriefing] = useState(false)
  const [pdfTier, setPdfTier] = useState('GROWTH')
  const [pdfGenerating, setPdfGenerating] = useState(false)
  const [pdfResult, setPdfResult] = useState(null)
  const [pdfErr, setPdfErr] = useState(null)

  async function generatePdfProposal() {
    setPdfGenerating(true); setPdfErr(null); setPdfResult(null)
    try {
      const r = await api.post('/api/v1/proposals/generate', {
        lead_id: lead.id,
        package_tier: pdfTier,
        tenant_id: DEFAULT_TENANT,
      })
      setPdfResult(r.data)
    } catch (e) {
      setPdfErr(e?.response?.data?.detail || 'PDF generation failed')
    }
    setPdfGenerating(false)
  }

  useEffect(() => {
    api.post('/api/v1/calls/pre-brief', { lead_id: lead.id, tenant_id: DEFAULT_TENANT })
      .then(r => setBrief(r.data))
      .catch(e => setBrief({ error: e?.response?.data?.detail || 'Failed to generate brief' }))
      .finally(() => setBriefLoading(false))
  }, [lead.id])

  async function handleTabSupport() {
    setTab('support')
    if (support) return
    try {
      const r = await api.get(`/api/v1/calls/live-support/${lead.id}`, { params: { tenant_id: DEFAULT_TENANT } })
      setSupport(r.data)
    } catch (e) {
      setSupport({ error: e?.response?.data?.detail || 'Failed to load live support' })
    }
  }

  async function submitDebrief() {
    if (!debrief.notes.trim()) return
    setDebriefing(true); setDebriefErr(null)
    try {
      await api.post('/api/v1/calls/debrief', {
        lead_id: lead.id,
        call_outcome: debrief.call_outcome,
        notes: debrief.notes,
        next_action: debrief.next_action || undefined,
        tenant_id: DEFAULT_TENANT,
      })
      setDebriefSent(true)
    } catch (e) {
      setDebriefErr(e?.response?.data?.detail || 'Debrief failed')
    }
    setDebriefing(false)
  }

  const company = leadCompany(lead)
  const score = brief?.jarvis_confidence_score
  const scoreColor = score >= 80 ? 'text-green-400' : score >= 60 ? 'text-yellow-400' : 'text-red-400'

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-start justify-end z-50 p-4" onClick={onClose}>
      <div
        className="glass rounded-2xl border border-white/10 w-full max-w-lg h-[calc(100vh-2rem)] overflow-hidden flex flex-col"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between p-5 border-b border-white/5">
          <div>
            <p className="text-xs text-purple-400 font-semibold uppercase tracking-wider mb-0.5">📞 Call Intelligence</p>
            <p className="text-white font-bold">{company}</p>
            {lead.contact_name && <p className="text-gray-400 text-sm">{lead.contact_name}</p>}
          </div>
          <button onClick={onClose} className="text-gray-500 hover:text-white text-xl leading-none transition-colors">×</button>
        </div>

        {/* PDF Proposal Generator */}
        <div className="px-5 py-3 border-b border-white/5 bg-white/[0.02]">
          <p className="text-xs text-gray-500 mb-2 font-semibold uppercase tracking-wider">📄 Generate PDF Proposal</p>
          {pdfResult ? (
            <div className="rounded-xl border border-green-500/25 bg-green-500/10 p-3 text-sm">
              <p className="text-green-300 font-semibold">✅ Proposal generated!</p>
              <p className="text-gray-400 text-xs mt-1">Proposal #{pdfResult.invoice_number || pdfResult.proposal_id} · Awaiting Captain approval</p>
              {pdfResult.pdf_url && (
                <a href={pdfResult.pdf_url} target="_blank" rel="noopener noreferrer" className="text-xs text-jarvis-cyan mt-1 block hover:underline">View PDF →</a>
              )}
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <select
                value={pdfTier}
                onChange={e => setPdfTier(e.target.value)}
                className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-white outline-none focus:border-purple-500/50"
              >
                <option value="STARTER">Starter — $2.5K setup + $750/mo</option>
                <option value="GROWTH">Growth — $6.5K setup + $2.5K/mo</option>
                <option value="ENTERPRISE">Enterprise — $15K setup + $5K/mo</option>
              </select>
              <button
                onClick={generatePdfProposal}
                disabled={pdfGenerating}
                className="px-3 py-1.5 rounded-lg bg-purple-600/20 hover:bg-purple-600/30 border border-purple-500/30 text-purple-300 text-xs font-semibold disabled:opacity-50 transition-colors whitespace-nowrap"
              >
                {pdfGenerating ? 'Generating…' : 'Generate PDF →'}
              </button>
            </div>
          )}
          {pdfErr && <p className="text-red-400 text-xs mt-1">{pdfErr}</p>}
        </div>

        {/* Tabs */}
        <div className="flex border-b border-white/5">
          {[
            { id: 'brief', label: '📋 Pre-Brief', onClick: () => setTab('brief') },
            { id: 'support', label: '🎯 Live Support', onClick: handleTabSupport },
            { id: 'debrief', label: '✍️ Debrief', onClick: () => setTab('debrief') },
          ].map(t => (
            <button
              key={t.id}
              onClick={t.onClick}
              className={`flex-1 py-2.5 text-xs font-semibold transition-colors ${tab === t.id ? 'text-purple-400 border-b-2 border-purple-400' : 'text-gray-500 hover:text-gray-300'}`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {/* Pre-Brief */}
          {tab === 'brief' && (
            briefLoading ? (
              <div className="text-center text-gray-500 py-12">Generating intelligence brief…</div>
            ) : brief?.error ? (
              <div className="text-red-400 text-sm p-4 bg-red-500/10 rounded-xl">{brief.error}</div>
            ) : brief ? (
              <>
                {score != null && (
                  <div className="glass rounded-xl p-4 border border-white/5 text-center">
                    <p className="text-xs text-gray-500 mb-1">JARVIS Confidence</p>
                    <p className={`text-3xl font-black ${scoreColor}`}>{score}<span className="text-base text-gray-500">/100</span></p>
                  </div>
                )}

                {brief.pricing_anchor && (
                  <div className="glass rounded-xl p-4 border border-jarvis-gold/20">
                    <p className="text-xs text-jarvis-gold font-semibold mb-2">💰 PRICING ANCHOR</p>
                    <p className="text-white text-sm">{brief.pricing_anchor}</p>
                  </div>
                )}

                {brief.what_to_say && (
                  <div className="glass rounded-xl p-4 border border-white/5">
                    <p className="text-xs text-jarvis-cyan font-semibold mb-2">✅ WHAT TO SAY</p>
                    {Array.isArray(brief.what_to_say)
                      ? <ul className="space-y-1.5">{brief.what_to_say.map((s, i) => <li key={i} className="text-sm text-gray-300 flex gap-2"><span className="text-jarvis-cyan mt-0.5 shrink-0">›</span>{s}</li>)}</ul>
                      : <p className="text-sm text-gray-300">{brief.what_to_say}</p>
                    }
                  </div>
                )}

                {brief.what_not_to_say?.length > 0 && (
                  <div className="glass rounded-xl p-4 border border-red-500/20">
                    <p className="text-xs text-red-400 font-semibold mb-2">🚫 AVOID</p>
                    <ul className="space-y-1">{brief.what_not_to_say.map((s, i) => <li key={i} className="text-sm text-gray-400">— {s}</li>)}</ul>
                  </div>
                )}

                {brief.objection_handlers?.length > 0 && (
                  <div className="glass rounded-xl p-4 border border-white/5">
                    <p className="text-xs text-orange-400 font-semibold mb-2">🛡️ OBJECTION HANDLERS</p>
                    <div className="space-y-3">
                      {brief.objection_handlers.map((obj, i) => (
                        <div key={i} className="text-sm">
                          <p className="text-gray-400 italic">"{obj.objection}"</p>
                          <p className="text-gray-200 mt-1 pl-3 border-l border-orange-500/30">{obj.response}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {brief.known_issues?.length > 0 && (
                  <div className="glass rounded-xl p-4 border border-white/5">
                    <p className="text-xs text-yellow-400 font-semibold mb-2">⚠️ KNOWN ISSUES</p>
                    <ul className="space-y-1">{brief.known_issues.map((s, i) => <li key={i} className="text-sm text-gray-400">• {s}</li>)}</ul>
                  </div>
                )}
              </>
            ) : null
          )}

          {/* Live Support */}
          {tab === 'support' && (
            !support ? (
              <div className="text-center text-gray-500 py-12">Loading live support…</div>
            ) : support?.error ? (
              <div className="text-red-400 text-sm p-4 bg-red-500/10 rounded-xl">{support.error}</div>
            ) : (
              <>
                {support.questions_to_ask?.length > 0 && (
                  <div className="glass rounded-xl p-4 border border-jarvis-cyan/20">
                    <p className="text-xs text-jarvis-cyan font-semibold mb-2">❓ QUESTIONS TO ASK</p>
                    <ul className="space-y-2">{support.questions_to_ask.map((q, i) => <li key={i} className="text-sm text-gray-300 flex gap-2"><span className="text-jarvis-cyan shrink-0">{i+1}.</span>{q}</li>)}</ul>
                  </div>
                )}

                {support.how_to_close?.length > 0 && (
                  <div className="glass rounded-xl p-4 border border-green-500/20">
                    <p className="text-xs text-green-400 font-semibold mb-2">🎯 HOW TO CLOSE</p>
                    <ul className="space-y-2">{support.how_to_close.map((c, i) => <li key={i} className="text-sm text-gray-300 flex gap-2"><span className="text-green-400 shrink-0">›</span>{c}</li>)}</ul>
                  </div>
                )}

                {support.danger_phrases_to_avoid?.length > 0 && (
                  <div className="glass rounded-xl p-4 border border-red-500/20">
                    <p className="text-xs text-red-400 font-semibold mb-2">🚫 NEVER SAY THIS</p>
                    <ul className="space-y-1">{support.danger_phrases_to_avoid.map((p, i) => <li key={i} className="text-sm text-gray-400 line-through">"{p}"</li>)}</ul>
                  </div>
                )}

                {support.objection_responses?.length > 0 && (
                  <div className="glass rounded-xl p-4 border border-white/5">
                    <p className="text-xs text-orange-400 font-semibold mb-2">🛡️ LIVE OBJECTIONS</p>
                    <div className="space-y-3">
                      {support.objection_responses.map((obj, i) => (
                        <div key={i} className="text-sm">
                          <p className="text-gray-400 italic">"{obj.objection}"</p>
                          <p className="text-gray-200 mt-1 pl-3 border-l border-orange-500/30">{obj.response}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )
          )}

          {/* Debrief */}
          {tab === 'debrief' && (
            debriefSent ? (
              <div className="text-center py-12 space-y-3">
                <p className="text-3xl">✅</p>
                <p className="text-white font-semibold">Debrief logged.</p>
                <p className="text-gray-400 text-sm">JARVIS has updated the lead record and learning database.</p>
              </div>
            ) : (
              <div className="space-y-4">
                <div>
                  <label className="text-xs text-gray-500 uppercase tracking-wider block mb-2">Call Outcome</label>
                  <div className="flex gap-2">
                    {[['won', '🏆 Won'], ['lost', '❌ Lost'], ['follow-up', '🔄 Follow-up']].map(([v, l]) => (
                      <button
                        key={v}
                        onClick={() => setDebrief(d => ({ ...d, call_outcome: v }))}
                        className={`flex-1 py-2 rounded-xl text-xs font-semibold border transition-colors ${debrief.call_outcome === v ? 'bg-purple-500/20 border-purple-500/50 text-purple-300' : 'border-white/10 text-gray-500 hover:text-gray-300'}`}
                      >
                        {l}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="text-xs text-gray-500 uppercase tracking-wider block mb-2">Call Notes *</label>
                  <textarea
                    rows={4}
                    value={debrief.notes}
                    onChange={e => setDebrief(d => ({ ...d, notes: e.target.value }))}
                    placeholder="What was discussed? Key pain points confirmed? Budget mentioned?"
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-600 text-sm focus:outline-none focus:border-purple-500/50 resize-none"
                  />
                </div>

                <div>
                  <label className="text-xs text-gray-500 uppercase tracking-wider block mb-2">Next Action</label>
                  <input
                    value={debrief.next_action}
                    onChange={e => setDebrief(d => ({ ...d, next_action: e.target.value }))}
                    placeholder="Send proposal, schedule demo, follow up in 3 days..."
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-white placeholder-gray-600 text-sm focus:outline-none focus:border-purple-500/50"
                  />
                </div>

                {debriefErr && <p className="text-red-400 text-sm">{debriefErr}</p>}

                <button
                  onClick={submitDebrief}
                  disabled={debriefing || !debrief.notes.trim()}
                  className="w-full py-3 rounded-xl bg-purple-600 hover:bg-purple-500 disabled:opacity-40 text-white font-semibold text-sm transition-colors"
                >
                  {debriefing ? 'Logging…' : 'Log Debrief →'}
                </button>
              </div>
            )
          )}
        </div>
      </div>
    </div>
  )
}

function LeadRow({ lead, onScore, onProposal, onCallBrief, onQueueOutreach }) {
  const [scoring, setScoring] = useState(false);
  const [queuing, setQueuing] = useState(false);

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

      <div className="flex items-center justify-between mt-3 gap-2">
        <span className="text-xs text-gray-600">Source: {lead.source}</span>
        <div className="flex items-center gap-2 flex-wrap justify-end">
          {lead.score === 0 && (
            <button
              onClick={handleScore}
              disabled={scoring}
              className="text-xs px-3 py-1 rounded-lg bg-blue-600/20 hover:bg-blue-600/40 text-blue-400 border border-blue-500/20 transition-colors disabled:opacity-50"
            >
              {scoring ? "Scoring..." : "Score with AI"}
            </button>
          )}
          {(lead.score || 0) >= 50 && (
            <>
              <button
                onClick={async () => {
                  setQueuing(true)
                  try { await api.post(`/api/v1/outreach/queue/${lead.id}`) } catch {}
                  setQueuing(false)
                }}
                disabled={queuing}
                className="text-xs px-3 py-1 rounded-lg bg-green-500/10 hover:bg-green-500/20 text-green-400 border border-green-500/20 transition-colors font-semibold disabled:opacity-50"
              >
                {queuing ? "Queueing…" : "📧 Outreach"}
              </button>
              <button
                onClick={() => onCallBrief(lead)}
                className="text-xs px-3 py-1 rounded-lg bg-purple-500/10 hover:bg-purple-500/20 text-purple-400 border border-purple-500/20 transition-colors font-semibold"
              >
                📞 Call Brief
              </button>
              <button
                onClick={() => onProposal(lead)}
                className="text-xs px-3 py-1 rounded-lg bg-jarvis-cyan/10 hover:bg-jarvis-cyan/20 text-jarvis-cyan border border-jarvis-cyan/20 transition-colors font-semibold"
              >
                Proposal →
              </button>
            </>
          )}
        </div>
      </div>
    </motion.div>
  );
}

export default function LeadsDashboard() {
  const { setActiveView, setProposalPrefill } = useJarvisStore()
  const [leads, setLeads] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [showAdd, setShowAdd] = useState(false);
  const [newLead, setNewLead] = useState({ company: "", contact_name: "", email: "", industry: "", country: "" });
  const [bulkScoring, setBulkScoring] = useState(false);
  const [notice, setNotice] = useState(null);
  const [callBriefLead, setCallBriefLead] = useState(null);
  const [showDiscover, setShowDiscover] = useState(false);
  const [discovering, setDiscovering] = useState(false);
  const [discoverForm, setDiscoverForm] = useState({ industry: '', country: 'usa', query: '', limit: 20 });

  function goGenerateProposal(lead) {
    setProposalPrefill({
      client_name: lead.contact_name || '',
      client_email: lead.email || '',
      client_company: lead.company_name || lead.company || '',
      service_type: lead.opportunity_type || lead.pain_points?.[0] || '',
      context: [lead.notes, lead.pain_points?.join(', ')].filter(Boolean).join('\n'),
    })
    setActiveView('proposals')
  }

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

  async function discoverLeads() {
    setDiscovering(true);
    try {
      const payload = {
        tenant_id: DEFAULT_TENANT,
        limit: Number(discoverForm.limit) || 20,
      };
      if (discoverForm.industry) payload.industry = discoverForm.industry.trim();
      if (discoverForm.country) payload.country = discoverForm.country.trim();
      if (discoverForm.query) payload.query = discoverForm.query.trim();
      const r = await api.post("/api/v1/leads/discover", payload);
      const inserted = r.data?.inserted ?? 0;
      setShowDiscover(false);
      setNotice({ tone: "success", text: `Lead discovery complete — ${inserted} new lead${inserted !== 1 ? 's' : ''} added to pipeline.` });
      setTimeout(loadAll, 1500);
    } catch (e) {
      setNotice({ tone: "error", text: errorText(e, "Lead discovery failed.") });
    } finally {
      setDiscovering(false);
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
        <div className="flex gap-2 flex-wrap justify-end">
          <button
            onClick={bulkScore}
            disabled={bulkScoring}
            className="px-4 py-2 border border-blue-500/30 text-blue-400 hover:bg-blue-500/10 rounded-lg text-sm transition-colors disabled:opacity-50"
          >
            {bulkScoring ? "Scoring..." : "Bulk Score AI"}
          </button>
          <button
            onClick={() => setShowDiscover(true)}
            className="px-4 py-2 border border-purple-500/30 text-purple-400 hover:bg-purple-500/10 rounded-lg text-sm transition-colors"
          >
            🔍 Discover Leads
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
            filtered.map(l => <LeadRow key={l.id} lead={l} onScore={scoreLead} onProposal={goGenerateProposal} onCallBrief={setCallBriefLead} />)
          )}
        </div>
      )}

      {/* Call Brief Panel */}
      {callBriefLead && <CallBriefModal lead={callBriefLead} onClose={() => setCallBriefLead(null)} />}

      {/* Discover Leads Modal */}
      {showDiscover && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4"
          onClick={() => setShowDiscover(false)}
        >
          <div
            className="glass rounded-2xl border border-white/10 p-6 w-full max-w-md"
            onClick={e => e.stopPropagation()}
          >
            <h2 className="text-lg font-bold text-white mb-1">Discover Leads</h2>
            <p className="text-xs text-gray-400 mb-4">JARVIS will search Apollo + live sources for qualified prospects matching your criteria.</p>
            <div className="space-y-3">
              <input
                value={discoverForm.query}
                onChange={e => setDiscoverForm(p => ({ ...p, query: e.target.value }))}
                placeholder="Search query (e.g. 'SaaS CFO', 'hotel chain operations')"
                className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 text-sm focus:outline-none focus:border-purple-500/50"
              />
              <input
                value={discoverForm.industry}
                onChange={e => setDiscoverForm(p => ({ ...p, industry: e.target.value }))}
                placeholder="Industry (saas, hotel, clinic, ecommerce...)"
                className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 text-sm focus:outline-none focus:border-purple-500/50"
              />
              <input
                value={discoverForm.country}
                onChange={e => setDiscoverForm(p => ({ ...p, country: e.target.value }))}
                placeholder="Country (usa, uk, canada, australia...)"
                className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 text-sm focus:outline-none focus:border-purple-500/50"
              />
              <div className="flex items-center gap-3">
                <label className="text-xs text-gray-400 whitespace-nowrap">Lead limit:</label>
                <select
                  value={discoverForm.limit}
                  onChange={e => setDiscoverForm(p => ({ ...p, limit: Number(e.target.value) }))}
                  className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-purple-500/50"
                >
                  {[10, 20, 50, 100].map(n => <option key={n} value={n}>{n} leads</option>)}
                </select>
              </div>
            </div>
            <p className="text-xs text-gray-500 mt-2">Discovered leads are auto-scored by JARVIS AI and appear in the pipeline immediately.</p>
            <div className="flex gap-3 mt-4">
              <button onClick={() => setShowDiscover(false)} className="flex-1 py-2 rounded-lg border border-white/10 text-gray-400 hover:text-white text-sm transition-colors">Cancel</button>
              <button
                onClick={discoverLeads}
                disabled={discovering}
                className="flex-1 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 disabled:opacity-40 text-white text-sm font-medium transition-colors"
              >
                {discovering ? "Discovering..." : "Discover Now"}
              </button>
            </div>
          </div>
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
