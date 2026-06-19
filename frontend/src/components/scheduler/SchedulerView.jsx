import { useState, useEffect } from "react";
import { api } from "../../services/api";

const TRIGGER_ICONS = { cron: "🕐", interval: "🔄", date: "📅" };
const AGENTS = ["jarvis", "growth_manager", "ops_manager", "lead_scout", "outreach_agent",
                "crm_agent", "research_agent", "content_writer", "reporting_agent"];
const TASK_TYPES = ["lead_scoring", "outreach", "briefing", "contact_sync", "analysis", "research", "custom"];

function JobCard({ job, dbJob, onPause, onResume, onDelete }) {
  const isPaused = !job.next_run;
  return (
    <div className="glass rounded-xl p-4 border border-white/5 hover:border-blue-500/20 transition-all">
      <div className="flex items-start justify-between mb-3">
        <div>
          <p className="font-medium text-white flex items-center gap-2">
            <span>{TRIGGER_ICONS[dbJob?.trigger_type] || "⚙️"}</span>
            {job.name}
          </p>
          <p className="text-xs text-gray-500 mt-0.5 font-mono">{job.trigger}</p>
        </div>
        <div className="flex gap-2">
          {isPaused ? (
            <button onClick={() => onResume(job.id)}
              className="text-xs px-2 py-1 rounded bg-green-500/10 text-green-400 border border-green-500/20 hover:bg-green-500/20 transition-colors">
              Resume
            </button>
          ) : (
            <button onClick={() => onPause(job.id)}
              className="text-xs px-2 py-1 rounded bg-yellow-500/10 text-yellow-400 border border-yellow-500/20 hover:bg-yellow-500/20 transition-colors">
              Pause
            </button>
          )}
          <button onClick={() => onDelete(job.id)}
            className="text-xs px-2 py-1 rounded bg-red-500/10 text-red-400 border border-red-500/20 hover:bg-red-500/20 transition-colors">
            Delete
          </button>
        </div>
      </div>
      <div className="flex items-center justify-between text-xs text-gray-500">
        <span>Next: {job.next_run ? new Date(job.next_run).toLocaleString() : "Paused"}</span>
        {dbJob && <span>Agent: {dbJob.agent}</span>}
      </div>
    </div>
  );
}

export default function SchedulerView() {
  const [jobs, setJobs] = useState([]);
  const [dbJobs, setDbJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState("jobs");
  const [failures, setFailures] = useState(null);
  const [failuresLoading, setFailuresLoading] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [newJobType, setNewJobType] = useState("cron");
  const [form, setForm] = useState({
    job_id: "", name: "", description: "",
    hour: 8, minute: 0, timezone: "UTC",
    hours: 0, minutes: 0, seconds: 0,
    agent: "jarvis", task_type: "custom", payload: "{}",
  });

  useEffect(() => { load(); }, []);

  async function load() {
    setLoading(true);
    try {
      const [j, d] = await Promise.all([
        api.get("/api/v1/scheduler/jobs").then(r => r.data),
        api.get("/api/v1/scheduler/jobs/db").then(r => r.data),
      ]);
      setJobs(j);
      setDbJobs(d);
    } catch (e) { console.error(e); }
    setLoading(false);
  }

  async function createJob() {
    try {
      let payload;
      try { payload = JSON.parse(form.payload || "{}"); } catch { payload = {}; }
      const body = { ...form, payload };
      if (newJobType === "cron") {
        await api.post("/api/v1/scheduler/jobs/cron", body);
      } else {
        await api.post("/api/v1/scheduler/jobs/interval", body);
      }
      setShowNew(false);
      load();
    } catch (e) { console.error(e); }
  }

  async function handlePause(id) {
    await api.post(`/api/v1/scheduler/jobs/${id}/pause`);
    load();
  }
  async function handleResume(id) {
    await api.post(`/api/v1/scheduler/jobs/${id}/resume`);
    load();
  }
  async function handleDelete(id) {
    await api.delete(`/api/v1/scheduler/jobs/${id}`);
    load();
  }

  async function loadFailures() {
    setFailuresLoading(true);
    try {
      const r = await api.get("/api/v1/scheduler/failures");
      setFailures(r.data);
    } catch (e) { setFailures({ error: e.response?.data?.detail || e.message }); }
    setFailuresLoading(false);
  }

  const dbJobMap = Object.fromEntries(dbJobs.map(j => [j.job_id, j]));

  const DEFAULT_JOBS = jobs.filter(j =>
    ["daily_briefing", "lead_scoring_sweep", "outreach_processor", "contact_sync"].includes(j.id)
  );
  const CUSTOM_JOBS = jobs.filter(j =>
    !["daily_briefing", "lead_scoring_sweep", "outreach_processor", "contact_sync"].includes(j.id)
  );

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Scheduler</h1>
          <p className="text-gray-400 text-sm">Automated agent jobs — cron, interval, one-shot</p>
        </div>
        <div className="flex gap-2">
          <button onClick={load} className="px-4 py-2 border border-white/10 text-gray-400 hover:text-white rounded-lg text-sm transition-colors">
            Refresh
          </button>
          <button onClick={() => setShowNew(true)} className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors">
            + Add Job
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="glass rounded-xl p-4 border border-white/5">
          <p className="text-gray-400 text-xs mb-1">Total Jobs</p>
          <p className="text-2xl font-bold text-white">{jobs.length}</p>
        </div>
        <div className="glass rounded-xl p-4 border border-white/5">
          <p className="text-gray-400 text-xs mb-1">Default Jobs</p>
          <p className="text-2xl font-bold text-green-400">{DEFAULT_JOBS.length}</p>
        </div>
        <div className="glass rounded-xl p-4 border border-white/5">
          <p className="text-gray-400 text-xs mb-1">Custom Jobs</p>
          <p className="text-2xl font-bold text-blue-400">{CUSTOM_JOBS.length}</p>
        </div>
      </div>

      {loading ? (
        <div className="text-center text-gray-500 py-12">Loading scheduler...</div>
      ) : (
        <div className="space-y-6">
          {DEFAULT_JOBS.length > 0 && (
            <div>
              <h2 className="text-sm font-semibold text-gray-400 mb-3">Built-in JARVIS Jobs</h2>
              <div className="space-y-3">
                {DEFAULT_JOBS.map(job => (
                  <JobCard key={job.id} job={job} dbJob={dbJobMap[job.id]}
                    onPause={handlePause} onResume={handleResume} onDelete={handleDelete} />
                ))}
              </div>
            </div>
          )}
          {CUSTOM_JOBS.length > 0 && (
            <div>
              <h2 className="text-sm font-semibold text-gray-400 mb-3">Custom Jobs</h2>
              <div className="space-y-3">
                {CUSTOM_JOBS.map(job => (
                  <JobCard key={job.id} job={job} dbJob={dbJobMap[job.id]}
                    onPause={handlePause} onResume={handleResume} onDelete={handleDelete} />
                ))}
              </div>
            </div>
          )}
          {jobs.length === 0 && (
            <div className="text-center text-gray-500 py-12">
              No jobs scheduled. Default jobs start automatically on server boot.
            </div>
          )}
        </div>
      )}

      {/* Job Failures */}
      <div className="glass rounded-xl p-5 border border-white/5 space-y-3">
        <div className="flex items-center justify-between">
          <p className="text-xs font-bold uppercase tracking-wider text-white/40">Job Failures</p>
          <button onClick={loadFailures} disabled={failuresLoading}
            className="px-3 py-1.5 rounded-lg border border-white/10 bg-white/5 text-gray-400 hover:text-white text-xs transition-colors disabled:opacity-40">
            {failuresLoading ? 'Loading…' : '↺ Load Failures'}
          </button>
        </div>
        {failures && (
          <pre className="text-xs text-gray-300 overflow-auto max-h-48 rounded-lg border border-white/10 bg-black/20 p-3">
            {JSON.stringify(failures, null, 2)}
          </pre>
        )}
      </div>

      {/* New Job Modal */}
      {showNew && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 overflow-y-auto py-8" onClick={() => setShowNew(false)}>
          <div className="glass rounded-2xl border border-white/10 p-6 w-full max-w-lg m-4" onClick={e => e.stopPropagation()}>
            <h2 className="text-lg font-bold text-white mb-4">New Scheduled Job</h2>

            <div className="flex gap-2 mb-4">
              {["cron", "interval"].map(t => (
                <button key={t} onClick={() => setNewJobType(t)}
                  className={`flex-1 py-2 rounded-lg text-sm font-medium transition-all capitalize ${newJobType === t ? "bg-blue-600 text-white" : "border border-white/10 text-gray-400"}`}>
                  {t}
                </button>
              ))}
            </div>

            <div className="space-y-3">
              <input value={form.job_id} onChange={e => setForm(f => ({ ...f, job_id: e.target.value }))}
                placeholder="Job ID (unique, e.g. weekly_report) *" maxLength={100}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 text-sm focus:outline-none focus:border-blue-500/50" />
              <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                placeholder="Display name *" maxLength={300}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 text-sm focus:outline-none focus:border-blue-500/50" />

              {newJobType === "cron" ? (
                <div className="flex gap-2">
                  <div className="flex-1">
                    <label className="text-xs text-gray-500">Hour (UTC)</label>
                    <input type="number" min={0} max={23} value={form.hour} onChange={e => setForm(f => ({ ...f, hour: Number(e.target.value) }))}
                      className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none mt-1" />
                  </div>
                  <div className="flex-1">
                    <label className="text-xs text-gray-500">Minute</label>
                    <input type="number" min={0} max={59} value={form.minute} onChange={e => setForm(f => ({ ...f, minute: Number(e.target.value) }))}
                      className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none mt-1" />
                  </div>
                </div>
              ) : (
                <div className="flex gap-2">
                  {["hours", "minutes", "seconds"].map(u => (
                    <div key={u} className="flex-1">
                      <label className="text-xs text-gray-500 capitalize">{u}</label>
                      <input type="number" min={0} value={form[u]} onChange={e => setForm(f => ({ ...f, [u]: Number(e.target.value) }))}
                        className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none mt-1" />
                    </div>
                  ))}
                </div>
              )}

              <div className="flex gap-2">
                <select value={form.agent} onChange={e => setForm(f => ({ ...f, agent: e.target.value }))}
                  className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none">
                  {AGENTS.map(a => <option key={a} value={a}>{a.replace(/_/g, " ")}</option>)}
                </select>
                <select value={form.task_type} onChange={e => setForm(f => ({ ...f, task_type: e.target.value }))}
                  className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none">
                  {TASK_TYPES.map(t => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
                </select>
              </div>
            </div>

            <div className="flex gap-3 mt-5">
              <button onClick={() => setShowNew(false)} className="flex-1 py-2 rounded-lg border border-white/10 text-gray-400 text-sm">Cancel</button>
              <button onClick={createJob} disabled={!form.job_id || !form.name}
                className="flex-1 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-40 text-white text-sm font-medium">
                Schedule Job
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
