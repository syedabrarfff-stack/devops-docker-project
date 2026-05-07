import React, { useEffect } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import Sidebar from './components/layout/Sidebar'
import TopBar from './components/layout/TopBar'
import Dashboard from './components/dashboard/Dashboard'
import ChatInterface from './components/chat/ChatInterface'
import MorningBriefing from './components/briefing/MorningBriefing'
import ApprovalQueue from './components/approvals/ApprovalQueue'
import AgentHierarchy from './components/agents/AgentHierarchy'
import useJarvisStore from './store/useJarvisStore'

const VIEWS = {
  dashboard: Dashboard,
  chat:      ChatInterface,
  briefing:  MorningBriefing,
  approvals: ApprovalQueue,
  agents:    AgentHierarchy,
}

export default function App() {
  const { activeView, connectWS } = useJarvisStore()

  useEffect(() => {
    connectWS()
  }, [])

  const View = VIEWS[activeView] || Dashboard

  return (
    <div className="flex h-screen overflow-hidden scanline">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar />
        <main className="flex-1 overflow-hidden">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeView}
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
              transition={{ duration: 0.15 }}
              className="h-full"
            >
              <View />
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  )
}
