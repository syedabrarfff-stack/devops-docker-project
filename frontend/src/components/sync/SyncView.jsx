import { useState, useEffect } from "react";
import { api } from "../../services/api";

export default function SyncView() {
  const [gmailStatus, setGmailStatus] = useState(null);
  const [webhookInfo, setWebhookInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [enriching, setEnriching] = useState(false);
  const [syncResult, setSyncResult] = useState(null);
  const [webhookUrl, setWebhookUrl] = useState("");
  const [enrichId, setEnrichId] = useState("");
  const [syncConfig, setSyncConfig] = useState({ industries: "", countries: "", limit: 50 });

  useEffect(() => { loadAll(); }, []);

  async function loadAll() {
    setLoading(true);
    try {
      const [gm, wh] = await Promise.all([
        api.get("/api/v1/auth/gmail/status").then(r => r.data).catch(() => null),
        api.get("/api/v1/sync/telegram/webhook/info").then(r => r.data).catch(() => null),
      ]);
      setGmailStatus(gm);
      setWebhookInfo(wh);
    } catch (e) { console.error(e); }
    setLoading(false);
  }

  async function connectGmail() {
    try {
      const r = await api.get("/api/v1/auth/gmail/initiate");
      window.open(r.data.auth_url, "_blank", "width=600,height=700");
    } catch (e) { alert(`Error: ${e.response?.data?.detail || e.message}`); }
  }

  async function revokeGmail() {
    await api.post("/api/v1/auth/gmail/revoke");
    loadAll();
  }

  async function runApolloSync() {
    setSyncing(true);
    setSyncResult(null);
    try {
      const body = {
        limit: syncConfig.limit,
        industries: syncConfig.industries ? syncConfig.industries.split(",").map(s => s.trim()) : null,
        countries: syncConfig.countries ? syncConfig.countries.split(",").map(s => s.trim()) : null,
      };
      const r = await api.post("/api/v1/sync/apollo", body);
      setSyncResult(r.data);
    } catch (e) {
      setSyncResult({ error: e.response?.data?.detail || e.message });
    }
    setSyncing(false);
  }

  async function enrichContact() {
    if (!enrichId) return;
    setEnriching(true);
    try {
      const r = await api.post(`/api/v1/sync/enrich/${enrichId}`);
      alert(r.data.enriched ? `Contact #${enrichId} enriched with Apollo data.` : `Not enriched: ${r.data.reason}`);
    } catch (e) { alert(`Error: ${e.response?.data?.detail || e.message}`); }
    setEnriching(false);
  }

  async function registerWebhook() {
    if (!webhookUrl) return;
    try {
      const r = await api.post(`/api/v1/sync/telegram/webhook/register?webhook_url=${encodeURIComponent(webhookUrl)}`);
      alert(r.data.ok ? "Webhook registered!" : `Failed: ${JSON.stringify(r.data)}`);
      loadAll();
    } catch (e) { alert(`Error: ${e.message}`); }
  }

  if (loading) return <div className="p-6 text-gray-500">Loading...</div>;

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Integrations &amp; Sync</h1>
        <p className="text-gray-400 text-sm">OAuth connections, contact sync, Telegram webhook</p>
      </div>

      {/* Gmail OAuth */}
      <div className="glass rounded-xl p-5 border border-white/5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="font-semibold text-white">Gmail OAuth</h2>
            <p className="text-xs text-gray-500">Send emails via Gmail API (more reliable than SMTP)</p>
          </div>
          <div className={`text-xs px-3 py-1 rounded-full border ${
            gmailStatus?.connected
              ? "border-green-500/30 bg-green-500/10 text-green-400"
              : "border-gray-600 text-gray-400"
          }`}>
            {gmailStatus?.connected ? "Connected" : "Not connected"}
          </div>
        </div>

        {gmailStatus?.connected ? (
          <div className="space-y-3">
            <div className="flex items-center gap-3 p-3 bg-white/5 rounded-lg">
              <span className="text-green-400">✅</span>
              <div>
                <p className="text-sm text-white">{gmailStatus.email}</p>
                <p className="text-xs text-gray-500">Send method: {gmailStatus.send_method}</p>
              </div>
            </div>
            <button onClick={revokeGmail}
              className="px-4 py-2 border border-red-500/30 text-red-400 hover:bg-red-500/10 rounded-lg text-sm transition-colors">
              Revoke Access
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {!gmailStatus?.oauth_configured ? (
              <p className="text-xs text-yellow-400 bg-yellow-500/10 rounded-lg p-3 border border-yellow-500/20">
                Add <code className="font-mono">GMAIL_CLIENT_ID</code> and <code className="font-mono">GMAIL_CLIENT_SECRET</code> to .env to enable OAuth.
              </p>
            ) : (
              <button onClick={connectGmail}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors">
                Connect Gmail
              </button>
            )}
          </div>
        )}
      </div>

      {/* Apollo Contact Sync */}
      <div className="glass rounded-xl p-5 border border-white/5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="font-semibold text-white">Apollo.io Contact Sync</h2>
            <p className="text-xs text-gray-500">Import ICP contacts from Apollo into JARVIS CRM</p>
          </div>
        </div>
        <div className="space-y-3">
          <input value={syncConfig.industries}
            onChange={e => setSyncConfig(s => ({ ...s, industries: e.target.value }))}
            placeholder="Industries (comma-separated, e.g. SaaS, Hotel)"
            className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 text-sm focus:outline-none focus:border-blue-500/50" />
          <input value={syncConfig.countries}
            onChange={e => setSyncConfig(s => ({ ...s, countries: e.target.value }))}
            placeholder="Countries (comma-separated, e.g. US, GB, CA)"
            className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 text-sm focus:outline-none focus:border-blue-500/50" />
          <div className="flex gap-3 items-center">
            <input type="number" value={syncConfig.limit} min={1} max={100}
              onChange={e => setSyncConfig(s => ({ ...s, limit: Number(e.target.value) }))}
              className="w-24 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none"
              placeholder="Limit" />
            <button onClick={runApolloSync} disabled={syncing}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-colors">
              {syncing ? "Syncing..." : "Run Apollo Sync"}
            </button>
          </div>
          {syncResult && (
            <div className={`p-3 rounded-lg text-sm ${syncResult.error ? "bg-red-500/10 text-red-400 border border-red-500/20" : "bg-green-500/10 text-green-400 border border-green-500/20"}`}>
              {syncResult.error ? `Error: ${syncResult.error}` : `✅ Synced ${syncResult.synced} contacts from ${syncResult.source}`}
            </div>
          )}
        </div>
      </div>

      {/* Contact Enrichment */}
      <div className="glass rounded-xl p-5 border border-white/5">
        <h2 className="font-semibold text-white mb-1">Contact Enrichment</h2>
        <p className="text-xs text-gray-500 mb-4">Enrich a CRM contact with Apollo.io data</p>
        <div className="flex gap-3">
          <input value={enrichId} onChange={e => setEnrichId(e.target.value)}
            placeholder="Contact ID"
            className="flex-1 bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 text-sm focus:outline-none focus:border-blue-500/50" />
          <button onClick={enrichContact} disabled={!enrichId || enriching}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-colors">
            {enriching ? "Enriching..." : "Enrich"}
          </button>
        </div>
      </div>

      {/* Telegram Webhook */}
      <div className="glass rounded-xl p-5 border border-white/5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="font-semibold text-white">Telegram Bot Webhook</h2>
            <p className="text-xs text-gray-500">Register JARVIS bot for commands + inline approvals</p>
          </div>
          {webhookInfo?.result?.url && (
            <span className="text-xs px-2 py-0.5 rounded-full border border-green-500/30 text-green-400 bg-green-500/10">Active</span>
          )}
        </div>
        {webhookInfo?.result?.url && (
          <p className="text-xs text-gray-400 bg-white/5 rounded-lg p-2 font-mono mb-3 truncate">
            {webhookInfo.result.url}
          </p>
        )}
        <div className="flex gap-3">
          <input value={webhookUrl} onChange={e => setWebhookUrl(e.target.value)}
            placeholder="https://your-domain.com/api/v1/sync/telegram/webhook"
            className="flex-1 bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 text-sm focus:outline-none focus:border-blue-500/50" />
          <button onClick={registerWebhook} disabled={!webhookUrl}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-colors whitespace-nowrap">
            Register
          </button>
        </div>
        <p className="text-xs text-gray-600 mt-2">Requires a public HTTPS URL (use ngrok for local dev).</p>
      </div>
    </div>
  );
}
