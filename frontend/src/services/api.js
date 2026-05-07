import axios from 'axios'

const BASE = import.meta.env.DEV ? 'http://localhost:8000' : ''

const api = axios.create({
  baseURL: BASE,
  timeout: 60000,
  headers: { 'Content-Type': 'application/json' },
})

// Chat
export const sendChat = (payload) => api.post('/api/v1/chat', payload).then((r) => r.data)
export const getChatHistory = (sessionId) => api.get(`/api/v1/history/${sessionId}`).then((r) => r.data)
export const getProviders = () => api.get('/api/v1/providers').then((r) => r.data)

// Briefing
export const getMorningBriefing = () => api.get('/api/v1/briefing/morning').then((r) => r.data)
export const getSystemStatus = () => api.get('/api/v1/briefing/status').then((r) => r.data)

// Approvals
export const getApprovals = (status = 'pending') =>
  api.get('/api/v1/approvals', { params: { status } }).then((r) => r.data)
export const getPendingCount = () => api.get('/api/v1/approvals/count').then((r) => r.data)
export const decideApproval = (id, decision) =>
  api.post(`/api/v1/approvals/${id}/decide`, decision).then((r) => r.data)

// Agents
export const getAgentHierarchy = () => api.get('/api/v1/agents/hierarchy').then((r) => r.data)
export const dispatchAgent = (payload) => api.post('/api/v1/agents/dispatch', payload).then((r) => r.data)

// Health
export const getHealth = () => api.get('/health').then((r) => r.data)

export default api
