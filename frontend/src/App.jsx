import React, { useEffect } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import Sidebar from './components/layout/Sidebar'
import TopBar from './components/layout/TopBar'
import Dashboard from './components/dashboard/Dashboard'
import ChatInterface from './components/chat/ChatInterface'
import MorningBriefing from './components/briefing/MorningBriefing'
import Approvals from './components/approvals/Approvals'
import AgentHierarchy from './components/agents/AgentHierarchy'
import CRMDashboard from './components/crm/CRMDashboard'
import LeadsDashboard from './components/leads/LeadsDashboard'
import OutreachDashboard from './components/outreach/OutreachDashboard'
import TaskQueue from './components/tasks/TaskQueue'
import NotificationCenter from './components/notifications/NotificationCenter'
import SchedulerView from './components/scheduler/SchedulerView'
import GovernanceDashboard from './components/governance/GovernanceDashboard'
import ServiceCatalog from './components/catalog/ServiceCatalog'
import GmailCenter from './components/gmail/GmailCenter'
import ProposalsView from './components/proposals/ProposalsView'
import InvoicesView from './components/invoices/InvoicesView'
import CouncilView from './components/council/CouncilView'
import MemoryView from './components/memory/MemoryView'
import IntelView from './components/intel/IntelView'
import DiscoveryView from './components/discovery/DiscoveryView'
import ProjectsView from './components/projects/ProjectsView'
import VoiceView from './components/voice/VoiceView'
import KnowledgeView from './components/knowledge/KnowledgeView'
import ResearchView from './components/research/ResearchView'
import SettingsView from './components/settings/SettingsView'
import useJarvisStore from './store/useJarvisStore'

export const VIEWS = {
  dashboard:     { path: '/',              title: 'Executive Dashboard',    Component: Dashboard },
  chat:          { path: '/chat',          title: 'JARVIS Chat',            Component: ChatInterface },
  briefing:      { path: '/briefing',      title: 'Morning Briefings',      Component: MorningBriefing },
  approvals:     { path: '/approvals',     title: 'Captain Approval Queue', Component: Approvals },
  leads:         { path: '/leads',         title: 'Lead Pipeline',          Component: LeadsDashboard },
  outreach:      { path: '/outreach',      title: 'Outreach Operations',    Component: OutreachDashboard },
  crm:           { path: '/crm',           title: 'Client Management',      Component: CRMDashboard },
  proposals:     { path: '/proposals',     title: 'Proposals',             Component: ProposalsView },
  invoices:      { path: '/invoices',      title: 'Invoices',              Component: InvoicesView },
  agents:        { path: '/agents',        title: 'Agent Registry',         Component: AgentHierarchy },
  council:       { path: '/council',       title: 'Council Sessions',       Component: CouncilView },
  memory:        { path: '/memory',        title: 'Memory Browser',         Component: MemoryView },
  intel:         { path: '/intel',         title: 'Market Intelligence',    Component: IntelView },
  discovery:     { path: '/discovery',     title: 'Lead Discovery',         Component: DiscoveryView },
  tasks:         { path: '/tasks',         title: 'Task Management',        Component: TaskQueue },
  projects:      { path: '/projects',      title: 'Project Tracker',        Component: ProjectsView },
  scheduler:     { path: '/scheduler',     title: 'Scheduler',              Component: SchedulerView },
  notifications: { path: '/notifications', title: 'Notifications',          Component: NotificationCenter },
  gmail:         { path: '/gmail',         title: 'Gmail Monitor',          Component: GmailCenter },
  voice:         { path: '/voice',         title: 'Voice Briefings',        Component: VoiceView },
  knowledge:     { path: '/knowledge',     title: 'Knowledge Base',         Component: KnowledgeView },
  research:      { path: '/research',      title: 'Research Reports',       Component: ResearchView },
  governance:    { path: '/governance',    title: 'Governance',             Component: GovernanceDashboard },
  catalog:       { path: '/catalog',       title: 'Service Catalog',        Component: ServiceCatalog },
  settings:      { path: '/settings',      title: 'Tenant Settings',        Component: SettingsView },
}

const VIEW_ENTRIES = Object.entries(VIEWS)
const PATH_TO_VIEW = VIEW_ENTRIES.reduce((acc, [id, view]) => ({ ...acc, [view.path]: id }), {})

function AppShell() {
  const { activeView, setActiveView, connectWS } = useJarvisStore()
  const location = useLocation()

  useEffect(() => {
    connectWS()
  }, [connectWS])

  useEffect(() => {
    const nextView = PATH_TO_VIEW[location.pathname] || 'dashboard'
    if (nextView !== activeView) setActiveView(nextView)
  }, [activeView, location.pathname, setActiveView])

  return (
    <div className="flex h-screen overflow-hidden scanline">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar />
        <main className="flex-1 overflow-hidden">
          <AnimatePresence mode="wait">
            <Routes location={location} key={location.pathname}>
              {VIEW_ENTRIES.map(([id, { path, Component }]) => (
                <Route
                  key={id}
                  path={path}
                  element={
                    <motion.div
                      key={id}
                      initial={{ opacity: 0, x: 10 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -10 }}
                      transition={{ duration: 0.15 }}
                      className="h-full"
                    >
                      <Component />
                    </motion.div>
                  }
                />
              ))}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </AnimatePresence>
        </main>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AppShell />
    </BrowserRouter>
  )
}
