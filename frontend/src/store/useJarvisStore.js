import { create } from 'zustand'

const useJarvisStore = create((set, get) => ({
  // Active view
  activeView: 'dashboard',
  setActiveView: (view) => set({ activeView: view }),

  // WebSocket
  ws: null,
  wsConnected: false,

  // Notifications
  notifications: [],
  addNotification: (n) => set((s) => ({
    notifications: [{ id: Date.now(), ...n }, ...s.notifications].slice(0, 50),
  })),
  clearNotification: (id) => set((s) => ({
    notifications: s.notifications.filter((n) => n.id !== id),
  })),

  // Approval count badge
  pendingApprovals: 0,
  setPendingApprovals: (n) => set({ pendingApprovals: n }),

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
