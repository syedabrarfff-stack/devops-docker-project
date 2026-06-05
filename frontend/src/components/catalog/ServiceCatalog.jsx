import React, { useEffect, useMemo, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import {
  Activity,
  Briefcase,
  ChevronDown,
  ChevronUp,
  Clock,
  DollarSign,
  Filter,
  Layers3,
  RefreshCw,
  ShieldCheck,
  Star,
  Tag,
  Users,
  Zap,
} from 'lucide-react'
import {
  getCatalogCapabilityModules,
  getCatalogDivisions,
  getCatalogGroups,
  getCatalogStats,
  getIntelligencePricingCatalog,
  getPricingMatrix,
  seedCatalog,
} from '../../services/api'

const GROUP_COLORS = {
  'Revenue Operations': { dot: 'bg-emerald-400', badge: 'text-emerald-300 bg-emerald-400/10 border-emerald-400/20', glow: 'from-emerald-400/18' },
  'AI Automation': { dot: 'bg-jarvis-blue', badge: 'text-jarvis-blue bg-jarvis-blue/10 border-jarvis-blue/20', glow: 'from-jarvis-blue/20' },
  'Cloud & DevOps': { dot: 'bg-orange-400', badge: 'text-orange-300 bg-orange-400/10 border-orange-400/20', glow: 'from-orange-400/18' },
  'Security & Compliance': { dot: 'bg-red-400', badge: 'text-red-300 bg-red-400/10 border-red-400/20', glow: 'from-red-400/18' },
  'Intelligence & Data': { dot: 'bg-amber-400', badge: 'text-amber-300 bg-amber-400/10 border-amber-400/20', glow: 'from-amber-400/18' },
  'Digital Products': { dot: 'bg-jarvis-purple', badge: 'text-jarvis-purple bg-jarvis-purple/10 border-jarvis-purple/20', glow: 'from-jarvis-purple/18' },
  'Strategic Intelligence': { dot: 'bg-cyan-300', badge: 'text-cyan-200 bg-cyan-300/10 border-cyan-300/20', glow: 'from-cyan-300/18' },
  'Sales & Marketing': { dot: 'bg-emerald-400', badge: 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20' },
  Security: { dot: 'bg-red-400', badge: 'text-red-400 bg-red-400/10 border-red-400/20' },
  'Content & Media': { dot: 'bg-pink-400', badge: 'text-pink-400 bg-pink-400/10 border-pink-400/20' },
  'Intelligence & Analytics': { dot: 'bg-amber-400', badge: 'text-amber-400 bg-amber-400/10 border-amber-400/20' },
}

const PRICING_LABELS = {
  project: { label: 'Per Project', color: 'text-jarvis-blue' },
  retainer: { label: 'Monthly Retainer', color: 'text-emerald-400' },
  hourly: { label: 'Hourly', color: 'text-amber-400' },
  subscription: { label: 'Subscription', color: 'text-jarvis-purple' },
}

function money(value) {
  if (value === null || value === undefined || value === '') return '-'
  return `$${Number(value).toLocaleString()}`
}

function PriceBadge({ pricing_model, price_range_usd }) {
  const pm = PRICING_LABELS[pricing_model] || { label: pricing_model, color: 'text-white/60' }
  const range = price_range_usd?.min ? `${money(price_range_usd.min)} - ${money(price_range_usd.max)}` : null
  return (
    <div className="flex items-center gap-2 text-xs">
      <DollarSign size={12} className={pm.color} />
      <span className={pm.color}>{pm.label}</span>
      {range && <span className="text-white/40">- {range}</span>}
    </div>
  )
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

function TierCard({ name, tier }) {
  return (
    <div className="rounded-2xl border border-white/[0.08] bg-white/[0.04] p-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-jarvis-blue/75">{name}</p>
          <h3 className="mt-1 text-xl font-black text-white">{money(tier.price_per_month)}/mo</h3>
          <p className="mt-1 text-xs text-white/45">Projects: {tier.project_range}</p>
        </div>
        <ShieldCheck size={18} className="text-emerald-300" />
      </div>
      <p className="mt-3 text-xs leading-5 text-white/58">{tier.best_for}</p>
    </div>
  )
}

function ProjectPackageCard({ packageKey, pkg }) {
  return (
    <div className="rounded-xl border border-white/[0.07] bg-white/[0.035] p-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-bold text-white">{pkg.label}</p>
          <p className="mt-1 text-[10px] uppercase tracking-[0.16em] text-white/35">{packageKey.replaceAll('_', ' ')}</p>
        </div>
        <p className="text-sm font-black text-emerald-300">{money(pkg.price)}</p>
      </div>
      <p className="mt-2 flex items-center gap-1 text-xs text-white/45">
        <Clock size={11} />
        {pkg.delivery}
      </p>
    </div>
  )
}

function ProjectTierSection({ tierKey, tier }) {
  return (
    <section className="rounded-2xl border border-white/[0.07] bg-white/[0.035] p-4">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-white/35">{tierKey}</p>
          <h3 className="text-lg font-black text-white">{tier.label}</h3>
          <p className="text-xs text-white/45">{tier.monthly_revenue_range}</p>
        </div>
        <div className="rounded-xl border border-emerald-300/20 bg-emerald-300/10 px-3 py-2 text-xs text-emerald-200">
          {tier.retainer?.label}: {money(tier.retainer?.min)}-{money(tier.retainer?.max)}/mo
        </div>
      </div>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {Object.entries(tier.packages || {}).map(([key, pkg]) => (
          <ProjectPackageCard key={key} packageKey={key} pkg={pkg} />
        ))}
      </div>
    </section>
  )
}

function DivisionCard({ d }) {
  const [open, setOpen] = useState(false)
  const colors = GROUP_COLORS[d.division_group] || { dot: 'bg-white/40', badge: 'text-white/50 bg-white/5 border-white/10' }

  return (
    <motion.div layout className="glass overflow-hidden rounded-xl border border-white/[0.07] transition-colors hover:border-white/[0.12]">
      <button className="flex w-full items-start gap-4 p-4 text-left" onClick={() => setOpen((o) => !o)}>
        <div className={`mt-1 h-2 w-2 flex-shrink-0 rounded-full ${colors.dot}`} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-semibold text-white">{d.name}</span>
            {d.is_featured && <Star size={12} className="flex-shrink-0 fill-amber-400 text-amber-400" />}
          </div>
          <div className="mt-1.5 flex flex-wrap items-center gap-3">
            <span className={`rounded-full border px-2 py-0.5 text-[10px] font-medium ${colors.badge}`}>{d.division_group}</span>
            <PriceBadge pricing_model={d.pricing_model} price_range_usd={d.price_range_usd} />
            {d.duration_estimate && (
              <div className="flex items-center gap-1 text-[10px] text-white/40">
                <Clock size={10} />
                {d.duration_estimate}
              </div>
            )}
          </div>
        </div>
        <div className="mt-0.5 flex-shrink-0 text-white/30">{open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}</div>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.2 }} className="overflow-hidden">
            <div className="space-y-3 border-t border-white/[0.05] px-4 pb-4 pt-3">
              <p className="text-xs leading-relaxed text-white/60">{d.description}</p>
              {d.deliverables?.length > 0 && (
                <div>
                  <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-white/40">Deliverables</p>
                  <div className="flex flex-wrap gap-1.5">
                    {d.deliverables.map((item) => (
                      <span key={item} className="rounded-md border border-white/[0.07] bg-white/[0.05] px-2 py-0.5 text-[10px] text-white/60">
                        {item}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {d.target_industries?.length > 0 && (
                <div className="flex flex-wrap items-center gap-1.5">
                  <Tag size={10} className="text-white/30" />
                  {d.target_industries.map((ind) => (
                    <span key={ind} className="text-[10px] text-white/40">{ind}</span>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

export default function ServiceCatalog() {
  const [divisions, setDivisions] = useState([])
  const [groups, setGroups] = useState([])
  const [stats, setStats] = useState(null)
  const [pricingMatrix, setPricingMatrix] = useState(null)
  const [pricingCatalog, setPricingCatalog] = useState(null)
  const [capabilityCatalog, setCapabilityCatalog] = useState(null)
  const [activeGroup, setActiveGroup] = useState('All')
  const [legacyGroup, setLegacyGroup] = useState('All')
  const [featuredOnly, setFeaturedOnly] = useState(false)
  const [loading, setLoading] = useState(true)
  const [seeding, setSeeding] = useState(false)

  const moduleGroups = capabilityCatalog?.groups || []
  const moduleGroupNames = useMemo(() => ['All', ...moduleGroups.map((group) => group.division)], [moduleGroups])
  const visibleModules = useMemo(() => {
    const modules = capabilityCatalog?.modules || []
    return activeGroup === 'All' ? modules : modules.filter((module) => module.division === activeGroup)
  }, [activeGroup, capabilityCatalog])

  const load = async () => {
    try {
      setLoading(true)
      const [moduleRes, divRes, grpRes, statRes, matrixRes, packageRes] = await Promise.all([
        getCatalogCapabilityModules(),
        getCatalogDivisions({ featured_only: featuredOnly }),
        getCatalogGroups(),
        getCatalogStats(),
        getPricingMatrix(),
        getIntelligencePricingCatalog(),
      ])
      setCapabilityCatalog(moduleRes)
      setDivisions(divRes.divisions || [])
      setGroups(['All', ...(grpRes.groups || [])])
      setStats(statRes)
      setPricingMatrix(matrixRes)
      setPricingCatalog(packageRes)
    } catch (_) {
      // Keep UI usable if one operational endpoint is temporarily unavailable.
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [featuredOnly])

  const handleSeed = async () => {
    setSeeding(true)
    try {
      await seedCatalog()
      await load()
    } catch (_) {
      // no-op
    } finally {
      setSeeding(false)
    }
  }

  const filteredLegacy = legacyGroup === 'All' ? divisions : divisions.filter((d) => d.division_group === legacyGroup)

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="mx-auto max-w-7xl space-y-6 pb-12">
        <div className="relative overflow-hidden rounded-3xl border border-white/10 bg-[radial-gradient(circle_at_top_left,rgba(0,200,255,0.20),transparent_34%),linear-gradient(135deg,rgba(255,255,255,0.08),rgba(255,255,255,0.03))] p-6 shadow-2xl shadow-black/25">
          <div className="absolute -right-20 -top-24 h-56 w-56 rounded-full bg-jarvis-blue/10 blur-3xl" />
          <div className="relative flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-[11px] font-black uppercase tracking-[0.28em] text-jarvis-blue/80">Canonical catalog</p>
              <h1 className="mt-2 text-3xl font-black text-white">25 Capability Modules</h1>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-white/58">
                The new Aliyar Solutions catalog: 25 service modules, each with a DIO, HIA, agent execution layer, KPI targets, weekly council cycle, and health visibility.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <MetricTile icon={Layers3} label="Modules" value={capabilityCatalog?.total || 25} tone="text-jarvis-blue" />
              <MetricTile icon={Briefcase} label="Divisions" value={capabilityCatalog?.division_count || 7} tone="text-emerald-300" />
              <MetricTile icon={Users} label="HIA owners" value={capabilityCatalog?.hia_count || 0} tone="text-amber-300" />
              <MetricTile icon={Activity} label="Governance" value="DIO" tone="text-cyan-200" />
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

            <section className="rounded-3xl border border-white/[0.08] bg-white/[0.035] p-5">
              <div className="mb-4 flex items-center gap-2">
                <ShieldCheck size={16} className="text-emerald-300" />
                <div>
                  <h2 className="text-base font-black text-white">Governance Model</h2>
                  <p className="text-xs text-white/42">Every module is controlled, observable, and client-readable.</p>
                </div>
              </div>
              <div className="grid gap-3 md:grid-cols-5">
                {Object.entries(capabilityCatalog?.governance_model || {}).map(([key, value]) => (
                  <div key={key} className="rounded-2xl border border-white/[0.07] bg-black/15 p-3">
                    <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-white/35">{key.replaceAll('_', ' ')}</p>
                    <p className="mt-2 text-sm font-semibold text-white/72">{value}</p>
                  </div>
                ))}
              </div>
            </section>

            <section className="rounded-3xl border border-white/[0.08] bg-white/[0.03] p-5">
              <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h2 className="text-base font-black text-white">Commercial Tiers</h2>
                  <p className="text-xs text-white/42">Pricing wrappers that sit above the 25 operational modules.</p>
                </div>
              </div>
              <div className="grid gap-4 xl:grid-cols-3">
                {Object.entries(pricingCatalog?.tiers || {}).map(([name, tier]) => (
                  <TierCard key={name} name={name} tier={tier} />
                ))}
              </div>
            </section>

            {pricingMatrix && (
              <section className="rounded-3xl border border-white/[0.08] bg-white/[0.03] p-5">
                <div className="mb-4 flex items-center gap-2">
                  <Layers3 size={16} className="text-jarvis-blue" />
                  <div>
                    <h2 className="text-base font-black text-white">Project Package Matrix</h2>
                    <p className="text-xs text-white/42">{pricingMatrix.pricing_philosophy}</p>
                  </div>
                </div>
                <div className="grid gap-4">
                  {Object.entries(pricingMatrix.tiers || {}).map(([tierKey, tier]) => (
                    <ProjectTierSection key={tierKey} tierKey={tierKey} tier={tier} />
                  ))}
                </div>
              </section>
            )}

            <section className="rounded-3xl border border-white/[0.08] bg-white/[0.03] p-5">
              <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h2 className="text-base font-black text-white">Legacy Capability Library</h2>
                  <p className="text-xs text-white/42">Older 30-service division library retained for proposal detail and delivery scoping.</p>
                </div>
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => setFeaturedOnly((f) => !f)}
                    className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition-all ${
                      featuredOnly ? 'border-amber-400/30 bg-amber-400/15 text-amber-400' : 'border-white/[0.08] bg-white/[0.03] text-white/50 hover:text-white/70'
                    }`}
                  >
                    <Star size={12} />
                    Featured
                  </button>
                  <button
                    onClick={handleSeed}
                    disabled={seeding}
                    className="flex items-center gap-1.5 rounded-lg border border-white/[0.08] bg-white/[0.03] px-3 py-1.5 text-xs font-medium text-white/50 transition-all hover:text-white/70"
                  >
                    <RefreshCw size={12} className={seeding ? 'animate-spin' : ''} />
                    Sync
                  </button>
                </div>
              </div>

              {stats && (
                <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-4">
                  <MetricTile icon={Briefcase} label="Legacy services" value={stats.total} />
                  <MetricTile icon={Activity} label="Active" value={stats.active} tone="text-emerald-300" />
                  <MetricTile icon={Star} label="Featured" value={stats.featured} tone="text-amber-300" />
                  <MetricTile icon={Layers3} label="Groups" value={Object.keys(stats.groups || {}).length} tone="text-jarvis-blue" />
                </div>
              )}

              <div className="mb-4 flex items-center gap-2 overflow-x-auto pb-1">
                <Filter size={12} className="shrink-0 text-white/30" />
                {groups.map((g) => {
                  const colors = GROUP_COLORS[g]
                  const active = legacyGroup === g
                  return (
                    <button
                      key={g}
                      onClick={() => setLegacyGroup(g)}
                      className={`flex shrink-0 items-center gap-1.5 rounded-lg border px-3 py-1 text-xs font-medium transition-all ${
                        active ? 'border-jarvis-blue/30 bg-jarvis-blue/15 text-jarvis-blue' : 'border-white/[0.06] bg-white/[0.03] text-white/40 hover:text-white/60'
                      }`}
                    >
                      {colors && <span className={`h-1.5 w-1.5 rounded-full ${colors.dot}`} />}
                      {g}
                    </button>
                  )
                })}
              </div>

              <div className="space-y-2">
                {filteredLegacy.length === 0 ? (
                  <div className="flex flex-col items-center justify-center space-y-2 py-16">
                    <Briefcase size={24} className="text-white/20" />
                    <p className="text-sm text-white/30">No capabilities in this category</p>
                  </div>
                ) : (
                  <AnimatePresence initial={false}>
                    {filteredLegacy.map((d) => (
                      <motion.div key={d.code} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.15 }}>
                        <DivisionCard d={d} />
                      </motion.div>
                    ))}
                  </AnimatePresence>
                )}
              </div>
            </section>
          </>
        )}
      </div>
    </div>
  )
}
