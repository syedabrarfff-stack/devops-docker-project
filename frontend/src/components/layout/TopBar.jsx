import React, { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Mic, MicOff, Volume2, VolumeX, Bell, X } from 'lucide-react'
import { format } from 'date-fns'
import useJarvisStore from '../../store/useJarvisStore'
import voiceService from '../../services/voice'
import { getActivityBriefing } from '../../services/api'

const LABELS = {
  dashboard: 'Command Center',
  automation: 'Automation Center',
  access: 'Access Vault',
  chat: 'JARVIS Chat',
  briefing: 'Briefing',
  approvals: 'Approval Queue',
  agents: 'Agent Hierarchy',
  crm: 'CRM',
  leads: 'Leads',
  outreach: 'Outreach',
  tasks: 'Task Queue',
  notifications: 'Notifications',
  scheduler: 'Scheduler',
  calendar: 'Calendar',
  sync: 'Sync',
  intelligence: 'Intelligence',
  governance: 'Governance',
  catalog: 'Services',
  ai_ops: 'AI Operations',
  team: 'Team Registry',
}

const MOBILE_VIEWS = [
  ['dashboard', 'Dashboard'],
  ['automation', 'Automation'],
  ['access', 'Access'],
  ['chat', 'JARVIS Chat'],
  ['briefing', 'Briefing'],
  ['approvals', 'Approvals'],
  ['agents', 'Agents'],
  ['crm', 'CRM'],
  ['leads', 'Leads'],
  ['outreach', 'Outreach'],
  ['tasks', 'Tasks'],
  ['notifications', 'Notifications'],
  ['team', 'Team'],
  ['scheduler', 'Scheduler'],
  ['calendar', 'Calendar'],
  ['sync', 'Sync'],
  ['intelligence', 'Intelligence'],
  ['governance', 'Governance'],
  ['catalog', 'Services'],
  ['ai_ops', 'AI Ops'],
]

export default function TopBar() {
  const {
    wsConnected,
    voiceActive,
    setVoiceActive,
    voiceListening,
    setVoiceListening,
    notifications,
    clearNotification,
    activeView,
    setActiveView,
  } = useJarvisStore()

  const [time, setTime] = useState(new Date())
  const [speakerOn, setSpeakerOn] = useState(() => localStorage.getItem('jarvis_speaker_on') !== 'false')
  const [showNotifs, setShowNotifs] = useState(false)
  const speakerOnRef = useRef(speakerOn)
  const awaitingBriefingRef = useRef(false)

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(t)
  }, [])

  useEffect(() => {
    speakerOnRef.current = speakerOn
  }, [speakerOn])

  const speakDashboardWelcome = () => {
    if (!speakerOnRef.current || sessionStorage.getItem('jarvis_dashboard_welcome_spoken') === 'true') return
    sessionStorage.setItem('jarvis_dashboard_welcome_spoken', 'true')
    const liveStatus = wsConnected ? 'The live dashboard link is connected.' : 'The live dashboard link is still reconnecting.'
    voiceService.speak(
      `Captain, Jarvis is online. ${liveStatus} I am watching approvals, leads, outreach, scheduled work, and the specialist teams. When you want it, say Jarvis, briefing, and I will ask before giving the full activity report.`,
      { rate: 0.9, pitch: 0.88, maxChars: 520, pause: 300, mood: 'friendly' }
    )
  }

  const speakActivityBriefing = async () => {
    if (!speakerOnRef.current) return
    voiceService.speak('Understood, Captain. Preparing the current activity briefing.', { mood: 'briefing', maxChars: 180 })
    try {
      const data = await getActivityBriefing()
      voiceService.speak(data.spoken, { mood: 'briefing', maxChars: 1600 })
    } catch {
      voiceService.speak('Captain, I could not reach the activity briefing service. The backend may need attention.', { mood: 'urgent' })
    }
  }

  const sendVoiceCommandToChat = (command) => {
    if (!command) return
    setActiveView('chat')
    window.setTimeout(() => {
      window.dispatchEvent(new CustomEvent('jarvis-voice-command', { detail: { command } }))
    }, 250)
  }

  const cleanWakeCommand = (transcript = '') => transcript
    .toLowerCase()
    .replace(/\bhey\s+jarvis\b/g, '')
    .replace(/\bokay\s+jarvis\b/g, '')
    .replace(/\bjarvis\b/g, '')
    .replace(/[.,!?]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()

  const isBriefingIntent = (command) =>
    /(brief|report|activity|what.*team|team.*working|what.*made|new leads|email|outreach|status)/i.test(command)

  const isListenIntent = (command) =>
    /^(listen|start listening|are you there|hello|hi|wake up|can you hear me)?$/i.test(command)

  const handleVoiceCommand = async (rawTranscript = '') => {
    const command = cleanWakeCommand(rawTranscript)
    setVoiceListening(true)

    if (awaitingBriefingRef.current) {
      if (/\b(yes|yeah|yep|sure|go ahead|brief me|continue)\b/i.test(command)) {
        awaitingBriefingRef.current = false
        await speakActivityBriefing()
        return
      }
      if (/\b(no|not now|cancel|later|stop)\b/i.test(command)) {
        awaitingBriefingRef.current = false
        if (speakerOnRef.current) voiceService.speak('Of course, Captain. I will stay on standby.', { mood: 'calm', maxChars: 160 })
        return
      }
    }

    if (isBriefingIntent(command)) {
      awaitingBriefingRef.current = true
      if (speakerOnRef.current) {
        voiceService.speak(
          'Captain, I can brief you on current activity: team work, prepared emails, lead status, tasks, and approvals. Shall I continue?',
          { mood: 'friendly', maxChars: 260 }
        )
      }
      return
    }

    if (isListenIntent(command)) {
      if (speakerOnRef.current) {
        voiceService.speak(
          'Yes, Captain. I am listening. You can ask for a briefing, current activity, leads, outreach, approvals, or give me a command.',
          { mood: 'friendly', maxChars: 260 }
        )
      }
      return
    }

    if (speakerOnRef.current) voiceService.speak('Understood, Captain. I will handle that in command chat.', { mood: 'calm', maxChars: 160 })
    sendVoiceCommandToChat(command)
  }

  const enableVoice = () => {
    setVoiceActive(true)
    voiceService.onWakeWord = handleVoiceCommand
    voiceService.startListening({
      continuous: true,
      onResult: (transcript) => {
        if (awaitingBriefingRef.current) handleVoiceCommand(transcript)
      },
      onEnd: () => setVoiceListening(false),
      onInterrupt: () => {
        awaitingBriefingRef.current = false
        setVoiceListening(false)
      },
    })
  }

  useEffect(() => {
    if (!voiceActive) enableVoice()
  }, [])

  useEffect(() => {
    if (activeView !== 'dashboard') return
    const timer = window.setTimeout(speakDashboardWelcome, 1200)
    return () => window.clearTimeout(timer)
  }, [activeView, wsConnected])

  const toggleSpeaker = () => {
    const next = !speakerOn
    setSpeakerOn(next)
    localStorage.setItem('jarvis_speaker_on', String(next))
    if (!next) voiceService.stopSpeaking()
  }

  const toggleVoice = () => {
    if (!voiceActive) {
      enableVoice()
    } else {
      voiceService.stopListening()
      setVoiceActive(false)
      setVoiceListening(false)
    }
  }

  const unread = notifications.length

  return (
    <header className="shrink-0 min-h-14 flex flex-wrap items-center justify-between gap-2 px-3 py-2 md:gap-3 md:px-6 md:py-0 border-b border-white/[0.06] bg-jarvis-dark/80 backdrop-blur-sm">
      <div className="min-w-0 flex-1 md:flex-none">
        <p className="text-sm font-semibold text-white/80">{LABELS[activeView] || 'JARVIS'}</p>
        <p className="text-[11px] text-white/30 font-mono">{format(time, 'EEE, dd MMM yyyy  HH:mm:ss')}</p>
      </div>

      <select
        value={activeView}
        onChange={(event) => setActiveView(event.target.value)}
        className="md:hidden min-w-0 max-w-[48vw] rounded-lg border border-jarvis-blue/30 bg-jarvis-blue/10 px-2 py-1.5 text-xs font-medium text-jarvis-blue outline-none"
        aria-label="Open dashboard section"
      >
        {MOBILE_VIEWS.map(([id, label]) => (
          <option key={id} value={id} className="bg-gray-950 text-white">{label}</option>
        ))}
      </select>

      <div className="flex min-w-0 items-center gap-1.5 md:gap-3">
        <button
          onClick={toggleSpeaker}
          className={`flex min-h-9 items-center justify-center gap-2 px-2 py-1.5 md:px-3 rounded-lg text-xs font-medium border transition-all ${
            speakerOn
              ? 'bg-jarvis-blue/15 border-jarvis-blue/40 text-jarvis-blue'
              : 'bg-red-400/10 border-red-400/20 text-red-400'
          }`}
          title={speakerOn ? 'Turn speaker off' : 'Turn speaker on'}
        >
          {speakerOn ? <Volume2 size={14} /> : <VolumeX size={14} />}
          <span className="hidden sm:inline">{speakerOn ? 'Speaker On' : 'Speaker Off'}</span>
        </button>

        <motion.button
          whileTap={{ scale: 0.95 }}
          onClick={toggleVoice}
          className={`flex min-h-9 items-center justify-center gap-2 px-2 py-1.5 md:px-3 rounded-lg text-xs font-medium border transition-all duration-200 ${
            voiceActive
              ? 'bg-jarvis-blue/15 border-jarvis-blue/40 text-jarvis-blue'
              : 'bg-white/[0.04] border-white/[0.10] text-white/40 hover:text-white/70'
          }`}
        >
          {voiceListening
            ? <motion.span animate={{ scale: [1, 1.3, 1] }} transition={{ repeat: Infinity, duration: 0.8 }}>
                <Mic size={13} className="text-jarvis-blue" />
              </motion.span>
            : voiceActive
              ? <Mic size={13} />
              : <MicOff size={13} />}
          <span className="hidden sm:inline">{voiceActive ? (voiceListening ? 'Listening...' : 'Wake: "Jarvis"') : 'Voice Off'}</span>
        </motion.button>

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
                className="absolute right-0 top-10 w-[min(20rem,calc(100vw-1rem))] glass border border-white/10 rounded-xl shadow-2xl z-50 overflow-hidden"
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
                    <div
                      key={n.id}
                      className="flex items-start gap-3 px-4 py-3 border-b border-white/[0.04] hover:bg-white/[0.03] group"
                    >
                      <div className={`mt-0.5 w-1.5 h-1.5 rounded-full flex-shrink-0 ${n.level === 'warning' ? 'bg-amber-400' : 'bg-jarvis-blue'}`} />
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

        <div className={`hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[11px] font-medium border transition-all ${
          wsConnected
            ? 'bg-green-400/10 border-green-400/20 text-green-400'
            : 'bg-red-400/10 border-red-400/20 text-red-400'
        }`}>
          <span className={`w-1.5 h-1.5 rounded-full ${wsConnected ? 'bg-green-400 animate-pulse' : 'bg-red-400'}`} />
          {wsConnected ? 'OPERATIONAL' : 'OFFLINE'}
        </div>
      </div>
    </header>
  )
}
