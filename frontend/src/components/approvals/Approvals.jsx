import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import {
  AlertTriangle,
  CheckCircle2,
  CheckSquare,
  ChevronDown,
  Clock,
  FileJson,
  Filter,
  Loader2,
  RefreshCw,
  ShieldAlert,
  XCircle,
} from 'lucide-react'
import { approveApproval, getApprovals, getProposalPreview, rejectApproval } from '../../services/api'
import { api } from '../../services/api'
import useJarvisStore from '../../store/useJarvisStore'

const FILTERS = [
  { id: 'all', label: 'All' },
  { id: 'high_risk', label: 'High Risk' },
  { id: 'proposals', label: 'Proposals' },
  { id: 'infrastructure', label: 'Infrastructure' },
  { id: 'financial', label: 'Financial' },
]

const RISK_STYLES = {
  critical: 'border-red-400/40 bg-red-500/10 text-red-200',
  high: 'border-red-400/40 bg-red-500/10 text-red-200',
  medium: 'border-orange-300/35 bg-orange-400/10 text-orange-200',
  low: 'border-jarvis-blue/35 bg-jarvis-blue/10 text-jarvis-blue',
}

function riskStyle(risk) {
  return RISK_STYLES[String(risk || 'medium').toLowerCase()] || RISK_STYLES.medium
}

function asDate(value) {
  const date = value ? new Date(value) : null
  return date && !Number.isNaN(date.getTime()) ? date : null
}

function hoursBetween(start, end = new Date()) {
  const created = asDate(start)
  if (!created) return 0
  return Math.max(0, (end.getTime() - created.getTime()) / 3_600_000)
}

function timeInQueue(createdAt) {
  const hours = hoursBetween(createdAt)
  if (hours < 1) return `${Math.max(1, Math.round(hours * 60))}m`
  if (hours < 24) return `${hours.toFixed(1)}h`
  return `${(hours / 24).toFixed(1)}d`
}

function todayCount(items) {
  const today = new Date().toISOString().slice(0, 10)
  return items.filter((item) => String(item.decided_at || '').slice(0, 10) === today).length
}

function averageQueueTime(items) {
  if (!items.length) return '0m'
  const total = items.reduce((sum, item) => sum + hoursBetween(item.created_at, asDate(item.decided_at) || new Date()), 0)
  const avg = total / items.length
  if (avg < 1) return `${Math.max(1, Math.round(avg * 60))}m`
  if (avg < 24) return `${avg.toFixed(1)}h`
  return `${(avg / 24).toFixed(1)}d`
}

function summarize(text, expanded) {
  const value = text || 'No summary provided.'
  if (expanded || value.length <= 200) return value
  return `${value.slice(0, 200).trim()}...`
}

function categoryMatch(item, filter) {
  if (filter === 'all') return true
  const risk = String(item.risk_level || '').toLowerCase()
  const haystack = [
    item.action_type,
    item.title,
    item.summary,
    JSON.stringify(item.payload || {}),
  ].join(' ').toLowerCase()

  if (filter === 'high_risk') return risk === 'high' || risk === 'critical'
  if (filter === 'proposals') return /proposal|quote|scope|contract/.test(haystack)
  if (filter === 'infrastructure') return /infra|server|ecs|aws|database|redis|deploy|security/.test(haystack)
  if (filter === 'financial') return /price|pricing|invoice|discount|payment|cost|spend|budget|revenue/.test(haystack)
  return true
}

function sortApprovals(a, b) {
  const priorityA = Number(a.priority || 0)
  const priorityB = Number(b.priority || 0)
  if (priorityA !== priorityB) return priorityB - priorityA
  return (asDate(a.created_at)?.getTime() || 0) - (asDate(b.created_at)?.getTime() || 0)
}

function StatPill({ label, value, tone = 'cyan' }) {
  const color = {
    cyan: 'text-jarvis-cyan border-jarvis-cyan/25 bg-jarvis-cyan/10',
    green: 'text-green-300 border-green-400/25 bg-green-400/10',
    red: 'text-red-300 border-red-400/25 bg-red-400/10',
    gold: 'text-jarvis-gold border-jarvis-gold/25 bg-jarvis-gold/10',
  }[tone]

  return (
    <div className={`rounded-xl border px-4 py-3 ${color}`}>
      <p className="text-xs text-white/45">{label}</p>
      <p className="mt-1 text-2xl font-bold">{value}</p>
    </div>
  )
}

function ProposalPreviewPanel({ proposalId, tenantId }) {
  const [open, setOpen] = useState(false)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState(null)

  async function load() {
    if (data || loading) return
    setLoading(true)
    setErr(null)
    try {
      setData(await getProposalPreview(proposalId, tenantId))
    } catch (e) {
      setErr(e?.response?.data?.detail || 'Preview failed to load.')
    } finally {
      setLoading(false)
    }
  }

  function handleToggle() {
    const next = !open
    setOpen(next)
    if (next) load()
  }

  const tierColor = {
    STARTER: 'text-blue-400 border-blue-500/30 bg-blue-500/10',
    GROWTH: 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10',
    ENTERPRISE: 'text-jarvis-gold border-jarvis-gold/30 bg-jarvis-gold/10',
  }[data?.package_tier?.toUpperCase()] || 'text-white/50 border-white/10 bg-white/5'

  return (
    <div className="mt-4 rounded-xl border border-purple-500/20 bg-purple-500/[0.04]">
      <button
        type="button"
        onClick={handleToggle}
        className="flex w-full items-center justify-between px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.16em] text-purple-300/70"
      >
        <span className="flex items-center gap-2">
          <span>📄</span>
          Proposal Content
        </span>
        <ChevronDown size={15} className={`transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden border-t border-purple-500/15"
          >
            <div className="p-4 space-y-3">
              {loading && (
                <div className="flex items-center gap-2 text-xs text-white/40 py-4 justify-center">
                  <Loader2 size={14} className="animate-spin" />
                  Loading proposal…
                </div>
              )}

              {err && (
                <p className="text-xs text-red-400 py-2">{err}</p>
              )}

              {data && !loading && (
                <>
                  <div className="flex flex-wrap items-center gap-2 mb-2">
                    {data.package_tier && (
                      <span className={`rounded-full border px-2.5 py-0.5 text-[11px] font-bold uppercase ${tierColor}`}>
                        {data.package_tier}
                      </span>
                    )}
                    {data.invoice_number && (
                      <span className="text-xs text-white/40">{data.invoice_number}</span>
                    )}
                    {data.pdf_url && (
                      <a
                        href={data.pdf_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-jarvis-cyan hover:text-white underline underline-offset-2"
                      >
                        View PDF →
                      </a>
                    )}
                  </div>

                  {data.pricing && Object.keys(data.pricing).length > 0 && (
                    <div className="flex flex-wrap gap-3 text-xs">
                      {data.pricing.setup_fee != null && (
                        <span className="text-white/60">Setup: <span className="text-white font-semibold">${Number(data.pricing.setup_fee).toLocaleString()}</span></span>
                      )}
                      {data.pricing.monthly_fee != null && (
                        <span className="text-white/60">Monthly: <span className="text-white font-semibold">${Number(data.pricing.monthly_fee).toLocaleString()}</span></span>
                      )}
                    </div>
                  )}

                  {data.content ? (
                    <pre className="max-h-96 overflow-y-auto whitespace-pre-wrap rounded-xl border border-white/10 bg-black/30 p-4 text-[11px] leading-5 text-white/70 font-sans">
                      {data.content}
                    </pre>
                  ) : (
                    <p className="text-xs text-white/30 text-center py-4">No proposal text stored — check the PDF link above.</p>
                  )}
                </>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function ApprovalCard({ approval, focused, onFocus, onApprove, onReject }) {
  const [summaryOpen, setSummaryOpen] = useState(false)
  const [payloadOpen, setPayloadOpen] = useState(false)
  const [note, setNote] = useState('')
  const [deciding, setDeciding] = useState(null)
  const buttonRef = useRef(null)
  const risk = String(approval.risk_level || 'medium').toLowerCase()
  const proposalId = approval.payload?.proposal_id ?? null
  const proposalTenantId = approval.payload?.tenant_id ?? null

  useEffect(() => {
    if (focused) buttonRef.current?.focus()
  }, [focused])

  const decide = async (decision) => {
    setDeciding(decision)
    try {
      if (decision === 'approved') await onApprove(approval.id, note)
      else await onReject(approval.id, note)
    } finally {
      setDeciding(null)
    }
  }

  return (
    <motion.article
      layout
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: -24 }}
      className={`glass border p-5 outline-none transition-all ${focused ? 'border-jarvis-cyan/60 shadow-[0_0_0_1px_rgba(0,200,255,0.25)]' : 'border-white/10'}`}
      tabIndex={0}
      onFocus={onFocus}
    >
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0 flex-1">
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <span className={`rounded-full border px-2.5 py-1 text-[11px] font-bold uppercase tracking-wide ${riskStyle(risk)}`}>
              {risk} risk
            </span>
            <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-[11px] uppercase tracking-wide text-white/50">
              {approval.action_type || 'approval'}
            </span>
            <span className="flex items-center gap-1 text-xs text-white/35">
              <Clock size={12} />
              {timeInQueue(approval.created_at)} in queue
            </span>
          </div>

          <h3 className="text-base font-semibold text-white">{approval.title || 'Untitled approval'}</h3>
          <p className="mt-2 text-sm leading-6 text-white/60">{summarize(approval.summary, summaryOpen)}</p>
          {(approval.summary || '').length > 200 && (
            <button
              type="button"
              onClick={() => setSummaryOpen((value) => !value)}
              className="mt-2 text-xs text-jarvis-cyan hover:text-white"
            >
              {summaryOpen ? 'Collapse summary' : 'Expand summary'}
            </button>
          )}
        </div>

        <div className="w-full shrink-0 space-y-2 lg:w-72">
          <textarea
            value={note}
            onChange={(event) => setNote(event.target.value)}
            placeholder="Optional Captain note before confirming"
            className="h-20 w-full resize-none rounded-xl border border-white/10 bg-white/[0.04] px-3 py-2 text-sm text-white/80 outline-none placeholder:text-white/25 focus:border-jarvis-cyan/40"
          />
          <div className="grid grid-cols-2 gap-2">
            <button
              ref={buttonRef}
              type="button"
              onClick={() => decide('approved')}
              disabled={Boolean(deciding)}
              className="flex items-center justify-center gap-2 rounded-xl border border-green-400/30 bg-green-400/10 px-3 py-2.5 text-sm font-bold text-green-300 transition hover:bg-green-400/20 disabled:opacity-50"
            >
              {deciding === 'approved' ? <Loader2 size={15} className="animate-spin" /> : <CheckCircle2 size={15} />}
              APPROVE
            </button>
            <button
              type="button"
              onClick={() => decide('rejected')}
              disabled={Boolean(deciding)}
              className="flex items-center justify-center gap-2 rounded-xl border border-red-400/30 bg-red-400/10 px-3 py-2.5 text-sm font-bold text-red-300 transition hover:bg-red-400/20 disabled:opacity-50"
            >
              {deciding === 'rejected' ? <Loader2 size={15} className="animate-spin" /> : <XCircle size={15} />}
              REJECT
            </button>
          </div>
        </div>
      </div>

      {proposalId && (
        <ProposalPreviewPanel proposalId={proposalId} tenantId={proposalTenantId} />
      )}

      <div className="mt-4 rounded-xl border border-white/10 bg-white/[0.03]">
        <button
          type="button"
          onClick={() => setPayloadOpen((value) => !value)}
          className="flex w-full items-center justify-between px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.16em] text-white/45"
        >
          <span className="flex items-center gap-2">
            <FileJson size={14} />
            Payload preview
          </span>
          <ChevronDown size={15} className={`transition-transform ${payloadOpen ? 'rotate-180' : ''}`} />
        </button>
        <AnimatePresence initial={false}>
          {payloadOpen && (
            <motion.pre
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="max-h-80 overflow-auto border-t border-white/10 p-4 text-xs leading-5 text-white/60"
            >
              {JSON.stringify(approval.payload || {}, null, 2)}
            </motion.pre>
          )}
        </AnimatePresence>
      </div>
    </motion.article>
  )
}

export default function Approvals() {
  const { setPendingApprovals } = useJarvisStore()
  const [pending, setPending] = useState([])
  const [autoStats, setAutoStats] = useState(null)
  const [approved, setApproved] = useState([])
  const [rejected, setRejected] = useState([])
  const [filter, setFilter] = useState('all')
  const [focusedId, setFocusedId] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [pendingRows, approvedRows, rejectedRows, statsRes] = await Promise.all([
        getApprovals('pending'),
        getApprovals('approved'),
        getApprovals('rejected'),
        api.get('/api/v1/governance/auto-approval-stats').then(r => r.data).catch(() => null),
      ])
      if (statsRes) setAutoStats(statsRes)
      setPending(Array.isArray(pendingRows) ? pendingRows : [])
      setApproved(Array.isArray(approvedRows) ? approvedRows : [])
      setRejected(Array.isArray(rejectedRows) ? rejectedRows : [])
      setPendingApprovals(Array.isArray(pendingRows) ? pendingRows.length : 0)
    } catch (err) {
      setError(err?.response?.data?.detail || 'Approval queue could not be loaded.')
      setPending([])
      setApproved([])
      setRejected([])
    } finally {
      setLoading(false)
    }
  }, [setPendingApprovals])

  useEffect(() => {
    load()
  }, [load])

  const visibleApprovals = useMemo(() => (
    pending.filter((item) => categoryMatch(item, filter)).sort(sortApprovals)
  ), [filter, pending])

  useEffect(() => {
    if (!visibleApprovals.length) setFocusedId(null)
    else if (!focusedId || !visibleApprovals.some((item) => item.id === focusedId)) {
      setFocusedId(visibleApprovals[0].id)
    }
  }, [focusedId, visibleApprovals])

  const decideAndRemove = useCallback(async (id, decision, note) => {
    if (decision === 'approved') await approveApproval(id, note)
    else await rejectApproval(id, note)
    setPending((items) => {
      const next = items.filter((item) => item.id !== id)
      setPendingApprovals(next.length)
      return next
    })
    load()
  }, [load, setPendingApprovals])

  useEffect(() => {
    const onKey = (event) => {
      if (['INPUT', 'TEXTAREA'].includes(document.activeElement?.tagName)) return
      if (!focusedId) return
      if (event.key.toLowerCase() === 'a') {
        event.preventDefault()
        decideAndRemove(focusedId, 'approved', '')
      }
      if (event.key.toLowerCase() === 'r') {
        event.preventDefault()
        decideAndRemove(focusedId, 'rejected', '')
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [decideAndRemove, focusedId])

  return (
    <div className="h-full min-h-0 overflow-y-auto p-6 pb-28 space-y-6">
      <header className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.22em] text-jarvis-cyan/70">Captain Decision Center</p>
          <div className="mt-2 flex flex-wrap items-center gap-3">
            <h1 className="text-3xl font-bold text-white">Captain's Queue</h1>
            <span className={`rounded-full border px-3 py-1 text-xs font-bold ${pending.length ? 'border-red-400/35 bg-red-400/10 text-red-200' : 'border-green-400/35 bg-green-400/10 text-green-200'}`}>
              {pending.length} pending
            </span>
          </div>
          <p className="mt-2 max-w-3xl text-sm text-white/45">
            JARVIS can execute routine work, but these actions need Captain approval before money, contracts, infrastructure, or risk moves forward.
          </p>
        </div>
        <button
          type="button"
          onClick={load}
          disabled={loading}
          className="btn-primary inline-flex items-center gap-2"
        >
          {loading ? <Loader2 size={15} className="animate-spin" /> : <RefreshCw size={15} />}
          Refresh Queue
        </button>
      </header>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        <StatPill label="Approved today" value={todayCount(approved)} tone="green" />
        <StatPill label="Rejected today" value={todayCount(rejected)} tone="red" />
        <StatPill label="Average time in queue" value={averageQueueTime([...pending, ...approved, ...rejected])} tone="gold" />
      </div>

      {autoStats && (
        <div className="rounded-xl border border-jarvis-cyan/20 bg-jarvis-cyan/[0.04] p-4">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-jarvis-cyan/70 mb-3">Autonomous Engine Stats</p>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <div className="rounded-lg border border-white/10 bg-black/20 p-3">
              <p className="text-[10px] text-white/40 uppercase tracking-widest">Auto-Invoices Sent</p>
              <p className="text-lg font-bold text-white mt-1">{autoStats.auto_approved_invoices?.count ?? 0}</p>
              <p className="text-xs text-green-400">${(autoStats.auto_approved_invoices?.total_value ?? 0).toLocaleString()}</p>
            </div>
            <div className="rounded-lg border border-white/10 bg-black/20 p-3">
              <p className="text-[10px] text-white/40 uppercase tracking-widest">Auto-Proposals Sent</p>
              <p className="text-lg font-bold text-white mt-1">{autoStats.auto_approved_proposals?.count ?? 0}</p>
              <p className="text-xs text-blue-400">${(autoStats.auto_approved_proposals?.total_value ?? 0).toLocaleString()}</p>
            </div>
            <div className="rounded-lg border border-white/10 bg-black/20 p-3">
              <p className="text-[10px] text-white/40 uppercase tracking-widest">Invoice Gate</p>
              <p className="text-lg font-bold text-jarvis-gold mt-1">${autoStats.thresholds?.invoice_usd ?? 'N/A'}</p>
              <p className="text-xs text-white/40">auto-approve below</p>
            </div>
            <div className="rounded-lg border border-white/10 bg-black/20 p-3">
              <p className="text-[10px] text-white/40 uppercase tracking-widest">Auto Outreach</p>
              <p className="text-lg font-bold mt-1 text-white">{autoStats.thresholds?.auto_outreach_enabled ? 'ON' : 'OFF'}</p>
              <p className="text-xs text-white/40">engine state</p>
            </div>
          </div>
        </div>
      )}

      <section className="glass p-4">
        <div className="mb-3 flex items-center gap-2 text-xs uppercase tracking-[0.18em] text-white/35">
          <Filter size={14} />
          Filters
        </div>
        <div className="flex flex-wrap gap-2">
          {FILTERS.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setFilter(item.id)}
              className={`rounded-xl border px-3 py-2 text-sm font-medium transition ${
                filter === item.id
                  ? 'border-jarvis-cyan/40 bg-jarvis-cyan/10 text-jarvis-cyan'
                  : 'border-white/10 bg-white/[0.03] text-white/45 hover:text-white/75'
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>
      </section>

      {error && (
        <div className="glass flex items-start gap-3 border-red-400/30 bg-red-500/10 p-4 text-sm text-red-100">
          <ShieldAlert size={18} className="mt-0.5" />
          {error}
        </div>
      )}

      {loading && !visibleApprovals.length && (
        <div className="flex justify-center py-16">
          <div className="glass flex items-center gap-3 px-5 py-4 text-sm text-white/50">
            <Loader2 size={18} className="animate-spin text-jarvis-cyan" />
            Loading Captain queue
          </div>
        </div>
      )}

      {!loading && !visibleApprovals.length && (
        <div className="glass p-12 text-center">
          <CheckSquare size={36} className="mx-auto mb-3 text-green-300/60" />
          <p className="text-base font-semibold text-white">No matching approvals.</p>
          <p className="mt-2 text-sm text-white/40">The current filter has no pending Captain decisions.</p>
        </div>
      )}

      <AnimatePresence mode="popLayout">
        {visibleApprovals.map((approval) => (
          <ApprovalCard
            key={approval.id}
            approval={approval}
            focused={focusedId === approval.id}
            onFocus={() => setFocusedId(approval.id)}
            onApprove={(id, note) => decideAndRemove(id, 'approved', note)}
            onReject={(id, note) => decideAndRemove(id, 'rejected', note)}
          />
        ))}
      </AnimatePresence>

      <div className="glass flex flex-wrap items-center gap-3 p-4 text-xs text-white/35">
        <AlertTriangle size={14} className="text-jarvis-gold" />
        Keyboard shortcuts: focus a card, then press A to approve or R to reject. Tab moves through cards and controls.
      </div>
    </div>
  )
}
