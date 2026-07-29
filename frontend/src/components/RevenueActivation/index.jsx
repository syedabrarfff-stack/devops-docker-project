import React, { useCallback, useEffect, useState } from 'react'
import {
  Activity,
  Building2,
  DollarSign,
  Globe,
  Key,
  Linkedin,
  Loader2,
  MessageSquare,
  Mic,
  Phone,
  RefreshCw,
  Slack,
  TrendingUp,
  Users,
  Webhook,
  Zap,
} from 'lucide-react'
import api from '../../services/api'

// ── Helpers ───────────────────────────────────────────────────────────────────
const fmt = (n) => (n == null ? '—' : Number(n).toLocaleString())
const gbp = (n) => (n == null ? '—' : `£${Number(n).toLocaleString()}`)

function Card({ icon: Icon, title, children, accent = 'cyan' }) {
  const border = accent === 'green' ? 'border-emerald-700/50' : 'border-slate-700/50'
  return (
    <div className={`bg-slate-800/60 border ${border} rounded-xl p-4`}>
      <div className="flex items-center gap-2 mb-3">
        {Icon && <Icon size={15} className={accent === 'green' ? 'text-emerald-400' : 'text-cyan-400'} />}
        <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-widest">{title}</h3>
      </div>
      {children}
    </div>
  )
}

function Stat({ label, value, sub }) {
  return (
    <div className="space-y-0.5">
      <p className="text-xs text-slate-400">{label}</p>
      <p className="text-xl font-bold text-white tabular-nums">{value}</p>
      {sub && <p className="text-[11px] text-slate-500">{sub}</p>}
    </div>
  )
}

// ── Tabs ──────────────────────────────────────────────────────────────────────
const TABS = [
  { id: 'mrr',       label: 'MRR',          Icon: TrendingUp },
  { id: 'tenants',   label: 'White-label',   Icon: Building2 },
  { id: 'linkedin',  label: 'LinkedIn',      Icon: Linkedin },
  { id: 'zapier',    label: 'Zapier/Make',   Icon: Webhook },
  { id: 'voice',     label: 'Voice',         Icon: Mic },
  { id: 'slack',     label: 'Slack',         Icon: Slack },
]

// ── MRR Panel ─────────────────────────────────────────────────────────────────
function MRRPanel() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const r = await api.get('/captain/licensing/mrr')
      setData(r.data)
    } catch {
      setData(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  if (loading) return <div className="flex justify-center py-8"><Loader2 className="animate-spin text-cyan-400" /></div>
  if (!data) return <p className="text-slate-400 text-sm">Could not load MRR data.</p>

  const breakdown = data.breakdown || {}
  const TIER_COLOR = { STARTER: 'text-slate-300', GROWTH: 'text-blue-400', ENTERPRISE: 'text-purple-400', INDUSTRY_OS: 'text-amber-400' }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <Card icon={DollarSign} title="Total MRR" accent="green">
          <Stat label="Monthly Recurring Revenue" value={gbp(data.total_mrr_gbp)} sub={`${fmt(data.total_tenants)} active tenants`} />
        </Card>
        <Card icon={Globe} title="Annual Run Rate" accent="green">
          <Stat label="ARR" value={gbp((data.total_mrr_gbp || 0) * 12)} sub="Projected at current MRR" />
        </Card>
      </div>

      <Card icon={Building2} title="Revenue by Plan Tier">
        <div className="space-y-2">
          {Object.entries(breakdown).map(([tier, d]) => (
            <div key={tier} className="flex items-center justify-between text-sm">
              <span className={`font-semibold ${TIER_COLOR[tier] || 'text-slate-300'}`}>{tier}</span>
              <span className="text-slate-400">{fmt(d.count)} tenant{d.count !== 1 ? 's' : ''}</span>
              <span className="text-white tabular-nums">{gbp(d.revenue_gbp)}/mo</span>
              <span className="text-slate-500 text-xs">{gbp(d.price_gbp)} each</span>
            </div>
          ))}
          {Object.keys(breakdown).length === 0 && (
            <p className="text-slate-500 text-xs">No active tenants yet.</p>
          )}
        </div>
      </Card>
    </div>
  )
}

// ── Tenants Panel ─────────────────────────────────────────────────────────────
function TenantsPanel() {
  const [tenants, setTenants] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/captain/licensing/tenants')
      .then(r => setTenants(r.data || []))
      .catch(() => setTenants([]))
      .finally(() => setLoading(false))
  }, [])

  const TIER_BADGE = {
    STARTER: 'bg-slate-700 text-slate-300',
    GROWTH: 'bg-blue-900/60 text-blue-300',
    ENTERPRISE: 'bg-purple-900/60 text-purple-300',
    INDUSTRY_OS: 'bg-amber-900/60 text-amber-300',
  }

  if (loading) return <div className="flex justify-center py-8"><Loader2 className="animate-spin text-cyan-400" /></div>

  return (
    <div className="space-y-2">
      {tenants.length === 0 && (
        <p className="text-slate-400 text-sm py-4">No white-label tenants provisioned yet.</p>
      )}
      {tenants.map(t => (
        <div key={t.tenant_id} className="flex items-center justify-between bg-slate-800/40 border border-slate-700/40 rounded-lg px-4 py-3 text-sm">
          <div>
            <p className="font-semibold text-white">{t.company_name}</p>
            <p className="text-slate-400 text-xs">{t.admin_email}</p>
          </div>
          <div className="flex items-center gap-3">
            <span className={`text-[11px] font-semibold px-2 py-0.5 rounded ${TIER_BADGE[t.plan_tier] || 'bg-slate-700 text-slate-300'}`}>
              {t.plan_tier}
            </span>
            <span className={`text-xs font-semibold ${t.is_active ? 'text-emerald-400' : 'text-red-400'}`}>
              {t.is_active ? 'ACTIVE' : 'INACTIVE'}
            </span>
          </div>
        </div>
      ))}
    </div>
  )
}

// ── LinkedIn Panel ────────────────────────────────────────────────────────────
function LinkedInPanel() {
  return (
    <div className="space-y-4">
      <Card icon={Linkedin} title="LinkedIn Outreach Engine">
        <div className="space-y-3 text-sm">
          <p className="text-slate-300">
            Enriches HOT leads (score ≥ 60) with LinkedIn profile data via Proxycurl
            and generates AI-crafted first-connection messages.
          </p>
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-slate-900/50 rounded-lg p-3">
              <p className="text-xs text-slate-400 mb-1">Sweep Frequency</p>
              <p className="text-white font-semibold">Every 2 hours</p>
            </div>
            <div className="bg-slate-900/50 rounded-lg p-3">
              <p className="text-xs text-slate-400 mb-1">Per-Sweep Cap</p>
              <p className="text-white font-semibold">25 leads</p>
            </div>
          </div>
          <div className="bg-slate-900/50 rounded-lg p-3 text-xs text-slate-400">
            <p className="font-semibold text-slate-300 mb-1">Setup Required:</p>
            <p>Set <code className="text-cyan-400">PROXYCURL_API_KEY</code> in .env to activate enrichment.</p>
            <p className="mt-1">Messages are generated via AI Fabric (SALES task type) and stored in lead.linkedin_message.</p>
          </div>
        </div>
      </Card>
    </div>
  )
}

// ── Zapier Panel ──────────────────────────────────────────────────────────────
function ZapierPanel() {
  const endpoints = [
    { method: 'POST', path: '/api/v1/webhooks/zapier/lead', desc: 'Inbound lead from any form (Typeform, JotForm, Calendly)' },
    { method: 'POST', path: '/api/v1/webhooks/zapier/payment', desc: 'Payment confirmed (Stripe, PayPal, Wise via Zapier)' },
    { method: 'POST', path: '/api/v1/webhooks/make/trigger', desc: 'Generic Make.com scenario trigger' },
    { method: 'POST', path: '/api/v1/webhooks/make/lead', desc: 'Lead from Make.com scenario' },
  ]
  return (
    <div className="space-y-4">
      <Card icon={Webhook} title="Inbound Webhook Endpoints">
        <div className="space-y-2">
          {endpoints.map(e => (
            <div key={e.path} className="bg-slate-900/50 rounded-lg p-3 text-xs">
              <div className="flex items-center gap-2 mb-1">
                <span className="bg-blue-900/60 text-blue-300 px-1.5 py-0.5 rounded font-mono">{e.method}</span>
                <code className="text-cyan-400">{e.path}</code>
              </div>
              <p className="text-slate-400">{e.desc}</p>
            </div>
          ))}
        </div>
      </Card>
      <Card icon={Zap} title="Outbound Events">
        <div className="space-y-1 text-xs text-slate-400">
          <p>Set in .env to trigger Zapier/Make on JARVIS events:</p>
          <code className="block text-cyan-400 mt-1">ZAPIER_LEAD_QUALIFIED_HOOK=https://hooks.zapier.com/...</code>
          <code className="block text-cyan-400">ZAPIER_PROPOSAL_SENT_HOOK=https://hooks.zapier.com/...</code>
          <code className="block text-cyan-400">MAKE_APPROVAL_HOOK=https://hook.eu1.make.com/...</code>
        </div>
      </Card>
    </div>
  )
}

// ── Voice Panel ───────────────────────────────────────────────────────────────
function VoicePanel() {
  const capabilities = [
    { icon: Mic, label: 'Inbound Transcription', desc: 'WhatsApp voice → Whisper → text + intent classification', endpoint: 'POST /webhooks/voice/transcribe' },
    { icon: Phone, label: 'Call Summariser', desc: 'Recording URL → transcribe → AI summary → Captain alert', endpoint: 'POST /webhooks/voice/call-ended' },
    { icon: MessageSquare, label: 'Voice Note Send', desc: 'Text → ElevenLabs TTS → Evolution API WhatsApp voice', endpoint: 'POST /voice/send-note' },
    { icon: Activity, label: 'Voice Analytics', desc: 'Daily metrics: inbound count, call outcomes, conversion rate', endpoint: 'Scheduler: 04:30 UTC' },
  ]
  return (
    <div className="grid grid-cols-2 gap-3">
      {capabilities.map(c => (
        <Card key={c.label} icon={c.icon} title={c.label}>
          <p className="text-xs text-slate-400 mb-2">{c.desc}</p>
          <code className="text-[11px] text-cyan-400">{c.endpoint}</code>
        </Card>
      ))}
    </div>
  )
}

// ── Slack Panel ───────────────────────────────────────────────────────────────
function SlackPanel() {
  const commands = [
    { cmd: '/jarvis status', desc: 'System health + active lead count' },
    { cmd: '/jarvis leads', desc: 'Top 5 active leads by ICP score' },
    { cmd: '/jarvis pipeline', desc: 'Pipeline breakdown by stage' },
    { cmd: '/jarvis approve <id>', desc: 'Approve a pending request' },
    { cmd: '/jarvis reject <id> [reason]', desc: 'Reject a pending request' },
    { cmd: '/jarvis briefing', desc: 'Trigger a briefing generation' },
  ]
  return (
    <div className="space-y-4">
      <Card icon={Slack} title="Slack Bot Commands">
        <div className="space-y-2">
          {commands.map(c => (
            <div key={c.cmd} className="flex items-start gap-3 text-xs">
              <code className="text-cyan-400 whitespace-nowrap shrink-0">{c.cmd}</code>
              <span className="text-slate-400">{c.desc}</span>
            </div>
          ))}
        </div>
      </Card>
      <Card icon={Key} title="Setup">
        <div className="space-y-1 text-xs text-slate-400">
          <p>1. Create a Slack App at <span className="text-cyan-400">api.slack.com/apps</span></p>
          <p>2. Enable Slash Commands → URL: <code className="text-cyan-400">/api/v1/webhooks/slack/command</code></p>
          <p>3. Enable Events API → URL: <code className="text-cyan-400">/api/v1/webhooks/slack/events</code></p>
          <p>4. Set in .env:</p>
          <code className="block text-cyan-400 ml-2">SLACK_BOT_TOKEN=xoxb-...</code>
          <code className="block text-cyan-400 ml-2">SLACK_SIGNING_SECRET=...</code>
        </div>
      </Card>
    </div>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────────
export default function RevenueActivation() {
  const [tab, setTab] = useState('mrr')

  const PANEL = {
    mrr:      <MRRPanel />,
    tenants:  <TenantsPanel />,
    linkedin: <LinkedInPanel />,
    zapier:   <ZapierPanel />,
    voice:    <VoicePanel />,
    slack:    <SlackPanel />,
  }

  return (
    <div className="space-y-4 p-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Revenue Activation</h1>
          <p className="text-xs text-slate-400 mt-0.5">White-label licensing · LinkedIn outreach · Zapier/Make · Voice · Slack</p>
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <Activity size={12} className="text-emerald-400" />
          Phase 6A + 6B
        </div>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 bg-slate-800/50 rounded-lg p-1 overflow-x-auto">
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors whitespace-nowrap ${
              tab === t.id
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700/40'
            }`}
          >
            <t.Icon size={12} />
            {t.label}
          </button>
        ))}
      </div>

      {/* Panel */}
      <div>{PANEL[tab]}</div>
    </div>
  )
}
