import React, { useCallback, useEffect, useState } from 'react'
import { CheckCircle2, ChevronDown, ChevronUp, FileText, Loader2, MailCheck, RefreshCw, Send, Sparkles } from 'lucide-react'
import api from '../../services/api'
import useJarvisStore from '../../store/useJarvisStore'

const DEFAULT_TENANT = '794d9b02-2dd6-49f0-b5c1-9f7c0b3af4b1'

const SERVICE_TYPES = [
  'AI Automation & Workflow',
  'Cloud Infrastructure & DevOps',
  'Lead Generation & Outreach',
  'CRM Architecture & Operations',
  'Web Application Development',
  'Cybersecurity & Compliance',
  'Revenue Operations & Analytics',
  'Executive AI Automation',
]

const PROPOSAL_STYLES = [
  { value: 'standard',     label: 'Standard' },
  { value: 'case_study',   label: 'Case Study' },
  { value: 'short_urgent', label: 'Short & Urgent' },
  { value: 'social_proof', label: 'Social Proof' },
]

const STATUS_CONFIG = {
  draft:       { label: 'Draft',       cls: 'border-gray-500/30 bg-gray-500/10 text-gray-300' },
  sent:        { label: 'Sent',        cls: 'border-blue-500/30 bg-blue-500/10 text-blue-300' },
  accepted:    { label: 'Accepted',    cls: 'border-green-500/30 bg-green-500/10 text-green-300' },
  declined:    { label: 'Declined',    cls: 'border-red-500/30 bg-red-500/10 text-red-400' },
  negotiating: { label: 'Negotiating', cls: 'border-yellow-500/30 bg-yellow-500/10 text-yellow-300' },
}

function StatusBadge({ status }) {
  const cfg = STATUS_CONFIG[status?.toLowerCase()] || STATUS_CONFIG.draft
  return (
    <span className={`inline-flex rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${cfg.cls}`}>
      {cfg.label}
    </span>
  )
}

function money(v) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0 }).format(v || 0)
}

function fmtDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

const PACKAGE_TIERS = ['starter', 'growth', 'enterprise', 'custom']

function ConvertToClientModal({ proposal, onClose, onSuccess }) {
  const [form, setForm] = useState({
    company_name: proposal.client_company || proposal.client_name || '',
    contact_name: proposal.client_name || '',
    email: proposal.client_email || '',
    package_tier: 'growth',
    mrr_usd: proposal.pricing?.monthly_retainer || '',
  })
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)
  const set = (k) => (v) => setForm(f => ({ ...f, [k]: v }))

  async function submit(e) {
    e.preventDefault()
    setBusy(true)
    setErr(null)
    try {
      const res = await api.post('/api/v1/clients', {
        company_name: form.company_name.trim(),
        contact_name: form.contact_name.trim() || undefined,
        email: form.email.trim() || undefined,
        package_tier: form.package_tier || undefined,
        mrr_usd: parseFloat(form.mrr_usd) || 0,
        status: 'active',
      })
      onSuccess(res.data.client)
    } catch (error) {
      setErr(error.response?.data?.detail || error.message || 'Client creation failed')
    }
    setBusy(false)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
         onClick={onClose}>
      <div className="w-full max-w-md rounded-2xl border border-white/10 bg-[#0c1418] p-6 shadow-2xl"
           onClick={e => e.stopPropagation()}>
        <h2 className="text-lg font-bold text-white mb-1">Onboard as Client</h2>
        <p className="text-xs text-gray-500 mb-5">
          Convert this accepted proposal into a live client record. MRR posts immediately to the Revenue Dashboard.
        </p>
        {err && (
          <div className="mb-4 rounded-lg border border-red-400/20 bg-red-400/10 p-3 text-sm text-red-200">{err}</div>
        )}
        <form onSubmit={submit} className="space-y-3">
          <div className="space-y-1">
            <label className="text-xs text-gray-400">Company Name *</label>
            <input required value={form.company_name} onChange={e => set('company_name')(e.target.value)}
              className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-white outline-none focus:border-jarvis-cyan/60" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-xs text-gray-400">Contact Name</label>
              <input value={form.contact_name} onChange={e => set('contact_name')(e.target.value)}
                className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-white outline-none focus:border-jarvis-cyan/60" />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-gray-400">Email</label>
              <input type="email" value={form.email} onChange={e => set('email')(e.target.value)}
                className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-white outline-none focus:border-jarvis-cyan/60" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-xs text-gray-400">Package Tier</label>
              <select value={form.package_tier} onChange={e => set('package_tier')(e.target.value)}
                className="w-full rounded-xl border border-white/10 bg-[#0f1a1e] px-4 py-2.5 text-sm text-white outline-none focus:border-jarvis-cyan/60">
                {PACKAGE_TIERS.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-xs text-gray-400">Monthly MRR ($)</label>
              <input type="number" min="0" value={form.mrr_usd} onChange={e => set('mrr_usd')(e.target.value)}
                placeholder="3500"
                className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-white outline-none focus:border-jarvis-cyan/60" />
            </div>
          </div>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose}
              className="flex-1 rounded-xl border border-white/10 py-2 text-sm text-gray-400 hover:text-white transition-colors">
              Cancel
            </button>
            <button type="submit" disabled={busy || !form.company_name.trim()}
              className="flex-1 btn-primary inline-flex items-center justify-center gap-2">
              {busy
                ? <><Loader2 size={14} className="animate-spin" /> Creating…</>
                : <><CheckCircle2 size={14} /> Activate Client</>
              }
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function Field({ label, children }) {
  return (
    <div className="space-y-1.5">
      <label className="block text-xs font-medium text-gray-400">{label}</label>
      {children}
    </div>
  )
}

function TextInput({ value, onChange, placeholder, type = 'text' }) {
  return (
    <input
      type={type}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-white outline-none placeholder:text-gray-600 focus:border-jarvis-cyan/60 transition-colors"
    />
  )
}

function SelectInput({ value, onChange, children }) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="w-full rounded-xl border border-white/10 bg-[#0f1a1e] px-4 py-2.5 text-sm text-white outline-none focus:border-jarvis-cyan/60 transition-colors"
    >
      {children}
    </select>
  )
}

function ProposalCard({ proposal, onRefresh, onConvert }) {
  const [expanded, setExpanded] = useState(false)
  const [busy, setBusy] = useState(false)
  const [sending, setSending] = useState(false)
  const [approving, setApproving] = useState(false)
  const [sendMsg, setSendMsg] = useState(null)
  const pricing = proposal.pricing || {}
  const monthly = pricing.monthly_retainer || 0

  const updateStatus = async (status) => {
    setBusy(true)
    try {
      await api.post(`/api/v1/governance/proposals/${proposal.id}/status`, { status })
      await onRefresh()
    } catch (err) {
      console.error('Status update failed:', err)
    }
    setBusy(false)
  }

  const approveProposal = async () => {
    setApproving(true)
    setSendMsg(null)
    try {
      await api.post(`/api/v1/proposals/${proposal.id}/approve`, { tenant_id: DEFAULT_TENANT })
      setSendMsg('approved')
      await onRefresh()
    } catch (err) {
      setSendMsg(err.response?.data?.detail || 'Approval failed')
    }
    setApproving(false)
  }

  const sendEmail = async () => {
    setSending(true)
    setSendMsg(null)
    try {
      await api.post(`/api/v1/proposals/${proposal.id}/send`, { tenant_id: DEFAULT_TENANT })
      setSendMsg('sent')
      await onRefresh()
    } catch (err) {
      setSendMsg(err.response?.data?.detail || 'Email send failed')
    }
    setSending(false)
  }

  return (
    <div className="rounded-xl border border-white/10 bg-white/5 overflow-hidden">
      <div
        className="flex items-start justify-between gap-4 p-4 cursor-pointer hover:bg-white/5 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <StatusBadge status={proposal.status} />
            {proposal.ai_generated && (
              <span className="inline-flex items-center gap-1 text-[11px] text-jarvis-cyan/70">
                <Sparkles size={10} /> AI
              </span>
            )}
          </div>
          <h3 className="mt-2 font-semibold text-white text-sm leading-snug">
            {proposal.title || `${proposal.service_type} — ${proposal.client_company || proposal.client_name}`}
          </h3>
          <div className="mt-1 flex items-center gap-2 text-xs text-gray-500 flex-wrap">
            <span>{proposal.client_company || proposal.client_name || '—'}</span>
            {proposal.service_type && <span>· {proposal.service_type}</span>}
            <span>· {fmtDate(proposal.created_at)}</span>
          </div>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          {monthly > 0 && (
            <div className="text-right">
              <p className="text-[10px] text-gray-500">Monthly</p>
              <p className="text-sm font-bold text-jarvis-gold">{money(monthly)}</p>
            </div>
          )}
          {expanded ? <ChevronUp size={15} className="text-gray-500" /> : <ChevronDown size={15} className="text-gray-500" />}
        </div>
      </div>

      {expanded && (
        <div className="border-t border-white/10 p-4 space-y-4">
          {Object.keys(pricing).length > 0 && (
            <div className="flex flex-wrap gap-2">
              {pricing.setup_fee > 0 && (
                <div className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-xs">
                  <p className="text-gray-500">Setup</p>
                  <p className="font-semibold text-white mt-0.5">{money(pricing.setup_fee)}</p>
                </div>
              )}
              {pricing.monthly_retainer > 0 && (
                <div className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-xs">
                  <p className="text-gray-500">Monthly</p>
                  <p className="font-semibold text-jarvis-gold mt-0.5">{money(pricing.monthly_retainer)}/mo</p>
                </div>
              )}
              {pricing.one_time > 0 && (
                <div className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-xs">
                  <p className="text-gray-500">One-time</p>
                  <p className="font-semibold text-white mt-0.5">{money(pricing.one_time)}</p>
                </div>
              )}
              {pricing.notes && (
                <div className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-xs flex-1">
                  <p className="text-gray-500">Pricing notes</p>
                  <p className="text-gray-300 mt-0.5">{pricing.notes}</p>
                </div>
              )}
            </div>
          )}

          {proposal.content && (
            <div>
              <p className="text-[10px] font-semibold text-gray-500 mb-2 uppercase tracking-wider">Proposal Content</p>
              <div className="rounded-lg border border-white/10 bg-black/20 p-4 text-sm text-gray-300 leading-relaxed whitespace-pre-wrap max-h-80 overflow-y-auto">
                {proposal.content}
              </div>
            </div>
          )}

          {sendMsg && sendMsg !== 'sent' && sendMsg !== 'approved' && (
            <p className="text-xs text-red-400 px-1">{sendMsg}</p>
          )}
          {sendMsg === 'sent' && (
            <p className="text-xs text-green-400 flex items-center gap-1 px-1"><MailCheck size={11} /> Email delivered</p>
          )}
          {sendMsg === 'approved' && (
            <p className="text-xs text-jarvis-gold flex items-center gap-1 px-1">✓ Captain approved — ready to send</p>
          )}
          <div className="flex items-center gap-2 flex-wrap">
            {proposal.status === 'draft' && (
              <>
                <button
                  type="button"
                  disabled={approving || busy || sending}
                  onClick={approveProposal}
                  className="inline-flex items-center gap-1.5 rounded border border-jarvis-gold/40 bg-jarvis-gold/10 px-3 py-1.5 text-xs font-semibold text-jarvis-gold hover:bg-jarvis-gold/20 disabled:opacity-40 transition-colors"
                >
                  {approving ? <Loader2 size={11} className="animate-spin" /> : null}
                  Captain Approve
                </button>
                <button
                  type="button"
                  disabled={sending || busy || approving}
                  onClick={sendEmail}
                  className="inline-flex items-center gap-1.5 rounded border border-jarvis-cyan/40 bg-jarvis-cyan/10 px-3 py-1.5 text-xs font-semibold text-jarvis-cyan hover:bg-jarvis-cyan/20 disabled:opacity-40 transition-colors"
                >
                  {sending ? <Loader2 size={11} className="animate-spin" /> : <MailCheck size={11} />}
                  Send via Email
                </button>
                <button
                  type="button"
                  disabled={busy || sending || approving}
                  onClick={() => updateStatus('sent')}
                  className="inline-flex items-center gap-1.5 rounded border border-blue-500/40 bg-blue-500/10 px-3 py-1.5 text-xs font-medium text-blue-300 hover:bg-blue-500/20 disabled:opacity-40 transition-colors"
                >
                  {busy ? <Loader2 size={11} className="animate-spin" /> : <Send size={11} />}
                  Mark Sent
                </button>
              </>
            )}
            {proposal.status === 'sent' && (
              <>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => updateStatus('accepted')}
                  className="inline-flex items-center gap-1.5 rounded border border-green-500/40 bg-green-500/10 px-3 py-1.5 text-xs font-medium text-green-300 hover:bg-green-500/20 disabled:opacity-40 transition-colors"
                >
                  {busy ? <Loader2 size={11} className="animate-spin" /> : null}
                  Won
                </button>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => updateStatus('negotiating')}
                  className="inline-flex items-center gap-1.5 rounded border border-yellow-500/40 bg-yellow-500/10 px-3 py-1.5 text-xs font-medium text-yellow-300 hover:bg-yellow-500/20 disabled:opacity-40 transition-colors"
                >
                  Negotiating
                </button>
              </>
            )}
            {proposal.status === 'accepted' && onConvert && (
              <button
                type="button"
                onClick={() => onConvert(proposal)}
                className="inline-flex items-center gap-1.5 rounded border border-jarvis-cyan/40 bg-jarvis-cyan/10 px-3 py-1.5 text-xs font-semibold text-jarvis-cyan hover:bg-jarvis-cyan/20 transition-colors"
              >
                <CheckCircle2 size={11} />
                Onboard as Client →
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default function ProposalsView() {
  const { proposalPrefill, setProposalPrefill } = useJarvisStore()
  const [proposals, setProposals] = useState([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [estimating, setEstimating] = useState(false)
  const [generatedProposal, setGeneratedProposal] = useState(null)
  const [error, setError] = useState(null)
  const [convertTarget, setConvertTarget] = useState(null)
  const [clientCreated, setClientCreated] = useState(null)

  const [form, setForm] = useState({
    client_name: '',
    client_email: '',
    client_company: '',
    service_type: SERVICE_TYPES[0],
    context: '',
    style: 'standard',
    setup_fee: '',
    monthly_retainer: '',
    pricing_notes: '',
  })

  const setField = (key) => (val) => setForm(prev => ({ ...prev, [key]: val }))

  useEffect(() => {
    if (proposalPrefill) {
      setForm(prev => ({
        ...prev,
        client_name: proposalPrefill.client_name || prev.client_name,
        client_email: proposalPrefill.client_email || prev.client_email,
        client_company: proposalPrefill.client_company || prev.client_company,
        service_type: proposalPrefill.service_type || prev.service_type,
        context: proposalPrefill.context || prev.context,
      }))
      setProposalPrefill(null)
    }
  }, [proposalPrefill, setProposalPrefill])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await api.get('/api/v1/governance/proposals')
      setProposals(res.data?.proposals || [])
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    }
    setLoading(false)
  }, [])

  useEffect(() => { load() }, [load])

  const generate = async (e) => {
    e.preventDefault()
    if (!form.client_name.trim()) return
    setGenerating(true)
    setError(null)
    setGeneratedProposal(null)
    try {
      const pricing = {}
      if (form.setup_fee) pricing.setup_fee = parseFloat(form.setup_fee)
      if (form.monthly_retainer) pricing.monthly_retainer = parseFloat(form.monthly_retainer)
      if (form.pricing_notes) pricing.notes = form.pricing_notes

      const res = await api.post('/api/v1/governance/proposals/generate', {
        client_name: form.client_name,
        client_email: form.client_email,
        client_company: form.client_company || form.client_name,
        service_type: form.service_type,
        context: form.context,
        style: form.style,
        pricing,
      })
      setGeneratedProposal(res.data?.proposal || null)
      await load()
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Proposal generation failed')
    }
    setGenerating(false)
  }

  const aiEstimate = async () => {
    if (!form.client_company && !form.client_name) return
    setEstimating(true)
    try {
      const res = await api.post('/api/v1/pricing/estimate', {
        company_name: form.client_company || form.client_name,
        services_needed: form.service_type ? [form.service_type] : [],
        notes: form.context || undefined,
      })
      const d = res.data
      const midRetainer = Math.round(((d.retainer?.monthly_min || 0) + (d.retainer?.monthly_max || 0)) / 2)
      const firstPkg = d.packages?.[0]?.price || 0
      setField('monthly_retainer')(String(midRetainer || ''))
      setField('setup_fee')(String(firstPkg || ''))
      if (d.positioning && !form.context) setField('context')(d.positioning)
    } catch (err) {
      console.error('Pricing estimate failed:', err)
    }
    setEstimating(false)
  }

  const accepted = proposals.filter(p => p.status === 'accepted').length
  const sent = proposals.filter(p => p.status === 'sent').length
  const totalMRR = proposals.filter(p => p.status === 'accepted').reduce((s, p) => s + (p.pricing?.monthly_retainer || 0), 0)

  return (
    <div className="min-h-[calc(100vh-3.5rem)] p-6 pb-10 space-y-6">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.22em] text-jarvis-cyan/70">Revenue</p>
          <h1 className="mt-2 text-3xl font-bold text-white">Proposal Center</h1>
          <p className="mt-2 max-w-2xl text-sm text-gray-400">
            AI-generated client proposals — professional, tailored to service type, and ready to send.
          </p>
        </div>
        <button type="button" onClick={load} disabled={loading} className="btn-primary inline-flex items-center justify-center gap-2">
          {loading ? <Loader2 size={15} className="animate-spin" /> : <RefreshCw size={15} />}
          Refresh
        </button>
      </header>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {[
          { label: 'Total Proposals', value: proposals.length, tone: 'text-jarvis-cyan' },
          { label: 'Sent to Clients', value: sent, tone: 'text-jarvis-gold' },
          { label: 'Won', value: accepted, tone: 'text-green-300' },
          { label: 'Accepted MRR', value: totalMRR > 0 ? `$${(totalMRR / 1000).toFixed(1)}K/mo` : '$0/mo', tone: 'text-purple-300' },
        ].map(m => (
          <div key={m.label} className="glass p-5">
            <p className="text-xs text-gray-400">{m.label}</p>
            <p className={`mt-2 text-2xl font-bold ${m.tone}`}>{m.value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        {/* Generator form */}
        <section className="glass p-5">
          <div className="flex items-center gap-2 mb-5">
            <Sparkles size={15} className="text-jarvis-cyan" />
            <h2 className="text-sm font-semibold text-white">Generate AI Proposal</h2>
          </div>

          {error && (
            <div className="mb-4 rounded-lg border border-red-400/20 bg-red-400/10 p-3 text-sm text-red-200">{error}</div>
          )}

          <form onSubmit={generate} className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <Field label="Client name *">
                <TextInput value={form.client_name} onChange={setField('client_name')} placeholder="John Smith" />
              </Field>
              <Field label="Company">
                <TextInput value={form.client_company} onChange={setField('client_company')} placeholder="Acme Corp" />
              </Field>
            </div>
            <Field label="Email">
              <TextInput type="email" value={form.client_email} onChange={setField('client_email')} placeholder="john@acme.com" />
            </Field>
            <Field label="Service *">
              <SelectInput value={form.service_type} onChange={setField('service_type')}>
                {SERVICE_TYPES.map(s => <option key={s} value={s}>{s}</option>)}
              </SelectInput>
            </Field>
            <Field label="Context">
              <textarea
                value={form.context}
                onChange={(e) => setField('context')(e.target.value)}
                placeholder="Client pain points, timeline, goals, or any specific context…"
                rows={3}
                className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none placeholder:text-gray-600 focus:border-jarvis-cyan/60 resize-none transition-colors"
              />
            </Field>
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-medium text-gray-400">Pricing</span>
              <button
                type="button"
                disabled={estimating || (!form.client_company && !form.client_name)}
                onClick={aiEstimate}
                className="inline-flex items-center gap-1 text-[11px] font-semibold text-jarvis-cyan hover:text-jarvis-cyan/80 disabled:opacity-40 transition-colors"
              >
                {estimating ? <Loader2 size={10} className="animate-spin" /> : <Sparkles size={10} />}
                AI Estimate
              </button>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <Field label="Setup fee ($)">
                <TextInput type="number" value={form.setup_fee} onChange={setField('setup_fee')} placeholder="2000" />
              </Field>
              <Field label="Monthly ($)">
                <TextInput type="number" value={form.monthly_retainer} onChange={setField('monthly_retainer')} placeholder="3500" />
              </Field>
              <Field label="Style">
                <SelectInput value={form.style} onChange={setField('style')}>
                  {PROPOSAL_STYLES.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
                </SelectInput>
              </Field>
            </div>
            <button
              type="submit"
              disabled={generating || !form.client_name.trim()}
              className="btn-primary w-full inline-flex items-center justify-center gap-2"
            >
              {generating
                ? <><Loader2 size={15} className="animate-spin" /> Generating…</>
                : <><Sparkles size={15} /> Generate Proposal</>
              }
            </button>
          </form>

          {generatedProposal && (
            <div className="mt-4 rounded-xl border border-jarvis-cyan/30 bg-jarvis-cyan/5 p-4">
              <p className="text-xs font-semibold text-jarvis-cyan">Proposal generated</p>
              <p className="text-xs text-gray-400 mt-0.5">{generatedProposal.title}</p>
              <p className="text-xs text-gray-600 mt-1">See the list to the right to review, expand, and send.</p>
            </div>
          )}
        </section>

        {/* Proposals list */}
        <section className="space-y-3">
          <div className="flex items-center gap-2">
            <FileText size={14} className="text-gray-400" />
            <h2 className="text-sm font-semibold text-white">All Proposals</h2>
            <span className="text-xs text-gray-600">{proposals.length} total</span>
          </div>

          {loading ? (
            <div className="glass p-10 flex items-center justify-center text-gray-500">
              <Loader2 size={18} className="animate-spin mr-2" /> Loading…
            </div>
          ) : proposals.length === 0 ? (
            <div className="glass p-10 flex flex-col items-center justify-center text-center">
              <FileText size={32} className="mb-3 opacity-20 text-gray-400" />
              <p className="text-sm text-gray-400">No proposals yet</p>
              <p className="text-xs mt-1 text-gray-600">Use the generator to create your first AI-written proposal.</p>
            </div>
          ) : (
            <div className="space-y-3 max-h-[620px] overflow-y-auto pr-1">
              {proposals.map(p => (
                <ProposalCard key={p.id} proposal={p} onRefresh={load} onConvert={setConvertTarget} />
              ))}
            </div>
          )}
        </section>
      </div>

      {convertTarget && (
        <ConvertToClientModal
          proposal={convertTarget}
          onClose={() => setConvertTarget(null)}
          onSuccess={(client) => {
            setConvertTarget(null)
            setClientCreated(client)
          }}
        />
      )}

      {clientCreated && (
        <div className="fixed bottom-6 right-6 z-50 rounded-xl border border-green-400/30 bg-[#0c1418] p-4 shadow-2xl max-w-sm">
          <div className="flex items-center gap-3 mb-2">
            <CheckCircle2 size={16} className="text-green-400 shrink-0" />
            <p className="text-sm font-semibold text-white">Client Activated</p>
            <button onClick={() => setClientCreated(null)} className="ml-auto text-xs text-gray-500 hover:text-white transition-colors">✕</button>
          </div>
          <p className="text-xs text-gray-400">
            <span className="text-white font-medium">{clientCreated.company_name}</span> is now live in the Revenue Dashboard.
          </p>
          {clientCreated.mrr_usd > 0 && (
            <p className="text-xs text-jarvis-gold mt-1">+${clientCreated.mrr_usd.toLocaleString()}/mo MRR added.</p>
          )}
        </div>
      )}
    </div>
  )
}
