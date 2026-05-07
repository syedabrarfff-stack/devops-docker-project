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

// Phase 3 — Auth / Gmail OAuth
export const getGmailStatus = () => api.get('/api/v1/auth/gmail/status').then(r => r.data)
export const initiateGmailOAuth = () => api.get('/api/v1/auth/gmail/initiate').then(r => r.data)
export const revokeGmailOAuth = () => api.post('/api/v1/auth/gmail/revoke').then(r => r.data)

// Phase 3 — Notifications
export const getNotifications = (params) => api.get('/api/v1/notifications/', { params }).then(r => r.data)
export const getUnreadCount = () => api.get('/api/v1/notifications/unread-count').then(r => r.data)
export const markNotifRead = (id) => api.post(`/api/v1/notifications/${id}/read`).then(r => r.data)
export const markAllNotifsRead = () => api.post('/api/v1/notifications/read-all').then(r => r.data)
export const broadcastNotif = (data) => api.post('/api/v1/notifications/broadcast', data).then(r => r.data)

// Phase 3 — Scheduler
export const getSchedulerJobs = () => api.get('/api/v1/scheduler/jobs').then(r => r.data)
export const getDbJobs = () => api.get('/api/v1/scheduler/jobs/db').then(r => r.data)
export const createCronJob = (data) => api.post('/api/v1/scheduler/jobs/cron', data).then(r => r.data)
export const createIntervalJob = (data) => api.post('/api/v1/scheduler/jobs/interval', data).then(r => r.data)
export const deleteSchedulerJob = (id) => api.delete(`/api/v1/scheduler/jobs/${id}`).then(r => r.data)
export const pauseJob = (id) => api.post(`/api/v1/scheduler/jobs/${id}/pause`).then(r => r.data)
export const resumeJob = (id) => api.post(`/api/v1/scheduler/jobs/${id}/resume`).then(r => r.data)

// Phase 3 — Calendar
export const getCalendarEvents = (params) => api.get('/api/v1/calendar/events', { params }).then(r => r.data)
export const createCalendarEvent = (data) => api.post('/api/v1/calendar/events', data).then(r => r.data)
export const scheduleMeeting = (data) => api.post('/api/v1/calendar/meetings/schedule', data).then(r => r.data)
export const getCalendars = () => api.get('/api/v1/calendar/calendars').then(r => r.data)

// Phase 3 — Sync
export const runApolloSync = (data) => api.post('/api/v1/sync/apollo', data).then(r => r.data)
export const enrichContact = (id) => api.post(`/api/v1/sync/enrich/${id}`).then(r => r.data)
export const registerTelegramWebhook = (url) => api.post(`/api/v1/sync/telegram/webhook/register?webhook_url=${encodeURIComponent(url)}`).then(r => r.data)
export const getTelegramWebhookInfo = () => api.get('/api/v1/sync/telegram/webhook/info').then(r => r.data)

// Phase 5 — Intelligence Layer
export const getIntelligencePulse = () => api.get('/api/v1/intelligence/pulse').then(r => r.data)
export const getTechRadar = () => api.get('/api/v1/intelligence/radar').then(r => r.data)
export const triggerTechScan = () => api.post('/api/v1/intelligence/radar/scan').then(r => r.data)
export const getRecommendations = (status) => api.get('/api/v1/intelligence/recommendations', { params: status ? { status } : {} }).then(r => r.data)
export const triggerOptimizationAnalysis = () => api.post('/api/v1/intelligence/recommendations/analyze').then(r => r.data)
export const approveRecommendation = (id) => api.post(`/api/v1/intelligence/recommendations/${id}/approve`).then(r => r.data)
export const dismissRecommendation = (id) => api.post(`/api/v1/intelligence/recommendations/${id}/dismiss`).then(r => r.data)
export const implementRecommendation = (id) => api.post(`/api/v1/intelligence/recommendations/${id}/implement`).then(r => r.data)
export const getResearchReports = (limit = 20) => api.get('/api/v1/intelligence/reports', { params: { limit } }).then(r => r.data)
export const generateResearchReport = (topic, category = 'market') => api.post('/api/v1/intelligence/reports/generate', { topic, category }).then(r => r.data)

// Phase 6 — Governance
export const getInvoices = (params) => api.get('/api/v1/governance/invoices', { params }).then(r => r.data)
export const createInvoice = (data) => api.post('/api/v1/governance/invoices', data).then(r => r.data)
export const updateInvoiceStatus = (id, status) => api.post(`/api/v1/governance/invoices/${id}/status`, { status }).then(r => r.data)
export const getProposals = (params) => api.get('/api/v1/governance/proposals', { params }).then(r => r.data)
export const generateProposal = (data) => api.post('/api/v1/governance/proposals/generate', data).then(r => r.data)
export const updateProposalStatus = (id, status) => api.post(`/api/v1/governance/proposals/${id}/status`, { status }).then(r => r.data)
export const getAgentPermissions = () => api.get('/api/v1/governance/permissions').then(r => r.data)
export const grantPermission = (data) => api.post('/api/v1/governance/permissions', data).then(r => r.data)
export const revokePermission = (id) => api.post(`/api/v1/governance/permissions/${id}/revoke`).then(r => r.data)
export const getGovernanceStats = () => api.get('/api/v1/governance/stats').then(r => r.data)

// Phase 6 — Emergency Control
export const getSystemHealth = () => api.get('/api/v1/emergency/health').then(r => r.data)
export const getIncidents = (params) => api.get('/api/v1/emergency/incidents', { params }).then(r => r.data)
export const declareIncident = (data) => api.post('/api/v1/emergency/incidents', data).then(r => r.data)
export const resolveIncident = (id, resolution) => api.post(`/api/v1/emergency/incidents/${id}/resolve`, { resolution }).then(r => r.data)
export const addIncidentAction = (id, action) => api.post(`/api/v1/emergency/incidents/${id}/action`, { action }).then(r => r.data)
export const sendEmergencyAlert = (data) => api.post('/api/v1/emergency/alert', data).then(r => r.data)

// Phase 6 — Knowledge / SOP
export const getSOPs = (params) => api.get('/api/v1/knowledge/sops', { params }).then(r => r.data)
export const generateSOP = (data) => api.post('/api/v1/knowledge/sops/generate', data).then(r => r.data)
export const getLearnings = (params) => api.get('/api/v1/knowledge/learnings', { params }).then(r => r.data)
export const logLearning = (data) => api.post('/api/v1/knowledge/learnings', data).then(r => r.data)
export const searchKnowledge = (query, params) => api.get('/api/v1/knowledge/search', { params: { query, ...params } }).then(r => r.data)
export const addKnowledgeEntry = (data) => api.post('/api/v1/knowledge/entries', data).then(r => r.data)
export const getKnowledgeStats = () => api.get('/api/v1/knowledge/stats').then(r => r.data)

export default api
