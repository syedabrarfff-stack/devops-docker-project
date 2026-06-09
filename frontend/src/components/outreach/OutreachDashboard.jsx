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

function SesOperationsPanel({ email }) {
  if (!email || email.provider !== "ses") return null;
  const review = email.account_review || {};
  const identities = email.identity_details || [];
  const records = identities.flatMap((identity) => identity.dkim_records || []);

  return (
    <div className="mt-4 rounded-xl border border-cyan-200/15 bg-cyan-500/[0.06] p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-cyan-100/70">AWS SES Sovereign Email</p>
          <h3 className="mt-1 text-sm font-black text-white">{email.from_name || "Joseph David"} &lt;{email.from_email || "not configured"}&gt;</h3>
          <p className="mt-1 text-xs leading-5 text-white/60">
            Production: {String(!!email.production_access_enabled).toUpperCase()} - Identity verified: {String(!!email.identity_verified).toUpperCase()} - Method: {email.send_method || "ses_raw_email"}
          </p>
        </div>
        <div className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-xs text-white/70">
          <span className="font-bold text-white">Review:</span> {review.status || "not submitted"}
          {review.case_id ? <span> - Case {review.case_id}</span> : null}
        </div>
      </div>

      {!!identities.length && (
        <div className="mt-3 grid gap-2 md:grid-cols-2">
          {identities.map((identity) => (
            <div key={identity.identity} className="rounded-lg border border-white/10 bg-black/20 p-3">
              <p className="text-xs font-bold text-white">{identity.identity}</p>
              <p className="mt-1 text-[11px] text-white/55">
                Verification: {identity.verification_status || "unknown"} - DKIM: {identity.dkim_status || "unknown"}
              </p>
            </div>
          ))}
        </div>
      )}

      {!!records.length && (
        <div className="mt-3 rounded-lg border border-white/10 bg-black/25 p-3">
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-cyan-100/70">DNS Records Required</p>
          <div className="mt-2 space-y-2">
            {records.map((record) => (
              <div key={record.name} className="rounded-md border border-white/10 bg-black/20 p-2">
                <p className="text-[11px] text-white/45">{record.type}</p>
                <p className="break-all text-xs font-semibold text-white">{record.name}</p>
                <p className="break-all text-xs text-cyan-100/75">{record.value}</p>
              </div>
            ))}
          </div>
        </div>
      )}
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
  const [notice, setNotice] = useState(null);

  useEffect(() => { loadAll(); }, []);

  useEffect(() => {
    const onMessage = (event) => {
      if (event.origin !== window.location.origin || event.data?.type !== "jarvis:email-connected") return;
      setLastRun({ email_connected: true });
      loadAll();
    };
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, []);

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
      const r = await api.post(`/api/v1/outreach/emails/${id}/send`);
      setNotice({ tone: "success", text: r.data?.message || "Email sent and logged." });
      await loadAll();
    } catch (e) {
      setNotice({ tone: "error", text: e?.response?.data?.detail || e.message || "Email send failed." });
    }
    setSending(s => ({ ...s, [id]: false }));
  }

  async function processDue() {
    setProcessing(true);
    try {
      const r = await api.post("/api/v1/outreach/emails/process-due?limit=10");
      setNotice({ tone: "success", text: `Processed ${r.data.processed ?? 0} emails, sent ${r.data.sent ?? 0}.` });
      await loadAll();
    } catch (e) {
      setNotice({ tone: "error", text: e?.response?.data?.detail || e.message || "Due email processing failed." });
    }
    setProcessing(false);
  }

  async function startEngine() {
    setStarting(true);
    try {
      const r = await api.post("/api/v1/outreach/execute", { limit: 48, autonomy_stage: "outreach_emails" });
      setLastRun(r.data);
      setNotice({ tone: "success", text: `Engine run completed: sent ${r.data?.sent ?? 0}, blocked ${r.data?.blocked ?? 0}.` });
      await loadAll();
    } catch (e) {
      const text = e?.response?.data?.detail || e.message || "Engine start failed";
      setLastRun({ error: text });
      setNotice({ tone: "error", text });
    } finally {
      setStarting(false);
    }
  }

  async function prepareCampaign() {
    setPreparing(true);
    try {
      const r = await api.post("/api/v1/outreach/prepare-campaign", { limit: 25, min_score: 80 });
      setLastRun(r.data);
      setNotice({ tone: "success", text: `Campaign queue prepared: ${r.data?.queued_leads ?? 0} leads queued.` });
      await loadAll();
    } catch (e) {
      const text = e?.response?.data?.detail || e.message || "Campaign preparation failed";
      setLastRun({ error: text });
      setNotice({ tone: "error", text });
    } finally {
      setPreparing(false);
    }
  }

  async function connectGmail() {
    try {
      await loadAll();
      setLastRun({ email_connected: true, note: "Executive email status refreshed." });
      setNotice({ tone: "success", text: "Executive email status refreshed." });
    } catch (e) {
      const text = e?.response?.data?.detail || e.message || "Email status refresh failed";
      setLastRun({ error: text });
      setNotice({ tone: "error", text });
    }
  }

  const engineReady = engine?.status === "ready";
  const engineBlocked = engine?.status === "blocked";
  const engineTone = engineReady
    ? "border-emerald-400/25 bg-emerald-500/[0.08] text-emerald-100"
    : "border-amber-400/25 bg-amber-500/[0.08] text-amber-100";

  return (
    <div className="min-h-full p-6 pb-24 space-y-6">
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

      {notice && (
        <div className={`rounded-xl border p-3 text-sm ${
          notice.tone === "error"
            ? "border-red-300/25 bg-red-500/10 text-red-100"
            : "border-emerald-300/25 bg-emerald-500/10 text-emerald-100"
        }`}>
          <div className="flex items-start justify-between gap-3">
            <p>{notice.text}</p>
            <button onClick={() => setNotice(null)} className="text-xs opacity-60 hover:opacity-100">Dismiss</button>
          </div>
        </div>
      )}

      {/* Engine Control */}
      <div className={`rounded-2xl border p-5 ${engineTone}`}>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.24em] opacity-70">Outreach Engine</p>
            <h2 className="mt-1 text-xl font-black text-white">
              {engineReady ? "Ready to send" : engineBlocked ? "Blocked before send" : "Reading live status"}
            </h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-white/65">
              {engine?.next_action || "JARVIS is checking executive email, queue, lead availability, authority, and daily send cap."}
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
          {engine?.email?.configured && !engine?.email?.connected && (
            <button
              onClick={connectGmail}
              className="rounded-xl border border-blue-300/30 bg-blue-500/15 px-5 py-2.5 text-sm font-bold text-blue-100 transition hover:bg-blue-500/25"
            >
              Refresh Email Status
            </button>
          )}
        </div>

        <div className="mt-5 grid gap-3 md:grid-cols-6">
          <Metric label="Mode" value={(engine?.status || "unknown").toUpperCase()} />
          <Metric label="Email" value={(engine?.email?.send_mode || "unknown").toUpperCase()} />
          <Metric label="Pending" value={engine?.queue?.pending_followups ?? "-"} />
          <Metric label="Captain Review" value={engine?.queue?.pending_approvals ?? "-"} />
          <Metric label="With Email" value={engine?.leads?.with_email ?? "-"} />
          <Metric label="Remaining Today" value={engine?.queue?.remaining_today ?? "-"} />
        </div>

        {(engine?.queue?.pending_approvals || 0) > 0 && (
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-sky-200/15 bg-sky-500/[0.07] p-3">
            <p className="text-xs leading-5 text-sky-100/80">
              {engine.queue.pending_approvals} lead or action is waiting for Captain review. Approved outreach enrollment reviews now auto-queue the lead.
            </p>
            <a
              href="/control-room/approvals"
              className="rounded-lg border border-sky-300/25 bg-sky-400/10 px-3 py-1.5 text-xs font-bold text-sky-100 transition hover:bg-sky-400/20"
            >
              Open Approvals
            </a>
          </div>
        )}

        {engine?.email?.send_mode === "blocked" && (
          <div className="mt-4 rounded-xl border border-orange-200/15 bg-orange-500/[0.07] p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.18em] text-orange-100/70">Email Action Required</p>
                <p className="mt-2 text-sm font-semibold text-white">{engine.email.human_message || "Executive email is not live yet."}</p>
                <p className="mt-1 text-xs leading-5 text-white/65">{engine.email.required_action || "Verify AWS SES before starting outreach."}</p>
              </div>
              {engine.email.configured && !engine.email.connected && (
                <button
                  onClick={connectGmail}
                  className="rounded-lg border border-orange-300/25 bg-orange-400/10 px-3 py-1.5 text-xs font-bold text-orange-100 transition hover:bg-orange-400/20"
                >
                  Refresh Email Status
                </button>
              )}
            </div>
            {!!engine.email.setup_steps?.length && (
              <div className="mt-3 grid gap-2 md:grid-cols-2">
                {engine.email.setup_steps.map((step, index) => (
                  <p key={`${index}-${step}`} className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-xs leading-5 text-white/65">
                    {index + 1}. {step}
                  </p>
                ))}
              </div>
            )}
          </div>
        )}

        <SesOperationsPanel email={engine?.email} />

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
              : lastRun.email_connected
                ? "Executive email status refreshed."
                : lastRun.email_connecting
                  ? "Waiting for SES provisioning..."
                  : lastRun.note
                    ? lastRun.note
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
                      {seq.emails_sent} sent - {seq.replies_received} replies - {seq.open_rate}% open rate
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
              <div key={email.id} className="glass rounded-xl p-4 border border-white/5 flex items-center justify-between gap-4">
                <div>
                  <p className="text-sm font-medium text-white">{email.subject}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    {email.company || email.to_name || "Queued lead"} - {email.to_email || "missing email"} - Step {email.step_number}
                    {email.scheduled_at ? ` - Due: ${new Date(email.scheduled_at).toLocaleDateString()}` : ""}
                  </p>
                  {email.body_preview && (
                    <p className="mt-2 max-w-3xl text-xs leading-5 text-gray-400">{email.body_preview}</p>
                  )}
                </div>
                {email.queue_source === "follow_up_queue" ? (
                  <button
                    onClick={startEngine}
                    disabled={!engineReady || starting}
                    className="px-3 py-1.5 rounded-lg bg-cyan-600/20 hover:bg-cyan-600/40 text-cyan-300 border border-cyan-500/20 text-xs transition-colors disabled:opacity-40 whitespace-nowrap"
                  >
                    {engineReady ? "Run Engine" : "Waiting SES"}
                  </button>
                ) : (
                  <button
                    onClick={() => sendEmail(email.id)}
                    disabled={sending[email.id]}
                    className="px-3 py-1.5 rounded-lg bg-green-600/20 hover:bg-green-600/40 text-green-400 border border-green-500/20 text-xs transition-colors disabled:opacity-50 whitespace-nowrap"
                  >
                    {sending[email.id] ? "Sending..." : "Send Now"}
                  </button>
                )}
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
