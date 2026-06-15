import React, { useCallback, useEffect, useState } from 'react'
import { AlertTriangle, CheckCircle2, FileText, Loader2, Plus, RefreshCw, Send, XCircle } from 'lucide-react'
import api from '../../services/api'

const STATUS_CONFIG = {
  draft:     { label: 'Draft',     cls: 'border-gray-500/30 bg-gray-500/10 text-gray-300' },
  sent:      { label: 'Sent',      cls: 'border-blue-500/30 bg-blue-500/10 text-blue-300' },
  paid:      { label: 'Paid',      cls: 'border-green-500/30 bg-green-500/10 text-green-300' },
  overdue:   { label: 'Overdue',   cls: 'border-red-500/30 bg-red-500/10 text-red-300' },
  cancelled: { label: 'Cancelled', cls: 'border-gray-600/30 bg-gray-600/10 text-gray-500' },
}

const CLIENT_STATUS_CFG = {
  active:    { cls: 'border-green-500/30 bg-green-500/10 text-green-300',  label: 'Active' },
  paused:    { cls: 'border-jarvis-gold/30 bg-jarvis-gold/10 text-jarvis-gold', label: 'Paused' },
  churned:   { cls: 'border-red-500/30 bg-red-500/10 text-red-300',       label: 'Churned' },
  prospect:  { cls: 'border-blue-500/30 bg-blue-500/10 text-blue-300',    label: 'Prospect' },
}

function StatusBadge({ status, cfg = STATUS_CONFIG }) {
  const c = cfg[status?.toLowerCase()] || cfg.draft || { cls: 'border-gray-500/30 bg-gray-500/10 text-gray-300', label: status }
  return (
    <span className={`inline-flex rounded-full border px-2.5 py-0.5 text-[11px] font-semibold tracking-wide ${c.cls}`}>
      {c.label}
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

function MetricCard({ label, value, sub, tone = 'cyan' }) {
  const tones = { cyan: 'text-jarvis-cyan', gold: 'text-jarvis-gold', green: 'text-green-300', red: 'text-red-400', purple: 'text-purple-300' }
  return (
    <div className="glass p-5">
      <p className="text-xs text-gray-400">{label}</p>
      <p className={`mt-2 text-2xl font-bold ${tones[tone] || tones.cyan}`}>{value}</p>
      {sub && <p className="mt-1 text-xs text-gray-600">{sub}</p>}
    </div>
  )
}

const EMPTY_INVOICE = {
  client_name: '', client_email: '', client_company: '',
  items: [{ description: '', qty: 1, unit_price: 0, amount: 0 }],
  tax_rate: 0, currency: 'USD', notes: '', due_days: 14,
}

function CreateInvoiceModal({ onClose, onCreated }) {
  const [form, setForm] = useState(EMPTY_INVOICE)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const updateItem = (i, field, val) => {
    const items = form.items.map((item, idx) => {
      if (idx !== i) return item
      const next = { ...item, [field]: val }
      if (field === 'qty' || field === 'unit_price') {
        next.amount = parseFloat(next.qty || 0) * parseFloat(next.unit_price || 0)
      }
      if (field === 'amount') next.amount = parseFloat(val) || 0
      return next
    })
    setForm(f => ({ ...f, items }))
  }

  const addItem = () => setForm(f => ({ ...f, items: [...f.items, { description: '', qty: 1, unit_price: 0, amount: 0 }] }))
  const removeItem = (i) => setForm(f => ({ ...f, items: f.items.filter((_, idx) => idx !== i) }))

  const subtotal = form.items.reduce((s, it) => s + (it.amount || 0), 0)
  const total = subtotal + subtotal * (form.tax_rate || 0) / 100

  const submit = async (e) => {
    e.preventDefault()
    if (!form.client_name.trim()) return setError('Client name required')
    setLoading(true)
    setError(null)
    try {
      const payload = {
        client_name: form.client_name,
        client_email: form.client_email,
        client_company: form.client_company,
        items: form.items.map(it => ({ ...it, qty: parseFloat(it.qty), unit_price: parseFloat(it.unit_price), amount: parseFloat(it.amount) })),
        tax_rate: parseFloat(form.tax_rate) || 0,
        currency: form.currency,
        notes: form.notes,
        due_days: parseInt(form.due_days) || 14,
      }
      const r = await api.post('/api/v1/governance/invoices', payload)
      onCreated(r.data)
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    }
    setLoading(false)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4" onClick={onClose}>
      <div
        className="relative w-full max-w-2xl max-h-[90vh] overflow-auto rounded-2xl border border-white/10 bg-[#0a0f1a] p-6 shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-bold text-white">Create Invoice</h2>
          <button type="button" onClick={onClose} className="text-gray-400 hover:text-white transition-colors">
            <XCircle size={20} />
          </button>
        </div>

        <form onSubmit={submit} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-gray-400 mb-1 block">Client Name *</label>
              <input
                value={form.client_name}
                onChange={e => setForm(f => ({ ...f, client_name: e.target.value }))}
                placeholder="John Smith"
                className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white outline-none placeholder:text-gray-500 focus:border-jarvis-cyan/60"
              />
            </div>
            <div>
              <label className="text-xs text-gray-400 mb-1 block">Company</label>
              <input
                value={form.client_company}
                onChange={e => setForm(f => ({ ...f, client_company: e.target.value }))}
                placeholder="Acme Corp"
                className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white outline-none placeholder:text-gray-500 focus:border-jarvis-cyan/60"
              />
            </div>
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Client Email</label>
            <input
              type="email"
              value={form.client_email}
              onChange={e => setForm(f => ({ ...f, client_email: e.target.value }))}
              placeholder="client@company.com"
              className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white outline-none placeholder:text-gray-500 focus:border-jarvis-cyan/60"
            />
          </div>

          {/* Line items */}
          <div>
            <label className="text-xs text-gray-400 mb-2 block">Line Items</label>
            <div className="space-y-2">
              {form.items.map((item, i) => (
                <div key={i} className="grid grid-cols-12 gap-2 items-center">
                  <input
                    className="col-span-5 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white outline-none placeholder:text-gray-500 focus:border-jarvis-cyan/60"
                    placeholder="Description"
                    value={item.description}
                    onChange={e => updateItem(i, 'description', e.target.value)}
                  />
                  <input
                    className="col-span-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white outline-none focus:border-jarvis-cyan/60"
                    type="number" placeholder="Qty" min={0}
                    value={item.qty}
                    onChange={e => updateItem(i, 'qty', e.target.value)}
                  />
                  <input
                    className="col-span-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white outline-none focus:border-jarvis-cyan/60"
                    type="number" placeholder="Price" min={0}
                    value={item.unit_price}
                    onChange={e => updateItem(i, 'unit_price', e.target.value)}
                  />
                  <div className="col-span-2 text-right text-sm text-gray-300">{money(item.amount)}</div>
                  <button type="button" onClick={() => removeItem(i)} disabled={form.items.length <= 1} className="col-span-1 text-gray-600 hover:text-red-400 disabled:opacity-20 transition-colors text-center">×</button>
                </div>
              ))}
            </div>
            <button type="button" onClick={addItem} className="mt-2 text-xs text-jarvis-cyan hover:text-jarvis-cyan/80 transition-colors">
              + Add line item
            </button>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="text-xs text-gray-400 mb-1 block">Tax Rate %</label>
              <input type="number" min={0} max={100}
                value={form.tax_rate}
                onChange={e => setForm(f => ({ ...f, tax_rate: e.target.value }))}
                className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white outline-none focus:border-jarvis-cyan/60"
              />
            </div>
            <div>
              <label className="text-xs text-gray-400 mb-1 block">Due Days</label>
              <input type="number" min={1}
                value={form.due_days}
                onChange={e => setForm(f => ({ ...f, due_days: e.target.value }))}
                className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white outline-none focus:border-jarvis-cyan/60"
              />
            </div>
            <div>
              <label className="text-xs text-gray-400 mb-1 block">Currency</label>
              <select
                value={form.currency}
                onChange={e => setForm(f => ({ ...f, currency: e.target.value }))}
                className="w-full rounded-xl border border-white/10 bg-black/40 px-3 py-2.5 text-sm text-white outline-none focus:border-jarvis-cyan/60"
              >
                {['USD', 'EUR', 'GBP', 'AED', 'INR', 'CAD', 'AUD'].map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
          </div>

          <div>
            <label className="text-xs text-gray-400 mb-1 block">Notes (optional)</label>
            <textarea
              value={form.notes}
              onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
              rows={2}
              className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white outline-none placeholder:text-gray-500 focus:border-jarvis-cyan/60"
            />
          </div>

          {/* Total */}
          <div className="rounded-xl border border-white/10 bg-white/5 px-4 py-3 flex items-center justify-between">
            <span className="text-sm text-gray-400">Total</span>
            <span className="text-xl font-bold text-white">{money(total)}</span>
          </div>

          {error && <p className="text-sm text-red-300">{error}</p>}

          <div className="flex gap-3 justify-end">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors">Cancel</button>
            <button type="submit" disabled={loading} className="btn-primary inline-flex items-center gap-2">
              {loading ? <Loader2 size={14} className="animate-spin" /> : <FileText size={14} />}
              Create Invoice
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function InvoicesView() {
  const [tab, setTab] = useState('invoices')
  const [invoices, setInvoices] = useState([])
  const [clients, setClients] = useState([])
  const [snapshot, setSnapshot] = useState(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState({})
  const [error, setError] = useState(null)
  const [showCreate, setShowCreate] = useState(false)
  const [statusFilter, setStatusFilter] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [invRes, snapRes, clientRes] = await Promise.allSettled([
        api.get('/api/v1/invoices/').catch(() => ({ data: { invoices: [] } })),
        api.get('/api/v1/revenue/snapshot').catch(() => ({ data: null })),
        api.get('/api/v1/clients').catch(() => ({ data: { clients: [] } })),
      ])
      setInvoices(invRes.status === 'fulfilled' ? (invRes.value.data?.invoices || []) : [])
      setSnapshot(snapRes.status === 'fulfilled' ? (snapRes.value.data || null) : null)
      setClients(clientRes.status === 'fulfilled' ? (clientRes.value.data?.clients || []) : [])
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    }
    setLoading(false)
  }, [])

  useEffect(() => { load() }, [load])

  const sendInvoice = async (invoice) => {
    setActionLoading(prev => ({ ...prev, [invoice.id]: 'sending' }))
    try {
      await api.post(`/api/v1/invoices/${invoice.id}/send`, {})
      await load()
    } catch (err) {
      console.error('Send invoice failed:', err)
    }
    setActionLoading(prev => { const n = { ...prev }; delete n[invoice.id]; return n })
  }

  const markPaid = async (invoice) => {
    setActionLoading(prev => ({ ...prev, [invoice.id]: 'paying' }))
    try {
      await api.post(`/api/v1/invoices/${invoice.id}/pay`, { amount: invoice.total || invoice.amount_usd })
      await load()
    } catch (err) {
      console.error('Mark paid failed:', err)
    }
    setActionLoading(prev => { const n = { ...prev }; delete n[invoice.id]; return n })
  }

  const handleCreated = async () => {
    setShowCreate(false)
    await load()
  }

  const totalInvoiced = snapshot?.invoiced_revenue_usd ?? invoices.reduce((s, i) => s + (i.total || 0), 0)
  const totalPaid = snapshot?.paid_revenue_usd ?? invoices.filter(i => i.status === 'paid').reduce((s, i) => s + (i.paid_amount_usd || i.total || 0), 0)
  const outstanding = snapshot?.outstanding_revenue_usd ?? (totalInvoiced - totalPaid)
  const overdueCnt = snapshot?.overdue_invoices ?? invoices.filter(i => i.status === 'overdue').length
  const activeClients = clients.filter(c => c.status === 'active')
  const totalMRR = activeClients.reduce((s, c) => s + (c.mrr_usd || 0), 0)

  const filteredInvoices = statusFilter ? invoices.filter(i => i.status === statusFilter) : invoices

  const TABS = [
    { id: 'invoices', label: 'Invoices', count: invoices.length },
    { id: 'clients', label: 'Active Clients', count: activeClients.length },
  ]

  return (
    <div className="min-h-[calc(100vh-3.5rem)] p-6 pb-10 space-y-6">
      {showCreate && <CreateInvoiceModal onClose={() => setShowCreate(false)} onCreated={handleCreated} />}

      {/* Header */}
      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.22em] text-jarvis-cyan/70">Finance</p>
          <h1 className="mt-2 text-3xl font-bold text-white">Invoice Center</h1>
          <p className="mt-2 max-w-2xl text-sm text-gray-400">
            Revenue operations — invoice tracking, payment status, and client MRR for Aliyar Solutions.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-2 rounded-xl border border-jarvis-cyan/40 bg-jarvis-cyan/10 px-4 py-2.5 text-sm font-medium text-jarvis-cyan hover:bg-jarvis-cyan/20 transition-colors"
          >
            <Plus size={14} /> Create Invoice
          </button>
          <button
            type="button"
            onClick={load}
            disabled={loading}
            className="btn-primary inline-flex items-center justify-center gap-2"
          >
            {loading ? <Loader2 size={15} className="animate-spin" /> : <RefreshCw size={15} />}
            Refresh
          </button>
        </div>
      </header>

      {/* Revenue Metrics */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
        <MetricCard label="Monthly MRR" value={money(snapshot?.mrr_usd ?? totalMRR)} sub={`${activeClients.length} active clients`} tone="cyan" />
        <MetricCard label="ARR (×12)" value={money((snapshot?.mrr_usd ?? totalMRR) * 12)} tone="gold" />
        <MetricCard label="Total Invoiced" value={money(totalInvoiced)} sub={`${invoices.length} invoices`} tone="purple" />
        <MetricCard label="Collected" value={money(totalPaid)} tone="green" />
        <MetricCard label="Outstanding" value={money(outstanding)} tone={outstanding > 0 ? 'gold' : 'green'} />
        <MetricCard label="Overdue" value={overdueCnt} sub={overdueCnt > 0 ? 'Needs attention' : 'All clear'} tone={overdueCnt > 0 ? 'red' : 'green'} />
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
            <span className="rounded-full bg-white/10 px-1.5 py-0.5 text-[10px] font-bold">{t.count}</span>
          </button>
        ))}
      </div>

      {/* Invoice Table */}
      {tab === 'invoices' && (
        <section className="glass p-5">
          <div className="flex items-center justify-between mb-5 flex-wrap gap-3">
            <div>
              <h2 className="text-sm font-semibold text-white">Invoices</h2>
              <p className="mt-0.5 text-xs text-gray-500">
                {loading ? 'Loading…' : `${filteredInvoices.length} invoice${filteredInvoices.length !== 1 ? 's' : ''}`}
              </p>
            </div>
            <div className="flex items-center gap-3">
              {overdueCnt > 0 && (
                <span className="inline-flex items-center gap-1 text-xs text-red-400">
                  <AlertTriangle size={12} /> {overdueCnt} overdue
                </span>
              )}
              <select
                value={statusFilter}
                onChange={e => setStatusFilter(e.target.value)}
                className="rounded-xl border border-white/10 bg-black/40 px-3 py-2 text-xs text-white outline-none focus:border-jarvis-cyan/60"
              >
                <option value="">All statuses</option>
                {Object.keys(STATUS_CONFIG).map(s => <option key={s} value={s}>{STATUS_CONFIG[s].label}</option>)}
              </select>
            </div>
          </div>

          {error && (
            <div className="mb-4 rounded-lg border border-red-400/20 bg-red-400/10 p-3 text-sm text-red-200">{error}</div>
          )}

          {loading ? (
            <div className="flex items-center justify-center py-16 text-gray-500">
              <Loader2 size={20} className="animate-spin mr-2" />Loading invoices…
            </div>
          ) : filteredInvoices.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-gray-500">
              <FileText size={36} className="mb-3 opacity-20" />
              <p className="text-sm font-medium text-gray-400">No invoices found</p>
              <p className="mt-1 text-xs text-gray-600">Click "Create Invoice" above or seed demo data in Captain Bridge.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/10 text-left">
                    <th className="pb-3 pr-4 text-xs font-medium text-gray-500 uppercase tracking-wider">Invoice #</th>
                    <th className="pb-3 pr-4 text-xs font-medium text-gray-500 uppercase tracking-wider">Client</th>
                    <th className="pb-3 pr-4 text-xs font-medium text-gray-500 uppercase tracking-wider text-right">Amount</th>
                    <th className="pb-3 pr-4 text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                    <th className="pb-3 pr-4 text-xs font-medium text-gray-500 uppercase tracking-wider">Due Date</th>
                    <th className="pb-3 text-xs font-medium text-gray-500 uppercase tracking-wider text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredInvoices.map((inv) => {
                    const busy = actionLoading[inv.id]
                    const st = inv.status?.toLowerCase()
                    return (
                      <tr key={inv.id} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                        <td className="py-4 pr-4">
                          <span className="font-mono text-xs text-jarvis-cyan">{inv.invoice_number}</span>
                        </td>
                        <td className="py-4 pr-4">
                          <p className="font-medium text-white">{inv.client_company || inv.client_name || '—'}</p>
                          {inv.client_email && <p className="text-xs text-gray-500 mt-0.5">{inv.client_email}</p>}
                        </td>
                        <td className="py-4 pr-4 text-right">
                          <span className="font-semibold text-white">{money(inv.total || inv.amount_usd)}</span>
                          {inv.currency && inv.currency !== 'USD' && (
                            <span className="ml-1 text-xs text-gray-500">{inv.currency}</span>
                          )}
                        </td>
                        <td className="py-4 pr-4">
                          <StatusBadge status={st} />
                        </td>
                        <td className="py-4 pr-4">
                          <span className={`text-xs ${st === 'overdue' ? 'text-red-400 font-medium' : 'text-gray-400'}`}>
                            {fmtDate(inv.due_date)}
                          </span>
                          {st === 'paid' && inv.paid_at && (
                            <p className="text-xs text-green-400 mt-0.5">Paid {fmtDate(inv.paid_at)}</p>
                          )}
                        </td>
                        <td className="py-4 text-right">
                          <div className="inline-flex items-center gap-2">
                            {st === 'draft' && (
                              <button
                                type="button"
                                disabled={!!busy}
                                onClick={() => sendInvoice(inv)}
                                className="inline-flex items-center gap-1.5 rounded border border-blue-500/40 bg-blue-500/10 px-3 py-1 text-xs font-medium text-blue-300 hover:bg-blue-500/20 disabled:opacity-40 transition-colors"
                              >
                                {busy === 'sending' ? <Loader2 size={11} className="animate-spin" /> : <Send size={11} />}
                                Send
                              </button>
                            )}
                            {(st === 'sent' || st === 'overdue') && (
                              <button
                                type="button"
                                disabled={!!busy}
                                onClick={() => markPaid(inv)}
                                className="inline-flex items-center gap-1.5 rounded border border-green-500/40 bg-green-500/10 px-3 py-1 text-xs font-medium text-green-300 hover:bg-green-500/20 disabled:opacity-40 transition-colors"
                              >
                                {busy === 'paying' ? <Loader2 size={11} className="animate-spin" /> : <CheckCircle2 size={11} />}
                                Mark Paid
                              </button>
                            )}
                            {st === 'paid' && (
                              <span className="inline-flex items-center gap-1 text-xs text-green-400">
                                <CheckCircle2 size={11} /> Collected
                              </span>
                            )}
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      {/* Clients Tab */}
      {tab === 'clients' && (
        <section className="glass p-5">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-sm font-semibold text-white">Active Revenue Clients</h2>
            <p className="text-xs text-gray-500">MRR per client from revenue database</p>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-16 text-gray-500">
              <Loader2 size={20} className="animate-spin mr-2" />Loading clients…
            </div>
          ) : clients.length === 0 ? (
            <div className="flex flex-col items-center py-16 text-gray-500">
              <FileText size={32} className="mb-3 opacity-20" />
              <p className="text-sm text-gray-400">No clients yet</p>
              <p className="mt-1 text-xs">Use Captain Bridge → Seed Demo Data to populate.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/10 text-left">
                    <th className="pb-3 pr-4 text-xs font-medium text-gray-500 uppercase tracking-wider">Company</th>
                    <th className="pb-3 pr-4 text-xs font-medium text-gray-500 uppercase tracking-wider">Contact</th>
                    <th className="pb-3 pr-4 text-xs font-medium text-gray-500 uppercase tracking-wider text-right">MRR</th>
                    <th className="pb-3 pr-4 text-xs font-medium text-gray-500 uppercase tracking-wider">Package</th>
                    <th className="pb-3 pr-4 text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                    <th className="pb-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Since</th>
                  </tr>
                </thead>
                <tbody>
                  {clients.map(client => (
                    <tr key={client.id} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                      <td className="py-4 pr-4">
                        <p className="font-medium text-white">{client.company_name}</p>
                      </td>
                      <td className="py-4 pr-4">
                        <p className="text-sm text-gray-300">{client.contact_name || '—'}</p>
                        {client.email && <p className="text-xs text-gray-500 mt-0.5">{client.email}</p>}
                      </td>
                      <td className="py-4 pr-4 text-right">
                        <span className="font-semibold text-jarvis-gold">{money(client.mrr_usd)}</span>
                        <p className="text-[10px] text-gray-600 mt-0.5">{money(client.mrr_usd * 12)}/yr</p>
                      </td>
                      <td className="py-4 pr-4">
                        {client.package_tier ? (
                          <span className="rounded-full border border-purple-500/30 bg-purple-500/10 px-2.5 py-0.5 text-[11px] font-semibold text-purple-300">
                            {client.package_tier}
                          </span>
                        ) : '—'}
                      </td>
                      <td className="py-4 pr-4">
                        <StatusBadge status={client.status} cfg={CLIENT_STATUS_CFG} />
                      </td>
                      <td className="py-4 text-xs text-gray-400">
                        {fmtDate(client.started_at || client.created_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {/* MRR summary row */}
              <div className="mt-4 pt-4 border-t border-white/10 flex justify-between items-center">
                <span className="text-xs text-gray-500">{activeClients.length} active clients</span>
                <div className="text-right">
                  <p className="text-sm font-semibold text-jarvis-gold">{money(totalMRR)} MRR</p>
                  <p className="text-xs text-gray-500">{money(totalMRR * 12)} ARR</p>
                </div>
              </div>
            </div>
          )}
        </section>
      )}
    </div>
  )
}
