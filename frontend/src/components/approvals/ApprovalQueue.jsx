import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { CheckSquare, AlertTriangle, CheckCircle, XCircle,
         Clock, DollarSign, Shield, ChevronDown, ChevronUp, RefreshCw } from 'lucide-react'
import { getApprovals, decideApproval } from '../../services/api'
import useJarvisStore from '../../store/useJarvisStore'

const RISK_COLORS = {
  low:      { border: 'border-green-400/20',  bg: 'bg-green-400/10',  text: 'text-green-400' },
  medium:   { border: 'border-amber-400/20',  bg: 'bg-amber-400/10',  text: 'text-amber-400' },
  high:     { border: 'border-orange-400/20', bg: 'bg-orange-400/10', text: 'text-orange-400' },
  critical: { border: 'border-red-400/20',    bg: 'bg-red-400/10',    text: 'text-red-400' },
}

const ApprovalCard = ({ approval, onDecide }) => {
  const [expanded, setExpanded] = useState(false)
  const [note, setNote] = useState('')
  const [deciding, setDeciding] = useState(false)
  const risk = RISK_COLORS[approval.risk_level] || RISK_COLORS.medium

  const decide = async (status) => {
    setDeciding(true)
    try {
      await onDecide(approval.id, { status, captain_note: note })
    } finally {
      setDeciding(false)
    }
  }

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: -20 }}
      className={`glass border ${risk.border} rounded-xl overflow-hidden`}
    >
      {/* Header */}
      <div className="p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3 flex-1">
            <div className={`p-2 rounded-lg ${risk.bg} flex-shrink-0 mt-0.5`}>
              <AlertTriangle size={14} className={risk.text} />
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2 flex-wrap">
                <h3 className="text-sm font-semibold text-white">{approval.title}</h3>
                <span className={`text-[10px] px-2 py-0.5 rounded-full ${risk.bg} ${risk.text} font-medium uppercase`}>
                  {approval.risk_level}
                </span>
              </div>
              <p className="text-xs text-white/50 mt-1">{approval.summary}</p>
              <div className="flex items-center gap-4 mt-2">
                <span className="flex items-center gap-1 text-[10px] text-white/30">
                  <Clock size={10} /> {new Date(approval.created_at).toLocaleString()}
                </span>
                {approval.estimated_cost && (
                  <span className="flex items-center gap-1 text-[10px] text-white/30">
                    <DollarSign size={10} /> {approval.estimated_cost}
                  </span>
                )}
                <span className="flex items-center gap-1 text-[10px] text-white/30">
                  <Shield size={10} /> {approval.action_type}
                </span>
              </div>
            </div>
          </div>
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-white/30 hover:text-white/60 p-1"
          >
            {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
        </div>
      </div>

      {/* Expanded detail */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="border-t border-white/[0.06]"
          >
            <div className="p-5 space-y-4">
              {/* Benefits & Risks */}
              <div className="grid grid-cols-2 gap-4">
                {approval.benefits && (
                  <div>
                    <p className="text-[10px] text-green-400/70 uppercase tracking-wider mb-2 font-medium">Benefits</p>
                    <ul className="space-y-1">
                      {(Array.isArray(approval.benefits) ? approval.benefits : [approval.benefits]).map((b, i) => (
                        <li key={i} className="text-xs text-white/50 flex items-start gap-1.5">
                          <span className="text-green-400/60 mt-0.5">+</span>{b}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {approval.risks && (
                  <div>
                    <p className="text-[10px] text-red-400/70 uppercase tracking-wider mb-2 font-medium">Risks</p>
                    <ul className="space-y-1">
                      {(Array.isArray(approval.risks) ? approval.risks : [approval.risks]).map((r, i) => (
                        <li key={i} className="text-xs text-white/50 flex items-start gap-1.5">
                          <span className="text-red-400/60 mt-0.5">-</span>{r}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
              {approval.rollback_plan && (
                <div className="px-3 py-2 rounded-lg bg-white/[0.03] border border-white/[0.06]">
                  <p className="text-[10px] text-white/30 uppercase tracking-wider mb-1">Rollback Plan</p>
                  <p className="text-xs text-white/50">{approval.rollback_plan}</p>
                </div>
              )}

              {/* Captain note */}
              <input
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Optional note before deciding…"
                className="w-full bg-white/[0.04] border border-white/[0.10] rounded-lg px-3 py-2
                           text-xs text-white/70 placeholder:text-white/25 outline-none
                           focus:border-jarvis-blue/40"
              />

              {/* Decision buttons */}
              <div className="flex gap-3">
                <motion.button
                  whileTap={{ scale: 0.96 }}
                  onClick={() => decide('approved')}
                  disabled={deciding}
                  className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg
                             bg-green-400/10 border border-green-400/30 text-green-400
                             text-sm font-medium hover:bg-green-400/20 transition-all
                             disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  <CheckCircle size={15} />
                  Approve
                </motion.button>
                <motion.button
                  whileTap={{ scale: 0.96 }}
                  onClick={() => decide('rejected')}
                  disabled={deciding}
                  className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg
                             bg-red-400/10 border border-red-400/30 text-red-400
                             text-sm font-medium hover:bg-red-400/20 transition-all
                             disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  <XCircle size={15} />
                  Reject
                </motion.button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

export default function ApprovalQueue() {
  const { setPendingApprovals } = useJarvisStore()
  const [approvals, setApprovals] = useState([])
  const [filter, setFilter] = useState('pending')
  const [loading, setLoading] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const data = await getApprovals(filter)
      setApprovals(data)
      if (filter === 'pending') setPendingApprovals(data.length)
    } catch {
      setApprovals([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [filter])

  const handleDecide = async (id, decision) => {
    await decideApproval(id, decision)
    load()
  }

  const FILTERS = ['pending', 'approved', 'rejected']

  return (
    <div className="p-6 h-full overflow-y-auto no-scrollbar space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-amber-400/10 border border-amber-400/20">
            <CheckSquare size={18} className="text-amber-400" />
          </div>
          <div>
            <h2 className="font-bold text-white text-sm">Approval Queue</h2>
            <p className="text-xs text-white/40">Review and authorize JARVIS operations</p>
          </div>
        </div>
        <button onClick={load} disabled={loading} className="btn-primary flex items-center gap-2">
          <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-2">
        {FILTERS.map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-all
                         ${filter === f
                           ? 'bg-jarvis-blue/15 border border-jarvis-blue/30 text-jarvis-blue'
                           : 'bg-white/[0.04] border border-white/[0.08] text-white/40 hover:text-white/60'}`}
          >
            {f}
          </button>
        ))}
      </div>

      {/* List */}
      {loading && approvals.length === 0 && (
        <div className="flex justify-center py-16">
          <div className="flex flex-col items-center gap-3">
            <RefreshCw size={24} className="text-jarvis-blue animate-spin" />
            <p className="text-xs text-white/30">Loading approvals…</p>
          </div>
        </div>
      )}

      {!loading && approvals.length === 0 && (
        <div className="glass p-12 text-center border border-white/[0.06]">
          <CheckCircle size={32} className="text-green-400/40 mx-auto mb-3" />
          <p className="text-white/40 text-sm">
            {filter === 'pending' ? 'No pending approvals. All clear, Captain.' : `No ${filter} approvals.`}
          </p>
        </div>
      )}

      <AnimatePresence mode="popLayout">
        {approvals.map((a) => (
          <ApprovalCard key={a.id} approval={a} onDecide={handleDecide} />
        ))}
      </AnimatePresence>
    </div>
  )
}
