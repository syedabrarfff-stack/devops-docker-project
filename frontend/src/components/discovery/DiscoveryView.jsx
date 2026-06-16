import React, { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { AlertCircle, CheckCircle2, Loader2, RefreshCw, Search, Users, Zap } from 'lucide-react'
import api from '../../services/api'

const ALIYAR_PACKAGES = [
  { name: 'AI Lead Generation', category: 'Sales' },
  { name: 'Outreach Systems', category: 'Sales' },
  { name: 'Sales Automation', category: 'Sales' },
  { name: 'CRM Architecture', category: 'Sales' },
  { name: 'Appointment Systems', category: 'AI Auto' },
  { name: 'Voice Receptionist', category: 'AI Auto' },
  { name: 'Workflow Automation', category: 'AI Auto' },
  { name: 'Executive Automation', category: 'AI Auto' },
  { name: 'AWS Architecture', category: 'DevOps' },
  { name: 'Docker & DevOps', category: 'DevOps' },
  { name: 'CI/CD Pipelines', category: 'DevOps' },
  { name: 'Terraform IaC', category: 'DevOps' },
  { name: 'Kubernetes', category: 'DevOps' },
  { name: 'Cloud Monitoring', category: 'DevOps' },
  { name: 'Cybersecurity Ops', category: 'Security' },
  { name: 'Vulnerability Assessment', category: 'Security' },
  { name: 'Compliance Hardening', category: 'Security' },
  { name: 'Content Automation', category: 'Content' },
  { name: 'YouTube Operations', category: 'Content' },
  { name: 'Social Media AI', category: 'Content' },
  { name: 'Web Applications', category: 'Digital' },
  { name: 'Client Portals', category: 'Digital' },
  { name: 'Operational Dashboards', category: 'Digital' },
  { name: 'AI Research', category: 'Intel' },
  { name: 'Business Intelligence', category: 'Intel' },
]

const ICP_MARKETS = ['United Kingdom', 'United Arab Emirates', 'United States', 'Australia', 'Canada', 'Bahrain']

const CATEGORY_COLORS = {
  Sales: 'border-jarvis-gold/25 bg-jarvis-gold/10 text-jarvis-gold',
  'AI Auto': 'border-jarvis-cyan/25 bg-jarvis-cyan/10 text-jarvis-cyan',
  DevOps: 'border-blue-400/25 bg-blue-400/10 text-blue-300',
  Security: 'border-red-400/25 bg-red-400/10 text-red-300',
  Content: 'border-purple-400/25 bg-purple-400/10 text-purple-300',
  Digital: 'border-green-400/25 bg-green-400/10 text-green-300',
  Intel: 'border-orange-400/25 bg-orange-400/10 text-orange-300',
}

function StatCard({ label, value, tone }) {
  const colors = { cyan: 'text-jarvis-cyan', gold: 'text-jarvis-gold', green: 'text-green-300' }
  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="glass p-5">
      <p className="text-xs text-gray-400">{label}</p>
      <p className={`mt-2 text-3xl font-black ${colors[tone] || colors.cyan}`}>{value}</p>
    </motion.div>
  )
}

export default function DiscoveryView() {
  const [stats, setStats] = useState(null)
  const [todayLeads, setTodayLeads] = useState([])
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState(null)
  const [bulkResult, setBulkResult] = useState(null)
  const [localForm, setLocalForm] = useState({
    industry: 'SaaS automation',
    location: 'Dubai',
    service_angle: 'workflow automation',
    limit: 10,
  })
  const [localResult, setLocalResult] = useState(null)
  const [freeSourceResult, setFreeSourceResult] = useState(null)
  const [scoutResult, setScoutResult] = useState(null)
  const [scoutStatus, setScoutStatus] = useState(null)

  async function load() {
    const [s, t] = await Promise.allSettled([
      api.get('/api/v1/leads/stats').then(r => r.data),
      api.get('/api/v1/discover/leads/today').then(r => r.data),
    ])
    if (s.status === 'fulfilled') setStats(s.value)
    if (t.status === 'fulfilled') setTodayLeads(t.value?.leads || t.value || [])
  }

  useEffect(() => { load() }, [])

  async function runBulkDiscover() {
    setBusy(true)
    setNotice(null)
    setBulkResult(null)
    try {
      const result = await api.post('/api/v1/leads/bulk-discover', null, { params: { limit: 200 } }).then(r => r.data)
      setBulkResult(result)
      setNotice({ tone: 'ok', text: result.message || `Discovery started — targeting ${result.targets} ICP segments.` })
      setTimeout(load, 8000)
    } catch (e) {
      setNotice({ tone: 'err', text: e.response?.data?.detail || e.message || 'Bulk discovery failed.' })
    } finally {
      setBusy(false)
    }
  }

  async function runFreeSourceDiscover() {
    setBusy(true)
    setFreeSourceResult(null)
    try {
      const result = await api.post('/api/v1/discover/free-sources', { limit: 50 }).then(r => r.data)
      setFreeSourceResult(result)
      setNotice({ tone: 'ok', text: `Free-source discovery done — ${result.count || result.leads?.length || 0} prospects found.` })
      setTimeout(load, 5000)
    } catch (e) {
      setNotice({ tone: 'err', text: e.response?.data?.detail || e.message || 'Free-source discovery failed.' })
    } finally {
      setBusy(false)
    }
  }

  async function runScoutNetwork() {
    setBusy(true)
    setScoutResult(null)
    try {
      const result = await api.post('/api/v1/scouts/run', {}).then(r => r.data)
      setScoutResult(result)
      setNotice({ tone: 'ok', text: result.message || 'Scout network activated.' })
    } catch (e) {
      setNotice({ tone: 'err', text: e.response?.data?.detail || e.message || 'Scout network failed.' })
    } finally {
      setBusy(false)
    }
  }

  async function checkScoutStatus() {
    try {
      const r = await api.get('/api/v1/scouts/status')
      setScoutStatus(r.data)
    } catch (e) {
      setScoutStatus({ error: e.response?.data?.detail || e.message })
    }
  }

  async function runLocalDiscover() {
    setBusy(true)
    setLocalResult(null)
    try {
      const result = await api.post('/api/v1/discovery/local-market', {
        ...localForm,
        limit: parseInt(localForm.limit) || 10,
      }).then(r => r.data)
      setLocalResult(result)
      setNotice({ tone: 'ok', text: `Local discovery done — ${result.leads?.length || result.count || 0} prospects.` })
      setTimeout(load, 3000)
    } catch (e) {
      setNotice({ tone: 'err', text: e.response?.data?.detail || e.message || 'Local discovery failed.' })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-[calc(100vh-3.5rem)] p-6 pb-10 space-y-6">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.22em] text-jarvis-cyan/70">Client Acquisition Engine</p>
          <h1 className="mt-2 text-3xl font-bold text-white">Lead Discovery</h1>
          <p className="mt-2 max-w-3xl text-sm text-gray-400">
            Autonomous lead generation across 25 Aliyar Solutions service packages — Apollo, Google Maps, and free-source discovery targeting 6 ICP markets.
          </p>
        </div>
        <button onClick={load} disabled={busy} className="btn-primary inline-flex items-center gap-2">
          {busy ? <Loader2 size={15} className="animate-spin" /> : <RefreshCw size={15} />}
          Refresh
        </button>
      </header>

      {notice && (
        <div className={`rounded-xl border p-3 text-sm ${
          notice.tone === 'err' ? 'border-red-300/25 bg-red-500/10 text-red-100' : 'border-emerald-300/25 bg-emerald-500/10 text-emerald-100'
        }`}>
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-2">
              {notice.tone === 'err' ? <AlertCircle size={14} className="mt-0.5 shrink-0" /> : <CheckCircle2 size={14} className="mt-0.5 shrink-0" />}
              <p>{notice.text}</p>
            </div>
            <button onClick={() => setNotice(null)} className="text-xs opacity-60 hover:opacity-100">✕</button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard label="Total leads" value={stats?.total ?? '—'} tone="cyan" />
        <StatCard label="High score (≥70)" value={stats?.high_score ?? '—'} tone="gold" />
        <StatCard label="Outreach eligible" value={stats?.outreach_eligible ?? '—'} tone="green" />
        <StatCard label="Discovered today" value={todayLeads.length} tone="cyan" />
      </div>

      {/* Bulk Discovery Panel */}
      <section className="glass p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-base font-bold text-white">Bulk Discovery — 200 ICP Leads</h2>
            <p className="mt-1 text-xs leading-5 text-gray-400">
              Fires 25 Apollo queries simultaneously — one per service package — across UK, UAE, USA, AUS, CA, BH. Scored and deduped automatically.
            </p>
          </div>
          <button onClick={runBulkDiscover} disabled={busy} className="btn-primary inline-flex shrink-0 items-center gap-2">
            {busy ? <Loader2 size={15} className="animate-spin" /> : <Zap size={15} />}
            Discover 200 Leads
          </button>
        </div>

        <div className="mt-5 grid grid-cols-2 gap-2 md:grid-cols-5">
          {ALIYAR_PACKAGES.map((pkg, i) => (
            <motion.div
              key={pkg.name}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: i * 0.015 }}
              className={`rounded-lg border p-2 ${CATEGORY_COLORS[pkg.category] || 'border-white/10 bg-white/5 text-gray-300'}`}
            >
              <p className="text-[10px] font-bold uppercase tracking-[0.1em] opacity-60">{pkg.category}</p>
              <p className="mt-0.5 text-xs font-semibold">{pkg.name}</p>
            </motion.div>
          ))}
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          {ICP_MARKETS.map(m => (
            <span key={m} className="rounded-full border border-white/15 bg-white/5 px-3 py-1 text-[11px] text-gray-300">
              {m}
            </span>
          ))}
        </div>

        {bulkResult && (
          <div className="mt-4 rounded-xl border border-white/10 bg-black/20 p-4">
            <p className="mb-2 text-xs font-bold uppercase tracking-[0.14em] text-white/40">Job Status</p>
            <pre className="text-xs text-gray-300">{JSON.stringify(bulkResult, null, 2)}</pre>
          </div>
        )}
      </section>

      {/* Local Market Discovery */}
      <section className="glass p-5">
        <h2 className="text-sm font-bold text-white">Local Market Drill-Down</h2>
        <p className="mt-1 text-xs text-gray-500">Target a specific city, industry, and service angle — returns hyper-local prospects.</p>
        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-4">
          {[
            { key: 'industry', placeholder: 'Industry (e.g. dental clinic)' },
            { key: 'location', placeholder: 'City (e.g. Dubai)' },
            { key: 'service_angle', placeholder: 'Service angle (e.g. booking system)' },
            { key: 'limit', placeholder: 'Limit (1-25)' },
          ].map(({ key, placeholder }) => (
            <input
              key={key}
              value={localForm[key]}
              onChange={e => setLocalForm(f => ({ ...f, [key]: e.target.value }))}
              placeholder={placeholder}
              className="rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none placeholder:text-gray-500 focus:border-jarvis-cyan/60"
            />
          ))}
        </div>
        <button onClick={runLocalDiscover} disabled={busy} className="btn-primary mt-4 inline-flex items-center gap-2">
          {busy ? <Loader2 size={15} className="animate-spin" /> : <Search size={15} />}
          Run Discovery
        </button>
        {localResult && (
          <pre className="mt-4 max-h-64 overflow-auto rounded-lg border border-white/10 bg-black/20 p-3 text-xs text-gray-300">
            {JSON.stringify(localResult, null, 2)}
          </pre>
        )}
      </section>

      {/* Free Source Discovery + Scout Network */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <section className="glass p-5 space-y-3">
          <div>
            <h2 className="text-sm font-bold text-white">Free-Source Discovery</h2>
            <p className="mt-1 text-xs text-gray-500">Scrape 50 leads from free public sources — no Apollo credits used.</p>
          </div>
          <button onClick={runFreeSourceDiscover} disabled={busy} className="btn-primary inline-flex items-center gap-2">
            {busy ? <Loader2 size={13} className="animate-spin" /> : <Search size={13} />}
            Run Free Discovery
          </button>
          {freeSourceResult && (
            <pre className="max-h-40 overflow-auto rounded-lg border border-white/10 bg-black/20 p-3 text-xs text-gray-300">
              {JSON.stringify(freeSourceResult, null, 2)}
            </pre>
          )}
        </section>

        <section className="glass p-5 space-y-3">
          <div>
            <h2 className="text-sm font-bold text-white">Scout Agent Network</h2>
            <p className="mt-1 text-xs text-gray-500">Activate the autonomous scout network to monitor target industries for new prospects.</p>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={runScoutNetwork} disabled={busy} className="btn-primary inline-flex items-center gap-2">
              {busy ? <Loader2 size={13} className="animate-spin" /> : <Zap size={13} />}
              Activate Scouts
            </button>
            <button onClick={checkScoutStatus} disabled={busy} className="inline-flex items-center gap-1.5 rounded-xl border border-white/10 bg-white/5 px-3 py-1.5 text-xs font-medium text-gray-300 hover:bg-white/10 transition-colors">
              Status
            </button>
          </div>
          {(scoutResult || scoutStatus) && (
            <pre className="max-h-40 overflow-auto rounded-lg border border-white/10 bg-black/20 p-3 text-xs text-gray-300">
              {JSON.stringify(scoutResult || scoutStatus, null, 2)}
            </pre>
          )}
        </section>
      </div>

      {/* Today's leads */}
      {todayLeads.length > 0 && (
        <section className="glass p-5">
          <h2 className="mb-4 flex items-center gap-2 text-sm font-bold text-white">
            <Users size={15} className="text-jarvis-cyan" />
            Discovered Today ({todayLeads.length})
          </h2>
          <div className="max-h-96 space-y-2 overflow-y-auto">
            {todayLeads.map((lead, i) => (
              <div key={lead.id || i} className="flex items-start justify-between gap-3 rounded-xl border border-white/10 bg-white/[0.03] p-3">
                <div>
                  <p className="text-sm font-semibold text-white">{lead.company_name || lead.company || 'Unknown'}</p>
                  <p className="text-xs text-gray-500">
                    {[lead.contact_name, lead.country, lead.industry].filter(Boolean).join(' · ')}
                  </p>
                  {lead.email && <p className="mt-0.5 text-xs text-jarvis-cyan/70">{lead.email}</p>}
                </div>
                <div className="shrink-0 text-right">
                  <p className="text-xs font-bold text-white">{lead.score ? `${Math.round(lead.score)}/100` : '—'}</p>
                  <p className="text-[10px] text-gray-500">{lead.status}</p>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
