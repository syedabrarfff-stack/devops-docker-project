import React, { useCallback, useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Cpu, Zap, CheckCircle, XCircle, Clock, Send, Edit3, ChevronDown,
  ChevronUp, RefreshCw, Loader, AlertCircle, User, Building2, Globe,
  TrendingUp, Star, Mail, Settings, Play, Trash2, Check, X, Eye,
} from 'lucide-react'
import { api } from '../../services/api'

// ── Score badge ──────────────────────────────────────────────────────────────

function ScoreBadge({ score }) {
  const color = score >= 70 ? 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10'
              : score >= 45 ? 'text-amber-400 border-amber-500/30 bg-amber-500/10'
              : 'text-red-400 border-red-500/30 bg-red-500/10'
  return (
    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${color}`}>
      {Number(score).toFixed(0)}
    </span>
  )
}

// ── Status chip ──────────────────────────────────────────────────────────────

const STATUS_STYLE = {
  pending:  'text-amber-400 bg-amber-500/10 border-amber-500/25',
  sent:     'text-emerald-400 bg-emerald-500/10 border-emerald-500/25',
  rejected: 'text-red-400 bg-red-500/10 border-red-500/25',
  error:    'text-orange-400 bg-orange-500/10 border-orange-500/25',
}

function StatusChip({ status }) {
  return (
    <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${STATUS_STYLE[status] || STATUS_STYLE.pending}`}>
      {status?.toUpperCase()}
    </span>
  )
}

// ── Stat card ────────────────────────────────────────────────────────────────

function StatCard({ label, value, icon: Icon, color = 'text-white/50' }) {
  return (
    <div className="flex-1 min-w-[90px] px-4 py-3 rounded-xl border border-white/[0.08] bg-white/[0.02]">
      <div className={`text-xs font-semibold mb-1 ${color} flex items-center gap-1.5`}>
        <Icon size={11} />
        {label}
      </div>
      <div className="text-2xl font-bold text-white">{value}</div>
    </div>
  )
}

// ── Email detail modal ────────────────────────────────────────────────────────

function DraftModal({ draft, onClose, onApprove, onReject, onEdit, loading }) {
  const [editMode, setEditMode]   = useState(false)
  const [subject, setSubject]     = useState(draft.subject || '')
  const [body, setBody]           = useState(draft.body || '')
  const [saving, setSaving]       = useState(false)

  async function handleSave() {
    setSaving(true)
    await onEdit(draft.id, subject, body)
    setSaving(false)
    setEditMode(false)
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
      onClick={e => { if (e.target === e.currentTarget) onClose() }}
    >
      <motion.div
        initial={{ scale: 0.95, opacity: 0, y: 12 }}
        animate={{ scale: 1, opacity: 1, y: 0 }}
        exit={{ scale: 0.95, opacity: 0 }}
        className="w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl
                   border border-white/[0.1] bg-[#0d0d14] shadow-2xl"
      >
        {/* Header */}
        <div className="flex items-start justify-between px-6 py-4 border-b border-white/[0.06]">
          <div>
            <h3 className="text-base font-semibold text-white">
              {draft.lead_company || '—'}
            </h3>
            <p className="text-xs text-white/40 mt-0.5">
              {draft.lead_contact && <span>{draft.lead_contact} · </span>}
              {draft.lead_email}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <StatusChip status={draft.status} />
            <button onClick={onClose} className="p-1.5 rounded-lg text-white/30 hover:text-white/70 hover:bg-white/[0.05]">
              <X size={15} />
            </button>
          </div>
        </div>

        {/* Lead intel strip */}
        <div className="px-6 py-3 flex flex-wrap gap-x-4 gap-y-1 border-b border-white/[0.04]
                        bg-white/[0.01] text-xs text-white/50">
          {draft.lead_industry && (
            <span className="flex items-center gap-1"><TrendingUp size={11} />{draft.lead_industry}</span>
          )}
          {draft.lead_country && (
            <span className="flex items-center gap-1"><Globe size={11} />{draft.lead_country}</span>
          )}
          <span className="flex items-center gap-1"><Star size={11} className="text-amber-400" />Score: <b className="text-amber-300">{Number(draft.lead_score || 0).toFixed(0)}</b></span>
          <span className="flex items-center gap-1"><User size={11} />{draft.persona_name}</span>
          <span className="flex items-center gap-1 opacity-60">{draft.tone}</span>
        </div>

        {/* Email content */}
        <div className="px-6 py-4 space-y-3">
          {/* Subject */}
          <div>
            <div className="text-[10px] text-white/30 uppercase tracking-wider mb-1.5">Subject</div>
            {editMode ? (
              <input
                value={subject}
                onChange={e => setSubject(e.target.value)}
                className="w-full px-3 py-2 text-sm bg-white/[0.05] border border-white/[0.12]
                           rounded-lg text-white outline-none focus:border-jarvis-blue/40"
              />
            ) : (
              <p className="text-sm font-semibold text-white">{draft.subject}</p>
            )}
          </div>

          {/* Body */}
          <div>
            <div className="text-[10px] text-white/30 uppercase tracking-wider mb-1.5">Email Body</div>
            {editMode ? (
              <textarea
                value={body}
                onChange={e => setBody(e.target.value)}
                rows={10}
                className="w-full px-3 py-2 text-sm bg-white/[0.05] border border-white/[0.12]
                           rounded-lg text-white outline-none focus:border-jarvis-blue/40
                           font-mono leading-relaxed resize-none"
              />
            ) : (
              <div className="text-sm text-white/75 whitespace-pre-wrap leading-relaxed font-mono
                              bg-white/[0.02] rounded-lg p-3 border border-white/[0.06]">
                {draft.body}
              </div>
            )}
          </div>
        </div>

        {/* Actions */}
        {draft.status === 'pending' && (
          <div className="px-6 py-4 border-t border-white/[0.06] flex items-center gap-2 flex-wrap">
            {editMode ? (
              <>
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium
                             bg-jarvis-blue/15 border border-jarvis-blue/30 text-jarvis-blue
                             hover:bg-jarvis-blue/25 transition-all"
                >
                  {saving ? <Loader size={13} className="animate-spin" /> : <Check size={13} />}
                  Save Changes
                </button>
                <button
                  onClick={() => { setEditMode(false); setSubject(draft.subject); setBody(draft.body) }}
                  className="px-3 py-2 rounded-lg text-sm text-white/40 hover:text-white/70 border
                             border-white/[0.06] hover:border-white/[0.15] transition-all"
                >
                  Cancel
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={() => onApprove(draft.id)}
                  disabled={loading}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-semibold
                             bg-emerald-500/15 border border-emerald-500/30 text-emerald-400
                             hover:bg-emerald-500/25 transition-all"
                >
                  {loading ? <Loader size={13} className="animate-spin" /> : <Send size={13} />}
                  Approve & Send
                </button>
                <button
                  onClick={() => setEditMode(true)}
                  className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm border
                             border-white/[0.08] text-white/50 hover:text-white/80 transition-all"
                >
                  <Edit3 size={13} /> Edit
                </button>
                <button
                  onClick={() => onReject(draft.id)}
                  className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm border
                             border-red-500/20 text-red-400/70 hover:text-red-400 hover:border-red-500/40 transition-all"
                >
                  <XCircle size={13} /> Reject
                </button>
              </>
            )}
          </div>
        )}
      </motion.div>
    </motion.div>
  )
}

// ── Draft card ────────────────────────────────────────────────────────────────

function DraftCard({ draft, onApprove, onReject, onViewDetail, approving }) {
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.97 }}
      className={`rounded-xl border transition-all
        ${draft.status === 'pending'
          ? 'border-white/[0.1] bg-white/[0.02] hover:border-white/[0.18]'
          : draft.status === 'sent'
          ? 'border-emerald-500/20 bg-emerald-500/5'
          : draft.status === 'rejected'
          ? 'border-red-500/15 bg-red-500/5 opacity-60'
          : 'border-white/[0.06] bg-white/[0.01]'}`}
    >
      {/* Card header */}
      <div className="flex items-start justify-between px-4 pt-4 pb-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <Building2 size={13} className="text-white/30 flex-shrink-0" />
            <span className="text-sm font-semibold text-white truncate">
              {draft.lead_company || '—'}
            </span>
            <ScoreBadge score={draft.lead_score || 0} />
            <StatusChip status={draft.status} />
          </div>
          <div className="mt-1 flex items-center gap-3 text-[11px] text-white/40">
            {draft.lead_contact && <span>{draft.lead_contact}</span>}
            {draft.lead_industry && <span className="opacity-60">{draft.lead_industry}</span>}
            {draft.persona_name && (
              <span className="flex items-center gap-1">
                <User size={10} />{draft.persona_name}
              </span>
            )}
          </div>
        </div>
        <div className="text-[10px] text-white/25 flex-shrink-0 ml-2 mt-0.5">
          {draft.created_at ? new Date(draft.created_at).toLocaleDateString() : ''}
        </div>
      </div>

      {/* Subject preview */}
      {draft.subject && (
        <div className="px-4 pb-3">
          <div className="text-[10px] text-white/25 uppercase tracking-wider mb-1">Subject</div>
          <p className="text-xs text-white/60 font-medium truncate">{draft.subject}</p>
        </div>
      )}

      {/* Body snippet */}
      {draft.body && (
        <div className="px-4 pb-3">
          <p className="text-[11px] text-white/35 line-clamp-2 leading-relaxed font-mono">
            {draft.body.slice(0, 140)}{draft.body.length > 140 ? '…' : ''}
          </p>
        </div>
      )}

      {/* Action row */}
      {draft.status === 'pending' && (
        <div className="px-4 pb-4 flex items-center gap-2 border-t border-white/[0.05] pt-3">
          <button
            onClick={() => onApprove(draft.id)}
            disabled={approving === draft.id}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold
                       bg-emerald-500/10 border border-emerald-500/25 text-emerald-400
                       hover:bg-emerald-500/20 transition-all disabled:opacity-50"
          >
            {approving === draft.id
              ? <Loader size={11} className="animate-spin" />
              : <Send size={11} />}
            Send
          </button>
          <button
            onClick={() => onViewDetail(draft)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs border
                       border-white/[0.08] text-white/40 hover:text-white/70 transition-all"
          >
            <Eye size={11} /> View & Edit
          </button>
          <button
            onClick={() => onReject(draft.id)}
            className="ml-auto flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs border
                       border-red-500/15 text-red-400/50 hover:text-red-400 hover:border-red-500/30 transition-all"
          >
            <XCircle size={11} /> Skip
          </button>
        </div>
      )}

      {draft.status === 'sent' && (
        <div className="px-4 pb-3 flex items-center gap-1.5 text-[11px] text-emerald-400/70">
          <CheckCircle size={11} />
          Sent to {draft.lead_email}
          {draft.sent_at && <span className="ml-1 opacity-50">{new Date(draft.sent_at).toLocaleTimeString()}</span>}
        </div>
      )}
    </motion.div>
  )
}

// ── Ignite settings panel ────────────────────────────────────────────────────

function IgnitePanel({ settings, onChange }) {
  return (
    <div className="grid grid-cols-3 gap-3 text-xs">
      <div>
        <div className="text-[10px] text-white/30 uppercase tracking-wider mb-1.5">Max Leads</div>
        <input
          type="number" min={1} max={25}
          value={settings.max_leads}
          onChange={e => onChange({ ...settings, max_leads: Number(e.target.value) })}
          className="w-full px-3 py-1.5 bg-white/[0.05] border border-white/[0.08] rounded-lg
                     text-white outline-none focus:border-jarvis-blue/40 text-xs"
        />
      </div>
      <div>
        <div className="text-[10px] text-white/30 uppercase tracking-wider mb-1.5">Min Score</div>
        <input
          type="number" min={0} max={100}
          value={settings.min_score}
          onChange={e => onChange({ ...settings, min_score: Number(e.target.value) })}
          className="w-full px-3 py-1.5 bg-white/[0.05] border border-white/[0.08] rounded-lg
                     text-white outline-none focus:border-jarvis-blue/40 text-xs"
        />
      </div>
      <div>
        <div className="text-[10px] text-white/30 uppercase tracking-wider mb-1.5">Tone</div>
        <select
          value={settings.tone}
          onChange={e => onChange({ ...settings, tone: e.target.value })}
          className="w-full px-3 py-1.5 bg-white/[0.05] border border-white/[0.08] rounded-lg
                     text-white outline-none focus:border-jarvis-blue/40 text-xs"
        >
          <option value="professional">Professional</option>
          <option value="warm">Warm</option>
          <option value="direct">Direct</option>
        </select>
      </div>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function AutopilotDashboard() {
  const [status, setStatus]       = useState(null)
  const [drafts, setDrafts]       = useState([])
  const [loading, setLoading]     = useState(true)
  const [igniting, setIgniting]   = useState(false)
  const [approving, setApproving] = useState(null)
  const [bulkSending, setBulkSending] = useState(false)
  const [clearing, setClearing]   = useState(false)
  const [errorMsg, setErrorMsg]   = useState('')
  const [successMsg, setSuccessMsg] = useState('')
  const [showSettings, setShowSettings] = useState(false)
  const [modalDraft, setModalDraft] = useState(null)
  const [filter, setFilter]       = useState('pending') // pending | all

  const [igniteSettings, setIgniteSettings] = useState({
    max_leads: 10,
    min_score: 55,
    tone: 'professional',
  })

  useEffect(() => {
    loadAll()
    const t = setInterval(loadStatus, 30_000)
    return () => clearInterval(t)
  }, [])

  async function loadAll() {
    setLoading(true)
    await Promise.all([loadStatus(), loadDrafts()])
    setLoading(false)
  }

  async function loadStatus() {
    try {
      const r = await api.get('/api/v1/autopilot/status')
      setStatus(r.data)
    } catch { /* ignore */ }
  }

  async function loadDrafts() {
    try {
      const r = await api.get('/api/v1/autopilot/all')
      setDrafts(r.data?.drafts || [])
    } catch {
      setDrafts([])
    }
  }

  function flash(msg, isError = false) {
    if (isError) {
      setErrorMsg(msg)
      setTimeout(() => setErrorMsg(''), 5000)
    } else {
      setSuccessMsg(msg)
      setTimeout(() => setSuccessMsg(''), 4000)
    }
  }

  async function handleIgnite() {
    setIgniting(true)
    setErrorMsg('')
    try {
      const r = await api.post('/api/v1/autopilot/ignite', igniteSettings)
      flash(`Autopilot composed ${r.data.composed} email${r.data.composed !== 1 ? 's' : ''}`)
      await loadAll()
    } catch (err) {
      flash(err?.response?.data?.detail || err.message || 'Ignite failed', true)
    } finally {
      setIgniting(false)
    }
  }

  async function handleApprove(draftId) {
    setApproving(draftId)
    try {
      const r = await api.post(`/api/v1/autopilot/approve/${draftId}`)
      flash(`Email sent to ${r.data.to}`)
      await loadDrafts()
      await loadStatus()
      setModalDraft(null)
    } catch (err) {
      flash(err?.response?.data?.detail || err.message || 'Send failed', true)
    } finally {
      setApproving(null)
    }
  }

  async function handleReject(draftId) {
    try {
      await api.post(`/api/v1/autopilot/reject/${draftId}`)
      await loadDrafts()
      setModalDraft(null)
    } catch (err) {
      flash(err?.response?.data?.detail || err.message || 'Reject failed', true)
    }
  }

  async function handleEdit(draftId, subject, body) {
    try {
      const r = await api.patch(`/api/v1/autopilot/draft/${draftId}`, { subject, body })
      setDrafts(prev => prev.map(d => d.id === draftId ? r.data.draft : d))
      setModalDraft(r.data.draft)
    } catch (err) {
      flash(err?.response?.data?.detail || err.message || 'Edit failed', true)
    }
  }

  async function handleApproveAll() {
    setBulkSending(true)
    try {
      const r = await api.post('/api/v1/autopilot/approve-all')
      flash(`Sent ${r.data.sent} email${r.data.sent !== 1 ? 's' : ''}${r.data.failed ? ` · ${r.data.failed} failed` : ''}`)
      await loadAll()
    } catch (err) {
      flash(err?.response?.data?.detail || err.message || 'Bulk send failed', true)
    } finally {
      setBulkSending(false)
    }
  }

  async function handleClear() {
    setClearing(true)
    try {
      const r = await api.delete('/api/v1/autopilot/clear')
      flash(`Cleared ${r.data.cleared} actioned draft${r.data.cleared !== 1 ? 's' : ''}`)
      await loadDrafts()
    } catch (err) {
      flash(err?.response?.data?.detail || err.message || 'Clear failed', true)
    } finally {
      setClearing(false)
    }
  }

  const displayDrafts = filter === 'pending'
    ? drafts.filter(d => d.status === 'pending')
    : drafts

  const pendingCount  = drafts.filter(d => d.status === 'pending').length
  const sentCount     = drafts.filter(d => d.status === 'sent').length
  const rejectedCount = drafts.filter(d => d.status === 'rejected').length

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-white/[0.06] flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-jarvis-blue/25 to-emerald-500/15
                          border border-jarvis-blue/30 flex items-center justify-center">
            <Cpu size={16} className="text-jarvis-blue" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-white">JARVIS AUTOPILOT</h2>
            <p className="text-[11px] text-white/40">Autonomous Outreach Pipeline</p>
          </div>
          {status?.last_run && (
            <div className="flex items-center gap-1.5 text-[11px] text-white/30 ml-3">
              <Clock size={11} />
              Last run: {new Date(status.last_run).toLocaleString()}
            </div>
          )}
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowSettings(!showSettings)}
            className={`p-2 rounded-lg border transition-all
              ${showSettings
                ? 'border-jarvis-blue/30 bg-jarvis-blue/10 text-jarvis-blue'
                : 'border-white/[0.08] text-white/40 hover:text-white/70'}`}
          >
            <Settings size={14} />
          </button>
          <button
            onClick={loadAll}
            className="p-2 rounded-lg border border-white/[0.08] text-white/40 hover:text-white/70 transition-all"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          </button>
          <motion.button
            whileTap={{ scale: 0.97 }}
            onClick={handleIgnite}
            disabled={igniting}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold border
              transition-all
              ${igniting
                ? 'opacity-60 cursor-wait border-jarvis-blue/20 text-jarvis-blue/60 bg-jarvis-blue/5'
                : 'border-jarvis-blue/30 bg-jarvis-blue/15 text-white hover:bg-jarvis-blue/25'}`}
          >
            {igniting ? <Loader size={14} className="animate-spin" /> : <Play size={14} />}
            {igniting ? 'Composing…' : 'Ignite Cycle'}
          </motion.button>
        </div>
      </div>

      {/* Settings panel */}
      <AnimatePresence>
        {showSettings && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="border-b border-white/[0.06] overflow-hidden"
          >
            <div className="px-6 py-4 bg-white/[0.01]">
              <div className="text-[10px] text-white/30 uppercase tracking-wider mb-3">Cycle Settings</div>
              <IgnitePanel settings={igniteSettings} onChange={setIgniteSettings} />
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Flash messages */}
      <AnimatePresence>
        {(errorMsg || successMsg) && (
          <motion.div
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className={`mx-6 mt-3 flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm border
              ${errorMsg
                ? 'bg-red-500/10 border-red-500/20 text-red-400'
                : 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'}`}
          >
            {errorMsg ? <AlertCircle size={14} /> : <CheckCircle size={14} />}
            {errorMsg || successMsg}
          </motion.div>
        )}
      </AnimatePresence>

      <div className="flex-1 overflow-y-auto no-scrollbar p-6 space-y-5">
        {/* Stats row */}
        <div className="flex gap-3 flex-wrap">
          <StatCard label="Pending" value={pendingCount}          icon={Clock}       color="text-amber-400" />
          <StatCard label="Sent"    value={sentCount}             icon={Send}        color="text-emerald-400" />
          <StatCard label="Skipped" value={rejectedCount}         icon={XCircle}     color="text-red-400/70" />
          <StatCard label="All-Time Sent" value={status?.total_sent_all_time || 0} icon={TrendingUp} color="text-jarvis-blue" />
        </div>

        {/* Controls row */}
        <div className="flex items-center justify-between flex-wrap gap-2">
          {/* Filter tabs */}
          <div className="flex gap-1 bg-white/[0.03] rounded-lg p-1 border border-white/[0.06]">
            {[
              { value: 'pending', label: `Pending (${pendingCount})` },
              { value: 'all',     label: `All (${drafts.length})` },
            ].map(tab => (
              <button
                key={tab.value}
                onClick={() => setFilter(tab.value)}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all
                  ${filter === tab.value
                    ? 'bg-white/[0.08] text-white'
                    : 'text-white/40 hover:text-white/70'}`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2">
            {pendingCount > 1 && (
              <button
                onClick={handleApproveAll}
                disabled={bulkSending}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border
                           border-emerald-500/25 bg-emerald-500/10 text-emerald-400
                           hover:bg-emerald-500/20 disabled:opacity-50 transition-all"
              >
                {bulkSending ? <Loader size={11} className="animate-spin" /> : <CheckCircle size={11} />}
                Send All ({pendingCount})
              </button>
            )}
            {drafts.some(d => d.status !== 'pending') && (
              <button
                onClick={handleClear}
                disabled={clearing}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs border
                           border-white/[0.06] text-white/30 hover:text-white/60 transition-all"
              >
                {clearing ? <Loader size={11} className="animate-spin" /> : <Trash2 size={11} />}
                Clear Actioned
              </button>
            )}
          </div>
        </div>

        {/* Drafts grid */}
        {loading ? (
          <div className="flex items-center justify-center py-16 text-white/30">
            <Loader size={20} className="animate-spin mr-2" />
            <span className="text-sm">Loading pipeline…</span>
          </div>
        ) : displayDrafts.length === 0 ? (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex flex-col items-center justify-center py-16 text-white/25"
          >
            <Cpu size={40} className="mb-4 opacity-30" />
            <p className="text-sm font-medium">
              {filter === 'pending' ? 'No pending drafts' : 'No drafts yet'}
            </p>
            <p className="text-xs mt-1 opacity-70">
              {filter === 'pending'
                ? 'Press Ignite Cycle to compose emails for your top leads'
                : 'Run a cycle to generate your first batch'}
            </p>
          </motion.div>
        ) : (
          <motion.div layout className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            <AnimatePresence mode="popLayout">
              {displayDrafts.map(draft => (
                <DraftCard
                  key={draft.id}
                  draft={draft}
                  onApprove={handleApprove}
                  onReject={handleReject}
                  onViewDetail={setModalDraft}
                  approving={approving}
                />
              ))}
            </AnimatePresence>
          </motion.div>
        )}
      </div>

      {/* Detail modal */}
      <AnimatePresence>
        {modalDraft && (
          <DraftModal
            draft={modalDraft}
            onClose={() => setModalDraft(null)}
            onApprove={handleApprove}
            onReject={handleReject}
            onEdit={handleEdit}
            loading={approving === modalDraft?.id}
          />
        )}
      </AnimatePresence>
    </div>
  )
}
