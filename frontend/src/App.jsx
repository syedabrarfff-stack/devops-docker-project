import React, { Component, useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom'

class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }
  static getDerivedStateFromError(error) {
    return { error }
  }
  componentDidCatch(error, info) {
    console.error('[JARVIS] Unhandled React error:', error, info)
  }
  render() {
    if (this.state.error) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-black text-white p-8">
          <div className="max-w-lg text-center space-y-4">
            <p className="text-2xl font-bold text-red-400">JARVIS encountered an error</p>
            <p className="text-sm text-gray-400">{this.state.error?.message}</p>
            <button
              onClick={() => { this.setState({ error: null }); window.location.reload() }}
              className="mt-4 px-6 py-2 bg-white/10 hover:bg-white/20 rounded text-sm"
            >
              Reload
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
import Sidebar from './components/layout/Sidebar'
import TopBar from './components/layout/TopBar'
import LoginPage from './components/auth/LoginPage'
import Dashboard from './components/dashboard/Dashboard'
import CommandCenter from './components/dashboard/CommandCenter'
import ChatInterface from './components/chat/ChatInterface'
import MorningBriefing from './components/briefing/MorningBriefing'
import Approvals from './components/approvals/Approvals'
import AgentHierarchy from './components/agents/AgentHierarchy'
import CRMDashboard from './components/crm/CRMDashboard'
import LeadsDashboard from './components/leads/LeadsDashboard'
import OutreachDashboard from './components/outreach/OutreachDashboard'
import TaskQueue from './components/tasks/TaskQueue'
import NotificationCenter from './components/notifications/NotificationCenter'
import SchedulerView from './components/scheduler/SchedulerView'
import GovernanceDashboard from './components/governance/GovernanceDashboard'
import ServiceCatalog from './components/catalog/ServiceCatalog'
import GmailCenter from './components/gmail/GmailCenter'
import ProposalsView from './components/proposals/ProposalsView'
import InvoicesView from './components/invoices/InvoicesView'
import CouncilView from './components/council/CouncilView'
import MemoryView from './components/memory/MemoryView'
import IntelView from './components/intel/IntelView'
import DiscoveryView from './components/discovery/DiscoveryView'
import ProjectsView from './components/projects/ProjectsView'
import VoiceView from './components/voice/VoiceView'
import KnowledgeView from './components/knowledge/KnowledgeView'
import ResearchView from './components/research/ResearchView'
import SettingsView from './components/settings/SettingsView'
import DepartmentsView from './components/departments/DepartmentsView'
import CaptainBridge from './components/frontier/CaptainBridge'
import RevenueIntelligence from './components/frontier/RevenueIntelligence'
import WarRoom from './components/frontier/WarRoom'
import WarRoomHQ from './components/dashboard/WarRoom'
import SystemHUD from './components/frontier/SystemHUD'
import ExpertCouncil from './components/frontier/ExpertCouncil'
import Relationships from './components/frontier/Relationships'
import IntelligenceHub from './components/frontier/IntelligenceHub'
import ConsciousnessHub from './components/consciousness/ConsciousnessHub'
import AionxArchitecture from './components/aionx/AionxArchitecture'
import CommunicationHub from './components/communication/CommunicationHub'
import AgentOpsCenter from './components/agent_ops/AgentOpsCenter'
import AIOpsDashboard from './components/ai_ops/AIOpsDashboard'
import ApprovalQueue from './components/approvals/ApprovalQueue'
import CalendarView from './components/calendar/CalendarView'
import EvolutionDashboard from './components/evolution/EvolutionDashboard'
import FrontierShell from './components/frontier/FrontierShell'
import IntelligenceDashboard from './components/intelligence/IntelligenceDashboard'
import SyncView from './components/sync/SyncView'
import TeamRegistry from './components/team/TeamRegistry'
import OnboardingWizard from './components/whitelabel/OnboardingWizard'
import TruthEngine from './components/truth/TruthEngine'
import ResilienceEngine from './components/resilience/ResilienceEngine'
import FinancialIntelligence from './components/financial/FinancialIntelligence'
import LearningEngine from './components/learning/LearningEngine'
import FounderDependency from './components/founder/FounderDependency'
import MoatEngine from './components/moat/MoatEngine'
import OmegaDashboard from './components/omega/OmegaDashboard'
import GhostWriter from './components/ghost/GhostWriter'
import AutopilotDashboard from './components/autopilot/AutopilotDashboard'
import useJarvisStore from './store/useJarvisStore'

export const CONTROL_ROOM_BASE = '/control-room'
const controlPath = (path) => `${CONTROL_ROOM_BASE}${path === '/' ? '/dashboard' : path}`
const EmailRedirect = () => <Navigate to={controlPath('/email')} replace />

export const VIEWS = {
  commandCenter: { path: controlPath('/command-center'), title: 'Command Center',        Component: CommandCenter },
  dashboard:     { path: controlPath('/'),              title: 'Executive Dashboard',    Component: Dashboard },
  chat:          { path: controlPath('/chat'),          title: 'Private Command Chat',   Component: ChatInterface },
  briefing:      { path: controlPath('/briefing'),      title: 'Morning Briefings',      Component: MorningBriefing },
  approvals:     { path: controlPath('/approvals'),     title: 'Captain Approval Queue', Component: Approvals },
  leads:         { path: controlPath('/leads'),         title: 'Lead Pipeline',          Component: LeadsDashboard },
  outreach:      { path: controlPath('/outreach'),      title: 'Outreach Operations',    Component: OutreachDashboard },
  communications:{ path: controlPath('/communications'), title: 'Communication Hub',     Component: CommunicationHub },
  crm:           { path: controlPath('/crm'),           title: 'Client Management',      Component: CRMDashboard },
  proposals:     { path: controlPath('/proposals'),     title: 'Proposals',             Component: ProposalsView },
  invoices:      { path: controlPath('/invoices'),      title: 'Invoices',              Component: InvoicesView },
  agents:        { path: controlPath('/agents'),        title: 'Agent Registry',         Component: AgentHierarchy },
  council:       { path: controlPath('/council'),       title: 'Council Sessions',       Component: CouncilView },
  memory:        { path: controlPath('/memory'),        title: 'Memory Browser',         Component: MemoryView },
  intel:         { path: controlPath('/intel'),         title: 'Market Intelligence',    Component: IntelView },
  discovery:     { path: controlPath('/discovery'),     title: 'Lead Discovery',         Component: DiscoveryView },
  tasks:         { path: controlPath('/tasks'),         title: 'Task Management',        Component: TaskQueue },
  projects:      { path: controlPath('/projects'),      title: 'Project Tracker',        Component: ProjectsView },
  scheduler:     { path: controlPath('/scheduler'),     title: 'Scheduler',              Component: SchedulerView },
  notifications: { path: controlPath('/notifications'), title: 'Notifications',          Component: NotificationCenter },
  gmail:         { path: controlPath('/email'),         title: 'Executive Email Center', Component: GmailCenter },
  gmailLegacy:   { path: controlPath('/gmail'),         title: 'Executive Email Center', Component: EmailRedirect },
  voice:         { path: controlPath('/voice'),         title: 'Voice Briefings',        Component: VoiceView },
  knowledge:     { path: controlPath('/knowledge'),     title: 'Knowledge Base',         Component: KnowledgeView },
  research:      { path: controlPath('/research'),      title: 'Research Reports',       Component: ResearchView },
  departments:   { path: controlPath('/departments'),   title: 'Department Intelligence', Component: DepartmentsView },
  governance:    { path: controlPath('/governance'),    title: 'Governance',             Component: GovernanceDashboard },
  catalog:       { path: controlPath('/catalog'),       title: 'Service Catalog',        Component: ServiceCatalog },
  settings:      { path: controlPath('/settings'),      title: 'Tenant Settings',        Component: SettingsView },
  captainBridge: { path: controlPath('/captain-bridge'), title: 'Captain Bridge',        Component: CaptainBridge },
  revenueIntel:  { path: controlPath('/revenue-intelligence'), title: 'Revenue Intelligence', Component: RevenueIntelligence },
  warRoom:       { path: controlPath('/war-room'),       title: 'War Room',              Component: WarRoom },
  warRoomHQ:    { path: controlPath('/war-room-hq'),    title: 'War Room HQ',           Component: WarRoomHQ },
  systemHud:     { path: controlPath('/system-hud'),     title: 'System HUD',            Component: SystemHUD },
  expertCouncil: { path: controlPath('/expert-council'), title: 'Expert Council',        Component: ExpertCouncil },
  relationships: { path: controlPath('/relationships'),  title: 'Relationships',         Component: Relationships },
  intelligenceHub:   { path: controlPath('/intelligence-hub'),  title: 'Intelligence Hub',  Component: IntelligenceHub },
  consciousness:     { path: controlPath('/consciousness'),      title: 'Consciousness Hub', Component: ConsciousnessHub },
  aionxArchitecture: { path: controlPath('/aionx-architecture'), title: 'AIONX Architecture', Component: AionxArchitecture },
  agentOps:          { path: controlPath('/agent-ops'),          title: 'Agent Operations',  Component: AgentOpsCenter },
  aiOps:             { path: controlPath('/ai-ops'),             title: 'AI Operations',     Component: AIOpsDashboard },
  approvalQueue:     { path: controlPath('/approval-queue'),     title: 'Approval Queue',    Component: ApprovalQueue },
  calendar:          { path: controlPath('/calendar'),           title: 'Calendar',          Component: CalendarView },
  evolution:         { path: controlPath('/evolution'),          title: 'System Evolution',  Component: EvolutionDashboard },
  frontierShell:     { path: controlPath('/frontier'),           title: 'Frontier Shell',    Component: FrontierShell },
  intelligenceDash:  { path: controlPath('/intelligence'),       title: 'Intelligence',      Component: IntelligenceDashboard },
  sync:              { path: controlPath('/sync'),               title: 'Data Sync',         Component: SyncView },
  team:              { path: controlPath('/team'),               title: 'Team Registry',     Component: TeamRegistry },
  whitelabel:        { path: controlPath('/whitelabel'),         title: 'White-label Setup', Component: OnboardingWizard },
  // Layer 18 — Truth, Validation & Resilience
  truthEngine:       { path: controlPath('/truth-engine'),        title: 'Truth Engine',            Component: TruthEngine },
  resilienceEngine:  { path: controlPath('/resilience'),          title: 'Resilience Engine',       Component: ResilienceEngine },
  financialIntel:    { path: controlPath('/financial-intel'),     title: 'Financial Intelligence',  Component: FinancialIntelligence },
  learningEngine:    { path: controlPath('/learning-engine'),     title: 'Learning Engine',         Component: LearningEngine },
  founderDependency: { path: controlPath('/founder-dependency'),  title: 'Founder Dependency',      Component: FounderDependency },
  moatEngine:        { path: controlPath('/moat-engine'),         title: 'Competitive Moat',        Component: MoatEngine },
  // OMEGA Global Intelligence Swarm
  omega:             { path: controlPath('/omega'),               title: 'OMEGA Swarm',             Component: OmegaDashboard },
  // GHOST — AI Outreach Intelligence Engine
  ghost:             { path: controlPath('/ghost'),               title: 'GHOST Outreach AI',       Component: GhostWriter },
  // AUTOPILOT — Autonomous Outreach Pipeline
  autopilot:         { path: controlPath('/autopilot'),           title: 'AUTOPILOT Pipeline',      Component: AutopilotDashboard },
}

const VIEW_ENTRIES = Object.entries(VIEWS)
const PATH_TO_VIEW = VIEW_ENTRIES.reduce((acc, [id, view]) => ({ ...acc, [view.path]: id }), {})
const toControlRoomRoute = (path) => path.replace(`${CONTROL_ROOM_BASE}/`, '')

const CONTACT_SERVICES = [
  'AI Automation & Workflow',
  'Cloud Infrastructure & DevOps',
  'Lead Generation & Outreach',
  'CRM & Revenue Operations',
  'Web Application Development',
  'Digital Growth Strategy',
  'Other',
]

function PublicWebsite() {
  const [contactForm, setContactForm] = useState({ name: '', company: '', email: '', service: CONTACT_SERVICES[0], message: '' })
  const [contactSent, setContactSent] = useState(false)
  const [contactSubmitting, setContactSubmitting] = useState(false)
  const [contactError, setContactError] = useState(null)
  const setField = (k) => (e) => setContactForm(f => ({ ...f, [k]: e.target.value }))

  async function handleContactSubmit(e) {
    e.preventDefault()
    setContactSubmitting(true)
    setContactError(null)
    try {
      await fetch('/api/v1/leads/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          company: contactForm.company,
          contact_name: contactForm.name,
          email: contactForm.email,
          opportunity_type: contactForm.service,
          notes: contactForm.message,
          source: 'website_contact',
          pain_points: [contactForm.service],
        }),
      })
      setContactSent(true)
    } catch {
      setContactError('Something went wrong. Please email info@aliyarsolutions.com directly.')
    }
    setContactSubmitting(false)
  }

  return (
    <main className="min-h-screen bg-[#f3efe6] text-[#17201d]">
      <section className="relative overflow-hidden px-6 py-8 sm:px-10 lg:px-16">
        <div className="absolute inset-0 opacity-70">
          <div className="absolute -left-24 top-16 h-72 w-72 rounded-full bg-[#d8b26e]/30 blur-3xl" />
          <div className="absolute right-0 top-0 h-96 w-96 rounded-full bg-[#47745f]/20 blur-3xl" />
          <div className="absolute bottom-0 left-1/3 h-80 w-80 rounded-full bg-[#203d4d]/15 blur-3xl" />
        </div>
        <div className="relative mx-auto flex max-w-7xl items-center justify-between">
          <div>
            <p className="text-xl font-black tracking-tight">Aliyar Solutions</p>
            <p className="text-xs uppercase tracking-[0.32em] text-[#6f756c]">AI, Cloud, Growth</p>
          </div>
          <a
            href="/control-room/dashboard"
            className="rounded-full border border-[#17201d]/15 bg-[#17201d] px-5 py-2 text-sm font-semibold text-white shadow-xl shadow-black/10"
          >
            Control Room
          </a>
        </div>

        <div className="relative mx-auto grid max-w-7xl gap-10 py-20 lg:grid-cols-[1.05fr_0.95fr] lg:py-28">
          <div>
            <p className="mb-5 inline-flex rounded-full border border-[#47745f]/25 bg-white/60 px-4 py-2 text-sm font-semibold text-[#47745f]">
              Enterprise-grade digital operations for ambitious businesses
            </p>
            <h1 className="max-w-4xl text-5xl font-black leading-[0.95] tracking-[-0.06em] sm:text-7xl">
              Build faster systems. Win better clients. Operate with clarity.
            </h1>
            <p className="mt-7 max-w-2xl text-lg leading-8 text-[#4e5750]">
              Aliyar Solutions designs AI automation, cloud infrastructure, lead generation, CRM, websites,
              dashboards, and digital growth systems for teams that need execution, not noise.
            </p>
            <div className="mt-9 flex flex-wrap gap-3">
              <a href="#contact" className="rounded-full bg-[#d8b26e] px-6 py-3 font-bold text-[#17201d] shadow-xl shadow-[#d8b26e]/30">
                Start a Project
              </a>
              <a href="#services" className="rounded-full border border-[#17201d]/15 bg-white/60 px-6 py-3 font-bold text-[#17201d]">
                View Services
              </a>
            </div>
          </div>

          <div className="rounded-[2rem] border border-white/70 bg-white/55 p-5 shadow-2xl shadow-black/10 backdrop-blur">
            <div className="rounded-[1.5rem] bg-[#17201d] p-6 text-white">
              <p className="text-sm uppercase tracking-[0.3em] text-[#d8b26e]">Operating Stack</p>
              <div className="mt-6 grid gap-3">
                {[
                  ['AI Automation', 'Workflow design, agent tooling, process intelligence'],
                  ['Cloud & DevOps', 'AWS, Docker, CI/CD, monitoring, recovery'],
                  ['Growth Systems', 'Lead pipelines, outreach operations, conversion flows'],
                  ['Digital Platforms', 'Websites, dashboards, portals, integrations'],
                ].map(([title, text]) => (
                  <div key={title} className="rounded-2xl border border-white/10 bg-white/[0.06] p-4">
                    <p className="font-bold">{title}</p>
                    <p className="mt-1 text-sm leading-6 text-white/62">{text}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="services" className="px-6 pb-20 sm:px-10 lg:px-16">
        <div className="mx-auto max-w-7xl">
          <div className="mb-8 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
            <div>
              <p className="text-sm font-bold uppercase tracking-[0.28em] text-[#47745f]">Services</p>
              <h2 className="mt-3 text-3xl font-black tracking-[-0.04em] sm:text-5xl">What we build</h2>
            </div>
            <p className="max-w-xl text-[#5f685f]">
              Practical packages for businesses that want stronger infrastructure, cleaner operations, and faster revenue execution.
            </p>
          </div>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {[
              'AI Automation Systems',
              'Cloud Infrastructure',
              'CRM & Pipeline Automation',
              'Lead Generation Operations',
              'Business Dashboards',
              'Website & Portal Builds',
              'DevOps & Monitoring',
              'Digital Growth Strategy',
            ].map((service) => (
              <div key={service} className="rounded-3xl border border-[#17201d]/10 bg-white/65 p-5 shadow-sm">
                <p className="font-extrabold">{service}</p>
                <p className="mt-3 text-sm leading-6 text-[#687167]">Designed, integrated, and operationalized for real business outcomes.</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Contact section */}
      <section id="contact" className="px-6 py-20 sm:px-10 lg:px-16 bg-[#17201d]">
        <div className="mx-auto max-w-7xl grid gap-16 lg:grid-cols-[0.9fr_1.1fr]">
          <div>
            <p className="text-sm font-bold uppercase tracking-[0.28em] text-[#d8b26e]">Start a Project</p>
            <h2 className="mt-4 text-4xl font-black leading-[0.95] tracking-[-0.05em] text-white sm:text-6xl">
              Let's build<br />something real.
            </h2>
            <p className="mt-6 text-lg leading-8 text-white/60">
              Tell us what you need. Our team reviews every submission and responds within 24 hours with a clear plan.
            </p>
            <div className="mt-10 space-y-4">
              {[
                ['Response time', '24 hours or less'],
                ['Engagement model', 'Retainer or project-based'],
                ['Pricing', '$2,000 – $25,000 depending on scope'],
              ].map(([label, value]) => (
                <div key={label} className="flex items-center gap-4">
                  <div className="h-1.5 w-1.5 rounded-full bg-[#d8b26e] flex-shrink-0" />
                  <p className="text-sm text-white/70"><span className="text-white font-semibold">{label}:</span> {value}</p>
                </div>
              ))}
            </div>
          </div>

          <div>
            {contactSent ? (
              <div className="rounded-3xl border border-[#47745f]/40 bg-[#1e3028]/60 p-10 text-center">
                <div className="mb-4 text-4xl">✓</div>
                <p className="text-2xl font-bold text-white">Message received.</p>
                <p className="mt-3 text-[#9fada0] leading-7">Our team will review your submission and reach out within 24 hours.</p>
              </div>
            ) : (
              <form onSubmit={handleContactSubmit} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-white/50 mb-2 uppercase tracking-wider">Name *</label>
                    <input required value={contactForm.name} onChange={setField('name')} placeholder="Your name"
                      className="w-full rounded-2xl border border-white/10 bg-white/5 px-5 py-3.5 text-white placeholder-white/25 outline-none focus:border-[#d8b26e]/60 transition-colors" />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-white/50 mb-2 uppercase tracking-wider">Company *</label>
                    <input required value={contactForm.company} onChange={setField('company')} placeholder="Company name"
                      className="w-full rounded-2xl border border-white/10 bg-white/5 px-5 py-3.5 text-white placeholder-white/25 outline-none focus:border-[#d8b26e]/60 transition-colors" />
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-white/50 mb-2 uppercase tracking-wider">Email *</label>
                  <input required type="email" value={contactForm.email} onChange={setField('email')} placeholder="your@email.com"
                    className="w-full rounded-2xl border border-white/10 bg-white/5 px-5 py-3.5 text-white placeholder-white/25 outline-none focus:border-[#d8b26e]/60 transition-colors" />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-white/50 mb-2 uppercase tracking-wider">Service Interest</label>
                  <select value={contactForm.service} onChange={setField('service')}
                    className="w-full rounded-2xl border border-white/10 bg-[#0f1a1e] px-5 py-3.5 text-white outline-none focus:border-[#d8b26e]/60 transition-colors">
                    {CONTACT_SERVICES.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-white/50 mb-2 uppercase tracking-wider">What do you need?</label>
                  <textarea value={contactForm.message} onChange={setField('message')} rows={4}
                    placeholder="Brief description of your goals, timeline, or current challenges..."
                    className="w-full rounded-2xl border border-white/10 bg-white/5 px-5 py-3.5 text-white placeholder-white/25 outline-none focus:border-[#d8b26e]/60 resize-none transition-colors" />
                </div>
                {contactError && (
                  <p className="text-sm text-red-400">{contactError}</p>
                )}
                <button type="submit" disabled={contactSubmitting}
                  className="w-full rounded-full bg-[#d8b26e] py-4 font-bold text-[#17201d] text-lg shadow-xl shadow-[#d8b26e]/20 hover:bg-[#e8c27e] disabled:opacity-60 transition-colors">
                  {contactSubmitting ? 'Sending…' : 'Send Message →'}
                </button>
              </form>
            )}
          </div>
        </div>
      </section>

      <footer className="px-6 py-8 sm:px-10 lg:px-16 bg-[#17201d] border-t border-white/[0.06]">
        <div className="mx-auto max-w-7xl flex items-center justify-between">
          <div>
            <p className="text-sm font-black text-white">Aliyar Solutions</p>
            <p className="text-xs text-white/30 mt-0.5">info@aliyarsolutions.com</p>
          </div>
          <a href="/control-room/dashboard"
            className="rounded-full border border-white/10 px-4 py-2 text-xs font-semibold text-white/50 hover:text-white transition-colors">
            Team Login
          </a>
        </div>
      </footer>
    </main>
  )
}

function isAuthed() {
  try {
    const raw = localStorage.getItem('jarvis_auth')
    if (!raw) return false
    const { at } = JSON.parse(raw)
    // Session lasts 7 days
    return Date.now() - at < 7 * 24 * 60 * 60 * 1000
  } catch {
    return false
  }
}

function AuthGate({ children }) {
  const [authed, setAuthed] = useState(isAuthed)
  if (!authed) return <LoginPage onLogin={() => setAuthed(true)} />
  return children
}

function AppShell() {
  const { activeView, setActiveView, connectWS } = useJarvisStore()
  const location = useLocation()

  useEffect(() => {
    connectWS()
  }, [connectWS])

  useEffect(() => {
    const nextView = PATH_TO_VIEW[location.pathname] || 'dashboard'
    if (nextView !== activeView) setActiveView(nextView)
  }, [activeView, location.pathname, setActiveView])

  return (
    <div className="flex h-dvh overflow-hidden scanline">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar />
        <main className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden overscroll-contain scroll-smooth">
          <AnimatePresence mode="wait">
            <Routes location={location} key={location.pathname}>
              {VIEW_ENTRIES.map(([id, { path, Component }]) => (
                <Route
                  key={id}
                  path={toControlRoomRoute(path)}
                  element={
                    <motion.div
                      key={id}
                      initial={{ opacity: 0, x: 10 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -10 }}
                      transition={{ duration: 0.15 }}
                      className="min-h-[calc(100dvh-3.5rem)] pb-24"
                    >
                      <Component />
                    </motion.div>
                  }
                />
              ))}
              <Route path="*" element={<Navigate to={toControlRoomRoute(VIEWS.dashboard.path)} replace />} />
            </Routes>
          </AnimatePresence>
        </main>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<PublicWebsite />} />
          {/* Legacy /command URL — redirect to control room */}
          <Route path="/command" element={<Navigate to={VIEWS.dashboard.path} replace />} />
          <Route path="/command/*" element={<Navigate to={VIEWS.dashboard.path} replace />} />
          <Route path="/control-room" element={<Navigate to={VIEWS.dashboard.path} replace />} />
          <Route
            path="/control-room/*"
            element={
              <ErrorBoundary>
                <AuthGate>
                  <AppShell />
                </AuthGate>
              </ErrorBoundary>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  )
}
