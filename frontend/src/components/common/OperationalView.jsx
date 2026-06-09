import React, { useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { AlertCircle, CheckCircle2, Loader2, RefreshCw } from 'lucide-react'
import api from '../../services/api'

function countRecords(value) {
  if (Array.isArray(value)) return value.length
  if (!value || typeof value !== 'object') return value == null ? 0 : 1

  const keys = [
    'items', 'leads', 'proposals', 'invoices', 'sessions', 'memories',
    'jobs', 'notifications', 'reports', 'entries', 'sops', 'results',
    'contacts', 'deals', 'tasks', 'data',
  ]
  for (const key of keys) {
    if (Array.isArray(value[key])) return value[key].length
  }

  return Object.keys(value).length
}

function preview(value) {
  if (value == null) return 'No records returned.'
  const text = JSON.stringify(value, null, 2)
  return text.length > 1800 ? `${text.slice(0, 1800)}\n...` : text
}

export default function OperationalView({
  eyebrow,
  title,
  description,
  endpoints = [],
  children,
}) {
  const [results, setResults] = useState({})
  const [loading, setLoading] = useState(false)

  const load = async () => {
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
  }

  useEffect(() => {
    load()
  }, [])

  const totalRecords = useMemo(() => (
    endpoints.reduce((sum, endpoint) => {
      const result = results[endpoint.key]
      return sum + (result?.ok ? countRecords(result.data) : 0)
    }, 0)
  ), [endpoints, results])

  return (
    <div className="h-full min-h-0 overflow-y-auto p-6 pb-28 space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.22em] text-jarvis-cyan/70">{eyebrow}</p>
          <h1 className="mt-2 text-3xl font-bold text-white">{title}</h1>
          <p className="mt-2 max-w-3xl text-sm text-gray-400">{description}</p>
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="btn-primary inline-flex items-center justify-center gap-2"
        >
          {loading ? <Loader2 size={15} className="animate-spin" /> : <RefreshCw size={15} />}
          Refresh
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="glass p-5">
          <p className="text-xs text-gray-400">Connected endpoints</p>
          <p className="mt-2 text-3xl font-bold text-jarvis-cyan">
            {endpoints.filter((endpoint) => results[endpoint.key]?.ok).length}/{endpoints.length}
          </p>
        </motion.div>
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.04 }} className="glass p-5">
          <p className="text-xs text-gray-400">Visible records</p>
          <p className="mt-2 text-3xl font-bold text-jarvis-gold">{totalRecords}</p>
        </motion.div>
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.08 }} className="glass p-5">
          <p className="text-xs text-gray-400">Blocked endpoints</p>
          <p className="mt-2 text-3xl font-bold text-red-400">
            {endpoints.filter((endpoint) => results[endpoint.key] && !results[endpoint.key].ok).length}
          </p>
        </motion.div>
      </div>

      {children}

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        {endpoints.map((endpoint) => {
          const result = results[endpoint.key]
          const ok = result?.ok
          return (
            <motion.section
              key={endpoint.key}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              className="glass p-5"
            >
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="text-sm font-semibold text-white">{endpoint.label}</h2>
                  <p className="mt-1 font-mono text-[11px] text-gray-500">{endpoint.path}</p>
                </div>
                <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium ${
                  !result
                    ? 'border-white/10 bg-white/5 text-gray-400'
                    : ok
                      ? 'border-green-400/25 bg-green-400/10 text-green-300'
                      : 'border-red-400/25 bg-red-400/10 text-red-300'
                }`}>
                  {result
                    ? ok
                      ? <CheckCircle2 size={13} />
                      : <AlertCircle size={13} />
                    : <Loader2 size={13} className={loading ? 'animate-spin' : ''} />}
                  {result ? (ok ? 'Live' : 'Blocked') : 'Pending'}
                </span>
              </div>

              {result?.ok ? (
                <pre className="mt-4 max-h-72 overflow-auto rounded-lg border border-white/10 bg-black/20 p-3 text-xs text-gray-300">
                  {preview(result.data)}
                </pre>
              ) : result ? (
                <div className="mt-4 rounded-lg border border-red-400/20 bg-red-400/10 p-3 text-sm text-red-200">
                  {String(result.error)}
                </div>
              ) : (
                <div className="mt-4 rounded-lg border border-white/10 bg-white/5 p-3 text-sm text-gray-400">
                  Waiting for the first refresh.
                </div>
              )}
            </motion.section>
          )
        })}
      </div>
    </div>
  )
}
