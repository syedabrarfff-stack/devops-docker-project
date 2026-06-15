import React, { useCallback, useEffect, useState } from 'react'
import { AlertTriangle, CheckCircle2, Clock, DollarSign, FileText, Loader2, RefreshCw, Send, XCircle } from 'lucide-react'
import api from '../../services/api'

const STATUS_CONFIG = {
  draft:     { label: 'Draft',     cls: 'border-gray-500/30 bg-gray-500/10 text-gray-300' },
  sent:      { label: 'Sent',      cls: 'border-blue-500/30 bg-blue-500/10 text-blue-300' },
  paid:      { label: 'Paid',      cls: 'border-green-500/30 bg-green-500/10 text-green-300' },
  overdue:   { label: 'Overdue',   cls: 'border-red-500/30 bg-red-500/10 text-red-300' },
  cancelled: { label: 'Cancelled', cls: 'border-gray-600/30 bg-gray-600/10 text-gray-500' },
}

function StatusBadge({ status }) {
  const cfg = STATUS_CONFIG[status?.toLowerCase()] || STATUS_CONFIG.draft
  return (
    <span className={`inline-flex rounded-full border px-2.5 py-0.5 text-[11px] font-semibold tracking-wide ${cfg.cls}`}>
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

function MetricCard({ label, value, sub, tone = 'cyan' }) {
  const tones = {
    cyan:   'text-jarvis-cyan',
    gold:   'text-jarvis-gold',
    green:  'text-green-300',
    red:    'text-red-400',
    purple: 'text-purple-300',
  }
  return (
    <div className="glass p-5">
      <p className="text-xs text-gray-400">{label}</p>
      <p className={`mt-2 text-2xl font-bold ${tones[tone] || tones.cyan}`}>{value}</p>
      {sub && <p className="mt-1 text-xs text-gray-600">{sub}</p>}
    </div>
  )
}

export default function InvoicesView() {
  const [invoices, setInvoices] = useState([])
  const [snapshot, setSnapshot] = useState(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState({})
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [invRes, snapRes] = await Promise.all([
        api.get('/api/v1/invoices/').catch(() => ({ data: { invoices: [] } })),
        api.get('/api/v1/revenue/snapshot').catch(() => ({ data: null })),
      ])
      setInvoices(invRes.data?.invoices || [])
      setSnapshot(snapRes.data || null)
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

  const totalInvoiced = snapshot?.invoiced_revenue_usd ?? invoices.reduce((s, i) => s + (i.total || 0), 0)
  const totalPaid = snapshot?.paid_revenue_usd ?? invoices.filter(i => i.status === 'paid').reduce((s, i) => s + (i.paid_amount_usd || i.total || 0), 0)
  const outstanding = snapshot?.outstanding_revenue_usd ?? (totalInvoiced - totalPaid)
  const overdueCnt = snapshot?.overdue_invoices ?? invoices.filter(i => i.status === 'overdue').length

  return (
    <div className="min-h-[calc(100vh-3.5rem)] p-6 pb-10 space-y-6">
      {/* Header */}
      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.22em] text-jarvis-cyan/70">Finance</p>
          <h1 className="mt-2 text-3xl font-bold text-white">Invoice Center</h1>
          <p className="mt-2 max-w-2xl text-sm text-gray-400">
            Revenue operations — invoice tracking, payment status, and financial reporting for Aliyar Solutions.
          </p>
        </div>
        <button
          type="button"
          onClick={load}
          disabled={loading}
          className="btn-primary inline-flex items-center justify-center gap-2"
        >
          {loading ? <Loader2 size={15} className="animate-spin" /> : <RefreshCw size={15} />}
          Refresh
        </button>
      </header>

      {/* Revenue Metrics */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
        <MetricCard
          label="Monthly MRR"
          value={money(snapshot?.mrr_usd ?? 0)}
          sub={snapshot ? `${snapshot.active_clients} active clients` : undefined}
          tone="cyan"
        />
        <MetricCard
          label="ARR (×12)"
          value={money((snapshot?.mrr_usd ?? 0) * 12)}
          tone="gold"
        />
        <MetricCard
          label="Total Invoiced"
          value={money(totalInvoiced)}
          sub={`${invoices.length} invoices`}
          tone="purple"
        />
        <MetricCard
          label="Collected"
          value={money(totalPaid)}
          tone="green"
        />
        <MetricCard
          label="Outstanding"
          value={money(outstanding)}
          tone={outstanding > 0 ? 'gold' : 'green'}
        />
        <MetricCard
          label="Overdue"
          value={overdueCnt}
          sub={overdueCnt > 0 ? 'Needs attention' : 'All clear'}
          tone={overdueCnt > 0 ? 'red' : 'green'}
        />
      </div>

      {/* Invoice Table */}
      <section className="glass p-5">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h2 className="text-sm font-semibold text-white">Invoices</h2>
            <p className="mt-0.5 text-xs text-gray-500">
              {loading ? 'Loading…' : `${invoices.length} invoice${invoices.length !== 1 ? 's' : ''} found`}
            </p>
          </div>
          <div className="flex items-center gap-2 text-xs text-gray-500">
            {overdueCnt > 0 && (
              <span className="inline-flex items-center gap-1 text-red-400">
                <AlertTriangle size={12} /> {overdueCnt} overdue
              </span>
            )}
          </div>
        </div>

        {error && (
          <div className="mb-4 rounded-lg border border-red-400/20 bg-red-400/10 p-3 text-sm text-red-200">
            {error}
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-16 text-gray-500">
            <Loader2 size={20} className="animate-spin mr-2" />
            Loading invoices…
          </div>
        ) : invoices.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-gray-500">
            <FileText size={36} className="mb-3 opacity-20" />
            <p className="text-sm font-medium text-gray-400">No invoices yet</p>
            <p className="mt-1 text-xs text-gray-600">
              Go to Captain Bridge and click "Seed Demo Data" to populate.
            </p>
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
                {invoices.map((inv) => {
                  const busy = actionLoading[inv.id]
                  const st = inv.status?.toLowerCase()
                  return (
                    <tr
                      key={inv.id}
                      className="border-b border-white/5 hover:bg-white/5 transition-colors"
                    >
                      <td className="py-4 pr-4">
                        <span className="font-mono text-xs text-jarvis-cyan">{inv.invoice_number}</span>
                      </td>
                      <td className="py-4 pr-4">
                        <p className="font-medium text-white">{inv.client_company || inv.client_name || '—'}</p>
                        {inv.client_email && (
                          <p className="text-xs text-gray-500 mt-0.5">{inv.client_email}</p>
                        )}
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
                          {st === 'cancelled' && (
                            <span className="inline-flex items-center gap-1 text-xs text-gray-500">
                              <XCircle size={11} /> Cancelled
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

      {/* Pro tip */}
      {!loading && invoices.length === 0 && (
        <div className="glass p-5 border-l-2 border-jarvis-cyan/40">
          <p className="text-xs font-semibold text-jarvis-cyan mb-1">Quick start</p>
          <p className="text-xs text-gray-400">
            Navigate to <span className="text-white">Captain Bridge</span> and click{' '}
            <span className="text-white">Seed Demo Data</span> to instantly populate 8 clients, 25 pipeline leads,
            and 90 days of MRR history for demos and testing.
          </p>
        </div>
      )}
    </div>
  )
}
