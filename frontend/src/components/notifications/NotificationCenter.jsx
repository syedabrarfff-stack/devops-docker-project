import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { api } from "../../services/api";

const LEVEL_STYLES = {
  info:     "border-blue-500/30 bg-blue-500/5 text-blue-300",
  success:  "border-green-500/30 bg-green-500/5 text-green-300",
  warning:  "border-yellow-500/30 bg-yellow-500/5 text-yellow-300",
  critical: "border-red-500/30 bg-red-500/5 text-red-300",
};
const LEVEL_ICON = { info: "ℹ️", success: "✅", warning: "⚠️", critical: "🔴" };
const CATEGORY_ICON = { lead: "🎯", outreach: "📧", approval: "🔔", system: "⚙️", task: "📋" };

function NotifCard({ notif, onRead }) {
  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      className={`rounded-xl p-4 border transition-all cursor-pointer ${
        notif.read ? "border-white/5 bg-white/2 opacity-60" : LEVEL_STYLES[notif.level] || LEVEL_STYLES.info
      }`}
      onClick={() => !notif.read && onRead(notif.id)}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 flex-1">
          <span className="text-lg mt-0.5 flex-shrink-0">
            {CATEGORY_ICON[notif.category] || LEVEL_ICON[notif.level] || "📌"}
          </span>
          <div className="min-w-0">
            <p className={`text-sm font-medium ${notif.read ? "text-gray-400" : "text-white"}`}>
              {notif.title}
            </p>
            <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{notif.body}</p>
          </div>
        </div>
        <div className="flex flex-col items-end gap-1 flex-shrink-0">
          {!notif.read && <div className="w-2 h-2 rounded-full bg-blue-400" />}
          <span className="text-xs text-gray-600">
            {new Date(notif.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
          </span>
        </div>
      </div>
      {notif.reference && (
        <p className="text-xs text-gray-600 mt-2 pl-9">ref: {notif.reference}</p>
      )}
    </motion.div>
  );
}

function SendNotificationModal({ onClose, onSent }) {
  const [form, setForm] = useState({ title: "", body: "", level: "info", category: "system", channels: ["websocket"] });
  const [sending, setSending] = useState(false);

  async function send() {
    setSending(true);
    try {
      await api.post("/api/v1/notifications/broadcast", form);
      onSent();
      onClose();
    } catch (e) { console.error(e); }
    setSending(false);
  }

  const toggleChannel = (ch) => {
    setForm(f => ({
      ...f,
      channels: f.channels.includes(ch) ? f.channels.filter(c => c !== ch) : [...f.channels, ch],
    }));
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50" onClick={onClose}>
      <div className="glass rounded-2xl border border-white/10 p-6 w-full max-w-md" onClick={e => e.stopPropagation()}>
        <h2 className="text-lg font-bold text-white mb-4">Send Notification</h2>
        <div className="space-y-3">
          <input value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
            placeholder="Title *" maxLength={500} className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 text-sm focus:outline-none focus:border-blue-500/50" />
          <textarea value={form.body} onChange={e => setForm(f => ({ ...f, body: e.target.value }))}
            placeholder="Body" rows={3} maxLength={10000} className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 text-sm focus:outline-none focus:border-blue-500/50 resize-none" />
          <div className="flex gap-2">
            <select value={form.level} onChange={e => setForm(f => ({ ...f, level: e.target.value }))}
              className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none">
              {["info", "success", "warning", "critical"].map(l => <option key={l} value={l}>{l}</option>)}
            </select>
            <select value={form.category} onChange={e => setForm(f => ({ ...f, category: e.target.value }))}
              className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none">
              {["system", "lead", "outreach", "approval", "task"].map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div>
            <p className="text-xs text-gray-500 mb-2">Channels</p>
            <div className="flex gap-2 flex-wrap">
              {["websocket", "telegram", "slack"].map(ch => (
                <button key={ch} onClick={() => toggleChannel(ch)}
                  className={`px-3 py-1 rounded-lg text-xs font-medium border transition-all ${
                    form.channels.includes(ch) ? "bg-blue-600/30 border-blue-500/40 text-blue-300" : "border-white/10 text-gray-400"
                  }`}>{ch}</button>
              ))}
            </div>
          </div>
        </div>
        <div className="flex gap-3 mt-5">
          <button onClick={onClose} className="flex-1 py-2 rounded-lg border border-white/10 text-gray-400 text-sm">Cancel</button>
          <button onClick={send} disabled={!form.title || sending} className="flex-1 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-40 text-white text-sm font-medium">
            {sending ? "Sending..." : "Send"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function NotificationCenter() {
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [filter, setFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [showSend, setShowSend] = useState(false);
  const wsRef = useRef(null);

  useEffect(() => {
    load();
    // Live WS updates
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    let _tok = '';
    try { const _r = localStorage.getItem('jarvis_auth'); if (_r) _tok = JSON.parse(_r).token || ''; } catch (_) {}
    const ws = new WebSocket(`${proto}//${window.location.host}/api/v1/ws/captain${_tok ? `?token=${encodeURIComponent(_tok)}` : ''}`);
    wsRef.current = ws;
    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      if (msg.type === "notification") {
        setNotifications(prev => [{
          id: Date.now(), ...msg.data, read: false,
          created_at: new Date().toISOString(),
        }, ...prev]);
        setUnreadCount(c => c + 1);
      }
    };
    return () => ws.close();
  }, []);

  async function load() {
    setLoading(true);
    try {
      const [n, c] = await Promise.all([
        api.get("/api/v1/notifications/?limit=100").then(r => r.data),
        api.get("/api/v1/notifications/unread-count").then(r => r.data),
      ]);
      setNotifications(n);
      setUnreadCount(c.unread);
    } catch (e) { console.error(e); }
    setLoading(false);
  }

  async function markRead(id) {
    await api.post(`/api/v1/notifications/${id}/read`);
    setNotifications(ns => ns.map(n => n.id === id ? { ...n, read: true } : n));
    setUnreadCount(c => Math.max(0, c - 1));
  }

  async function markAllRead() {
    await api.post("/api/v1/notifications/read-all");
    setNotifications(ns => ns.map(n => ({ ...n, read: true })));
    setUnreadCount(0);
  }

  async function clearAll() {
    if (!window.confirm('Clear all notifications? This cannot be undone.')) return;
    await api.delete("/api/v1/notifications/clear");
    setNotifications([]);
    setUnreadCount(0);
  }

  const filtered = filter === "all" ? notifications :
    filter === "unread" ? notifications.filter(n => !n.read) :
    notifications.filter(n => n.category === filter);

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Notifications</h1>
          <p className="text-gray-400 text-sm">
            Real-time JARVIS alerts &amp; events
            {unreadCount > 0 && <span className="ml-2 text-blue-400 font-medium">{unreadCount} unread</span>}
          </p>
        </div>
        <div className="flex gap-2">
          {unreadCount > 0 && (
            <button onClick={markAllRead} className="px-4 py-2 border border-white/10 text-gray-400 hover:text-white rounded-lg text-sm transition-colors">
              Mark all read
            </button>
          )}
          {notifications.length > 0 && (
            <button onClick={clearAll} className="px-4 py-2 border border-red-500/20 text-red-400 hover:text-red-300 rounded-lg text-sm transition-colors">
              Clear all
            </button>
          )}
          <button onClick={() => setShowSend(true)} className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors">
            + Send Notification
          </button>
        </div>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-1 bg-white/5 rounded-lg p-1 w-fit flex-wrap">
        {["all", "unread", "lead", "outreach", "approval", "task", "system"].map(f => (
          <button key={f} onClick={() => setFilter(f)}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all capitalize ${filter === f ? "bg-blue-600 text-white" : "text-gray-400 hover:text-white"}`}>
            {f}
          </button>
        ))}
      </div>

      {/* Notification list */}
      {loading ? (
        <div className="text-center text-gray-500 py-12">Loading...</div>
      ) : (
        <div className="space-y-2 max-h-[calc(100vh-280px)] overflow-y-auto no-scrollbar">
          <AnimatePresence>
            {filtered.length === 0 ? (
              <p className="text-gray-500 text-center py-12">No notifications yet.</p>
            ) : (
              filtered.map(n => (
                <NotifCard key={n.id} notif={n} onRead={markRead} />
              ))
            )}
          </AnimatePresence>
        </div>
      )}

      {showSend && <SendNotificationModal onClose={() => setShowSend(false)} onSent={load} />}
    </div>
  );
}
