import React, { useEffect } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import Sidebar from './components/layout/Sidebar'
import TopBar from './components/layout/TopBar'
import Dashboard from './components/dashboard/Dashboard'
import ChatInterface from './components/chat/ChatInterface'
import MorningBriefing from './components/briefing/MorningBriefing'
import ApprovalQueue from './components/approvals/ApprovalQueue'
import AgentHierarchy from './components/agents/AgentHierarchy'
import CRMDashboard from './components/crm/CRMDashboard'
import LeadsDashboard from './components/leads/LeadsDashboard'
import OutreachDashboard from './components/outreach/OutreachDashboard'
import TaskQueue from './components/tasks/TaskQueue'
import NotificationCenter from './components/notifications/NotificationCenter'
import SchedulerView from './components/scheduler/SchedulerView'
import CalendarView from './components/calendar/CalendarView'
import SyncView from './components/sync/SyncView'
import IntelligenceDashboard from './components/intelligence/IntelligenceDashboard'
import GovernanceDashboard from './components/governance/GovernanceDashboard'
import ServiceCatalog from './components/catalog/ServiceCatalog'
import AIOpsDashboard from './components/ai_ops/AIOpsDashboard'
import TeamRegistry from './components/team/TeamRegistry'
import AutomationCenter from './components/automation/AutomationCenter'
import AccessVault from './components/access/AccessVault'
import useJarvisStore from './store/useJarvisStore'

const VIEWS = {
  dashboard:     Dashboard,
  chat:          ChatInterface,
  briefing:      MorningBriefing,
  approvals:     ApprovalQueue,
  agents:        AgentHierarchy,
  crm:           CRMDashboard,
  leads:         LeadsDashboard,
  outreach:      OutreachDashboard,
  tasks:         TaskQueue,
  notifications: NotificationCenter,
  scheduler:     SchedulerView,
  calendar:      CalendarView,
  sync:          SyncView,
  intelligence:  IntelligenceDashboard,
  governance:    GovernanceDashboard,
  catalog:       ServiceCatalog,
  ai_ops:        AIOpsDashboard,
  team:          TeamRegistry,
  automation:    AutomationCenter,
  access:        AccessVault,
}

export default function App() {
  const { activeView, connectWS } = useJarvisStore()

  useEffect(() => {
    connectWS()
  }, [])

  const View = VIEWS[activeView] || Dashboard

  return (
    <div className="app-shell jarvis-mobile-safe flex overflow-hidden scanline">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar />
        <main className="app-main flex-1 min-w-0">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeView}
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
              transition={{ duration: 0.15 }}
              className="app-view h-full min-w-0"
            >
              <View />
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  )
}
