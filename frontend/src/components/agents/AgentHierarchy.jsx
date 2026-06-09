import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Users, ChevronDown, ChevronRight, Zap, Brain, Send } from 'lucide-react'
import { getAgentHierarchy, dispatchAgent } from '../../services/api'

const ROLE_COLORS = {
  CEO:      'text-yellow-400 border-yellow-400/30 bg-yellow-400/10',
  CTO:      'text-jarvis-blue border-jarvis-blue/30 bg-jarvis-blue/10',
  Manager:  'text-purple-400 border-purple-400/30 bg-purple-400/10',
  Director: 'text-blue-400 border-blue-400/30 bg-blue-400/10',
  Lead:     'text-green-400 border-green-400/30 bg-green-400/10',
  Worker:   'text-white/50 border-white/20 bg-white/5',
}

const getRoleColor = (role = '') => {
  for (const [key, val] of Object.entries(ROLE_COLORS)) {
    if (role.includes(key)) return val
  }
  return ROLE_COLORS.Worker
}

const AgentNode = ({ name, agent, depth = 0 }) => {
  const [open, setOpen] = useState(depth === 0)
  const hasChildren = agent.workers?.length > 0
  const color = getRoleColor(agent.role)

  return (
    <div className={`${depth > 0 ? 'ml-6 border-l border-white/[0.05] pl-4' : ''}`}>
      <motion.div
        initial={{ opacity: 0, x: -10 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: depth * 0.05 }}
        className={`flex items-center gap-3 p-3 rounded-xl glass border mb-2
                    hover:bg-white/[0.04] transition-all cursor-pointer group
                    ${depth === 0 ? 'border-jarvis-blue/15' : 'border-white/[0.06]'}`}
        onClick={() => hasChildren && setOpen(!open)}
      >
        {hasChildren && (
          <span className="text-white/30 group-hover:text-white/60">
            {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
          </span>
        )}
        {!hasChildren && <span className="w-4" />}

        <div className={`px-2 py-0.5 rounded text-[10px] font-medium border ${color}`}>
          {agent.role}
        </div>

        <div className="flex-1">
          <p className="text-sm text-white/80 font-medium">{name}</p>
          {agent.focus && (
            <p className="text-[10px] text-white/30 mt-0.5 truncate max-w-xs">{agent.focus}</p>
          )}
        </div>

        <div className="flex items-center gap-1">
          {(agent.capabilities || []).slice(0, 3).map((cap) => (
            <span key={cap}
                  className="text-[9px] px-1.5 py-0.5 rounded bg-white/[0.04] border border-white/[0.08] text-white/30">
              {cap}
            </span>
          ))}
          {(agent.capabilities?.length || 0) > 3 && (
            <span className="text-[9px] text-white/25">+{agent.capabilities.length - 3}</span>
          )}
        </div>

        <div className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-green-400 shadow-[0_0_5px_#4ade80]" />
          <span className="text-[10px] text-green-400/70">Ready</span>
        </div>
      </motion.div>

      {open && hasChildren && agent.workers?.map((workerName) => (
        <AgentNode
          key={workerName}
          name={workerName}
          agent={{ role: 'Specialist', capabilities: [], focus: `Under ${name}` }}
          depth={depth + 1}
        />
      ))}
    </div>
  )
}

export default function AgentHierarchy() {
  const [hierarchy, setHierarchy] = useState(null)
  const [dispatchForm, setDispatchForm] = useState({ task: '', agent: '', show: false })
  const [result, setResult] = useState(null)
  const [dispatching, setDispatching] = useState(false)

  useEffect(() => {
    getAgentHierarchy().then(setHierarchy).catch(() => {})
  }, [])

  const handleDispatch = async () => {
    if (!dispatchForm.task.trim()) return
    setDispatching(true)
    try {
      const r = await dispatchAgent({ task: dispatchForm.task, agent_name: dispatchForm.agent || null })
      setResult(r)
      setDispatchForm((f) => ({ ...f, show: false, task: '' }))
    } catch {
      setResult({
        message: 'Dispatch paused. The control room could not reach the live backend just now, but the request has been preserved.',
      })
    } finally {
      setDispatching(false)
    }
  }

  return (
    <div className="p-6 pb-28 h-full min-h-0 overflow-y-auto no-scrollbar space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-purple-400/10 border border-purple-400/20">
            <Users size={18} className="text-purple-400" />
          </div>
          <div>
            <h2 className="font-bold text-white text-sm">AI Agent Hierarchy</h2>
            <p className="text-xs text-white/40">22 agents · 10 managers · 12 specialists</p>
          </div>
        </div>
        <button
          onClick={() => setDispatchForm((f) => ({ ...f, show: !f.show }))}
          className="btn-primary flex items-center gap-2"
        >
          <Send size={12} />
          Dispatch Task
        </button>
      </div>

      {/* Dispatch form */}
      {dispatchForm.show && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass p-5 border border-jarvis-blue/20"
        >
          <p className="text-xs font-semibold text-white/60 mb-3">Dispatch to Agent Network</p>
          <div className="space-y-3">
            <textarea
              value={dispatchForm.task}
              onChange={(e) => setDispatchForm((f) => ({ ...f, task: e.target.value }))}
              placeholder="Describe the task for the agent network…"
              rows={3}
              className="w-full bg-white/[0.04] border border-white/[0.10] rounded-lg px-3 py-2
                         text-sm text-white/70 placeholder:text-white/25 outline-none resize-none
                         focus:border-jarvis-blue/40"
            />
            <input
              value={dispatchForm.agent}
              onChange={(e) => setDispatchForm((f) => ({ ...f, agent: e.target.value }))}
              placeholder="Specific agent name (optional — auto-routes if blank)"
              className="w-full bg-white/[0.04] border border-white/[0.10] rounded-lg px-3 py-2
                         text-sm text-white/70 placeholder:text-white/25 outline-none
                         focus:border-jarvis-blue/40"
            />
            <button
              onClick={handleDispatch}
              disabled={!dispatchForm.task.trim() || dispatching}
              className="btn-primary w-full flex items-center justify-center gap-2"
            >
              <Zap size={13} />
              {dispatching ? 'Dispatching…' : 'Dispatch'}
            </button>
          </div>
        </motion.div>
      )}

      {result && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="glass p-4 border border-green-400/20"
        >
          <p className="text-xs text-green-400 font-medium mb-1">Dispatch Result</p>
          <p className="text-xs text-white/60">{result.message || JSON.stringify(result)}</p>
          <button onClick={() => setResult(null)} className="text-[10px] text-white/30 hover:text-white/50 mt-2">
            Dismiss
          </button>
        </motion.div>
      )}

      {/* Hierarchy tree */}
      <div className="space-y-2">
        {hierarchy ? (
          Object.entries(hierarchy).map(([name, agent]) => (
            <AgentNode key={name} name={name} agent={agent} depth={0} />
          ))
        ) : (
          // Skeleton
          Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="glass p-3 rounded-xl border border-white/[0.06] animate-pulse">
              <div className="h-4 bg-white/[0.04] rounded w-2/3" />
            </div>
          ))
        )}
      </div>
    </div>
  )
}
