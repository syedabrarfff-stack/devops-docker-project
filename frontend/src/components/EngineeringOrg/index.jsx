import React, { useCallback, useEffect, useState } from 'react'
import {
  Bot, ChevronDown, ChevronRight, GitBranch, Loader2, RefreshCw,
  Send, ShieldCheck, Users, Workflow,
} from 'lucide-react'
import {
  engineeringDashboard, engineeringDepartments, engineeringDispatch,
  engineeringSubmitObjective, engineeringTaskGraph,
} from '../../services/api'

const STATUS_STYLE = {
  PENDING:   'text-slate-400 bg-slate-800/60',
  DRAFTING:  'text-amber-300 bg-amber-900/30',
  IN_REVIEW: 'text-sky-300 bg-sky-900/30',
  APPROVED:  'text-emerald-300 bg-emerald-900/30',
  DEPLOYED:  'text-emerald-400 bg-emerald-900/50',
  REJECTED:  'text-red-300 bg-red-900/30',
  BLOCKED:   'text-purple-300 bg-purple-900/30',
  PLANNING:  'text-slate-400 bg-slate-800/60',
  IN_PROGRESS: 'text-sky-300 bg-sky-900/30',
  COMPLETED: 'text-emerald-300 bg-emerald-900/30',
  FAILED:    'text-red-300 bg-red-900/30',
}

function StatusPill({ status }) {
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_STYLE[status] || 'text-slate-400 bg-slate-800/60'}`}>
      {status}
    </span>
  )
}

function DepartmentGrid({ departments }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
      {departments.map((d) => (
        <div key={d.id} className="rounded-xl border border-white/10 bg-white/5 backdrop-blur-sm p-4">
          <div className="flex items-center justify-between mb-1">
            <h4 className="text-sm font-semibold text-white">{d.name}</h4>
            <span className="text-[10px] uppercase tracking-wide text-slate-400">{d.builder}</span>
          </div>
          <p className="text-xs text-slate-400">{d.owns}</p>
        </div>
      ))}
    </div>
  )
}

function WorkPackageRow({ wp }) {
  const [expanded, setExpanded] = useState(false)
  return (
    <div className="rounded-lg border border-white/10 bg-black/20">
      <button
        className="w-full flex items-center justify-between px-3 py-2 text-left"
        onClick={() => setExpanded((e) => !e)}
      >
        <div className="flex items-center gap-2 min-w-0">
          {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          <span className="text-xs uppercase tracking-wide text-slate-500 w-24 shrink-0">{wp.department}</span>
          <span className="text-sm text-white truncate">{wp.title}</span>
        </div>
        <StatusPill status={wp.status} />
      </button>
      {expanded && (
        <div className="px-3 pb-3 text-xs text-slate-400 space-y-2">
          {wp.authority_tier && <div>Authority tier: <span className="text-slate-300">{wp.authority_tier}</span></div>}
          {wp.draft_output?.summary && <div>Draft: {wp.draft_output.summary}</div>}
          {wp.review_result?.decision && (
            <div>Review: <span className="text-slate-300">{wp.review_result.decision}</span> (confidence {Math.round((wp.review_result.aggregate_confidence || 0) * 100)}%)</div>
          )}
          {wp.deploy_result?.mode && <div>Deploy: {wp.deploy_result.mode}</div>}
        </div>
      )}
    </div>
  )
}

function TaskGraphCard({ graph, onOpen }) {
  return (
    <button
      onClick={() => onOpen(graph.id)}
      className="w-full text-left rounded-xl border border-white/10 bg-white/5 hover:bg-white/10 transition p-4"
    >
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-slate-500">{graph.objective_type}</span>
        <StatusPill status={graph.status} />
      </div>
      <p className="text-sm text-white line-clamp-2">{graph.objective}</p>
      <p className="text-xs text-slate-500 mt-1">decomposed by {graph.decomposed_by || 'n/a'}</p>
    </button>
  )
}

export default function EngineeringOrg() {
  const [departments, setDepartments] = useState([])
  const [dash, setDash] = useState(null)
  const [selectedGraph, setSelectedGraph] = useState(null)
  const [objective, setObjective] = useState('')
  const [objectiveType, setObjectiveType] = useState('feature')
  const [submitting, setSubmitting] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const refresh = useCallback(async () => {
    try {
      const [deptResp, dashResp] = await Promise.all([engineeringDepartments(), engineeringDashboard()])
      setDepartments(deptResp.departments || [])
      setDash(dashResp)
      setError(null)
    } catch (e) {
      setError(e?.response?.data?.detail || e.message || 'Failed to load Engineering Organization')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { refresh() }, [refresh])

  const openGraph = useCallback(async (id) => {
    const detail = await engineeringTaskGraph(id)
    setSelectedGraph(detail)
  }, [])

  const submit = useCallback(async () => {
    if (!objective.trim()) return
    setSubmitting(true)
    try {
      const detail = await engineeringSubmitObjective(objective.trim(), objectiveType)
      setSelectedGraph(detail)
      setObjective('')
      await refresh()
    } catch (e) {
      setError(e?.response?.data?.detail || e.message || 'Failed to submit objective')
    } finally {
      setSubmitting(false)
    }
  }, [objective, objectiveType, refresh])

  const dispatch = useCallback(async () => {
    if (!selectedGraph) return
    await engineeringDispatch(selectedGraph.id)
    const detail = await engineeringTaskGraph(selectedGraph.id)
    setSelectedGraph(detail)
    await refresh()
  }, [selectedGraph, refresh])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-400">
        <Loader2 className="animate-spin mr-2" size={18} /> Loading Engineering Organization…
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6 text-white">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold flex items-center gap-2"><Workflow size={20} /> Engineering Organization</h2>
          <p className="text-sm text-slate-400">Mission Planner + 12 autonomous departments — Phase 7</p>
        </div>
        <button onClick={refresh} className="p-2 rounded-lg border border-white/10 hover:bg-white/10">
          <RefreshCw size={16} />
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-900/20 text-red-300 text-sm px-3 py-2">{error}</div>
      )}

      {/* Objective submission */}
      <div className="rounded-xl border border-white/10 bg-white/5 p-4 space-y-3">
        <h3 className="text-sm font-semibold flex items-center gap-2"><Send size={14} /> Submit an engineering objective</h3>
        <textarea
          value={objective}
          onChange={(e) => setObjective(e.target.value)}
          placeholder="e.g. Add rate limiting to the outreach webhook"
          rows={2}
          className="w-full rounded-lg bg-black/30 border border-white/10 px-3 py-2 text-sm text-white placeholder-slate-500"
        />
        <div className="flex items-center gap-3">
          <select
            value={objectiveType}
            onChange={(e) => setObjectiveType(e.target.value)}
            className="rounded-lg bg-black/30 border border-white/10 px-2 py-1 text-xs text-white"
          >
            {['feature', 'infra', 'security', 'migration', 'incident'].map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
          <button
            onClick={submit}
            disabled={submitting || !objective.trim()}
            className="ml-auto px-3 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 disabled:opacity-40 text-xs font-medium flex items-center gap-1.5"
          >
            {submitting ? <Loader2 className="animate-spin" size={14} /> : <Bot size={14} />} Decompose
          </button>
        </div>
      </div>

      {/* Dashboard summary */}
      {dash && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="rounded-xl border border-white/10 bg-white/5 p-4">
            <div className="text-2xl font-semibold">{dash.total_task_graphs}</div>
            <div className="text-xs text-slate-400">Task graphs</div>
          </div>
          {Object.entries(dash.work_packages_by_status || {}).map(([status, count]) => (
            <div key={status} className="rounded-xl border border-white/10 bg-white/5 p-4">
              <div className="text-2xl font-semibold">{count}</div>
              <div className="text-xs text-slate-400"><StatusPill status={status} /></div>
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-3">
          <h3 className="text-sm font-semibold flex items-center gap-2"><GitBranch size={14} /> Recent task graphs</h3>
          <div className="space-y-2">
            {(dash?.recent_task_graphs || []).map((g) => (
              <TaskGraphCard key={g.id} graph={g} onOpen={openGraph} />
            ))}
            {(!dash?.recent_task_graphs || dash.recent_task_graphs.length === 0) && (
              <p className="text-xs text-slate-500">No objectives submitted yet.</p>
            )}
          </div>
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold flex items-center gap-2"><ShieldCheck size={14} /> Selected graph</h3>
            {selectedGraph && (
              <button onClick={dispatch} className="text-xs px-2 py-1 rounded-lg border border-white/10 hover:bg-white/10">
                Dispatch ready packages
              </button>
            )}
          </div>
          {!selectedGraph && <p className="text-xs text-slate-500">Select a task graph to see its work packages.</p>}
          {selectedGraph && (
            <div className="space-y-2">
              <p className="text-sm text-white">{selectedGraph.objective}</p>
              {(selectedGraph.work_packages || []).map((wp) => (
                <WorkPackageRow key={wp.id} wp={wp} />
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="space-y-3">
        <h3 className="text-sm font-semibold flex items-center gap-2"><Users size={14} /> Departments</h3>
        <DepartmentGrid departments={departments} />
      </div>
    </div>
  )
}
