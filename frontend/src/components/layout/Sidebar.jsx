import React from 'react'
import { motion } from 'framer-motion'
import {
  LayoutDashboard, MessageSquare, CheckSquare, Users, Newspaper,
  Zap, Activity, UserCircle, Target, Mail, ListTodo, Bell, Clock,
  Brain, Shield, Layers, Inbox, FileText, Receipt, Database,
  Search, BriefcaseBusiness, Volume2, BookOpen, Microscope, Settings, Building2,
  DollarSign,
} from 'lucide-react'
import useJarvisStore from '../../store/useJarvisStore'

const NAV = [
  { id: 'dashboard',      path: '/',              label: 'Dashboard',     icon: LayoutDashboard },
  { id: 'chat',           path: '/chat',          label: 'Chat',          icon: MessageSquare },
  { id: 'briefing',       path: '/briefing',      label: 'Briefings',     icon: Newspaper },
  { id: 'captainBridge',  path: '/captain-bridge', label: 'Captain Bridge', icon: UserCircle },
  { id: 'approvals',      path: '/approvals',     label: 'Approvals',     icon: CheckSquare },
  { id: 'warRoom',        path: '/war-room',      label: 'War Room',      icon: Shield },
  { id: 'systemHud',      path: '/system-hud',    label: 'System HUD',    icon: Activity },
  { id: 'leads',          path: '/leads',         label: 'Leads',         icon: Target },
  { id: 'outreach',       path: '/outreach',      label: 'Outreach',      icon: Mail },
  { id: 'crm',            path: '/crm',           label: 'CRM',           icon: UserCircle },
  { id: 'relationships',  path: '/relationships', label: 'Relationships', icon: Users },
  { id: 'proposals',      path: '/proposals',     label: 'Proposals',     icon: FileText },
  { id: 'invoices',       path: '/invoices',      label: 'Invoices',      icon: Receipt },
  { id: 'revenueIntel',   path: '/revenue-intelligence', label: 'Revenue Intel', icon: DollarSign },
  { id: 'agents',         path: '/agents',        label: 'Agents',        icon: Users },
  { id: 'departments',    path: '/departments',   label: 'Departments',   icon: Building2 },
  { id: 'council',        path: '/council',       label: 'Council',       icon: Brain },
  { id: 'expertCouncil',  path: '/expert-council', label: 'Expert Council', icon: Brain },
  { id: 'memory',         path: '/memory',        label: 'Memory',        icon: Database },
  { id: 'intel',          path: '/intel',         label: 'Intel',         icon: Search },
  { id: 'intelligenceHub', path: '/intelligence-hub', label: 'Intel Hub',  icon: Search },
  { id: 'discovery',      path: '/discovery',     label: 'Discovery',     icon: Target },
  { id: 'tasks',          path: '/tasks',         label: 'Tasks',         icon: ListTodo },
  { id: 'projects',       path: '/projects',      label: 'Projects',      icon: BriefcaseBusiness },
  { id: 'scheduler',      path: '/scheduler',     label: 'Scheduler',     icon: Clock },
  { id: 'notifications',  path: '/notifications', label: 'Alerts',        icon: Bell },
  { id: 'gmail',          path: '/gmail',         label: 'Gmail',         icon: Inbox },
  { id: 'voice',          path: '/voice',         label: 'Voice',         icon: Volume2 },
  { id: 'knowledge',      path: '/knowledge',     label: 'Knowledge',     icon: BookOpen },
  { id: 'research',       path: '/research',      label: 'Research',      icon: Microscope },
  { id: 'governance',     path: '/governance',    label: 'Governance',    icon: Shield },
  { id: 'catalog',        path: '/catalog',       label: 'Catalog',       icon: Layers },
  { id: 'settings',       path: '/settings',      label: 'Settings',      icon: Settings },
]

export default function Sidebar() {
  const { activeView, setActiveView, wsConnected, pendingApprovals } = useJarvisStore()

  return (
    <aside className="w-64 h-screen flex flex-col glass border-r border-white/[0.06] rounded-none">
      {/* Logo */}
      <div className="px-6 py-6 border-b border-white/[0.06]">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-jarvis-blue/30 to-jarvis-purple/30
                          border border-jarvis-blue/30 flex items-center justify-center glow-blue">
            <Zap size={18} className="text-jarvis-blue" />
          </div>
          <div>
            <p className="font-bold text-white text-sm tracking-wider">JARVIS</p>
            <p className="text-xs text-white/40">Aliyar Solutions</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto no-scrollbar">
        {NAV.map(({ id, label, icon: Icon }) => {
          const active = activeView === id
          const badge = id === 'approvals' && pendingApprovals > 0 ? pendingApprovals : null
          return (
            <motion.button
              key={id}
              whileTap={{ scale: 0.97 }}
              onClick={() => setActiveView(id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm
                         transition-all duration-200 group relative
                         ${active
                           ? 'bg-jarvis-blue/15 border border-jarvis-blue/25 text-jarvis-blue'
                           : 'text-white/50 hover:bg-white/[0.05] hover:text-white/80'}`}
            >
              <Icon size={16} className={active ? 'text-jarvis-blue' : 'text-white/40 group-hover:text-white/60'} />
              <span className="font-medium">{label}</span>
              {badge && (
                <span className="ml-auto bg-amber-500 text-black text-[10px] font-bold
                                  w-5 h-5 rounded-full flex items-center justify-center">
                  {badge > 9 ? '9+' : badge}
                </span>
              )}
              {active && (
                <motion.div
                  layoutId="activeIndicator"
                  className="absolute right-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-jarvis-blue rounded-full"
                />
              )}
            </motion.button>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="px-4 py-4 border-t border-white/[0.06]">
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/[0.03]">
          <div className={`status-dot ${wsConnected ? 'online' : 'offline'}`} />
          <span className="text-xs text-white/40">
            {wsConnected ? 'Live' : 'Offline'}
          </span>
          <Activity size={12} className="ml-auto text-white/20" />
        </div>
      </div>
    </aside>
  )
}
