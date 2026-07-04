import React, { useEffect, useRef, useState } from 'react'
import { Loader2, Send, ShieldCheck, ShieldAlert, CheckCircle2, XCircle, Terminal, Wrench } from 'lucide-react'
import { hqSendMessage, hqApprove, hqReject, hqHistory, hqAutonomousFeed } from '../../services/api'

const AUTONOMOUS_POLL_MS = 30000

const SESSION_KEY = 'jarvis_hq_session_id'

function getSessionId() {
  let id = localStorage.getItem(SESSION_KEY)
  if (!id) {
    id = `hq-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
    localStorage.setItem(SESSION_KEY, id)
  }
  return id
}

const STATUS_BADGE = {
  DRAFTED: { label: 'Drafted', color: 'bg-white/10 text-white/60' },
  PENDING_APPROVAL: { label: 'Awaiting your approval', color: 'bg-amber-500/20 text-amber-300' },
  EXECUTING: { label: 'Executing', color: 'bg-blue-500/20 text-blue-300' },
  COMPLETED: { label: 'Verified', color: 'bg-emerald-500/20 text-emerald-300' },
  FAILED: { label: 'Failed — rolled back', color: 'bg-red-500/20 text-red-300' },
  REJECTED: { label: 'Rejected', color: 'bg-red-500/20 text-red-300' },
  NEVER_BLOCKED: { label: 'Blocked (NEVER tier)', color: 'bg-red-600/20 text-red-400' },
  ROLLED_BACK: { label: 'Rolled back', color: 'bg-red-500/20 text-red-300' },
}

function StatusBadge({ status }) {
  const cfg = STATUS_BADGE[status] || { label: status, color: 'bg-white/10 text-white/60' }
  return (
    <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium ${cfg.color}`}>
      {cfg.label}
    </span>
  )
}

function PlanSteps({ plan }) {
  if (!plan || plan.length === 0) return null
  return (
    <div className="mt-2 space-y-1 border-l-2 border-white/10 pl-3">
      {plan.map((step, i) => (
        <div key={i} className="flex items-center gap-2 text-xs text-white/50 font-mono">
          <Terminal size={12} />
          <span className="text-white/70">{step.tool}</span>
          <span className="truncate">{JSON.stringify(step.args || {})}</span>
        </div>
      ))}
    </div>
  )
}

function AutonomousMessage({ item }) {
  return (
    <div className="rounded-xl border border-amber-500/20 bg-amber-500/[0.04] p-4 space-y-1.5">
      <div className="flex items-center gap-2">
        <Wrench size={13} className="text-amber-400" />
        <span className="text-[11px] font-semibold text-amber-400 uppercase tracking-wide">
          Autonomous — {item.driver_model}
        </span>
        <span className="text-[11px] text-white/30 ml-auto">
          {new Date(item.created_at).toLocaleTimeString()}
        </span>
      </div>
      <p className="text-xs text-white/60 whitespace-pre-wrap">{item.answer_text}</p>
    </div>
  )
}

function Message({ item, onApprove, onReject, busy }) {
  if (item.kind === 'autonomous_operation') {
    return <AutonomousMessage item={item} />
  }
  const isChange = item.kind === 'change_request'
  return (
    <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-4 space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-sm text-white/90 font-medium">{item.request_text}</p>
        <StatusBadge status={item.status} />
      </div>

      {!isChange && item.answer_text && (
        <p className="text-sm text-white/60 whitespace-pre-wrap">{item.answer_text}</p>
      )}

      {isChange && (
        <>
          <div className="flex items-center gap-3 text-[11px] text-white/40">
            {item.driver_model && <span>drafted by {item.driver_model}</span>}
            {item.reviewer_model && <span>reviewed by {item.reviewer_model}</span>}
            {item.tier && <span>tier: {item.tier}</span>}
          </div>
          <PlanSteps plan={item.plan} />
          {item.answer_text && item.status !== 'PENDING_APPROVAL' && (
            <p className="text-xs text-white/50 whitespace-pre-wrap">{item.answer_text}</p>
          )}
          {item.status === 'PENDING_APPROVAL' && (
            <div className="flex gap-2 pt-2">
              <button
                disabled={busy}
                onClick={() => onApprove(item.id)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30
                           text-emerald-300 text-xs font-medium disabled:opacity-50"
              >
                <CheckCircle2 size={14} /> Approve
              </button>
              <button
                disabled={busy}
                onClick={() => onReject(item.id)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-500/20 hover:bg-red-500/30
                           text-red-300 text-xs font-medium disabled:opacity-50"
              >
                <XCircle size={14} /> Reject
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}

export default function Headquarters() {
  const [sessionId] = useState(getSessionId)
  const [items, setItems] = useState([])
  const [text, setText] = useState('')
  const [sending, setSending] = useState(false)
  const [actionBusyId, setActionBusyId] = useState(null)
  const bottomRef = useRef(null)

  const mergeSorted = (list) => {
    const byId = new Map(list.map((i) => [i.id, i]))
    return Array.from(byId.values()).sort(
      (a, b) => new Date(a.created_at || 0) - new Date(b.created_at || 0)
    )
  }

  const loadHistory = async () => {
    try {
      const { items: history } = await hqHistory(sessionId)
      const { items: autonomous } = await hqAutonomousFeed()
      setItems((prev) => mergeSorted([...prev, ...history, ...autonomous]))
    } catch (err) {
      console.warn('[Headquarters] history load failed', err)
    }
  }

  const pollAutonomousFeed = async () => {
    try {
      const { items: autonomous } = await hqAutonomousFeed()
      setItems((prev) => mergeSorted([...prev, ...autonomous]))
    } catch (err) {
      console.warn('[Headquarters] autonomous feed poll failed', err)
    }
  }

  useEffect(() => {
    loadHistory()
    const interval = setInterval(pollAutonomousFeed, AUTONOMOUS_POLL_MS)
    return () => clearInterval(interval)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [items])

  const send = async () => {
    const message = text.trim()
    if (!message || sending) return
    setText('')
    setSending(true)
    try {
      const result = await hqSendMessage(message, sessionId)
      setItems((prev) => [
        ...prev,
        {
          id: result.request_id,
          request_text: message,
          kind: result.kind,
          status: result.status || 'COMPLETED',
          answer_text: result.briefing || result.answer || result.reason,
          plan: result.plan,
          driver_model: result.driver_model,
          reviewer_model: result.reviewer_model,
          tier: result.tier,
          created_at: new Date().toISOString(),
        },
      ])
    } catch (err) {
      setItems((prev) => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          request_text: message,
          kind: 'status_query',
          status: 'FAILED',
          answer_text: err?.response?.data?.detail || 'Headquarters is unreachable.',
          created_at: new Date().toISOString(),
        },
      ])
    } finally {
      setSending(false)
    }
  }

  const handleApprove = async (id) => {
    setActionBusyId(id)
    try {
      await hqApprove(id)
      await loadHistory()
    } finally {
      setActionBusyId(null)
    }
  }

  const handleReject = async (id) => {
    setActionBusyId(id)
    try {
      await hqReject(id)
      await loadHistory()
    } finally {
      setActionBusyId(null)
    }
  }

  return (
    <div className="flex flex-col h-full max-w-3xl mx-auto">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-white/[0.06]">
        <ShieldCheck size={18} className="text-jarvis-blue" />
        <h1 className="text-sm font-semibold text-white/90">Headquarters</h1>
        <span className="text-[11px] text-white/40">— talk to it in plain English</span>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {items.length === 0 && (
          <div className="text-center text-white/30 text-sm mt-12">
            Try: "is production okay?" or "fix the dashboard bug"
          </div>
        )}
        {items.map((item) => (
          <Message
            key={item.id}
            item={item}
            onApprove={handleApprove}
            onReject={handleReject}
            busy={actionBusyId === item.id}
          />
        ))}
        <div ref={bottomRef} />
      </div>

      <div className="p-4 border-t border-white/[0.06] flex items-center gap-2">
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && send()}
          placeholder="Tell Headquarters what you need..."
          className="flex-1 bg-white/[0.04] border border-white/[0.08] rounded-xl px-4 py-2.5
                     text-sm text-white/90 placeholder-white/30 focus:outline-none focus:border-jarvis-blue/50"
        />
        <button
          onClick={send}
          disabled={sending || !text.trim()}
          className="p-2.5 rounded-xl bg-jarvis-blue/20 hover:bg-jarvis-blue/30 text-jarvis-blue disabled:opacity-40"
        >
          {sending ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
        </button>
      </div>
    </div>
  )
}
