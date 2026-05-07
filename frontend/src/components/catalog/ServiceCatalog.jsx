import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Briefcase, Star, ChevronDown, ChevronUp, Tag,
  Clock, DollarSign, Filter, Zap, RefreshCw,
} from 'lucide-react'
import { getCatalogDivisions, getCatalogGroups, getCatalogStats, seedCatalog } from '../../services/api'

const GROUP_COLORS = {
  'Sales & Marketing':       { dot: 'bg-emerald-400',   badge: 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20' },
  'AI Automation':           { dot: 'bg-jarvis-blue',   badge: 'text-jarvis-blue bg-jarvis-blue/10 border-jarvis-blue/20' },
  'Cloud & DevOps':          { dot: 'bg-orange-400',    badge: 'text-orange-400 bg-orange-400/10 border-orange-400/20' },
  'Security':                { dot: 'bg-red-400',       badge: 'text-red-400 bg-red-400/10 border-red-400/20' },
  'Content & Media':         { dot: 'bg-pink-400',      badge: 'text-pink-400 bg-pink-400/10 border-pink-400/20' },
  'Digital Products':        { dot: 'bg-jarvis-purple', badge: 'text-jarvis-purple bg-jarvis-purple/10 border-jarvis-purple/20' },
  'Intelligence & Analytics':{ dot: 'bg-amber-400',     badge: 'text-amber-400 bg-amber-400/10 border-amber-400/20' },
}

const PRICING_LABELS = {
  project:      { label: 'Per Project',   color: 'text-jarvis-blue' },
  retainer:     { label: 'Monthly Retainer', color: 'text-emerald-400' },
  hourly:       { label: 'Hourly',        color: 'text-amber-400' },
  subscription: { label: 'Subscription',  color: 'text-jarvis-purple' },
}

function PriceBadge({ pricing_model, price_range_usd }) {
  const pm = PRICING_LABELS[pricing_model] || { label: pricing_model, color: 'text-white/60' }
  const range = price_range_usd && price_range_usd.min
    ? `$${price_range_usd.min.toLocaleString()} – $${price_range_usd.max.toLocaleString()}`
    : null
  return (
    <div className="flex items-center gap-2 text-xs">
      <DollarSign size={12} className={pm.color} />
      <span className={pm.color}>{pm.label}</span>
      {range && <span className="text-white/40">· {range}</span>}
    </div>
  )
}

function DivisionCard({ d }) {
  const [open, setOpen] = useState(false)
  const colors = GROUP_COLORS[d.division_group] || { dot: 'bg-white/40', badge: 'text-white/50 bg-white/5 border-white/10' }

  return (
    <motion.div
      layout
      className="glass border border-white/[0.07] rounded-xl overflow-hidden hover:border-white/[0.12] transition-colors"
    >
      {/* Header */}
      <button
        className="w-full flex items-start gap-4 p-4 text-left"
        onClick={() => setOpen(o => !o)}
      >
        <div className={`mt-1 w-2 h-2 rounded-full flex-shrink-0 ${colors.dot}`} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-white">{d.name}</span>
            {d.is_featured && (
              <Star size={12} className="text-amber-400 fill-amber-400 flex-shrink-0" />
            )}
          </div>
          <div className="flex items-center gap-3 mt-1.5 flex-wrap">
            <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full border ${colors.badge}`}>
              {d.division_group}
            </span>
            <PriceBadge pricing_model={d.pricing_model} price_range_usd={d.price_range_usd} />
            {d.duration_estimate && (
              <div className="flex items-center gap-1 text-[10px] text-white/40">
                <Clock size={10} />
                {d.duration_estimate}
              </div>
            )}
          </div>
        </div>
        <div className="flex-shrink-0 text-white/30 mt-0.5">
          {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </div>
      </button>

      {/* Expanded */}
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
                    <span key={i} className="text-[10px] text-white/40">{ind}{i < d.target_industries.length - 1 ? ' ·' : ''}</span>
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
  const [activeGroup, setActiveGroup] = useState('All')
  const [featuredOnly, setFeaturedOnly] = useState(false)
  const [loading, setLoading] = useState(true)
  const [seeding, setSeeding] = useState(false)

  const load = async () => {
    try {
      setLoading(true)
      const [divRes, grpRes, statRes] = await Promise.all([
        getCatalogDivisions({ featured_only: featuredOnly }),
        getCatalogGroups(),
        getCatalogStats(),
      ])
      setDivisions(divRes.divisions || [])
      setGroups(['All', ...(grpRes.groups || [])])
      setStats(statRes)
    } catch (_) { /* no-op */ }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [featuredOnly])

  const handleSeed = async () => {
    setSeeding(true)
    try { await seedCatalog(); await load() } catch (_) { /* */ }
    finally { setSeeding(false) }
  }

  const filtered = activeGroup === 'All'
    ? divisions
    : divisions.filter(d => d.division_group === activeGroup)

  return (
    <div className="h-full flex flex-col overflow-hidden p-6 space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Service Catalog</h1>
          <p className="text-xs text-white/40 mt-0.5">Aliyar Solutions — 30 Global Service Divisions</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setFeaturedOnly(f => !f)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-all
              ${featuredOnly
                ? 'bg-amber-400/15 border-amber-400/30 text-amber-400'
                : 'bg-white/[0.03] border-white/[0.08] text-white/50 hover:text-white/70'}`}
          >
            <Star size={12} />
            Featured
          </button>
          <button
            onClick={handleSeed}
            disabled={seeding}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border
                       bg-white/[0.03] border-white/[0.08] text-white/50 hover:text-white/70 transition-all"
          >
            <RefreshCw size={12} className={seeding ? 'animate-spin' : ''} />
            Seed
          </button>
        </div>
      </div>

      {/* Stats row */}
      {stats && (
        <div className="grid grid-cols-4 gap-3">
          {[
            { label: 'Total Services', value: stats.total, color: 'text-white' },
            { label: 'Active', value: stats.active, color: 'text-emerald-400' },
            { label: 'Featured', value: stats.featured, color: 'text-amber-400' },
            { label: 'Divisions', value: Object.keys(stats.groups || {}).length, color: 'text-jarvis-blue' },
          ].map(({ label, value, color }) => (
            <div key={label} className="glass border border-white/[0.07] rounded-xl px-4 py-3">
              <p className={`text-lg font-bold ${color}`}>{value}</p>
              <p className="text-[10px] text-white/40 mt-0.5">{label}</p>
            </div>
          ))}
        </div>
      )}

      {/* Group filter tabs */}
      <div className="flex items-center gap-2 overflow-x-auto no-scrollbar pb-1">
        <Filter size={12} className="text-white/30 flex-shrink-0" />
        {groups.map(g => {
          const colors = GROUP_COLORS[g]
          const active = activeGroup === g
          return (
            <button
              key={g}
              onClick={() => setActiveGroup(g)}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium whitespace-nowrap border transition-all
                ${active
                  ? 'bg-jarvis-blue/15 border-jarvis-blue/30 text-jarvis-blue'
                  : 'bg-white/[0.03] border-white/[0.06] text-white/40 hover:text-white/60'}`}
            >
              {colors && <span className={`w-1.5 h-1.5 rounded-full ${colors.dot}`} />}
              {g}
            </button>
          )
        })}
      </div>

      {/* Division list */}
      <div className="flex-1 overflow-y-auto no-scrollbar space-y-2 pr-1">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Zap size={20} className="text-jarvis-blue animate-pulse" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 space-y-2">
            <Briefcase size={24} className="text-white/20" />
            <p className="text-sm text-white/30">No services in this category</p>
            <button onClick={handleSeed} className="text-xs text-jarvis-blue hover:underline">
              Seed catalog
            </button>
          </div>
        ) : (
          <AnimatePresence initial={false}>
            {filtered.map(d => (
              <motion.div
                key={d.code}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.15 }}
              >
                <DivisionCard d={d} />
              </motion.div>
            ))}
          </AnimatePresence>
        )}
      </div>
    </div>
  )
}
