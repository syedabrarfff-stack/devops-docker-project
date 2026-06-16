import axios from 'axios'

const BASE = import.meta.env.DEV ? 'http://localhost:8000' : ''

const api = axios.create({
  baseURL: BASE,
  timeout: 60000,
  headers: { 'Content-Type': 'application/json' },
})

const API_PREFIX = '/api/v1'
const API_RESOURCES = new Set([
  'agent-ops',
  'agents',
  'ai-ops',
  'aionx',
  'approvals',
  'auth',
  'batch1',
  'briefing',
  'calendar',
  'calls',
  'catalog',
  'chat',
  'civilization',
  'clients',
  'communication',
  'connector-hub',
  'council',
  'crm',
  'departments',
  'demos',
  'discovery',
  'economics',
  'emergency',
  'gmail',
  'governance',
  'innovation',
  'intelligence',
  'invoices',
  'jarvis',
  'knowledge',
  'leads',
  'memory',
  'notifications',
  'outreach',
  'pilot',
  'pricing',
  'proposals',
  'revenue',
  'scheduler',
  'sync',
  'tasks',
  'team',
  'voice',
])

api.interceptors.request.use((config) => {
  const url = config.url || ''
  if (url.startsWith('/') && !url.startsWith('/api/') && !url.startsWith('/health') && !url.startsWith('/readyz')) {
    const resource = url.slice(1).split(/[/?#]/)[0]
    if (API_RESOURCES.has(resource)) {
      config.url = `${API_PREFIX}${url}`
    }
  }
  // Attach captain JWT if present
  try {
    const raw = localStorage.getItem('jarvis_auth')
    if (raw) {
      const { token } = JSON.parse(raw)
      if (token) {
        config.headers = config.headers || {}
        config.headers.Authorization = `Bearer ${token}`
      }
    }
  } catch (err) {
    console.warn('[JARVIS] Could not parse stored auth token — clearing session', err)
    localStorage.removeItem('jarvis_auth')
  }
  return config
})

export { api }

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
export const approveApproval = (id, captain_note = '') =>
  api.post(`/api/v1/approvals/${id}/approve`, { captain_note }).then((r) => r.data)
export const rejectApproval = (id, reason = '') =>
  api.post(`/api/v1/approvals/${id}/reject`, { reason }).then((r) => r.data)

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

// Clients
export const getClients = (params) => api.get('/api/v1/clients', { params }).then(r => r.data)
export const getClient = (id, params) => api.get(`/api/v1/clients/${id}`, { params }).then(r => r.data)
export const createClient = (data) => api.post('/api/v1/clients', data).then(r => r.data)
export const updateClient = (id, data) => api.patch(`/api/v1/clients/${id}`, data).then(r => r.data)
export const updateClientStatus = (id, data) => api.post(`/api/v1/clients/${id}/status`, data).then(r => r.data)

// Leads
export const getLeads = (params) => api.get('/api/v1/leads/', { params }).then(r => r.data)
export const createLead = (data) => api.post('/api/v1/leads/', data).then(r => r.data)
export const scoreLead = (id) => api.post(`/api/v1/leads/${id}/score`).then(r => r.data)
export const bulkScoreLeads = () => api.post('/api/v1/leads/bulk-score').then(r => r.data)
export const getLeadStats = () => api.get('/api/v1/leads/stats').then(r => r.data)

// Outreach
export const getSequenceStats = () => api.get('/api/v1/outreach/sequences/stats').then(r => r.data)
export const getOutreachEngineStatus = () => api.get('/api/v1/outreach/engine-status').then(r => r.data)
export const prepareOutreachCampaign = (limit = 25, min_score = 80) => api.post('/api/v1/outreach/prepare-campaign', { limit, min_score }).then(r => r.data)
export const createSequence = (data) => api.post('/api/v1/outreach/sequences', data).then(r => r.data)
export const getPendingEmails = () => api.get('/api/v1/outreach/emails/pending').then(r => r.data)
export const sendOutreachEmail = (id) => api.post(`/api/v1/outreach/emails/${id}/send`).then(r => r.data)
export const processDueEmails = () => api.post('/api/v1/outreach/emails/process-due').then(r => r.data)
export const executeOutreachEngine = (limit = 48) => api.post('/api/v1/outreach/execute', { limit, autonomy_stage: 'outreach_emails' }).then(r => r.data)

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
export const getGmailOAuthStatus = () => api.get('/api/v1/auth/gmail/status').then(r => r.data)
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

// Service Catalog
export const getCatalogDivisions = (params) => api.get('/api/v1/catalog/divisions', { params }).then(r => r.data)
export const getCatalogDivision = (code) => api.get(`/api/v1/catalog/divisions/${code}`).then(r => r.data)
export const getCatalogGroups = () => api.get('/api/v1/catalog/groups').then(r => r.data)
export const getCatalogStats = () => api.get('/api/v1/catalog/stats').then(r => r.data)
export const getCatalogCapabilityModules = () => api.get('/api/v1/catalog/capability-modules').then(r => r.data)
export const seedCatalog = () => api.post('/api/v1/catalog/seed').then(r => r.data)
export const syncCatalogCanonical = () => api.post('/api/v1/catalog/sync-canonical').then(r => r.data)
export const updateCatalogDivision = (code, data) => api.patch(`/api/v1/catalog/divisions/${code}`, data).then(r => r.data)

// Phase 8 — AI Operations
export const getAIOpsPulse = () => api.get('/api/v1/ai-ops/pulse').then(r => r.data)
export const getAIOpsHealth = () => api.get('/api/v1/ai-ops/health').then(r => r.data)
export const resetAICircuit = (provider) => api.post(`/api/v1/ai-ops/health/${provider}/reset`).then(r => r.data)
export const getAIOpsCostToday = () => api.get('/api/v1/ai-ops/cost/today').then(r => r.data)
export const getAIOpsCostSummary = (days = 7) => api.get('/api/v1/ai-ops/cost/summary', { params: { days } }).then(r => r.data)
export const getAIOpsAudit = (limit = 50, provider) => api.get('/api/v1/ai-ops/audit', { params: { limit, provider } }).then(r => r.data)
export const getAIOpsCredentials = () => api.get('/api/v1/ai-ops/credentials').then(r => r.data)
export const getAIOpsRoutingTable = () => api.get('/api/v1/ai-ops/routing-table').then(r => r.data)

// AIONX Architecture Glass Wall
export const getAionxArchitecture = () => api.get('/api/v1/aionx/architecture').then(r => r.data)
export const getAionxDashboard = () => api.get('/api/v1/aionx/dashboard').then(r => r.data)
export const getAionxSystemInfo = () => api.get('/api/v1/aionx/system-info').then(r => r.data)
export const getAionxOperatingIntelligence = () => api.get('/api/v1/aionx/operating-intelligence').then(r => r.data)
export const getAionxAdaptiveIntelligence = () => api.get('/api/v1/aionx/adaptive-intelligence').then(r => r.data)
export const getAionxTechnologyExploration = () => api.get('/api/v1/aionx/technology-exploration').then(r => r.data)
export const getAionxRevenuePipeline = () => api.get('/api/v1/aionx/revenue-pipeline').then(r => r.data)
export const getAionxModuleDependencies = () => api.get('/api/v1/aionx/module-dependencies').then(r => r.data)
export const getAionxDataBackbone = () => api.get('/api/v1/aionx/data-backbone').then(r => r.data)
export const getAionxGatewayExperience = () => api.get('/api/v1/aionx/gateway-experience').then(r => r.data)
export const getAionxCaptainInterface = () => api.get('/api/v1/aionx/captain-interface').then(r => r.data)
export const getAionxOperationalIntegrity = () => api.get('/api/v1/aionx/operational-integrity').then(r => r.data)
export const createAionxMissionPlan = (payload) => api.post('/api/v1/aionx/operational-integrity/mission-plan', payload).then(r => r.data)
export const issueAionxQaCertificate = (payload) => api.post('/api/v1/aionx/operational-integrity/qa-certificate', payload).then(r => r.data)
export const createAionxRepairInstruction = (payload) => api.post('/api/v1/aionx/operational-integrity/repair-instruction', payload).then(r => r.data)
export const runAionxFallbackDrill = (payload) => api.post('/api/v1/aionx/operational-integrity/fallback-drill', payload).then(r => r.data)
export const synthesizeAionxMilestoneLearning = (payload) => api.post('/api/v1/aionx/operational-integrity/knowledge-synthesis', payload).then(r => r.data)
export const getAionxSovereignOrgans = () => api.get('/api/v1/aionx/sovereign-organs').then(r => r.data)
export const getAionxSystemState = () => api.get('/api/v1/aionx/system-state').then(r => r.data)
export const debateAionxDecision = (payload) => api.post('/api/v1/aionx/cognitive-cortex/debate', payload).then(r => r.data)
export const proposeAionxGenesis = (payload) => api.post('/api/v1/aionx/genesis/propose', payload).then(r => r.data)
export const scanAionxImmuneSystem = (payload) => api.post('/api/v1/aionx/immune-system/scan', payload).then(r => r.data)
export const simulateAionxStrategy = (payload) => api.post('/api/v1/aionx/simulation-twin/scenario', payload).then(r => r.data)
export const getAionxUltimateJourney = () => api.get('/api/v1/aionx/ultimate-journey').then(r => r.data)
export const getAionxPreventiveMonitoring = () => api.get('/api/v1/aionx/preventive-monitoring').then(r => r.data)
export const createAionxHieBriefing = (payload) => api.post('/api/v1/aionx/hie/briefing', payload).then(r => r.data)
export const extractAionxPostCall = (payload) => api.post('/api/v1/aionx/hie/post-call-extraction', payload).then(r => r.data)
export const getAionxOperationalPersistence = () => api.get('/api/v1/aionx/operational-persistence').then(r => r.data)
export const getAionxLatestPersistence = (limit = 10) => api.get(`/api/v1/aionx/operational-persistence/latest?limit=${limit}`).then(r => r.data)
export const snapshotAionxSystemState = () => api.post('/api/v1/aionx/system-state/snapshot').then(r => r.data)
export const snapshotAionxPreventiveMonitoring = () => api.post('/api/v1/aionx/preventive-monitoring/snapshot').then(r => r.data)
export const createAionxAutonomyProposal = (payload) => api.post('/api/v1/aionx/autonomy/proposal', payload).then(r => r.data)
export const recordAionxExternalScan = (payload) => api.post('/api/v1/aionx/external-scan/record', payload).then(r => r.data)
export const runAionxGovernedIntegrityCycle = () => api.post('/api/v1/aionx/governed-integrity-cycle').then(r => r.data)
export const getAionxSupremeCouncil = () => api.get('/api/v1/aionx/supreme-council').then(r => r.data)
export const getAionxSupremeCalibration = () => api.get('/api/v1/aionx/supreme-council/calibration').then(r => r.data)
export const getAionxSupremeConvergence = () => api.get('/api/v1/aionx/supreme-council/convergence').then(r => r.data)
export const getAionxSupremeSafetyMembrane = () => api.get('/api/v1/aionx/supreme-council/safety-membrane').then(r => r.data)
export const getAionxSupremeMetaLearning = () => api.get('/api/v1/aionx/supreme-council/meta-learning').then(r => r.data)
export const createAionxSupremeRecommendation = (payload) => api.post('/api/v1/aionx/supreme-council/recommendation', payload).then(r => r.data)
export const evaluateAionxSelfModification = (payload) => api.post('/api/v1/aionx/supreme-council/self-modification/evaluate', payload).then(r => r.data)
export const runAionxSupremeMetaLearningCycle = () => api.post('/api/v1/aionx/supreme-council/meta-learning-cycle').then(r => r.data)
export const getAionxCompletionMatrix = () => api.get('/api/v1/aionx/completion-matrix').then(r => r.data)
export const getAionxCrossValidation = () => api.get('/api/v1/aionx/cross-validation').then(r => r.data)
export const validateAionxDeliveryReadiness = (missionId, payload) => api.post(`/api/v1/aionx/cross-validation/delivery-readiness/${missionId}`, payload).then(r => r.data)
export const validateAionxSalesAccuracy = (proposalId, payload) => api.post(`/api/v1/aionx/cross-validation/sales-accuracy/${proposalId}`, payload).then(r => r.data)
export const validateAionxClientFit = (clientId, payload) => api.post(`/api/v1/aionx/cross-validation/client-fit/${clientId}`, payload).then(r => r.data)
export const validateAionxStageTransition = (subjectId, payload) => api.post(`/api/v1/aionx/cross-validation/stage-transition/${subjectId}`, payload).then(r => r.data)
export const getBatch1Workflow = () => api.get('/api/v1/batch1/workflow').then(r => r.data)
export const getAxiomOperatingModel = () => api.get('/api/v1/departments/axiom/operating-model').then(r => r.data)
export const getAxiomPulse = () => api.get('/api/v1/departments/axiom/pulse').then(r => r.data)

// Phase 9 — Team Registry
export const getTeamMembers = (params) => api.get('/api/v1/team/members', { params }).then(r => r.data)
export const getTeamMember = (id) => api.get(`/api/v1/team/members/${id}`).then(r => r.data)
export const getMemberForService = (category) => api.get(`/api/v1/team/members/for-service/${category}`).then(r => r.data)
export const updateTeamMember = (id, data) => api.patch(`/api/v1/team/members/${id}`, data).then(r => r.data)
export const seedTeam = () => api.post('/api/v1/team/seed').then(r => r.data)
export const getTeamStats = () => api.get('/api/v1/team/stats').then(r => r.data)
export const getTeamCommunicationGuide = () => api.get('/api/v1/team/communication-guide').then(r => r.data)

// JARVIS Self-Awareness
export const getJarvisStatus = () => api.get('/api/v1/jarvis/status').then(r => r.data)
export const getJarvisBriefing = () => api.get('/api/v1/jarvis/briefing').then(r => r.data)
export const getJarvisSelfImprovement = () => api.get('/api/v1/jarvis/self-improvement').then(r => r.data)
export const enhanceIdea = (idea) => api.post('/api/v1/jarvis/enhance-idea', { idea }).then(r => r.data)
export const spawnAgentTeam = (task) => api.post('/api/v1/jarvis/spawn-team', { task }).then(r => r.data)
export const jarvisChat = (message, task_type = 'FAST', history = [], session_id = null) => api.post('/api/v1/jarvis/chat', { message, task_type, history, session_id }).then(r => r.data)

// JARVIS Memory & Evolution
export const getJarvisMemory = (query = '', memory_type = null, limit = 20) => api.get('/api/v1/jarvis/memory', { params: { query, memory_type, limit } }).then(r => r.data)
export const getJarvisMemoryStats = () => api.get('/api/v1/jarvis/memory/stats').then(r => r.data)
export const storeJarvisMemory = (content, memory_type = 'instruction', importance = 0.9, tags = []) => api.post('/api/v1/jarvis/memory/store', { content, memory_type, importance, tags }).then(r => r.data)
export const triggerEvolution = () => api.post('/api/v1/jarvis/evolve').then(r => r.data)
export const getEvolutionLog = (limit = 10) => api.get('/api/v1/jarvis/evolution-log', { params: { limit } }).then(r => r.data)
export const logOutcome = (action_type, action_detail, action_ref = null, importance = 0.6) => api.post('/api/v1/jarvis/outcomes', { action_type, action_detail, action_ref, importance }).then(r => r.data)
export const resolveOutcome = (id, outcome, note = null) => api.post(`/api/v1/jarvis/outcomes/${id}/resolve`, { outcome, note }).then(r => r.data)

// Gmail Operations Center
export const getGmailStatus = () => api.get('/api/v1/gmail/status').then(r => r.data)
export const getGmailInbox = (category = null, needs_action = null, limit = 50) => api.get('/api/v1/gmail/inbox', { params: { category, needs_action, limit } }).then(r => r.data)
export const getGmailStats = () => api.get('/api/v1/gmail/stats').then(r => r.data)
export const fetchGmailInbox = () => api.post('/api/v1/gmail/fetch').then(r => r.data)
export const markEmailRead = (id) => api.post(`/api/v1/gmail/messages/${id}/read`).then(r => r.data)
export const sendEmail = (to, subject, body, to_name = null) => api.post('/api/v1/gmail/send', { to, subject, body, to_name }).then(r => r.data)

// Agent Operations Center
export const getAgentOpsStatus = () => api.get('/api/v1/agent-ops/status').then(r => r.data)
export const getAllAgentTeams = () => api.get('/api/v1/agent-ops/teams').then(r => r.data)
export const getAgentTeam = (teamId) => api.get(`/api/v1/agent-ops/teams/${teamId}`).then(r => r.data)
export const getAllAgents = () => api.get('/api/v1/agent-ops/agents').then(r => r.data)
export const getAgentDetail = (agentId) => api.get(`/api/v1/agent-ops/agents/${agentId}`).then(r => r.data)
export const chatWithAgent = (agentId, message, context = null, task_type = 'FAST') => api.post(`/api/v1/agent-ops/agents/${agentId}/chat`, { message, context, task_type }).then(r => r.data)
export const chatWithTeam = (teamId, message, context = null, task_type = 'FAST') => api.post(`/api/v1/agent-ops/teams/${teamId}/chat`, { message, context, task_type }).then(r => r.data)
export const getTeamActivity = (teamId) => api.get(`/api/v1/agent-ops/teams/${teamId}/activity`).then(r => r.data)

// JARVIS Authority Matrix
export const getJarvisAuthority = () => api.get('/api/v1/jarvis/authority').then(r => r.data)
export const createApprovalRequest = (title, action_type, summary, payload = {}, risk_level = 'medium', estimated_cost = null) =>
  api.post('/api/v1/approvals', { title, action_type, summary, payload, risk_level, estimated_cost }).then(r => r.data)

// Overnight Engine — manual trigger endpoints
export const triggerLeadDiscovery = () => api.post('/api/v1/leads/bulk-score').then(r => r.data)
export const triggerProposalEngine = () => api.post('/api/v1/jarvis/spawn-team', { task: 'overnight_proposal_engine' }).then(r => r.data)

// JARVIS Voice & Greeting
export const getJarvisGreeting = () => api.get('/api/v1/jarvis/greeting').then(r => r.data)
export const getJarvisVoiceBrief = () => api.get('/api/v1/jarvis/voice-brief').then(r => r.data)
export const getJarvisAIHealth = () => api.get('/api/v1/jarvis/ai-health').then(r => r.data)

// Backend TTS
export const requestTTS = (text, provider = 'auto') =>
  api.post('/api/v1/voice/tts', { text, provider }, { timeout: 30000 }).then(r => r.data)
export const getVoiceProviders = () => api.get('/api/v1/voice/providers').then(r => r.data)

// Local Market Discovery
export const discoverLocalMarket = (payload) =>
  api.post('/api/v1/discovery/local-market', payload, { timeout: 30000 }).then(r => r.data)
export const getTargetIndustries = () => api.get('/api/v1/discovery/industries').then(r => r.data)

// Pricing Engine
export const getPricingEstimate = (payload) =>
  api.post('/api/v1/pricing/estimate', payload).then(r => r.data)
export const getPricingMatrix = () => api.get('/api/v1/pricing/matrix').then(r => r.data)
export const getIntelligencePricingCatalog = () => api.get('/api/v1/intelligence/pricing/catalog').then(r => r.data)

// Department Intelligence — 6-Layer Autonomous System
export const getDepartmentHealth       = () => api.get('/api/v1/departments/health').then(r => r.data)
export const initializeDios            = (tenantId) => api.post('/api/v1/departments/dios/initialize', { tenant_id: tenantId }).then(r => r.data)
export const getDios                   = () => api.get('/api/v1/departments/dios').then(r => r.data)
export const getDio                    = (code) => api.get(`/api/v1/departments/dios/${code}`).then(r => r.data)
export const collectDioMetrics         = () => api.post('/api/v1/departments/dios/collect-metrics').then(r => r.data)
export const submitMilestone           = (payload) => api.post('/api/v1/departments/milestones/submit', payload).then(r => r.data)
export const runMilestoneCouncilReview = (id, tenantId) => api.post(`/api/v1/departments/milestones/${id}/council-review`, { tenant_id: tenantId }).then(r => r.data)
export const runBulkMilestoneReview    = (tenantId) => api.post('/api/v1/departments/milestones/bulk-review', { tenant_id: tenantId }).then(r => r.data)
export const getMilestones             = () => api.get('/api/v1/departments/milestones').then(r => r.data)
export const getMilestoneReport        = () => api.get('/api/v1/departments/milestones/report').then(r => r.data)
export const implementMilestone        = (id, notes) => api.post(`/api/v1/departments/milestones/${id}/implement`, { notes }).then(r => r.data)
export const runTechDiscovery          = (tenantId) => api.post('/api/v1/departments/tech/discover', { tenant_id: tenantId }).then(r => r.data)
export const getTechDiscoveries        = () => api.get('/api/v1/departments/tech/discoveries').then(r => r.data)
export const getTechLandscape          = () => api.get('/api/v1/departments/tech/landscape').then(r => r.data)
export const evaluateTechnology        = (id) => api.post(`/api/v1/departments/tech/${id}/evaluate`).then(r => r.data)
export const techCouncilReview         = (id, tenantId) => api.post(`/api/v1/departments/tech/${id}/council-review`, { tenant_id: tenantId }).then(r => r.data)
export const scheduleClientCall        = (payload) => api.post('/api/v1/departments/calls/schedule', payload).then(r => r.data)
export const generateCallBriefing      = (id) => api.post(`/api/v1/departments/calls/${id}/generate-briefing`).then(r => r.data)
export const callBriefingCouncilReview = (id, tenantId) => api.post(`/api/v1/departments/calls/${id}/council-review`, { tenant_id: tenantId }).then(r => r.data)
export const deployVoiceAgent          = (id, tenantId) => api.post(`/api/v1/departments/calls/${id}/deploy-voice-agent`, { tenant_id: tenantId }).then(r => r.data)
export const recordCallOutcome         = (id, payload) => api.post(`/api/v1/departments/calls/${id}/outcome`, payload).then(r => r.data)
export const getClientCalls            = () => api.get('/api/v1/departments/calls').then(r => r.data)
export const generateDailyStrategy    = (tenantId) => api.post('/api/v1/departments/strategy/daily-report', { tenant_id: tenantId }).then(r => r.data)
export const generateWeeklyStrategy   = (tenantId) => api.post('/api/v1/departments/strategy/weekly-report', { tenant_id: tenantId }).then(r => r.data)
export const getStrategyReports        = () => api.get('/api/v1/departments/strategy/reports').then(r => r.data)
export const getStrategyDashboard      = () => api.get('/api/v1/departments/strategy/dashboard').then(r => r.data)

// Communication — SES + WhatsApp unified status layer
export const getCommunicationStatus     = (tenantId) => api.get('/api/v1/communication/status', { params: tenantId ? { tenant_id: tenantId } : {} }).then(r => r.data)
export const getCommunicationEvents     = (params)   => api.get('/api/v1/communication/events', { params }).then(r => r.data)
export const getWhatsAppStatus          = (tenantId) => api.get('/api/v1/communication/whatsapp/status', { params: tenantId ? { tenant_id: tenantId } : {} }).then(r => r.data)
export const getWhatsAppQR              = (number)   => api.get('/api/v1/communication/whatsapp/qr', { params: number ? { number } : {} }).then(r => r.data)
export const createWhatsAppInstance     = ()         => api.post('/api/v1/communication/whatsapp/instance').then(r => r.data)
export const configureWhatsAppWebhook   = ()         => api.post('/api/v1/communication/whatsapp/webhook/configure').then(r => r.data)
export const sendWhatsAppText           = (number, text, leadId, tenantId) => api.post('/api/v1/communication/whatsapp/send-text', { number, text, lead_id: leadId }, { params: tenantId ? { tenant_id: tenantId } : {} }).then(r => r.data)
export const sendWhatsAppMedia          = (number, mediaUrl, caption, mediaType, leadId) => api.post('/api/v1/communication/whatsapp/send-media', { number, media_url: mediaUrl, caption, media_type: mediaType, lead_id: leadId }).then(r => r.data)

// Lead Generation — Bulk Discovery & Import
export const bulkDiscoverLeads  = (limit = 200, tenantId) => api.post('/api/v1/leads/bulk-discover', null, { params: { limit, ...(tenantId ? { tenant_id: tenantId } : {}) } }).then(r => r.data)
export const batchImportLeads   = (leadsData, tenantId) => api.post('/api/v1/leads/batch-import', leadsData, { params: tenantId ? { tenant_id: tenantId } : {}, timeout: 120000 }).then(r => r.data)
export const discoverLeadsApollo = (payload) => api.post('/api/v1/leads/discover', payload, { timeout: 90000 }).then(r => r.data)
export const syncLeadsToHubSpot  = (tenantId) => api.post('/api/v1/crm/hubspot-sync', { tenant_id: tenantId }).then(r => r.data)
// AIONX System Intelligence
export const getSystemHUD       = () => api.get('/api/v1/system/hud').then(r => r.data)
export const getFrontierStatus  = () => api.get('/api/v1/frontier/status').then(r => r.data)
export const getConsciousnessSnapshot = () => api.get('/api/v1/consciousness/snapshot').then(r => r.data)
export const getBatch1Board     = () => api.get('/api/v1/batch1/board').then(r => r.data)
export const getConnectorHubStatus = () => api.get('/api/v1/connector-hub/status').then(r => r.data)

// Captain Mirror
export const getCaptainMirrorProfile  = () => api.get('/api/v1/captain/mirror/profile').then(r => r.data)
export const recordCaptainDecision    = (payload) => api.post('/api/v1/captain/mirror/record', payload).then(r => r.data)

export default api
