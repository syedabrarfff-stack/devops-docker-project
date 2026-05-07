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

// CRM
export const getContacts = (params) => api.get('/api/v1/crm/contacts', { params }).then(r => r.data)
export const createContact = (data) => api.post('/api/v1/crm/contacts', data).then(r => r.data)
export const getDeals = (params) => api.get('/api/v1/crm/deals', { params }).then(r => r.data)
export const createDeal = (data) => api.post('/api/v1/crm/deals', data).then(r => r.data)
export const getPipelineStats = () => api.get('/api/v1/crm/deals/pipeline').then(r => r.data)
export const getContactStats = () => api.get('/api/v1/crm/contacts/stats').then(r => r.data)

// Leads
export const getLeads = (params) => api.get('/api/v1/leads/', { params }).then(r => r.data)
export const createLead = (data) => api.post('/api/v1/leads/', data).then(r => r.data)
export const scoreLead = (id) => api.post(`/api/v1/leads/${id}/score`).then(r => r.data)
export const bulkScoreLeads = () => api.post('/api/v1/leads/bulk-score').then(r => r.data)
export const getLeadStats = () => api.get('/api/v1/leads/stats').then(r => r.data)

// Outreach
export const getSequenceStats = () => api.get('/api/v1/outreach/sequences/stats').then(r => r.data)
export const createSequence = (data) => api.post('/api/v1/outreach/sequences', data).then(r => r.data)
export const getPendingEmails = () => api.get('/api/v1/outreach/emails/pending').then(r => r.data)
export const sendOutreachEmail = (id) => api.post(`/api/v1/outreach/emails/${id}/send`).then(r => r.data)
export const processDueEmails = () => api.post('/api/v1/outreach/emails/process-due').then(r => r.data)

// Tasks
export const getTasks = (params) => api.get('/api/v1/tasks/', { params }).then(r => r.data)
export const enqueueTask = (data) => api.post('/api/v1/tasks/enqueue', data).then(r => r.data)
export const getQueueStats = () => api.get('/api/v1/tasks/queue').then(r => r.data)
export const getAgentsStatus = () => api.get('/api/v1/tasks/agents/status').then(r => r.data)
export const sendAgentMessage = (data) => api.post('/api/v1/tasks/messages/send', data).then(r => r.data)

// Memory
export const storeMemory = (data) => api.post('/api/v1/memory/store', data).then(r => r.data)
export const recallMemory = (query, params) => api.get('/api/v1/memory/recall', { params: { query, ...params } }).then(r => r.data)

export default api
