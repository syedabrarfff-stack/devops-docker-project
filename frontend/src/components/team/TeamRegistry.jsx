import React, { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Users, Mail, Phone, Linkedin, Briefcase, Tag,
  RefreshCw, UserCheck, Building2, ChevronDown, ChevronUp, Zap,
} from 'lucide-react'
import { getTeamMembers, getTeamStats, seedTeam } from '../../services/api'

const STYLE_COLORS = {
  warm:          { bg: 'bg-amber-500/10',   border: 'border-amber-500/20',   text: 'text-amber-400'   },
  consultative:  { bg: 'bg-jarvis-blue/10', border: 'border-jarvis-blue/20', text: 'text-jarvis-blue' },
  technical:     { bg: 'bg-purple-500/10',  border: 'border-purple-500/20',  text: 'text-purple-400'  },
  direct:        { bg: 'bg-red-500/10',     border: 'border-red-500/20',     text: 'text-red-400'     },
}

function MemberCard({ member }) {
  const [expanded, setExpanded] = useState(false)
  const style = STYLE_COLORS[member.communication_style] || STYLE_COLORS.consultative

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass rounded-xl border border-white/[0.06] overflow-hidden"
    >
      {/* Header */}
      <div className="p-5">
        <div className="flex items-start gap-4">
          {/* Avatar */}
          <div className={`w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0
                          ${style.bg} border ${style.border}`}>
            <span className={`text-lg font-bold ${style.text}`}>
              {member.first_name[0]}{member.name.split(' ')[1]?.[0]}
            </span>
          </div>

          {/* Name + role */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="font-semibold text-white text-sm">{member.name}</h3>
              <span className={`text-[10px] px-2 py-0.5 rounded-full border font-medium
                               ${style.bg} ${style.border} ${style.text}`}>
                {member.communication_style}
              </span>
              {!member.is_active && (
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-white/5 text-white/40 border border-white/10">
                  inactive
                </span>
              )}
            </div>
            <p className="text-xs text-jarvis-blue mt-0.5">{member.role}</p>
            <p className="text-xs text-white/40 flex items-center gap-1 mt-0.5">
              <Building2 size={10} />
              {member.department}
            </p>
          </div>

          <button
            onClick={() => setExpanded(e => !e)}
            className="text-white/30 hover:text-white/70 transition-colors mt-1"
          >
            {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
        </div>

        {/* Contact row */}
        <div className="flex items-center gap-4 mt-3 flex-wrap">
          <a href={`mailto:${member.email}`}
             className="flex items-center gap-1.5 text-xs text-white/50 hover:text-white/80 transition-colors">
            <Mail size={12} />
            {member.email}
          </a>
          {member.phone && (
            <span className="flex items-center gap-1.5 text-xs text-white/50">
              <Phone size={12} />
              {member.phone}
            </span>
          )}
        </div>

        {/* Service categories */}
        <div className="flex flex-wrap gap-1.5 mt-3">
          {(member.service_categories || []).slice(0, 6).map(cat => (
            <span key={cat}
              className="text-[10px] px-2 py-0.5 rounded bg-white/[0.05] text-white/50 border border-white/[0.08]">
              {cat}
            </span>
          ))}
          {(member.service_categories || []).length > 6 && (
            <span className="text-[10px] text-white/30">+{member.service_categories.length - 6} more</span>
          )}
        </div>
      </div>

      {/* Expanded detail */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden border-t border-white/[0.06]"
          >
            <div className="p-5 space-y-4">
              {/* Specializations */}
              {member.specializations?.length > 0 && (
                <div>
                  <p className="text-[10px] text-white/30 uppercase tracking-wider mb-2 flex items-center gap-1">
                    <Tag size={10} /> Specializations
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {member.specializations.map(s => (
                      <span key={s} className="text-xs px-2 py-0.5 rounded bg-jarvis-blue/10
                                               border border-jarvis-blue/20 text-jarvis-blue/80">
                        {s}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Personality traits */}
              {member.personality_traits?.length > 0 && (
                <div>
                  <p className="text-[10px] text-white/30 uppercase tracking-wider mb-2 flex items-center gap-1">
                    <UserCheck size={10} /> Personality
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {member.personality_traits.map(t => (
                      <span key={t} className="text-xs px-2 py-0.5 rounded bg-white/[0.04]
                                               border border-white/[0.08] text-white/50">
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Email signature preview */}
              {member.email_signature && (
                <div>
                  <p className="text-[10px] text-white/30 uppercase tracking-wider mb-2 flex items-center gap-1">
                    <Mail size={10} /> Email Signature
                  </p>
                  <pre className="text-xs text-white/50 font-mono whitespace-pre-wrap
                                  bg-white/[0.03] rounded-lg p-3 border border-white/[0.06]">
                    {member.email_signature}
                  </pre>
                </div>
              )}

              {/* LinkedIn */}
              {member.linkedin && (
                <div className="flex items-center gap-1.5 text-xs text-jarvis-blue/70">
                  <Linkedin size={12} />
                  <span>{member.linkedin}</span>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

function StatCard({ label, value, icon: Icon, color = 'blue' }) {
  const colors = {
    blue:   'text-jarvis-blue',
    purple: 'text-purple-400',
    amber:  'text-amber-400',
    green:  'text-emerald-400',
  }
  return (
    <div className="glass rounded-xl border border-white/[0.06] p-4">
      <div className="flex items-center gap-2 mb-1">
        <Icon size={14} className={colors[color]} />
        <span className="text-xs text-white/40">{label}</span>
      </div>
      <p className={`text-2xl font-bold ${colors[color]}`}>{value}</p>
    </div>
  )
}

export default function TeamRegistry() {
  const [members, setMembers] = useState([])
  const [stats, setStats]     = useState(null)
  const [loading, setLoading] = useState(true)
  const [seeding, setSeeding] = useState(false)
  const [filter, setFilter]   = useState('all')

  const load = async () => {
    setLoading(true)
    try {
      const [membersRes, statsRes] = await Promise.all([
        getTeamMembers(),
        getTeamStats(),
      ])
      setMembers(membersRes.members || [])
      setStats(statsRes)
    } catch {
      // swallow — empty state shown
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const handleSeed = async () => {
    setSeeding(true)
    try {
      await seedTeam()
      await load()
    } finally {
      setSeeding(false)
    }
  }

  const departments = ['all', ...new Set(members.map(m => m.department))]
  const visible = filter === 'all' ? members : members.filter(m => m.department === filter)

  return (
    <div className="h-full overflow-y-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Users size={20} className="text-jarvis-blue" />
            Team Registry
          </h1>
          <p className="text-xs text-white/40 mt-1">
            Aliyar Solutions human identity system — all client-facing personas
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={load}
            className="p-2 glass rounded-lg border border-white/[0.06] text-white/40
                       hover:text-white/70 transition-colors"
          >
            <RefreshCw size={14} />
          </button>
          {members.length === 0 && (
            <button
              onClick={handleSeed}
              disabled={seeding}
              className="px-4 py-2 bg-jarvis-blue/20 hover:bg-jarvis-blue/30 border border-jarvis-blue/30
                         rounded-lg text-jarvis-blue text-xs font-medium transition-all
                         flex items-center gap-2 disabled:opacity-50"
            >
              <Zap size={12} />
              {seeding ? 'Seeding…' : 'Seed Team'}
            </button>
          )}
        </div>
      </div>

      {/* Stats row */}
      {stats && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard label="Total Members"    value={stats.total}          icon={Users}      color="blue"   />
          <StatCard label="Active"           value={stats.active}         icon={UserCheck}  color="green"  />
          <StatCard label="Client-Facing"    value={stats.client_facing}  icon={Briefcase}  color="purple" />
          <StatCard label="Departments"      value={Object.keys(stats.departments || {}).length} icon={Building2} color="amber" />
        </div>
      )}

      {/* Department filter */}
      {members.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {departments.map(dept => (
            <button
              key={dept}
              onClick={() => setFilter(dept)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all border
                ${filter === dept
                  ? 'bg-jarvis-blue/20 border-jarvis-blue/30 text-jarvis-blue'
                  : 'bg-white/[0.03] border-white/[0.08] text-white/40 hover:text-white/70'}`}
            >
              {dept === 'all' ? 'All Departments' : dept}
            </button>
          ))}
        </div>
      )}

      {/* Member grid */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <RefreshCw size={20} className="text-white/30 animate-spin" />
        </div>
      ) : members.length === 0 ? (
        <div className="text-center py-20">
          <Users size={32} className="text-white/20 mx-auto mb-3" />
          <p className="text-white/40 text-sm">No team members registered yet.</p>
          <button
            onClick={handleSeed}
            disabled={seeding}
            className="mt-4 px-5 py-2 bg-jarvis-blue/20 hover:bg-jarvis-blue/30
                       border border-jarvis-blue/30 rounded-lg text-jarvis-blue
                       text-xs font-medium transition-all disabled:opacity-50"
          >
            {seeding ? 'Seeding…' : 'Seed Team Members'}
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
          {visible.map(m => <MemberCard key={m.id} member={m} />)}
        </div>
      )}

      {/* Communication guide callout */}
      <div className="glass rounded-xl border border-white/[0.06] p-5">
        <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
          <Zap size={14} className="text-jarvis-blue" />
          Communication Identity Policy
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs text-white/50">
          <div>
            <p className="text-white/70 font-medium mb-1">External Presentation</p>
            <p>All client-facing output uses "Aliyar Solutions Team" language. Never expose AI tooling or infrastructure.</p>
          </div>
          <div>
            <p className="text-white/70 font-medium mb-1">Forbidden Phrases</p>
            <p className="text-red-400/70">AI agent · bot · GPT · Claude · autonomous · machine-generated · "I hope this email finds you well"</p>
          </div>
          <div>
            <p className="text-white/70 font-medium mb-1">Tone Principles</p>
            <p>Human · startup energy · premium consulting · lead with curiosity · be concise · match prospect energy</p>
          </div>
        </div>
      </div>
    </div>
  )
}
