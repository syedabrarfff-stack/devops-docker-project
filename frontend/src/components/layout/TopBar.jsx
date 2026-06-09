import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Mic, MicOff, Volume2, VolumeX, Bell, X } from 'lucide-react'
import { format } from 'date-fns'
import useJarvisStore from '../../store/useJarvisStore'
import voiceService from '../../services/voice'
import { api } from '../../services/api'

export default function TopBar() {
  const { wsConnected, voiceActive, setVoiceActive, voiceListening,
          setVoiceListening, notifications, clearNotification, activeView } = useJarvisStore()
  const [time, setTime] = useState(new Date())
  const [muted, setMuted] = useState(false)
  const [showNotifs, setShowNotifs] = useState(false)
  const [runtimeStatus, setRuntimeStatus] = useState({
    level: 'checking',
    label: 'CHECKING',
    detail: 'Checking production subsystems',
  })

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(t)
  }, [])

  useEffect(() => {
    let active = true

    const checkRuntime = async () => {
      try {
        const [ready, email, outreach] = await Promise.all([
          api.get('/readyz'),
          api.get('/api/v1/gmail/status'),
          api.get('/api/v1/outreach/compliance/status'),
        ])

        if (!active) return

        if (ready.data?.status !== 'ready') {
          setRuntimeStatus({
            level: 'degraded',
            label: 'DEGRADED',
            detail: 'Backend readiness check is not fully ready',
          })
          return
        }

        if (!email.data?.connected) {
          setRuntimeStatus({
            level: 'degraded',
            label: 'EMAIL BLOCKED',
            detail: email.data?.message || 'Executive email is configured but not connected',
          })
          return
        }

        if (outreach.data?.outreach_paused) {
          setRuntimeStatus({
            level: 'degraded',
            label: 'OUTREACH PAUSED',
            detail: 'Outreach is paused by compliance controls',
          })
          return
        }

        setRuntimeStatus({
          level: 'operational',
          label: 'OPERATIONAL',
          detail: 'Core runtime, executive email, and outreach controls are ready',
        })
      } catch {
        if (!active) return
        setRuntimeStatus({
          level: 'degraded',
          label: 'CHECK FAILED',
          detail: 'Could not verify production subsystem readiness',
        })
      }
    }

    checkRuntime()
    const t = setInterval(checkRuntime, 30000)
    return () => {
      active = false
      clearInterval(t)
    }
  }, [])

  const toggleVoice = () => {
    if (!voiceActive) {
      setVoiceActive(true)
      voiceService.onWakeWord = () => {
        setVoiceListening(true)
        if (!muted) voiceService.speak('Yes, Captain. How can I help?')
      }
      voiceService.startListening({ continuous: true })
    } else {
      voiceService.stopListening()
      setVoiceActive(false)
      setVoiceListening(false)
    }
  }

  const labels = {
    dashboard: 'Executive Dashboard',
    chat: 'JARVIS Chat',
    briefing: 'Morning Briefings',
    approvals: 'Captain Approval Queue',
    leads: 'Lead Pipeline',
    outreach: 'Outreach Operations',
    communications: 'Communication Hub',
    crm: 'Client Management',
    proposals: 'Proposals',
    invoices: 'Invoices',
    agents: 'Agent Registry',
    council: 'Council Sessions',
    memory: 'Memory Browser',
    intel: 'Market Intelligence',
    discovery: 'Lead Discovery',
    tasks: 'Task Management',
    projects: 'Project Tracker',
    scheduler: 'Scheduler',
    notifications: 'Notifications',
    gmail: 'Email Monitor',
    voice: 'Voice Briefings',
    knowledge: 'Knowledge Base',
    research: 'Research Reports',
    governance: 'Governance',
    catalog: 'Service Catalog',
    settings: 'Tenant Settings',
  }

  const unread = notifications.length
  const effectiveStatus = wsConnected ? runtimeStatus : {
    level: 'offline',
    label: 'OFFLINE',
    detail: 'Realtime backend connection is offline',
  }
  const statusStyles = {
    operational: 'bg-green-400/10 border-green-400/20 text-green-400',
    degraded: 'bg-amber-400/10 border-amber-400/25 text-amber-300',
    checking: 'bg-sky-400/10 border-sky-400/20 text-sky-300',
    offline: 'bg-red-400/10 border-red-400/20 text-red-400',
  }
  const dotStyles = {
    operational: 'bg-green-400 animate-pulse',
    degraded: 'bg-amber-300 animate-pulse',
    checking: 'bg-sky-300 animate-pulse',
    offline: 'bg-red-400',
  }

  return (
    <header className="h-14 flex items-center justify-between px-6
                       border-b border-white/[0.06] bg-jarvis-dark/80 backdrop-blur-sm">
      {/* Page title */}
      <div>
        <p className="text-sm font-semibold text-white/80">{labels[activeView] || 'JARVIS'}</p>
        <p className="text-[11px] text-white/30 font-mono">{format(time, 'EEE, dd MMM yyyy  HH:mm:ss')}</p>
      </div>

      {/* Controls */}
      <div className="flex items-center gap-3">
        {/* Mute */}
        <button
          onClick={() => { setMuted(!muted); if (!muted) voiceService.stopSpeaking() }}
          className={`p-2 rounded-lg transition-all ${muted ? 'text-red-400 bg-red-400/10' : 'text-white/40 hover:text-white/70'}`}
          title={muted ? 'Unmute' : 'Mute JARVIS voice'}
        >
          {muted ? <VolumeX size={16} /> : <Volume2 size={16} />}
        </button>

        {/* Wake word toggle */}
        <motion.button
          whileTap={{ scale: 0.95 }}
          onClick={toggleVoice}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium
                      border transition-all duration-200
                      ${voiceActive
                        ? 'bg-jarvis-blue/15 border-jarvis-blue/40 text-jarvis-blue'
                        : 'bg-white/[0.04] border-white/[0.10] text-white/40 hover:text-white/70'}`}
        >
          {voiceListening
            ? <motion.span animate={{ scale: [1,1.3,1] }} transition={{ repeat: Infinity, duration: 0.8 }}>
                <Mic size={13} className="text-jarvis-blue" />
              </motion.span>
            : voiceActive
              ? <Mic size={13} />
              : <MicOff size={13} />}
          {voiceActive ? (voiceListening ? 'Listening...' : 'Wake: "Jarvis"') : 'Voice Off'}
        </motion.button>

        {/* Notifications */}
        <div className="relative">
          <button
            onClick={() => setShowNotifs(!showNotifs)}
            className="p-2 rounded-lg text-white/40 hover:text-white/70 transition-colors relative"
          >
            <Bell size={16} />
            {unread > 0 && (
              <span className="absolute top-1 right-1 w-2 h-2 bg-amber-400 rounded-full" />
            )}
          </button>

          <AnimatePresence>
            {showNotifs && (
              <motion.div
                initial={{ opacity: 0, y: -8, scale: 0.96 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -8, scale: 0.96 }}
                className="absolute right-0 top-10 w-80 glass border border-white/10
                           rounded-xl shadow-2xl z-50 overflow-hidden"
              >
                <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.06]">
                  <span className="text-xs font-semibold text-white/70">Notifications</span>
                  <button onClick={() => setShowNotifs(false)} className="text-white/30 hover:text-white/60">
                    <X size={14} />
                  </button>
                </div>
                <div className="max-h-64 overflow-y-auto no-scrollbar">
                  {notifications.length === 0 && (
                    <p className="text-center text-white/30 text-xs py-8">All clear, Captain.</p>
                  )}
                  {notifications.map((n) => (
                    <div key={n.id}
                         className="flex items-start gap-3 px-4 py-3 border-b border-white/[0.04]
                                    hover:bg-white/[0.03] group">
                      <div className={`mt-0.5 w-1.5 h-1.5 rounded-full flex-shrink-0
                                       ${n.level === 'warning' ? 'bg-amber-400' : 'bg-jarvis-blue'}`} />
                      <p className="text-xs text-white/60 flex-1">{n.message}</p>
                      <button
                        onClick={() => clearNotification(n.id)}
                        className="text-white/20 hover:text-white/50 opacity-0 group-hover:opacity-100"
                      >
                        <X size={12} />
                      </button>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Status pill */}
        <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[11px] font-medium
                         border transition-all
                         ${statusStyles[effectiveStatus.level] || statusStyles.degraded}`}
             title={effectiveStatus.detail}>
          <span className={`w-1.5 h-1.5 rounded-full ${dotStyles[effectiveStatus.level] || dotStyles.degraded}`} />
          {effectiveStatus.label}
        </div>
      </div>
    </header>
  )
}
