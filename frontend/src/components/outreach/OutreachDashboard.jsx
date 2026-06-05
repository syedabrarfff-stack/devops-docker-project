import { useState, useEffect } from "react";
import { api } from "../../services/api";

const STATUS_COLOR = {
  scheduled: "text-blue-400 bg-blue-500/10 border-blue-500/20",
  sent: "text-green-400 bg-green-500/10 border-green-500/20",
  failed: "text-red-400 bg-red-500/10 border-red-500/20",
  opened: "text-yellow-400 bg-yellow-500/10 border-yellow-500/20",
  replied: "text-purple-400 bg-purple-500/10 border-purple-500/20",
};

function asArray(value, key) {
  if (Array.isArray(value)) return value;
  if (Array.isArray(value?.[key])) return value[key];
  return [];
}

function Metric({ label, value }) {
  return (
    <div className="rounded-xl border border-white/10 bg-black/20 p-3">
      <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-white/35">{label}</p>
      <p className="mt-1 text-lg font-black text-white">{value}</p>
    </div>
  );
}

export default function OutreachDashboard() {
  const [tab, setTab] = useState("sequences");
  const [sequences, setSequences] = useState([]);
  const [pendingEmails, setPendingEmails] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [newSeq, setNewSeq] = useState({ name: "", target_industry: "saas", target_country: "usa", service_offered: "AI automation" });
  const [sending, setSending] = useState({});
  const [processing, setProcessing] = useState(false);
  const [engine, setEngine] = useState(null);
  const [starting, setStarting] = useState(false);
  const [preparing, setPreparing] = useState(false);
  const [lastRun, setLastRun] = useState(null);

  useEffect(() => { loadAll(); }, []);

  async function loadAll() {
    setLoading(true);
    try {
      const [s, e, engineStatus] = await Promise.all([
        api.get("/api/v1/outreach/sequences/stats").then(r => r.data),
        api.get("/api/v1/outreach/emails/pending?limit=50").then(r => r.data),
        api.get("/api/v1/outreach/engine-status").then(r => r.data).catch(() => null),
      ]);
      setSequences(asArray(s, "sequences"));
      setPendingEmails(asArray(e, "emails"));
      setEngine(engineStatus);
    } catch (e) { console.error(e); }
    setLoading(false);
  }

  async function createSequence() {
    try {
      await api.post("/api/v1/outreach/sequences?ai_generate=true", newSeq);
      setShowNew(false);
      setNewSeq({ name: "", target_industry: "saas", target_country: "usa", service_offered: "AI automation" });
      loadAll();
    } catch (e) { console.error(e); }
  }

  async function sendEmail(id) {
    setSending(s => ({ ...s, [id]: true }));
    try {
      await api.post(`/api/v1/outreach/emails/${id}/send`);
      loadAll();
    } catch (e) { console.error(e); }
    setSending(s => ({ ...s, [id]: false }));
  }

  async function processDue() {
    setProcessing(true);
    try {
      const r = await api.post("/api/v1/outreach/emails/process-due?limit=10");
      alert(`Processed ${r.data.processed} emails, sent ${r.data.sent}`);
      loadAll();
    } catch (e) { console.error(e); }
    setProcessing(false);
  }

  async function startEngine() {
    setStarting(true);
    try {
      const r = await api.post("/api/v1/outreach/execute", { limit: 48, autonomy_stage: "outreach_emails" });
      setLastRun(r.data);
      await loadAll();
    } catch (e) {
      setLastRun({ error: e?.response?.data?.detail || e.message || "Engine start failed" });
    } finally {
      setStarting(false);
    }
  }

  async function prepareCampaign() {
    setPreparing(true);
    try {
      const r = await api.post("/api/v1/outreach/prepare-campaign", { limit: 25, min_score: 65 });
      setLastRun(r.data);
      await loadAll();
    } catch (e) {
      setLastRun({ error: e?.response?.data?.detail || e.message || "Campaign preparation failed" });
    } finally {
      setPreparing(false);
    }
  }

  async function connectGmail() {
    try {
      const r = await api.get("/api/v1/auth/gmail/initiate");
      window.open(r.data.auth_url, "_blank", "width=720,height=760");
    } catch (e) {
      setLastRun({ error: e?.response?.data?.detail || e.message || "Gmail OAuth start failed" });
    }
  }

  const engineReady = engine?.status === "ready";
  const engineBlocked = engine?.status === "blocked";
  const engineTone = engineReady
    ? "border-emerald-400/25 bg-emerald-500/[0.08] text-emerald-100"
    : "border-amber-400/25 bg-amber-500/[0.08] text-amber-100";

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Outreach</h1>
          <p className="text-gray-400 text-sm">Email sequences &amp; campaigns</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={processDue}
            disabled={processing}
            className="px-4 py-2 border border-green-500/30 text-green-400 hover:bg-green-500/10 rounded-lg text-sm transition-colors disabled:opacity-50"
          >
            {processing ? "Sending..." : "Send Due Emails"}
          </button>
          <button
            onClick={() => setShowNew(true)}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors"
          >
            + New Sequence
          </button>
        </div>
      </div>

      {/* Engine Control */}
      <div className={`rounded-2xl border p-5 ${engineTone}`}>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.24em] opacity-70">Outreach Engine</p>
            <h2 className="mt-1 text-xl font-black text-white">
              {engineReady ? "Ready to send" : engineBlocked ? "Blocked before send" : "Reading live status"}
            </h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-white/65">
              {engine?.next_action || "JARVIS is checking Gmail, queue, lead availability, authority, and daily send cap."}
            </p>
          </div>
          <button
            onClick={startEngine}
            disabled={!engineReady || starting}
            className="rounded-xl border border-emerald-300/30 bg-emerald-500/15 px-5 py-2.5 text-sm font-bold text-emerald-100 transition hover:bg-emerald-500/25 disabled:cursor-not-allowed disabled:border-white/10 disabled:bg-white/5 disabled:text-white/35"
          >
            {starting ? "Starting..." : "Start Outreach Engine"}
          </button>
          <button
            onClick={prepareCampaign}
            disabled={preparing}
            className="rounded-xl border border-cyan-300/30 bg-cyan-500/15 px-5 py-2.5 text-sm font-bold text-cyan-100 transition hover:bg-cyan-500/25 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {preparing ? "Preparing..." : "Prepare Campaign Queue"}
          </button>
          {engine?.gmail?.oauth_configured && !engine?.gmail?.oauth_connected && (
            <button
              onClick={connectGmail}
              className="rounded-xl border border-blue-300/30 bg-blue-500/15 px-5 py-2.5 text-sm font-bold text-blue-100 transition hover:bg-blue-500/25"
            >
              Connect Gmail OAuth
            </button>
          )}
        </div>

        <div className="mt-5 grid gap-3 md:grid-cols-5">
          <Metric label="Mode" value={(engine?.status || "unknown").toUpperCase()} />
          <Metric label="Gmail" value={(engine?.gmail?.send_mode || "unknown").toUpperCase()} />
          <Metric label="Pending" value={engine?.queue?.pending_followups ?? "-"} />
          <Metric label="With Email" value={engine?.leads?.with_email ?? "-"} />
          <Metric label="Remaining Today" value={engine?.queue?.remaining_today ?? "-"} />
        </div>

        {!!engine?.blockers?.length && (
          <div className="mt-4 rounded-xl border border-amber-200/15 bg-black/20 p-3">
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-amber-100/70">Blockers</p>
            <div className="mt-2 space-y-1">
              {engine.blockers.map((blocker) => (
                <p key={blocker} className="text-xs leading-5 text-white/70">{blocker}</p>
              ))}
            </div>
          </div>
        )}

        {lastRun && (
          <div className="mt-4 rounded-xl border border-cyan-200/15 bg-cyan-500/[0.06] p-3 text-xs text-cyan-100/80">
            {lastRun.error
              ? `Last action failed: ${lastRun.error}`
              : lastRun.queued_leads !== undefined
                ? `Prepared queue: ${lastRun.queued_leads} leads queued, ${lastRun.skipped?.length || 0} skipped.`
                : `Last run: sent ${lastRun.sent ?? 0} emails for tenant ${lastRun.tenant_id || ""}`}
          </div>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <div className="glass rounded-xl p-4 border border-white/5">
          <p className="text-gray-400 text-xs mb-1">Active Sequences</p>
          <p className="text-2xl font-bold text-blue-400">{sequences.length}</p>
        </div>
        <div className="glass rounded-xl p-4 border border-white/5">
          <p className="text-gray-400 text-xs mb-1">Pending Emails</p>
          <p className="text-2xl font-bold text-yellow-400">{pendingEmails.length}</p>
        </div>
        <div className="glass rounded-xl p-4 border border-white/5">
          <p className="text-gray-400 text-xs mb-1">Avg Open Rate</p>
          <p className="text-2xl font-bold text-green-400">
            {sequences.length ? Math.round(sequences.reduce((s, q) => s + (q.open_rate || 0), 0) / sequences.length) : 0}%
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-white/5 rounded-lg p-1 w-fit">
        {["sequences", "pending"].map(t => (
          <button key={t} onClick={() => setTab(t)} className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all capitalize ${tab === t ? "bg-blue-600 text-white" : "text-gray-400 hover:text-white"}`}>{t}</button>
        ))}
      </div>

      {/* Content */}
      {loading ? (
        <div className="text-center text-gray-500 py-12">Loading...</div>
      ) : tab === "sequences" ? (
        <div className="space-y-3">
          {sequences.length === 0 ? (
            <div className="text-center text-gray-500 py-12">
              <p>No sequences yet.</p>
              <p className="text-sm mt-1">Create your first AI-powered email sequence.</p>
            </div>
          ) : (
            sequences.map(seq => (
              <div key={seq.id} className="glass rounded-xl p-4 border border-white/5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-semibold text-white">{seq.name}</p>
                    <p className="text-xs text-gray-500 mt-1">
                      {seq.emails_sent} sent · {seq.replies_received} replies · {seq.open_rate}% open rate
                    </p>
                  </div>
                  <span className={`text-xs px-2 py-0.5 rounded-full border ${seq.status === "active" ? "border-green-500/30 text-green-400" : "border-gray-600 text-gray-400"}`}>
                    {seq.status}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {pendingEmails.length === 0 ? (
            <div className="text-center text-gray-500 py-12">No pending emails.</div>
          ) : (
            pendingEmails.map(email => (
              <div key={email.id} className="glass rounded-xl p-4 border border-white/5 flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-white">{email.subject}</p>
                  <p className="text-xs text-gray-500 mt-1">{email.to_email} · Step {email.step_number} · Due: {new Date(email.scheduled_at).toLocaleDateString()}</p>
                </div>
                <button
                  onClick={() => sendEmail(email.id)}
                  disabled={sending[email.id]}
                  className="ml-4 px-3 py-1.5 rounded-lg bg-green-600/20 hover:bg-green-600/40 text-green-400 border border-green-500/20 text-xs transition-colors disabled:opacity-50 whitespace-nowrap"
                >
                  {sending[email.id] ? "Sending..." : "Send Now"}
                </button>
              </div>
            ))
          )}
        </div>
      )}

      {/* New Sequence Modal */}
      {showNew && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50" onClick={() => setShowNew(false)}>
          <div className="glass rounded-2xl border border-white/10 p-6 w-full max-w-md" onClick={e => e.stopPropagation()}>
            <h2 className="text-lg font-bold text-white mb-4">New Outreach Sequence</h2>
            <div className="space-y-3">
              {[
                { key: "name", placeholder: "Sequence name *" },
                { key: "target_industry", placeholder: "Target industry (saas, hotel, clinic...)" },
                { key: "target_country", placeholder: "Target country (usa, uk, canada...)" },
                { key: "service_offered", placeholder: "Service offered (AI automation, DevOps...)" },
              ].map(f => (
                <input key={f.key} value={newSeq[f.key]} onChange={e => setNewSeq(p => ({ ...p, [f.key]: e.target.value }))} placeholder={f.placeholder}
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 text-sm focus:outline-none focus:border-blue-500/50" />
              ))}
            </div>
            <p className="text-xs text-gray-500 mt-2">Gemini AI will generate the 3-step email sequence automatically.</p>
            <div className="flex gap-3 mt-4">
              <button onClick={() => setShowNew(false)} className="flex-1 py-2 rounded-lg border border-white/10 text-gray-400 text-sm">Cancel</button>
              <button onClick={createSequence} disabled={!newSeq.name} className="flex-1 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-40 text-white text-sm font-medium">Create with AI</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
