import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { AlertCircle, CheckCircle2, Loader2, RefreshCw, Send } from 'lucide-react'
import api from '../../services/api'

export const DEFAULT_TENANT = '794d9b02-2dd6-49f0-b5c1-9f7c0b3af4b1'

function countRecords(value) {
  if (Array.isArray(value)) return value.length
  if (!value || typeof value !== 'object') return value == null ? 0 : 1
  for (const key of [
    'items', 'leads', 'clients', 'contacts', 'companies', 'deals', 'actions',
    'threats', 'sessions', 'nodes', 'edges', 'queue', 'events', 'milestones',
    'approvals', 'recommendations', 'profiles', 'competitors', 'jobs',
  ]) {
    if (Array.isArray(value[key])) return value[key].length
  }
  return Object.keys(value).length
}

function compactJson(value) {
  if (value == null) return 'No data returned yet.'
  const text = JSON.stringify(value, null, 2)
  return text.length > 2600 ? `${text.slice(0, 2600)}\n...` : text
}

export function useEndpointBundle(endpoints = []) {
  const [results, setResults] = useState({})
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    const next = {}
    await Promise.all(endpoints.map(async (endpoint) => {
      try {
        const response = await api.request({
          method: endpoint.method || 'get',
          url: endpoint.path,
          params: endpoint.params,
          data: endpoint.body,
        })
        next[endpoint.key] = { ok: true, data: response.data }
      } catch (error) {
        next[endpoint.key] = {
          ok: false,
          error: error.response?.data?.detail || error.message || 'Endpoint unavailable',
        }
      }
    }))
    setResults(next)
    setLoading(false)
  }, [endpoints])

  useEffect(() => {
    load()
  }, [load])

  const summary = useMemo(() => {
    const connected = endpoints.filter((endpoint) => results[endpoint.key]?.ok).length
    const blocked = endpoints.filter((endpoint) => results[endpoint.key] && !results[endpoint.key].ok).length
    const records = endpoints.reduce((sum, endpoint) => {
      const result = results[endpoint.key]
      return sum + (result?.ok ? countRecords(result.data) : 0)
    }, 0)
    return { connected, blocked, records }
  }, [endpoints, results])

  return { results, loading, load, summary }
}

export function FrontierShell({ eyebrow, title, description, subtitle, endpoints = [], children }) {
  const { results, loading, load, summary } = useEndpointBundle(endpoints)
  const childContent = typeof children === 'function'
    ? children({ results, loading, refresh: load })
    : children

  return (
    <div className="min-h-[calc(100vh-3.5rem)] p-6 pb-10 space-y-6">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          {eyebrow && <p className="text-xs uppercase tracking-[0.22em] text-jarvis-cyan/70">{eyebrow}</p>}
          <h1 className="mt-2 text-3xl font-bold text-white">{title}</h1>
          {(description || subtitle) && (
            <p className="mt-2 max-w-4xl text-sm text-gray-400">{description || subtitle}</p>
          )}
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

      <MetricStrip items={[
        { label: 'Live endpoints', value: `${summary.connected}/${endpoints.length}`, tone: 'cyan' },
        { label: 'Visible records', value: summary.records, tone: 'gold' },
        { label: 'Blocked paths', value: summary.blocked, tone: summary.blocked ? 'red' : 'green' },
      ]} />

      {childContent}

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        {endpoints.map((endpoint) => (
          <JsonPanel
            key={endpoint.key}
            title={endpoint.label}
            subtitle={endpoint.path}
            result={results[endpoint.key]}
          />
        ))}
      </div>
    </div>
  )
}

export function MetricStrip({ items }) {
  const tones = {
    cyan: 'text-jarvis-cyan',
    gold: 'text-jarvis-gold',
    green: 'text-green-300',
    red: 'text-red-300',
    purple: 'text-purple-300',
  }

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
      {items.map((item, index) => (
        <motion.div
          key={item.label}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: index * 0.03 }}
          className="glass p-5"
        >
          <p className="text-xs text-gray-400">{item.label}</p>
          <p className={`mt-2 text-3xl font-bold ${tones[item.tone] || tones.cyan}`}>{item.value}</p>
          {item.detail && <p className="mt-2 text-xs text-gray-500">{item.detail}</p>}
        </motion.div>
      ))}
    </div>
  )
}

export function JsonPanel({ title, subtitle, result }) {
  const ok = result?.ok
  return (
    <section className="glass p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold text-white">{title}</h2>
          {subtitle && <p className="mt-1 font-mono text-[11px] text-gray-500">{subtitle}</p>}
        </div>
        <StatusPill result={result} />
      </div>
      {result?.ok ? (
        <pre className="mt-4 max-h-80 overflow-auto rounded-lg border border-white/10 bg-black/20 p-3 text-xs text-gray-300">
          {compactJson(result.data)}
        </pre>
      ) : result ? (
        <div className="mt-4 rounded-lg border border-red-400/20 bg-red-400/10 p-3 text-sm text-red-200">
          {String(result.error)}
        </div>
      ) : (
        <div className="mt-4 rounded-lg border border-white/10 bg-white/5 p-3 text-sm text-gray-400">
          Waiting for first refresh.
        </div>
      )}
    </section>
  )
}

export function StatusPill({ result }) {
  if (!result) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-[11px] font-medium text-gray-400">
        <Loader2 size={13} /> Pending
      </span>
    )
  }
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium ${
      result.ok
        ? 'border-green-400/25 bg-green-400/10 text-green-300'
        : 'border-red-400/25 bg-red-400/10 text-red-300'
    }`}>
      {result.ok ? <CheckCircle2 size={13} /> : <AlertCircle size={13} />}
      {result.ok ? 'Live' : 'Blocked'}
    </span>
  )
}

export function ActionCard({ title, subtitle, description, children }) {
  return (
    <section className="glass p-5">
      <h2 className="text-sm font-semibold text-white">{title}</h2>
      {(subtitle || description) && <p className="mt-1 text-xs text-gray-500">{subtitle || description}</p>}
      <div className="mt-4 space-y-3">{children}</div>
    </section>
  )
}

export function Textarea({ value, onChange, placeholder, rows = 4, maxLength }) {
  return (
    <textarea
      value={value}
      onChange={(event) => onChange(event.target.value)}
      rows={rows}
      placeholder={placeholder}
      maxLength={maxLength}
      className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none placeholder:text-gray-500 focus:border-jarvis-cyan/60"
    />
  )
}

export function Input({ value, onChange, placeholder }) {
  return (
    <input
      value={value}
      onChange={(event) => onChange(event.target.value)}
      placeholder={placeholder}
      className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none placeholder:text-gray-500 focus:border-jarvis-cyan/60"
    />
  )
}

export function RunButton({ loading, disabled, children, label, onClick, type = 'submit' }) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={loading || disabled}
      className="btn-primary inline-flex min-w-36 items-center justify-center gap-2"
    >
      {loading ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />}
      {children || label}
    </button>
  )
}

export function ResultBox({ result }) {
  if (!result) return null
  return (
    <pre className="max-h-72 overflow-auto rounded-lg border border-white/10 bg-black/20 p-3 text-xs text-gray-300">
      {compactJson(result)}
    </pre>
  )
}

export default FrontierShell
