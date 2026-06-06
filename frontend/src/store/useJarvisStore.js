import { create } from 'zustand'

const VIEW_PATHS = {
  dashboard: '/control-room/dashboard',
  chat: '/control-room/chat',
  briefing: '/control-room/briefing',
  captainBridge: '/control-room/captain-bridge',
  approvals: '/control-room/approvals',
  warRoom: '/control-room/war-room',
  systemHud: '/control-room/system-hud',
  leads: '/control-room/leads',
  outreach: '/control-room/outreach',
  crm: '/control-room/crm',
  relationships: '/control-room/relationships',
  proposals: '/control-room/proposals',
  invoices: '/control-room/invoices',
  revenueIntel: '/control-room/revenue-intelligence',
  agents: '/control-room/agents',
  council: '/control-room/council',
  expertCouncil: '/control-room/expert-council',
  memory: '/control-room/memory',
  intel: '/control-room/intel',
  intelligenceHub: '/control-room/intelligence-hub',
  departments: '/control-room/departments',
  consciousness: '/control-room/consciousness',
  aionxArchitecture: '/control-room/aionx-architecture',
  discovery: '/control-room/discovery',
  tasks: '/control-room/tasks',
  projects: '/control-room/projects',
  scheduler: '/control-room/scheduler',
  notifications: '/control-room/notifications',
  gmail: '/control-room/email',
  voice: '/control-room/voice',
  knowledge: '/control-room/knowledge',
  research: '/control-room/research',
  governance: '/control-room/governance',
  catalog: '/control-room/catalog',
  settings: '/control-room/settings',
}

function syncBrowserPath(view) {
  if (typeof window === 'undefined') return
  const path = VIEW_PATHS[view]
  if (!path || window.location.pathname === path) return
  window.history.pushState({}, '', path)
  window.dispatchEvent(new PopStateEvent('popstate'))
}

const useJarvisStore = create((set, get) => ({
  // Identity and tenant context
  user: null,
  tenant: null,
  setUser: (user) => set({ user }),
  setTenant: (tenant) => set({ tenant }),

  // Active view
  activeView: 'dashboard',
  setActiveView: (view) => {
    syncBrowserPath(view)
    set({ activeView: view })
  },

  // WebSocket
  ws: null,
  wsConnected: false,

  // Notifications
  notifications: [],
  setNotifications: (notifications) => set({ notifications }),
  addNotification: (n) => set((s) => ({
    notifications: [{ id: Date.now(), ...n }, ...s.notifications].slice(0, 50),
  })),
  clearNotification: (id) => set((s) => ({
    notifications: s.notifications.filter((n) => n.id !== id),
  })),

  // Approval count badge
  pendingApprovals: 0,
  setPendingApprovals: (n) => set({ pendingApprovals: n }),
  captainQueue: [],
  setCaptainQueue: (captainQueue) => set({ captainQueue }),

  // System health
  systemHealth: null,
  setSystemHealth: (systemHealth) => set({ systemHealth }),

  // AI providers
  providers: {},
  setProviders: (p) => set({ providers: p }),

  // Voice state
  voiceActive: false,
  voiceListening: false,
  voiceSpeaking: false,
  setVoiceActive: (v) => set({ voiceActive: v }),
  setVoiceListening: (v) => set({ voiceListening: v }),
  setVoiceSpeaking: (v) => set({ voiceSpeaking: v }),

  // Chat session
  sessionId: `session_${Date.now()}`,

  // Connect WebSocket
  connectWS: () => {
    const existing = get().ws
    if (existing && [WebSocket.CONNECTING, WebSocket.OPEN].includes(existing.readyState)) {
      return
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = import.meta.env.DEV
      ? `${window.location.hostname}:8000`
      : window.location.host
    const url = `${protocol}//${host}/api/v1/ws/captain`

    const ws = new WebSocket(url)

    ws.onopen = () => {
      set({ wsConnected: true })
    }

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data)
        if (msg.type === 'captain_connected' && typeof msg.data?.pending_approvals === 'number') {
          get().setPendingApprovals(msg.data.pending_approvals)
        }
        if (msg.type === 'captain_queue') {
          get().setCaptainQueue(msg.data?.items || [])
        }
        if (msg.type === 'system_health') {
          get().setSystemHealth(msg.data)
        }
        if (msg.type === 'approval_created') {
          get().setPendingApprovals(get().pendingApprovals + 1)
          get().addNotification({ type: 'approval', message: `New approval: ${msg.data.title}`, level: 'warning' })
        }
        if (msg.type === 'approval_decided') {
          get().setPendingApprovals(Math.max(0, get().pendingApprovals - 1))
          get().addNotification({ type: 'info', message: `Approval ${msg.data.status}: ${msg.data.title}`, level: 'info' })
        }
      } catch {}
    }

    ws.onclose = () => {
      set({ wsConnected: false, ws: null })
      setTimeout(() => get().connectWS(), 5000)
    }

    ws.onerror = () => ws.close()

    set({ ws })

    // Keepalive ping
    const ping = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'ping' }))
      } else {
        clearInterval(ping)
      }
    }, 25000)
  },
}))

export default useJarvisStore
