import { useState, useEffect } from "react";
import { api } from "../../services/api";

const STATUS_STYLE = {
  queued: "text-blue-400 bg-blue-500/10 border-blue-500/20",
  running: "text-yellow-400 bg-yellow-500/10 border-yellow-500/20 animate-pulse",
  completed: "text-green-400 bg-green-500/10 border-green-500/20",
  failed: "text-red-400 bg-red-500/10 border-red-500/20",
};

const PRIORITY_LABEL = { 1: "Critical", 2: "High", 3: "Medium", 5: "Normal", 8: "Low", 10: "Background" };
const AGENTS = ["jarvis", "growth_manager", "ops_manager", "lead_scout", "outreach_agent", "crm_agent", "research_agent", "content_writer"];

function TaskRow({ task, expanded, onToggle }) {
  return (
    <div className="glass rounded-xl border border-white/5 overflow-hidden">
      <button
        className="w-full flex items-center justify-between p-4 text-left hover:bg-white/2 transition-colors"
        onClick={onToggle}
      >
        <div className="flex items-center gap-3">
          <span className="text-gray-500 text-xs w-6">#{task.id}</span>
          <div>
            <p className="text-sm font-medium text-white">{task.title}</p>
            <p className="text-xs text-gray-500">{task.assigned_to} · P{task.priority} · {task.task_type}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className={`text-xs px-2 py-0.5 rounded-full border ${STATUS_STYLE[task.status] || "text-gray-400"}`}>
            {task.status}
          </span>
          <span className="text-gray-600 text-xs">{expanded ? "▲" : "▼"}</span>
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4 pt-0 border-t border-white/5">
          {task.result && (
            <div className="mt-3">
              <p className="text-xs text-gray-500 mb-1">Result</p>
              <p className="text-sm text-gray-300 bg-white/5 rounded-lg p-3 whitespace-pre-wrap">{task.result}</p>
            </div>
          )}
          {task.error && (
            <div className="mt-3">
              <p className="text-xs text-red-400 mb-1">Error</p>
              <p className="text-sm text-red-300 bg-red-500/5 rounded-lg p-3">{task.error}</p>
            </div>
          )}
          <p className="text-xs text-gray-600 mt-3">
            Created: {new Date(task.created_at).toLocaleString()}
            {task.completed_at && ` · Completed: ${new Date(task.completed_at).toLocaleString()}`}
          </p>
        </div>
      )}
    </div>
  );
}

export default function TaskQueue() {
  const [tasks, setTasks] = useState([]);
  const [queueStats, setQueueStats] = useState({});
  const [agentStatus, setAgentStatus] = useState({});
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState("tasks");
  const [expandedId, setExpandedId] = useState(null);
  const [filter, setFilter] = useState("all");
  const [showNew, setShowNew] = useState(false);
  const [newTask, setNewTask] = useState({ title: "", description: "", task_type: "research", priority: 5, assigned_to: "jarvis" });
  const [submitting, setSubmitting] = useState(false);
  const [broadcasting, setBroadcasting] = useState(false);
  const [broadcastMsg, setBroadcastMsg] = useState('');
  const [broadcastResult, setBroadcastResult] = useState(null);
  const [delegateForm, setDelegateForm] = useState({ to_agent: 'jarvis', message: '', task_type: 'general', priority: 5 });
  const [delegating, setDelegating] = useState(false);
  const [showBroadcast, setShowBroadcast] = useState(false);
  const [inboxAgent, setInboxAgent] = useState('jarvis');
  const [inbox, setInbox] = useState(null);
  const [inboxLoading, setInboxLoading] = useState(false);
  const [msgForm, setMsgForm] = useState({ from_agent: 'CAPTAIN', to_agent: 'jarvis', content: '', message_type: 'directive' });
  const [msgSending, setMsgSending] = useState(false);
  const [msgResult, setMsgResult] = useState(null);

  useEffect(() => {
    loadAll();
    const timer = setInterval(loadAll, 10000);
    return () => clearInterval(timer);
  }, []);

  async function loadAll() {
    setLoading(false);
    try {
      const [t, q, a] = await Promise.all([
        api.get("/tasks/?limit=50").then(r => r.data),
        api.get("/tasks/queue").then(r => r.data),
        api.get("/tasks/agents/status").then(r => r.data),
      ]);
      setTasks(t);
      setQueueStats(q);
      setAgentStatus(a);
    } catch (e) { console.error(e); }
  }

  async function enqueueTask() {
    setSubmitting(true);
    try {
      await api.post("/tasks/enqueue", newTask);
      setShowNew(false);
      setNewTask({ title: "", description: "", task_type: "research", priority: 5, assigned_to: "jarvis" });
      loadAll();
    } catch (e) { console.error(e); }
    setSubmitting(false);
  }

  async function broadcastToAgents() {
    if (!broadcastMsg.trim()) return;
    setBroadcasting(true);
    try {
      const r = await api.post("/tasks/agents/broadcast", { message: broadcastMsg, sender: 'CAPTAIN' });
      setBroadcastResult(r.data);
      setBroadcastMsg('');
    } catch (e) {
      setBroadcastResult({ error: e.response?.data?.detail || e.message });
    }
    setBroadcasting(false);
  }

  async function delegateToAgent() {
    if (!delegateForm.message.trim()) return;
    setDelegating(true);
    try {
      await api.post("/tasks/delegate", delegateForm);
      setDelegateForm({ to_agent: 'jarvis', message: '', task_type: 'general', priority: 5 });
    } catch (e) { console.error(e); }
    setDelegating(false);
    await loadAll();
  }

  async function loadInbox() {
    setInboxLoading(true);
    try {
      const r = await api.get(`/tasks/messages/inbox/${inboxAgent}`, { params: { unread_only: false } });
      setInbox(r.data);
    } catch (e) { setInbox({ error: e.response?.data?.detail || e.message }); }
    setInboxLoading(false);
  }

  async function sendMessage() {
    if (!msgForm.content.trim()) return;
    setMsgSending(true);
    try {
      const r = await api.post('/tasks/messages/send', msgForm);
      setMsgResult({ ok: true, data: r.data });
      setMsgForm(f => ({ ...f, content: '' }));
    } catch (e) { setMsgResult({ ok: false, error: e.response?.data?.detail || e.message }); }
    setMsgSending(false);
  }

  const filtered = filter === "all" ? tasks : tasks.filter(t => t.status === filter);

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Task Queue</h1>
          <p className="text-gray-400 text-sm">AI task orchestration &amp; agent comms</p>
        </div>
        <button onClick={() => setShowNew(true)} className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors">
          + Enqueue Task
        </button>
      </div>

      {/* Queue Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Queued", value: queueStats.queued || 0, color: "text-blue-400" },
          { label: "Running", value: queueStats.running || 0, color: "text-yellow-400" },
          { label: "Completed", value: queueStats.completed || 0, color: "text-green-400" },
          { label: "Failed", value: queueStats.failed || 0, color: "text-red-400" },
        ].map(s => (
          <div key={s.label} className="glass rounded-xl p-4 border border-white/5">
            <p className="text-gray-400 text-xs mb-1">{s.label}</p>
            <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-white/5 rounded-lg p-1 w-fit">
        {["tasks", "agents", "messages"].map(t => (
          <button key={t} onClick={() => setTab(t)} className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all capitalize ${tab === t ? "bg-blue-600 text-white" : "text-gray-400 hover:text-white"}`}>{t}</button>
        ))}
      </div>

      {tab === "tasks" ? (
        <>
          {/* Status Filter */}
          <div className="flex gap-1 flex-wrap">
            {["all", "queued", "running", "completed", "failed"].map(f => (
              <button key={f} onClick={() => setFilter(f)} className={`px-3 py-1 rounded-lg text-xs font-medium transition-all capitalize ${filter === f ? "bg-white/15 text-white" : "text-gray-500 hover:text-gray-300"}`}>{f}</button>
            ))}
          </div>
          <div className="space-y-2">
            {filtered.length === 0 ? (
              <div className="text-center text-gray-500 py-12">No tasks. Enqueue one to get started.</div>
            ) : (
              filtered.map(task => (
                <TaskRow
                  key={task.id}
                  task={task}
                  expanded={expandedId === task.id}
                  onToggle={() => setExpandedId(expandedId === task.id ? null : task.id)}
                />
              ))
            )}
          </div>
        </>
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {Object.entries(agentStatus).map(([name, info]) => (
              <div key={name} className="glass rounded-xl p-4 border border-white/5">
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <p className="font-medium text-white text-sm">{name.replace(/_/g, " ")}</p>
                    <p className="text-xs text-gray-500">{info.role}</p>
                  </div>
                  <div className="text-right">
                    {info.pending_tasks > 0 && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-yellow-500/10 text-yellow-400 border border-yellow-500/20">
                        {info.pending_tasks} tasks
                      </span>
                    )}
                  </div>
                </div>
                <p className="text-xs text-gray-600">{info.focus}</p>
                {info.unread_messages > 0 && (
                  <p className="text-xs text-blue-400 mt-1">{info.unread_messages} unread messages</p>
                )}
              </div>
            ))}
          </div>

          {/* Delegate + Broadcast */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="glass rounded-xl p-5 border border-white/5 space-y-3">
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-white/50">Delegate to Agent</p>
              <select value={delegateForm.to_agent} onChange={e => setDelegateForm(p => ({ ...p, to_agent: e.target.value }))}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-xs focus:outline-none focus:border-blue-500/50">
                {AGENTS.map(a => <option key={a} value={a}>{a.replace(/_/g, ' ')}</option>)}
              </select>
              <textarea value={delegateForm.message} onChange={e => setDelegateForm(p => ({ ...p, message: e.target.value }))}
                placeholder="Task description / delegation message…" rows={2}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white placeholder-gray-500 text-xs focus:outline-none focus:border-blue-500/50 resize-none" />
              <button onClick={delegateToAgent} disabled={delegating || !delegateForm.message.trim()}
                className="w-full py-2 rounded-lg bg-blue-600/80 hover:bg-blue-500 disabled:opacity-40 text-white text-xs font-medium transition-colors">
                {delegating ? 'Delegating…' : 'Delegate →'}
              </button>
            </div>

            <div className="glass rounded-xl p-5 border border-white/5 space-y-3">
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-white/50">Broadcast to All Agents</p>
              <textarea value={broadcastMsg} onChange={e => setBroadcastMsg(e.target.value)}
                placeholder="Message from Captain to all AI employees…" rows={2}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white placeholder-gray-500 text-xs focus:outline-none focus:border-blue-500/50 resize-none" />
              <button onClick={broadcastToAgents} disabled={broadcasting || !broadcastMsg.trim()}
                className="w-full py-2 rounded-lg border border-purple-500/30 bg-purple-500/10 text-purple-300 hover:bg-purple-500/20 disabled:opacity-40 text-xs font-bold transition-colors">
                {broadcasting ? 'Broadcasting…' : '📢 Broadcast to All Agents'}
              </button>
              {broadcastResult && (
                <pre className="rounded-lg border border-white/10 bg-black/20 p-2 text-[10px] text-gray-300 max-h-24 overflow-auto">
                  {JSON.stringify(broadcastResult, null, 2)}
                </pre>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Messages Tab */}
      {tab === "messages" && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Inbox */}
            <div className="glass rounded-xl p-5 border border-white/5 space-y-3">
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-white/50">Agent Inbox</p>
              <div className="flex gap-2">
                <select value={inboxAgent} onChange={e => setInboxAgent(e.target.value)}
                  className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-xs focus:outline-none focus:border-blue-500/50">
                  {AGENTS.map(a => <option key={a} value={a}>{a.replace(/_/g, ' ')}</option>)}
                </select>
                <button onClick={loadInbox} disabled={inboxLoading}
                  className="px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-gray-300 text-xs hover:bg-white/10 disabled:opacity-40 transition-colors">
                  {inboxLoading ? '…' : 'Load'}
                </button>
              </div>
              {inbox && (
                inbox.error ? (
                  <p className="text-xs text-red-400">{inbox.error}</p>
                ) : (
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {(Array.isArray(inbox) ? inbox : inbox.messages || []).length === 0 ? (
                      <p className="text-xs text-gray-500">Inbox is empty.</p>
                    ) : (Array.isArray(inbox) ? inbox : inbox.messages || []).map((msg, i) => (
                      <div key={msg.id || i} className="rounded-lg border border-white/10 bg-black/20 p-2.5 space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] text-jarvis-cyan font-mono">{msg.from_agent} → {msg.to_agent}</span>
                          <span className="text-[10px] text-gray-600">{msg.message_type}</span>
                        </div>
                        <p className="text-xs text-gray-300">{msg.content}</p>
                      </div>
                    ))}
                  </div>
                )
              )}
            </div>

            {/* Send Message */}
            <div className="glass rounded-xl p-5 border border-white/5 space-y-3">
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-white/50">Send to Agent</p>
              <div className="grid grid-cols-2 gap-2">
                <select value={msgForm.from_agent} onChange={e => setMsgForm(f => ({ ...f, from_agent: e.target.value }))}
                  className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-xs focus:outline-none focus:border-blue-500/50">
                  <option value="CAPTAIN">CAPTAIN</option>
                  {AGENTS.map(a => <option key={a} value={a}>{a.replace(/_/g, ' ')}</option>)}
                </select>
                <select value={msgForm.to_agent} onChange={e => setMsgForm(f => ({ ...f, to_agent: e.target.value }))}
                  className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-xs focus:outline-none focus:border-blue-500/50">
                  {AGENTS.map(a => <option key={a} value={a}>{a.replace(/_/g, ' ')}</option>)}
                </select>
              </div>
              <select value={msgForm.message_type} onChange={e => setMsgForm(f => ({ ...f, message_type: e.target.value }))}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-xs focus:outline-none focus:border-blue-500/50">
                {['directive', 'question', 'update', 'escalation', 'acknowledgement'].map(t => <option key={t} value={t}>{t}</option>)}
              </select>
              <textarea value={msgForm.content} onChange={e => setMsgForm(f => ({ ...f, content: e.target.value }))}
                placeholder="Message content…" rows={3}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white placeholder-gray-500 text-xs focus:outline-none focus:border-blue-500/50 resize-none" />
              <button onClick={sendMessage} disabled={msgSending || !msgForm.content.trim()}
                className="w-full py-2 rounded-lg bg-blue-600/80 hover:bg-blue-500 disabled:opacity-40 text-white text-xs font-medium transition-colors">
                {msgSending ? 'Sending…' : 'Send Message →'}
              </button>
              {msgResult && (
                <p className={`text-xs ${msgResult.ok ? 'text-green-400' : 'text-red-400'}`}>
                  {msgResult.ok ? `Sent. ID: ${msgResult.data?.id || '—'}` : msgResult.error}
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* New Task Modal */}
      {showNew && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50" onClick={() => setShowNew(false)}>
          <div className="glass rounded-2xl border border-white/10 p-6 w-full max-w-md" onClick={e => e.stopPropagation()}>
            <h2 className="text-lg font-bold text-white mb-4">Enqueue Task</h2>
            <div className="space-y-3">
              <input value={newTask.title} onChange={e => setNewTask(p => ({ ...p, title: e.target.value }))} placeholder="Task title *"
                className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 text-sm focus:outline-none focus:border-blue-500/50" />
              <textarea value={newTask.description} onChange={e => setNewTask(p => ({ ...p, description: e.target.value }))} placeholder="Description (optional)"
                rows={3} className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 text-sm focus:outline-none focus:border-blue-500/50 resize-none" />
              <select value={newTask.assigned_to} onChange={e => setNewTask(p => ({ ...p, assigned_to: e.target.value }))}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-blue-500/50">
                {AGENTS.map(a => <option key={a} value={a}>{a.replace(/_/g, " ")}</option>)}
              </select>
              <div className="flex gap-3">
                <select value={newTask.task_type} onChange={e => setNewTask(p => ({ ...p, task_type: e.target.value }))}
                  className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-blue-500/50">
                  {["research", "outreach", "analysis", "generation", "review", "general"].map(t => <option key={t} value={t}>{t}</option>)}
                </select>
                <select value={newTask.priority} onChange={e => setNewTask(p => ({ ...p, priority: Number(e.target.value) }))}
                  className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-blue-500/50">
                  {[1, 2, 3, 5, 8, 10].map(p => <option key={p} value={p}>{PRIORITY_LABEL[p] || p}</option>)}
                </select>
              </div>
            </div>
            <div className="flex gap-3 mt-5">
              <button onClick={() => setShowNew(false)} className="flex-1 py-2 rounded-lg border border-white/10 text-gray-400 text-sm">Cancel</button>
              <button onClick={enqueueTask} disabled={!newTask.title || submitting} className="flex-1 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-40 text-white text-sm font-medium">
                {submitting ? "Enqueueing..." : "Enqueue"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
