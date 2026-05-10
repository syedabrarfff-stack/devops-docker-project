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
        {["tasks", "agents"].map(t => (
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
