import React, { useEffect, useMemo, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import {
  Activity,
  Brain,
  Briefcase,
  ChevronDown,
  ChevronUp,
  Filter,
  GitBranch,
  Layers3,
  ShieldCheck,
  Sparkles,
  Users,
  Zap,
} from 'lucide-react'
import { getCatalogCapabilityModules } from '../../services/api'

const GROUP_COLORS = {
  'Revenue Operations': { dot: 'bg-emerald-400', badge: 'text-emerald-300 bg-emerald-400/10 border-emerald-400/20', glow: 'from-emerald-400/18' },
  'AI Automation': { dot: 'bg-jarvis-blue', badge: 'text-jarvis-blue bg-jarvis-blue/10 border-jarvis-blue/20', glow: 'from-jarvis-blue/20' },
  'Cloud & DevOps': { dot: 'bg-orange-400', badge: 'text-orange-300 bg-orange-400/10 border-orange-400/20', glow: 'from-orange-400/18' },
  'Security & Compliance': { dot: 'bg-red-400', badge: 'text-red-300 bg-red-400/10 border-red-400/20', glow: 'from-red-400/18' },
  'Intelligence & Data': { dot: 'bg-amber-400', badge: 'text-amber-300 bg-amber-400/10 border-amber-400/20', glow: 'from-amber-400/18' },
  'Digital Products': { dot: 'bg-jarvis-purple', badge: 'text-jarvis-purple bg-jarvis-purple/10 border-jarvis-purple/20', glow: 'from-jarvis-purple/18' },
  'Strategic Intelligence': { dot: 'bg-cyan-300', badge: 'text-cyan-200 bg-cyan-300/10 border-cyan-300/20', glow: 'from-cyan-300/18' },
}

function MetricTile({ icon: Icon, label, value, tone = 'text-white' }) {
  return (
    <div className="rounded-2xl border border-white/[0.08] bg-white/[0.045] px-4 py-3 shadow-xl shadow-black/10">
      <div className="flex items-center gap-2">
        <Icon size={14} className={tone} />
        <p className={`text-xl font-black ${tone}`}>{value}</p>
      </div>
      <p className="mt-1 text-[10px] uppercase tracking-[0.18em] text-white/35">{label}</p>
    </div>
  )
}

function CapabilityModuleCard({ module }) {
  const [open, setOpen] = useState(false)
  const colors = GROUP_COLORS[module.division] || { dot: 'bg-white/40', badge: 'text-white/50 bg-white/5 border-white/10', glow: 'from-white/10' }

  return (
    <motion.article
      layout
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`relative overflow-hidden rounded-2xl border border-white/[0.08] bg-gradient-to-br ${colors.glow} via-white/[0.045] to-slate-950/30 shadow-2xl shadow-black/20`}
    >
      <div className="absolute -right-10 -top-10 h-32 w-32 rounded-full bg-white/[0.035] blur-2xl" />
      <button className="relative w-full p-5 text-left" onClick={() => setOpen((value) => !value)}>
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-xl border border-white/10 bg-black/20 px-2 py-1 text-[10px] font-black uppercase tracking-[0.22em] text-white/45">
                {String(module.sort_order).padStart(2, '0')} / 25
              </span>
              <span className={`rounded-xl border px-2 py-1 text-[10px] font-bold ${colors.badge}`}>{module.division}</span>
            </div>
            <div className="mt-4 flex items-center gap-3">
              <span className={`h-3 w-3 rounded-full ${colors.dot} shadow-[0_0_18px_currentColor]`} />
              <div>
                <h3 className="text-lg font-black text-white">{module.code}</h3>
                <p className="text-sm font-semibold text-white/72">{module.name}</p>
              </div>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2 text-white/35">
            <span className="hidden rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-[10px] font-bold uppercase tracking-[0.16em] md:block">
              HIA
            </span>
            {open ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </div>
        </div>
        <p className="mt-4 text-sm leading-6 text-white/65">{module.description}</p>
        <div className="mt-4 flex flex-wrap gap-2">
          <span className="rounded-xl border border-jarvis-blue/20 bg-jarvis-blue/10 px-3 py-1 text-xs font-semibold text-jarvis-blue">
            {module.human_interface_executive}
          </span>
          <span className="rounded-xl border border-white/10 bg-white/[0.04] px-3 py-1 text-xs text-white/50">
            DIO monitored
          </span>
          <span className="rounded-xl border border-white/10 bg-white/[0.04] px-3 py-1 text-xs text-white/50">
            Weekly council cycle
          </span>
        </div>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="relative grid gap-3 border-t border-white/[0.07] px-5 pb-5 pt-4 md:grid-cols-2">
              <div className="rounded-xl bg-black/15 p-3">
                <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.2em] text-white/35">Agent Work</p>
                <div className="flex flex-wrap gap-2">
                  {(module.agent_layer || []).map((item) => (
                    <span key={item} className="rounded-lg border border-white/[0.08] bg-white/[0.05] px-2 py-1 text-xs text-white/62">
                      {item}
                    </span>
                  ))}
                </div>
              </div>
              <div className="rounded-xl bg-black/15 p-3">
                <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.2em] text-white/35">KPI Targets</p>
                <div className="flex flex-wrap gap-2">
                  {(module.kpi_targets || []).map((item) => (
                    <span key={item} className="rounded-lg border border-emerald-300/15 bg-emerald-300/10 px-2 py-1 text-xs text-emerald-100/75">
                      {item}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.article>
  )
}

function DataCard({ title, items, icon: Icon }) {
  return (
    <section className="rounded-3xl border border-white/[0.08] bg-white/[0.03] p-5">
      <div className="mb-4 flex items-center gap-2">
        <Icon size={16} className="text-jarvis-blue" />
        <h2 className="text-base font-black text-white">{title}</h2>
      </div>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {items.map((item) => (
          <div key={item.name || item} className="rounded-2xl border border-white/[0.07] bg-black/15 p-3">
            <p className="text-sm font-black text-white">{item.name || item}</p>
            {item.function && <p className="mt-2 text-xs leading-5 text-white/55">{item.function}</p>}
          </div>
        ))}
      </div>
    </section>
  )
}

function KeyValueCard({ title, data, icon: Icon }) {
  return (
    <section className="rounded-3xl border border-white/[0.08] bg-white/[0.03] p-5">
      <div className="mb-4 flex items-center gap-2">
        <Icon size={16} className="text-emerald-300" />
        <h2 className="text-base font-black text-white">{title}</h2>
      </div>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {Object.entries(data || {}).map(([key, value]) => (
          <div key={key} className="rounded-2xl border border-white/[0.07] bg-black/15 p-3">
            <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-white/35">{key.replaceAll('_', ' ')}</p>
            <p className="mt-2 text-sm leading-5 text-white/66">{value}</p>
          </div>
        ))}
      </div>
    </section>
  )
}

export default function ServiceCatalog() {
  const [capabilityCatalog, setCapabilityCatalog] = useState(null)
  const [activeGroup, setActiveGroup] = useState('All')
  const [loading, setLoading] = useState(true)

  const moduleGroups = capabilityCatalog?.groups || []
  const operatingSystem = capabilityCatalog?.operating_system || {}
  const moduleGroupNames = useMemo(() => ['All', ...moduleGroups.map((group) => group.division)], [moduleGroups])
  const visibleModules = useMemo(() => {
    const modules = capabilityCatalog?.modules || []
    return activeGroup === 'All' ? modules : modules.filter((module) => module.division === activeGroup)
  }, [activeGroup, capabilityCatalog])

  useEffect(() => {
    let mounted = true
    getCatalogCapabilityModules()
      .then((data) => {
        if (mounted) setCapabilityCatalog(data)
      })
      .finally(() => {
        if (mounted) setLoading(false)
      })
    return () => {
      mounted = false
    }
  }, [])

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="mx-auto max-w-7xl space-y-6 pb-12">
        <div className="relative overflow-hidden rounded-3xl border border-white/10 bg-[radial-gradient(circle_at_top_left,rgba(0,200,255,0.20),transparent_34%),linear-gradient(135deg,rgba(255,255,255,0.08),rgba(255,255,255,0.03))] p-6 shadow-2xl shadow-black/25">
          <div className="absolute -right-20 -top-24 h-56 w-56 rounded-full bg-jarvis-blue/10 blur-3xl" />
          <div className="relative flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-[11px] font-black uppercase tracking-[0.28em] text-jarvis-blue/80">Final canonical catalog</p>
              <h1 className="mt-2 text-3xl font-black text-white">25 Capability Modules</h1>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-white/58">
                This is the finalized AIONX product architecture: modules, DIOs, HIAs, governance, lifecycle, integrity layers, adaptive learning, and orchestration spine.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <MetricTile icon={Layers3} label="Modules" value={capabilityCatalog?.total || 25} tone="text-jarvis-blue" />
              <MetricTile icon={Briefcase} label="Divisions" value={capabilityCatalog?.division_count || 7} tone="text-emerald-300" />
              <MetricTile icon={Users} label="HIA owners" value={capabilityCatalog?.hia_count || 0} tone="text-amber-300" />
              <MetricTile icon={ShieldCheck} label="Authority" value="Tiered" tone="text-cyan-200" />
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 overflow-x-auto pb-1">
          <Filter size={13} className="shrink-0 text-white/35" />
          {moduleGroupNames.map((group) => {
            const colors = GROUP_COLORS[group]
            const active = activeGroup === group
            return (
              <button
                key={group}
                onClick={() => setActiveGroup(group)}
                className={`flex shrink-0 items-center gap-1.5 rounded-xl border px-3 py-1.5 text-xs font-bold transition-all ${
                  active ? 'border-jarvis-blue/40 bg-jarvis-blue/15 text-jarvis-blue' : 'border-white/[0.07] bg-white/[0.035] text-white/45 hover:text-white/70'
                }`}
              >
                {colors && <span className={`h-1.5 w-1.5 rounded-full ${colors.dot}`} />}
                {group}
              </button>
            )
          })}
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Zap size={20} className="animate-pulse text-jarvis-blue" />
          </div>
        ) : (
          <>
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {visibleModules.map((module) => (
                <CapabilityModuleCard key={module.code} module={module} />
              ))}
            </div>

            <KeyValueCard title="Governance Model" data={capabilityCatalog?.governance_model || {}} icon={ShieldCheck} />
            <KeyValueCard title="Authority Boundaries" data={operatingSystem.authority_boundaries || {}} icon={GitBranch} />
            <DataCard title="8 Operational Integrity Layers" items={operatingSystem.operational_integrity_layers || []} icon={Activity} />
            <DataCard title="8 Client Lifecycle Divisions" items={operatingSystem.client_lifecycle_divisions || []} icon={Users} />
            <DataCard title="9 Sovereign Organs" items={operatingSystem.sovereign_organs || []} icon={Brain} />
            <DataCard title="10 Constitutional Systems" items={operatingSystem.constitutional_systems || []} icon={ShieldCheck} />
            <DataCard title="Adaptive Learning Loop" items={operatingSystem.adaptive_learning_loop || []} icon={Sparkles} />
            <DataCard title="Integration Spine" items={operatingSystem.integration_spine || []} icon={GitBranch} />
          </>
        )}
      </div>
    </div>
  )
}
