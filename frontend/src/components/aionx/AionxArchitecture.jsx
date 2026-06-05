import React, { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  CircuitBoard,
  GitBranch,
  Layers3,
  Network,
  ShieldCheck,
} from 'lucide-react'
import { getAionxArchitecture, getAionxDashboard, getAionxSystemInfo } from '../../services/api'

const STATUS_STYLE = {
  LIVE: 'border-emerald-400/30 bg-emerald-400/10 text-emerald-200',
  LIVE_FOUNDATION: 'border-cyan-400/30 bg-cyan-400/10 text-cyan-200',
  LIVE_WITH_DORMANT_ORGANS: 'border-blue-400/30 bg-blue-400/10 text-blue-200',
  PARTIAL: 'border-amber-400/30 bg-amber-400/10 text-amber-200',
  DESIGN_PARTIAL: 'border-orange-400/30 bg-orange-400/10 text-orange-200',
  REGISTRY_ONLY: 'border-fuchsia-400/30 bg-fuchsia-400/10 text-fuchsia-200',
}

function statusClass(status) {
  return STATUS_STYLE[status] || 'border-white/10 bg-white/5 text-white/70'
}

function StatusPill({ status }) {
  return (
    <span className={`rounded-full border px-2.5 py-1 text-[10px] font-bold tracking-[0.18em] ${statusClass(status)}`}>
      {String(status || 'UNKNOWN').replaceAll('_', ' ')}
    </span>
  )
}

function StatCard({ icon: Icon, label, value, sub }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-white/10 bg-white/[0.045] p-4 shadow-2xl shadow-black/20"
    >
      <div className="flex items-center justify-between">
        <div className="rounded-xl border border-cyan-300/20 bg-cyan-300/10 p-2 text-cyan-200">
          <Icon size={18} />
        </div>
        <p className="text-2xl font-black text-white">{value}</p>
      </div>
      <p className="mt-3 text-xs uppercase tracking-[0.24em] text-white/40">{label}</p>
      {sub && <p className="mt-1 text-xs text-white/55">{sub}</p>}
    </motion.div>
  )
}

function BlueprintCard({ item, index }) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.04 }}
      className="rounded-3xl border border-white/10 bg-slate-950/55 p-5 shadow-2xl shadow-black/25"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[11px] uppercase tracking-[0.26em] text-cyan-200/60">{item.id}</p>
          <h3 className="mt-1 text-lg font-black text-white">{item.name}</h3>
        </div>
        <StatusPill status={item.status} />
      </div>

      <div className="mt-5 grid gap-4 lg:grid-cols-2">
        <div>
          <p className="mb-2 text-xs font-bold uppercase tracking-[0.2em] text-emerald-200/70">Live Evidence</p>
          <div className="space-y-2">
            {(item.live_evidence || []).map((entry) => (
              <div key={entry} className="flex gap-2 rounded-xl bg-emerald-400/[0.06] px-3 py-2 text-sm text-white/75">
                <CheckCircle2 size={15} className="mt-0.5 shrink-0 text-emerald-300" />
                <span>{entry}</span>
              </div>
            ))}
          </div>
        </div>
        <div>
          <p className="mb-2 text-xs font-bold uppercase tracking-[0.2em] text-amber-200/70">Still To Connect</p>
          <div className="space-y-2">
            {(item.pending_work || []).map((entry) => (
              <div key={entry} className="flex gap-2 rounded-xl bg-amber-400/[0.06] px-3 py-2 text-sm text-white/70">
                <AlertTriangle size={15} className="mt-0.5 shrink-0 text-amber-300" />
                <span>{entry}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </motion.section>
  )
}

function ConnectionRow({ row }) {
  return (
    <div className="grid gap-3 rounded-2xl border border-white/10 bg-white/[0.035] p-4 md:grid-cols-[180px_1fr_150px]">
      <p className="font-black text-cyan-100">{row.event}</p>
      <p className="text-sm text-white/70">{row.connects}</p>
      <div className="md:text-right">
        <StatusPill status={row.status} />
      </div>
    </div>
  )
}

export default function AionxArchitecture() {
  const [state, setState] = useState({ loading: true, architecture: null, dashboard: null, system: null, error: null })

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const [architecture, dashboard, system] = await Promise.all([
          getAionxArchitecture(),
          getAionxDashboard(),
          getAionxSystemInfo(),
        ])
        if (!cancelled) setState({ loading: false, architecture, dashboard, system, error: null })
      } catch (error) {
        if (!cancelled) setState({ loading: false, architecture: null, dashboard: null, system: null, error })
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [])

  if (state.loading) {
    return (
      <div className="flex h-full items-center justify-center bg-slate-950 text-white/60">
        Reading AIONX live architecture...
      </div>
    )
  }

  if (state.error) {
    return (
      <div className="h-full overflow-auto bg-slate-950 p-8">
        <div className="rounded-3xl border border-red-400/20 bg-red-500/10 p-6 text-red-100">
          AIONX architecture endpoint is not reachable: {state.error.message}
        </div>
      </div>
    )
  }

  const architecture = state.architecture || {}
  const counts = architecture.counts || {}
  const iq = state.dashboard?.sections?.operational_iq?.operational_iq
  const wisdom = state.dashboard?.sections?.wisdom_index?.wisdom_score

  return (
    <div className="h-full overflow-auto bg-[radial-gradient(circle_at_top_left,rgba(34,211,238,0.18),transparent_34%),linear-gradient(135deg,#020617,#07111f_52%,#031017)] p-6 text-white">
      <div className="mx-auto max-w-7xl space-y-6">
        <motion.header initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} className="relative overflow-hidden rounded-[2rem] border border-cyan-200/15 bg-white/[0.045] p-7 shadow-2xl shadow-cyan-950/30">
          <div className="absolute right-8 top-8 h-32 w-32 rounded-full bg-cyan-400/10 blur-3xl" />
          <p className="text-xs font-bold uppercase tracking-[0.36em] text-cyan-200/70">Captain Glass Wall</p>
          <div className="mt-3 flex flex-wrap items-end justify-between gap-5">
            <div>
              <h1 className="text-4xl font-black tracking-tight">AIONX Architecture Reconciliation</h1>
              <p className="mt-3 max-w-4xl text-sm leading-6 text-white/65">{architecture.verdict}</p>
            </div>
            <StatusPill status={state.system?.status || 'UNKNOWN'} />
          </div>
        </motion.header>

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          <StatCard icon={Layers3} label="Canonical Batches" value={counts.canonical_batches || 0} sub="Batch 1, 2, 3 plus strategic blocks" />
          <StatCard icon={CircuitBoard} label="AIONX Tables" value={`${counts.live_aionx_tables || 0}/${counts.expected_aionx_tables || 0}`} sub={`${counts.missing_aionx_tables || 0} missing`} />
          <StatCard icon={Network} label="AIONX Routes" value={counts.aionx_api_endpoints_expected || 0} sub="Registered backend surface" />
          <StatCard icon={Activity} label="Operational IQ" value={iq ?? '-'} sub="Live Cortex signal" />
          <StatCard icon={ShieldCheck} label="Wisdom Score" value={wisdom ?? '-'} sub="Institutional fitness signal" />
        </div>

        <section className="grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
          <div className="rounded-3xl border border-white/10 bg-white/[0.04] p-5">
            <div className="mb-4 flex items-center gap-2">
              <GitBranch className="text-cyan-200" size={18} />
              <h2 className="text-lg font-black">Connection Map</h2>
            </div>
            <div className="space-y-3">
              {(architecture.connection_map || []).map((row) => <ConnectionRow key={row.event} row={row} />)}
            </div>
          </div>

          <div className="rounded-3xl border border-white/10 bg-white/[0.04] p-5">
            <h2 className="text-lg font-black">Canonical Next Build Order</h2>
            <div className="mt-4 space-y-3">
              {(architecture.canonical_next_build_order || []).map((step, index) => (
                <div key={step} className="flex gap-3 rounded-2xl border border-cyan-200/10 bg-cyan-300/[0.05] p-3">
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-cyan-300/15 text-xs font-black text-cyan-100">{index + 1}</span>
                  <p className="text-sm text-white/72">{step}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <div className="grid gap-5">
          {(architecture.blueprint || []).map((item, index) => <BlueprintCard key={item.id} item={item} index={index} />)}
        </div>

        <section className="rounded-3xl border border-white/10 bg-black/20 p-5">
          <h2 className="text-lg font-black">Authority Boundaries</h2>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {(architecture.authority_boundaries || []).map((rule) => (
              <div key={rule} className="rounded-2xl border border-fuchsia-200/10 bg-fuchsia-300/[0.05] p-4 text-sm text-white/72">
                {rule}
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  )
}
