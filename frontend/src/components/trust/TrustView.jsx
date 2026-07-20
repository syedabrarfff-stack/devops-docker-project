import React, { useCallback, useEffect, useState } from 'react'
import { Shield, Search, Loader2, RefreshCw, Gift, TrendingUp, FileText } from 'lucide-react'
import api from '../../services/api'

const STATUS_FILTERS = ['all', 'pending', 'sent', 'accepted', 'declined']

function StatusBadge({ status }) {
  const cfg = {
    pending:  'border-jarvis-gold/30 bg-jarvis-gold/10 text-jarvis-gold',
    sent:     'border-jarvis-cyan/30 bg-jarvis-cyan/10 text-jarvis-cyan',
    accepted: 'border-green-500/30 bg-green-500/10 text-green-300',
    declined: 'border-red-500/30 bg-red-500/10 text-red-300',
  }[status] || 'border-gray-500/30 bg-gray-500/10 text-gray-300'
  return <span className={`inline-flex rounded-full border px-2.5 py-0.5 text-[11px] font-semibold tracking-wide ${cfg}`}>{status || 'unknown'}</span>
}

function ReferralCard({ r }) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/5 p-4">
      <div className="flex items-center justify-between gap-3">
        <span className="text-sm font-medium text-white truncate">{r.request_type || 'referral'}</span>
        <StatusBadge status={r.status} />
      </div>
      {r.content && <p className="mt-2 text-xs text-gray-400 whitespace-pre-wrap">{r.content}</p>}
      {r.response && (
        <div className="mt-2 rounded-lg border border-white/10 bg-white/[0.03] p-2">
          <p className="text-[11px] text-gray-500 mb-1">Response</p>
          <p className="text-xs text-gray-300 whitespace-pre-wrap">{r.response}</p>
        </div>
      )}
      <div className="mt-2 flex gap-4 text-[11px] text-gray-500">
        <span>Created {r.created_at ? new Date(r.created_at).toLocaleDateString() : '—'}</span>
        {r.sent_at && <span>Sent {new Date(r.sent_at).toLocaleDateString()}</span>}
        {r.responded_at && <span>Responded {new Date(r.responded_at).toLocaleDateString()}</span>}
      </div>
    </div>
  )
}

export default function TrustView() {
  const [referrals, setReferrals] = useState([])
  const [statusFilter, setStatusFilter] = useState('all')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [leadId, setLeadId] = useState('')
  const [score, setScore] = useState(null)
  const [briefs, setBriefs] = useState(null)
  const [lookupLoading, setLookupLoading] = useState(false)
  const [lookupError, setLookupError] = useState(null)

  const loadReferrals = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = statusFilter !== 'all' ? { status: statusFilter } : {}
      const res = await api.get('/api/v1/trust/referrals', { params })
      setReferrals(res.data || [])
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Failed to load referrals.')
    }
    setLoading(false)
  }, [statusFilter])

  useEffect(() => { loadReferrals() }, [loadReferrals])

  async function runLookup() {
    if (!leadId.trim()) return
    setLookupLoading(true)
    setLookupError(null)
    setScore(null)
    setBriefs(null)
    try {
      const [scoreRes, briefsRes] = await Promise.allSettled([
        api.get(`/api/v1/trust/score/${leadId.trim()}`),
        api.get(`/api/v1/trust/briefs/${leadId.trim()}`),
      ])
      if (scoreRes.status === 'fulfilled') setScore(scoreRes.value.data)
      if (briefsRes.status === 'fulfilled') setBriefs(briefsRes.value.data)
      if (scoreRes.status === 'rejected' && briefsRes.status === 'rejected') {
        setLookupError('No trust data found for this lead ID.')
      }
    } catch (e) {
      setLookupError(e.message || 'Lookup failed.')
    }
    setLookupLoading(false)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-white flex items-center gap-2">
            <Shield size={18} className="text-jarvis-cyan" /> Client Trust
          </h1>
          <p className="text-xs text-gray-500 mt-1">Trust scoring, executive briefs, and client referral requests.</p>
        </div>
        <button
          onClick={loadReferrals}
          className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-gray-300 hover:bg-white/10"
        >
          <RefreshCw size={13} /> Refresh
        </button>
      </div>

      {/* Trust score / brief lookup */}
      <div className="rounded-xl border border-white/10 bg-white/5 p-4">
        <p className="text-sm font-medium text-white mb-2 flex items-center gap-2">
          <Search size={14} className="text-gray-400" /> Look up a lead's trust score
        </p>
        <div className="flex gap-2">
          <input
            value={leadId}
            onChange={e => setLeadId(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && runLookup()}
            placeholder="Lead UUID"
            className="flex-1 rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2 text-xs text-white outline-none focus:border-jarvis-cyan/40"
          />
          <button
            onClick={runLookup}
            disabled={lookupLoading || !leadId.trim()}
            className="rounded-lg bg-jarvis-cyan/20 border border-jarvis-cyan/30 px-4 py-2 text-xs font-medium text-jarvis-cyan hover:bg-jarvis-cyan/30 disabled:opacity-40"
          >
            {lookupLoading ? <Loader2 size={13} className="animate-spin" /> : 'Look up'}
          </button>
        </div>

        {lookupError && <p className="mt-2 text-xs text-red-400">{lookupError}</p>}

        {score && (
          <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-2">
            <div className="rounded-lg border border-white/10 bg-white/[0.03] p-2">
              <p className="text-[10px] text-gray-500">Trust score</p>
              <p className="text-sm font-semibold text-white mt-0.5">{score.trust_score}</p>
            </div>
            <div className="rounded-lg border border-white/10 bg-white/[0.03] p-2">
              <p className="text-[10px] text-gray-500">Conversion prob.</p>
              <p className="text-sm font-semibold text-white mt-0.5">{score.conversion_probability}%</p>
            </div>
            <div className="rounded-lg border border-white/10 bg-white/[0.03] p-2">
              <p className="text-[10px] text-gray-500">Events</p>
              <p className="text-sm font-semibold text-white mt-0.5">{score.event_count}</p>
            </div>
            <div className="rounded-lg border border-white/10 bg-white/[0.03] p-2">
              <p className="text-[10px] text-gray-500">Proposal-ready</p>
              <p className={`text-sm font-semibold mt-0.5 ${score.ready_for_proposal ? 'text-green-400' : 'text-gray-400'}`}>
                {score.ready_for_proposal ? 'Yes' : 'Not yet'}
              </p>
            </div>
          </div>
        )}

        {briefs && briefs.length > 0 && (
          <div className="mt-3 space-y-2">
            <p className="text-xs text-gray-500 flex items-center gap-1.5"><FileText size={12} /> Executive briefs</p>
            {briefs.map(b => (
              <div key={b.id} className="rounded-lg border border-white/10 bg-white/[0.03] p-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-white">{b.company_name}</span>
                  <StatusBadge status={b.status} />
                </div>
                {b.narrative && <p className="mt-1 text-xs text-gray-400 line-clamp-3">{b.narrative}</p>}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Referrals */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <p className="text-sm font-medium text-white flex items-center gap-2">
            <Gift size={14} className="text-gray-400" /> Referral requests
          </p>
          <div className="flex gap-1.5">
            {STATUS_FILTERS.map(s => (
              <button
                key={s}
                onClick={() => setStatusFilter(s)}
                className={`rounded-full px-2.5 py-1 text-[11px] font-medium ${
                  statusFilter === s ? 'bg-jarvis-cyan/20 text-jarvis-cyan border border-jarvis-cyan/30' : 'text-gray-500 border border-white/10 hover:bg-white/5'
                }`}
              >
                {s}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <div className="flex justify-center py-10"><Loader2 size={20} className="animate-spin text-gray-500" /></div>
        ) : error ? (
          <p className="text-xs text-red-400">{error}</p>
        ) : referrals.length === 0 ? (
          <div className="rounded-xl border border-white/10 bg-white/5 p-6 text-center text-xs text-gray-500">
            No referral requests yet — generated automatically when a client is signed and healthy.
          </div>
        ) : (
          <div className="space-y-2">
            {referrals.map(r => <ReferralCard key={r.id} r={r} />)}
          </div>
        )}
      </div>
    </div>
  )
}
