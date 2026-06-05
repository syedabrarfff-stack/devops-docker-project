import React, { useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import {
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
  Zap,
} from 'lucide-react'
import {
  getCatalogDivisions,
  getCatalogGroups,
  getCatalogStats,
  getIntelligencePricingCatalog,
  getPricingMatrix,
  seedCatalog,
} from '../../services/api'

const GROUP_COLORS = {
  'Sales & Marketing': { dot: 'bg-emerald-400', badge: 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20' },
  'AI Automation': { dot: 'bg-jarvis-blue', badge: 'text-jarvis-blue bg-jarvis-blue/10 border-jarvis-blue/20' },
  'Cloud & DevOps': { dot: 'bg-orange-400', badge: 'text-orange-400 bg-orange-400/10 border-orange-400/20' },
  Security: { dot: 'bg-red-400', badge: 'text-red-400 bg-red-400/10 border-red-400/20' },
  'Content & Media': { dot: 'bg-pink-400', badge: 'text-pink-400 bg-pink-400/10 border-pink-400/20' },
  'Digital Products': { dot: 'bg-jarvis-purple', badge: 'text-jarvis-purple bg-jarvis-purple/10 border-jarvis-purple/20' },
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

function TierCard({ name, tier }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-jarvis-blue/20 bg-gradient-to-br from-jarvis-blue/15 via-white/[0.045] to-emerald-400/[0.04] p-5 shadow-2xl shadow-black/20"
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-jarvis-blue/75">{name}</p>
          <h3 className="mt-1 text-2xl font-black text-white">{money(tier.price_per_month)}/mo</h3>
          <p className="mt-1 text-xs text-white/45">Projects: {tier.project_range}</p>
        </div>
        <ShieldCheck size={21} className="text-emerald-300" />
      </div>
      <p className="mt-4 text-sm leading-5 text-white/68">{tier.best_for}</p>
      <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
        {[
          ['Team', tier.team_members],
          ['Services', tier.services],
          ['Response', tier.response_time],
          ['Reporting', tier.reporting],
        ].map(([label, value]) => (
          <div key={label} className="rounded-xl bg-white/[0.05] p-2">
            <p className="text-white/35">{label}</p>
            <p className="font-semibold text-white">{value}</p>
          </div>
        ))}
      </div>
    </motion.div>
  )
}

function ProjectPackageCard({ packageKey, pkg }) {
  return (
    <div className="rounded-xl border border-white/[0.07] bg-white/[0.035] p-3 hover:border-jarvis-blue/25 transition-colors">
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
    <motion.div layout className="glass border border-white/[0.07] rounded-xl overflow-hidden hover:border-white/[0.12] transition-colors">
      <button className="w-full flex items-start gap-4 p-4 text-left" onClick={() => setOpen((o) => !o)}>
        <div className={`mt-1 w-2 h-2 rounded-full flex-shrink-0 ${colors.dot}`} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-white">{d.name}</span>
            {d.is_featured && <Star size={12} className="text-amber-400 fill-amber-400 flex-shrink-0" />}
          </div>
          <div className="flex items-center gap-3 mt-1.5 flex-wrap">
            <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full border ${colors.badge}`}>{d.division_group}</span>
            <PriceBadge pricing_model={d.pricing_model} price_range_usd={d.price_range_usd} />
            {d.duration_estimate && (
              <div className="flex items-center gap-1 text-[10px] text-white/40">
                <Clock size={10} />
                {d.duration_estimate}
              </div>
            )}
          </div>
        </div>
        <div className="flex-shrink-0 text-white/30 mt-0.5">{open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}</div>
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
            <div className="px-4 pb-4 border-t border-white/[0.05] pt-3 space-y-3">
              <p className="text-xs text-white/60 leading-relaxed">{d.description}</p>
              {d.deliverables?.length > 0 && (
                <div>
                  <p className="text-[10px] font-semibold text-white/40 uppercase tracking-wider mb-1.5">Deliverables</p>
                  <div className="flex flex-wrap gap-1.5">
                    {d.deliverables.map((item, i) => (
                      <span key={i} className="text-[10px] px-2 py-0.5 rounded-md bg-white/[0.05] text-white/60 border border-white/[0.07]">
                        {item}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {d.technologies?.length > 0 && (
                <div>
                  <p className="text-[10px] font-semibold text-white/40 uppercase tracking-wider mb-1.5">Technologies</p>
                  <div className="flex flex-wrap gap-1.5">
                    {d.technologies.map((tech, i) => (
                      <span key={i} className="text-[10px] px-2 py-0.5 rounded-md bg-jarvis-blue/10 text-jarvis-blue border border-jarvis-blue/20">
                        {tech}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {d.target_industries?.length > 0 && (
                <div className="flex items-center gap-1.5 flex-wrap">
                  <Tag size={10} className="text-white/30" />
                  {d.target_industries.map((ind, i) => (
                    <span key={i} className="text-[10px] text-white/40">{ind}{i < d.target_industries.length - 1 ? ' -' : ''}</span>
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
  const [activeGroup, setActiveGroup] = useState('All')
  const [featuredOnly, setFeaturedOnly] = useState(false)
  const [loading, setLoading] = useState(true)
  const [seeding, setSeeding] = useState(false)

  const load = async () => {
    try {
      setLoading(true)
      const [divRes, grpRes, statRes, matrixRes, packageRes] = await Promise.all([
        getCatalogDivisions({ featured_only: featuredOnly }),
        getCatalogGroups(),
        getCatalogStats(),
        getPricingMatrix(),
        getIntelligencePricingCatalog(),
      ])
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

  const filtered = activeGroup === 'All' ? divisions : divisions.filter((d) => d.division_group === activeGroup)

  return (
    <div className="h-full flex flex-col overflow-hidden p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">New Service Packages</h1>
          <p className="text-xs text-white/40 mt-0.5">Aliyar Solutions pricing catalog - packages first, capability library second</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setFeaturedOnly((f) => !f)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
              featuredOnly
                ? 'bg-amber-400/15 border-amber-400/30 text-amber-400'
                : 'bg-white/[0.03] border-white/[0.08] text-white/50 hover:text-white/70'
            }`}
          >
            <Star size={12} />
            Featured capabilities
          </button>
          <button
            onClick={handleSeed}
            disabled={seeding}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border bg-white/[0.03] border-white/[0.08] text-white/50 hover:text-white/70 transition-all"
          >
            <RefreshCw size={12} className={seeding ? 'animate-spin' : ''} />
            Sync library
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Zap size={20} className="text-jarvis-blue animate-pulse" />
        </div>
      ) : (
        <>
          <div className="grid gap-4 xl:grid-cols-3">
            {Object.entries(pricingCatalog?.tiers || {}).map(([name, tier]) => (
              <TierCard key={name} name={name} tier={tier} />
            ))}
          </div>

          {pricingMatrix && (
            <div className="glass border border-white/[0.07] rounded-2xl p-5 space-y-4 overflow-visible">
              <div className="flex items-center gap-2">
                <Layers3 size={16} className="text-jarvis-blue" />
                <div>
                  <h2 className="text-base font-bold text-white">Project Packages</h2>
                  <p className="text-xs text-white/40">{pricingMatrix.pricing_philosophy}</p>
                </div>
              </div>
              <div className="grid gap-4">
                {Object.entries(pricingMatrix.tiers || {}).map(([tierKey, tier]) => (
                  <ProjectTierSection key={tierKey} tierKey={tierKey} tier={tier} />
                ))}
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <div className="rounded-xl border border-white/[0.07] bg-white/[0.035] p-3">
                  <p className="text-xs font-bold uppercase tracking-[0.2em] text-white/35">Payment Terms</p>
                  <p className="mt-2 text-sm text-white/65">{pricingMatrix.payment_terms}</p>
                </div>
                <div className="rounded-xl border border-white/[0.07] bg-white/[0.035] p-3">
                  <p className="text-xs font-bold uppercase tracking-[0.2em] text-white/35">Add-ons</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {Object.entries(pricingCatalog?.add_ons || {}).map(([key, value]) => (
                      <span key={key} className="rounded-lg border border-white/[0.08] bg-white/[0.04] px-2 py-1 text-xs text-white/60">
                        {key.replaceAll('_', ' ')}: {money(value)}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
              {pricingCatalog?.pricing_notes?.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {pricingCatalog.pricing_notes.map((note) => (
                    <span key={note} className="rounded-full border border-amber-300/20 bg-amber-300/10 px-3 py-1 text-[11px] text-amber-100/80">
                      {note}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}

          {stats && (
            <div className="grid grid-cols-4 gap-3">
              {[
                { label: 'Capabilities', value: stats.total, color: 'text-white' },
                { label: 'Active', value: stats.active, color: 'text-emerald-400' },
                { label: 'Featured', value: stats.featured, color: 'text-amber-400' },
                { label: 'Groups', value: Object.keys(stats.groups || {}).length, color: 'text-jarvis-blue' },
              ].map(({ label, value, color }) => (
                <div key={label} className="glass border border-white/[0.07] rounded-xl px-4 py-3">
                  <p className={`text-lg font-bold ${color}`}>{value}</p>
                  <p className="text-[10px] text-white/40 mt-0.5">{label}</p>
                </div>
              ))}
            </div>
          )}

          <div>
            <h2 className="text-base font-bold text-white">Capability Library</h2>
            <p className="text-xs text-white/40">Supporting service divisions used by proposals, routing, and delivery scoping.</p>
          </div>

          <div className="flex items-center gap-2 overflow-x-auto no-scrollbar pb-1">
            <Filter size={12} className="text-white/30 flex-shrink-0" />
            {groups.map((g) => {
              const colors = GROUP_COLORS[g]
              const active = activeGroup === g
              return (
                <button
                  key={g}
                  onClick={() => setActiveGroup(g)}
                  className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium whitespace-nowrap border transition-all ${
                    active
                      ? 'bg-jarvis-blue/15 border-jarvis-blue/30 text-jarvis-blue'
                      : 'bg-white/[0.03] border-white/[0.06] text-white/40 hover:text-white/60'
                  }`}
                >
                  {colors && <span className={`w-1.5 h-1.5 rounded-full ${colors.dot}`} />}
                  {g}
                </button>
              )
            })}
          </div>

          <div className="min-h-[280px] flex-1 overflow-y-auto no-scrollbar space-y-2 pr-1">
            {filtered.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 space-y-2">
                <Briefcase size={24} className="text-white/20" />
                <p className="text-sm text-white/30">No capabilities in this category</p>
                <button onClick={handleSeed} className="text-xs text-jarvis-blue hover:underline">
                  Sync capability library
                </button>
              </div>
            ) : (
              <AnimatePresence initial={false}>
                {filtered.map((d) => (
                  <motion.div key={d.code} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.15 }}>
                    <DivisionCard d={d} />
                  </motion.div>
                ))}
              </AnimatePresence>
            )}
          </div>
        </>
      )}
    </div>
  )
}
