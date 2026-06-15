import React, { useCallback, useEffect, useState } from 'react'
import { AlertTriangle, CheckCircle2, ChevronDown, ChevronRight, Clock, Layers, Loader2, Plus, RefreshCw, Send, Zap } from 'lucide-react'
import api from '../../services/api'

const TASK_STATUS_CFG = {
  pending:    { cls: 'border-gray-500/30 bg-gray-500/10 text-gray-300',       label: 'Pending' },
  running:    { cls: 'border-blue-500/30 bg-blue-500/10 text-blue-300',        label: 'Running' },
  completed:  { cls: 'border-green-500/30 bg-green-500/10 text-green-300',     label: 'Done' },
  failed:     { cls: 'border-red-500/30 bg-red-500/10 text-red-300',          label: 'Failed' },
  cancelled:  { cls: 'border-gray-600/30 bg-gray-600/10 text-gray-500',       label: 'Cancelled' },
}

const DEAL_STAGE_CFG = {
  discovery:  { cls: 'border-gray-500/30 bg-gray-500/10 text-gray-300' },
  proposal:   { cls: 'border-blue-500/30 bg-blue-500/10 text-blue-300' },
  negotiation:{ cls: 'border-jarvis-gold/30 bg-jarvis-gold/10 text-jarvis-gold' },
  closed_won: { cls: 'border-green-500/30 bg-green-500/10 text-green-300' },
  closed_lost:{ cls: 'border-red-500/30 bg-red-500/10 text-red-300' },
}

function StatusBadge({ status, cfg }) {
  const c = cfg[status?.toLowerCase()] || { cls: 'border-gray-500/30 bg-gray-500/10 text-gray-300', label: status }
  return <span className={`inline-flex rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${c.cls}`}>{c.label || status}</span>
}

function money(v) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0 }).format(v || 0)
}

function fmtDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function TaskCard({ task }) {
  const [open, setOpen] = useState(false)
  const cfg = TASK_STATUS_CFG[task.status] || TASK_STATUS_CFG.pending
  return (
    <div className="rounded-xl border border-white/10 bg-white/5">
      <button type="button" onClick={() => setOpen(v => !v)} className="flex w-full items-start gap-3 p-4 text-left">
        {open ? <ChevronDown size={13} className="mt-0.5 shrink-0 text-gray-400" /> : <ChevronRight size={13} className="mt-0.5 shrink-0 text-gray-400" />}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-white truncate">{task.title}</p>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            <span className={`inline-flex rounded-full border px-2 py-0.5 text-[10px] font-semibold ${cfg.cls}`}>{cfg.label}</span>
            {task.task_type && <span className="text-[10px] text-gray-500 uppercase tracking-wider">{task.task_type}</span>}
            {task.assigned_to && <span className="text-[10px] text-gray-600">→ {task.assigned_to}</span>}
            <span className="ml-auto text-[10px] text-gray-600">{fmtDate(task.created_at)}</span>
          </div>
        </div>
        <span className={`shrink-0 text-xs font-bold ${task.priority >= 8 ? 'text-red-400' : task.priority >= 6 ? 'text-jarvis-gold' : 'text-gray-500'}`}>P{task.priority}</span>
      </button>
      {open && task.result && (
        <div className="border-t border-white/10 px-4 pb-4 pt-3">
          <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1">Result</p>
          <pre className="text-xs text-gray-300 whitespace-pre-wrap">{typeof task.result === 'string' ? task.result : JSON.stringify(task.result, null, 2)}</pre>
          {task.error && <p className="text-xs text-red-400 mt-2">{task.error}</p>}
        </div>
      )}
    </div>
  )
}

export default function ProjectsView() {
  const [tasks, setTasks] = useState([])
  const [queueStats, setQueueStats] = useState(null)
  const [deals, setDeals] = useState([])
  const [pipeline, setPipeline] = useState(null)
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('')
  const [agentFilter, setAgentFilter] = useState('')
  const [enqueueForm, setEnqueueForm] = useState({ title: '', description: '', task_type: 'general', priority: 5, assigned_to: 'jarvis' })
  const [enqueueLoading, setEnqueueLoading] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [tab, setTab] = useState('tasks')

  const load = useCallback(async () => {
    setLoading(true)
    const [taskRes, queueRes, dealRes, pipelineRes] = await Promise.allSettled([
      api.get('/api/v1/tasks/', { params: { limit: 50, ...(statusFilter && { status: statusFilter }), ...(agentFilter && { assigned_to: agentFilter }) } }),
      api.get('/api/v1/tasks/queue'),
      api.get('/api/v1/crm/deals').catch(() => null),
      api.get('/api/v1/crm/deals/pipeline').catch(() => null),
    ])
    if (taskRes.status === 'fulfilled') setTasks(taskRes.value.data || [])
    if (queueRes.status === 'fulfilled') setQueueStats(queueRes.value.data || null)
    if (dealRes.status === 'fulfilled' && dealRes.value) setDeals(dealRes.value.data?.deals || dealRes.value.data || [])
    if (pipelineRes.status === 'fulfilled' && pipelineRes.value) setPipeline(pipelineRes.value.data || null)
    setLoading(false)
  }, [statusFilter, agentFilter])

  useEffect(() => { load() }, [load])

  const enqueue = async (e) => {
    e.preventDefault()
    if (!enqueueForm.title.trim()) return
    setEnqueueLoading(true)
    try {
      await api.post('/api/v1/tasks/enqueue', enqueueForm)
      setEnqueueForm({ title: '', description: '', task_type: 'general', priority: 5, assigned_to: 'jarvis' })
      setShowForm(false)
      await load()
    } catch {}
    setEnqueueLoading(false)
  }

  const pendingCount = tasks.filter(t => t.status === 'pending').length
  const runningCount = tasks.filter(t => t.status === 'running').length
  const failedCount = tasks.filter(t => t.status === 'failed').length
  const openDeals = deals.filter(d => !['closed_won', 'closed_lost'].includes(d.stage?.toLowerCase()))
  const totalDealValue = openDeals.reduce((s, d) => s + (d.value || d.deal_value || 0), 0)

  const TABS = [
    { id: 'tasks', label: 'Task Queue', count: tasks.length },
    { id: 'deals', label: 'Active Deals', count: openDeals.length },
  ]

  return (
    <div className="min-h-[calc(100vh-3.5rem)] p-6 pb-10 space-y-6">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.22em] text-jarvis-cyan/70">Delivery</p>
          <h1 className="mt-2 text-3xl font-bold text-white">Project Tracker</h1>
          <p className="mt-2 max-w-2xl text-sm text-gray-400">
            Agent task queue, delivery pipeline, and open CRM deals for active client work.
          </p>
        </div>
        <button type="button" onClick={load} disabled={loading} className="btn-primary inline-flex items-center justify-center gap-2">
          {loading ? <Loader2 size={15} className="animate-spin" /> : <RefreshCw size={15} />}
          Refresh
        </button>
      </header>

      {/* Metrics */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4 xl:grid-cols-6">
        {[
          { label: 'Total Tasks', value: tasks.length, tone: 'text-jarvis-cyan' },
          { label: 'Pending', value: pendingCount, tone: 'text-gray-300' },
          { label: 'Running', value: runningCount, tone: runningCount > 0 ? 'text-blue-300' : 'text-gray-300' },
          { label: 'Failed', value: failedCount, tone: failedCount > 0 ? 'text-red-400' : 'text-green-300' },
          { label: 'Open Deals', value: openDeals.length, tone: 'text-jarvis-gold' },
          { label: 'Deal Pipeline', value: money(totalDealValue), tone: 'text-green-300' },
        ].map(m => (
          <div key={m.label} className="glass p-5">
            <p className="text-xs text-gray-400">{m.label}</p>
            <p className={`mt-2 text-xl font-bold ${m.tone}`}>{m.value}</p>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-white/10">
        {TABS.map(t => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px ${
              tab === t.id ? 'border-jarvis-cyan text-jarvis-cyan' : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            {t.label}
            {t.count != null && (
              <span className="rounded-full bg-white/10 px-1.5 py-0.5 text-[10px] font-bold">{t.count}</span>
            )}
          </button>
        ))}
      </div>

      {/* Tasks Tab */}
      {tab === 'tasks' && (
        <section className="glass p-5 space-y-4">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <h2 className="text-sm font-semibold text-white">Agent Task Queue</h2>
            <div className="flex items-center gap-2 flex-wrap">
              <select
                value={statusFilter}
                onChange={e => setStatusFilter(e.target.value)}
                className="rounded-xl border border-white/10 bg-black/40 px-3 py-2 text-xs text-white outline-none focus:border-jarvis-cyan/60"
              >
                <option value="">All statuses</option>
                {Object.keys(TASK_STATUS_CFG).map(s => <option key={s} value={s}>{s}</option>)}
              </select>
              <select
                value={agentFilter}
                onChange={e => setAgentFilter(e.target.value)}
                className="rounded-xl border border-white/10 bg-black/40 px-3 py-2 text-xs text-white outline-none focus:border-jarvis-cyan/60"
              >
                <option value="">All agents</option>
                {['jarvis', 'research', 'outreach', 'engineering', 'operations', 'strategy'].map(a => (
                  <option key={a} value={a}>{a}</option>
                ))}
              </select>
              <button
                type="button"
                onClick={() => setShowForm(v => !v)}
                className="inline-flex items-center gap-1.5 rounded border border-jarvis-cyan/40 bg-jarvis-cyan/10 px-3 py-1.5 text-xs font-medium text-jarvis-cyan hover:bg-jarvis-cyan/20 transition-colors"
              >
                <Plus size={12} /> Enqueue Task
              </button>
            </div>
          </div>

          {showForm && (
            <form onSubmit={enqueue} className="rounded-xl border border-white/10 bg-white/5 p-4 space-y-3">
              <p className="text-xs font-semibold text-jarvis-cyan">New Agent Task</p>
              <input
                value={enqueueForm.title}
                onChange={e => setEnqueueForm(p => ({ ...p, title: e.target.value }))}
                placeholder="Task title"
                className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-white outline-none placeholder:text-gray-500 focus:border-jarvis-cyan/60"
              />
              <textarea
                value={enqueueForm.description}
                onChange={e => setEnqueueForm(p => ({ ...p, description: e.target.value }))}
                rows={2} placeholder="Task description (optional)"
                className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-white outline-none placeholder:text-gray-500 focus:border-jarvis-cyan/60"
              />
              <div className="grid grid-cols-3 gap-3">
                <select
                  value={enqueueForm.task_type}
                  onChange={e => setEnqueueForm(p => ({ ...p, task_type: e.target.value }))}
                  className="rounded-xl border border-white/10 bg-black/40 px-3 py-2.5 text-sm text-white outline-none focus:border-jarvis-cyan/60"
                >
                  {['general', 'research', 'outreach', 'proposal', 'analysis', 'engineering', 'reporting'].map(t => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
                <select
                  value={enqueueForm.assigned_to}
                  onChange={e => setEnqueueForm(p => ({ ...p, assigned_to: e.target.value }))}
                  className="rounded-xl border border-white/10 bg-black/40 px-3 py-2.5 text-sm text-white outline-none focus:border-jarvis-cyan/60"
                >
                  {['jarvis', 'research', 'outreach', 'engineering', 'operations', 'strategy'].map(a => (
                    <option key={a} value={a}>{a}</option>
                  ))}
                </select>
                <input
                  type="number" min={1} max={10} placeholder="Priority"
                  value={enqueueForm.priority}
                  onChange={e => setEnqueueForm(p => ({ ...p, priority: parseInt(e.target.value) || 5 }))}
                  className="rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white outline-none focus:border-jarvis-cyan/60"
                />
              </div>
              <div className="flex gap-2">
                <button type="submit" disabled={enqueueLoading} className="btn-primary inline-flex items-center gap-2">
                  {enqueueLoading ? <Loader2 size={13} className="animate-spin" /> : <Send size={13} />}
                  Enqueue
                </button>
                <button type="button" onClick={() => setShowForm(false)} className="px-3 py-1.5 text-xs text-gray-400 hover:text-gray-200">Cancel</button>
              </div>
            </form>
          )}

          {queueStats && (
            <div className="flex gap-4 text-xs text-gray-500 flex-wrap">
              {Object.entries(queueStats).map(([k, v]) => (
                <span key={k}><span className="text-gray-400">{k}:</span> {String(v)}</span>
              ))}
            </div>
          )}

          {loading ? (
            <div className="flex items-center justify-center py-8 text-gray-500"><Loader2 size={18} className="animate-spin mr-2" />Loading…</div>
          ) : tasks.length === 0 ? (
            <div className="flex flex-col items-center py-10 text-gray-500">
              <Layers size={32} className="mb-3 opacity-20" />
              <p className="text-sm">No tasks in queue.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {tasks.map(t => <TaskCard key={t.id} task={t} />)}
            </div>
          )}
        </section>
      )}

      {/* Deals Tab */}
      {tab === 'deals' && (
        <section className="glass p-5 space-y-4">
          <h2 className="text-sm font-semibold text-white">Active CRM Deals</h2>
          {loading ? (
            <div className="flex items-center justify-center py-8 text-gray-500"><Loader2 size={18} className="animate-spin mr-2" />Loading…</div>
          ) : openDeals.length === 0 ? (
            <div className="flex flex-col items-center py-10 text-gray-500">
              <Zap size={32} className="mb-3 opacity-20" />
              <p className="text-sm">No open deals — go to CRM to add prospects.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/10 text-left">
                    <th className="pb-3 pr-4 text-xs font-medium text-gray-500 uppercase tracking-wider">Company</th>
                    <th className="pb-3 pr-4 text-xs font-medium text-gray-500 uppercase tracking-wider">Stage</th>
                    <th className="pb-3 pr-4 text-xs font-medium text-gray-500 uppercase tracking-wider text-right">Value</th>
                    <th className="pb-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Close Date</th>
                  </tr>
                </thead>
                <tbody>
                  {openDeals.map(deal => (
                    <tr key={deal.id} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                      <td className="py-4 pr-4">
                        <p className="font-medium text-white">{deal.company || deal.client_name || '—'}</p>
                        {deal.contact_name && <p className="text-xs text-gray-500 mt-0.5">{deal.contact_name}</p>}
                      </td>
                      <td className="py-4 pr-4">
                        <span className={`inline-flex rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${(DEAL_STAGE_CFG[deal.stage?.toLowerCase()] || DEAL_STAGE_CFG.discovery).cls}`}>
                          {deal.stage}
                        </span>
                      </td>
                      <td className="py-4 pr-4 text-right">
                        <span className="font-semibold text-white">{money(deal.value || deal.deal_value)}</span>
                      </td>
                      <td className="py-4 text-xs text-gray-400">
                        {deal.expected_close_date ? new Date(deal.expected_close_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}
    </div>
  )
}
