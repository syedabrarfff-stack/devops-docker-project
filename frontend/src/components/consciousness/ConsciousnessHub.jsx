import React, { useMemo, useState } from 'react'
import api from '../../services/api'
import {
  ActionCard,
  DEFAULT_TENANT,
  FrontierShell,
  ResultBox,
  RunButton,
  Textarea,
} from '../frontier/FrontierShell'

const TABS = [
  { key: 'emotional',    label: 'Emotional State' },
  { key: 'soul',         label: 'Soul & Values' },
  { key: 'giants',       label: 'Council of Giants' },
  { key: 'competitive',  label: 'Competitive Intel' },
  { key: 'heart',        label: 'Prospect Heart' },
  { key: 'vision',       label: 'Vision & Horizon' },
  { key: 'offer',        label: 'Offer Engine' },
  { key: 'upgrade',      label: 'Self-Upgrade' },
  { key: 'captain',      label: 'Captain Profile' },
]

const DEFAULT_PIPELINE = {
  clients_signed: 0,
  hot_leads: 3,
  closing_leads: 0,
  leads_gone_cold_7d: 2,
  days_since_last_win: 999,
  open_proposals: 1,
  positive_reply_last_48h: false,
}

export default function ConsciousnessHub() {
  const [activeTab, setActiveTab] = useState('emotional')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [inputText, setInputText] = useState('')
  const [inputText2, setInputText2] = useState('')
  const [pageError, setPageError] = useState(null)

  async function run(fn) {
    setLoading(true)
    setResult(null)
    setPageError(null)
    try {
      const data = await fn()
      setResult(data)
    } catch (err) {
      const message = err.response?.data?.detail || err.message || 'Unknown error'
      setResult({ error: message })
      setPageError(message)
    } finally {
      setLoading(false)
    }
  }

  // ── Tab: Emotional State ──────────────────────────────────────────────────
  function renderEmotional() {
    return (
      <div className="space-y-3">
        <ActionCard title="Assess Emotional State" description="Read the live pipeline and set JARVIS's operating mode.">
          <RunButton
            label="Assess Current State"
            loading={loading}
            onClick={() => run(async () => {
              const r = await api.post('/api/v1/consciousness/emotional-state', DEFAULT_PIPELINE)
              return r.data
            })}
          />
        </ActionCard>
        <ActionCard title="Tone Profile" description="Get the writing tone profile for a state (e.g. HUNGRY, OBSESSED, IGNITED).">
          <input
            value={inputText}
            onChange={e => setInputText(e.target.value)}
            placeholder="State: HUNGRY"
            className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white/80 outline-none mb-2"
          />
          <RunButton
            label="Get Tone Profile"
            loading={loading}
            onClick={() => run(async () => {
              const r = await api.get(`/api/v1/consciousness/emotional-state/tone/${inputText || 'HUNGRY'}`)
              return r.data
            })}
          />
        </ActionCard>
      </div>
    )
  }

  // ── Tab: Soul ─────────────────────────────────────────────────────────────
  function renderSoul() {
    return (
      <div className="space-y-3">
        <ActionCard title="Identity Affirmation" description="Who we are. Non-negotiable.">
          <RunButton label="Get Identity" loading={loading} onClick={() => run(async () => {
            const r = await api.get('/api/v1/consciousness/soul/identity')
            return r.data
          })} />
        </ActionCard>
        <ActionCard title="Non-Negotiables" description="The 7 principles JARVIS will never cross.">
          <RunButton label="View Non-Negotiables" loading={loading} onClick={() => run(async () => {
            const r = await api.get('/api/v1/consciousness/soul/non-negotiables')
            return r.data
          })} />
        </ActionCard>
        <ActionCard title="Cultural Profile" description="Communication intelligence for a geography.">
          <input
            value={inputText}
            onChange={e => setInputText(e.target.value)}
            placeholder="Geography: UK, UAE, USA, INDIA..."
            className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white/80 outline-none mb-2"
          />
          <RunButton label="Get Cultural Profile" loading={loading} onClick={() => run(async () => {
            const r = await api.get(`/api/v1/consciousness/soul/culture/${inputText || 'UK'}`)
            return r.data
          })} />
        </ActionCard>
        <ActionCard title="Validate Action" description="Check whether an action violates our soul.">
          <Textarea value={inputText} onChange={setInputText} placeholder="Describe the proposed action..." />
          <RunButton label="Validate" loading={loading} onClick={() => run(async () => {
            const r = await api.post('/api/v1/consciousness/soul/validate', { proposed_action: inputText })
            return r.data
          })} />
        </ActionCard>
      </div>
    )
  }

  // ── Tab: Council of Giants ────────────────────────────────────────────────
  function renderGiants() {
    return (
      <div className="space-y-3">
        <ActionCard title="Convene the Council" description="Bring the 15 Giants to a strategic decision.">
          <input
            value={inputText}
            onChange={e => setInputText(e.target.value)}
            placeholder="Decision type: pricing, strategy, offer, competition..."
            className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white/80 outline-none mb-2"
          />
          <Textarea value={inputText2} onChange={setInputText2} placeholder="Describe the decision context..." />
          <RunButton label="Convene" loading={loading} onClick={() => run(async () => {
            const r = await api.post('/api/v1/consciousness/council-of-giants/convene', {
              decision_type: inputText || 'strategy',
              context: inputText2 || 'How do we acquire our first client?',
              options: [],
            })
            return r.data
          })} />
        </ActionCard>
        <ActionCard title="Giant on Demand" description="Ask a specific Giant a question.">
          <input
            value={inputText}
            onChange={e => setInputText(e.target.value)}
            placeholder="Giant key: MUSK, BEZOS, HORMOZI, JOBS..."
            className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white/80 outline-none mb-2"
          />
          <Textarea value={inputText2} onChange={setInputText2} placeholder="The question..." />
          <RunButton label="Ask" loading={loading} onClick={() => run(async () => {
            const r = await api.get(`/api/v1/consciousness/council-of-giants/giant/${inputText || 'HORMOZI'}`, {
              params: { question: inputText2 || 'How do we make our offer irresistible?' }
            })
            return r.data
          })} />
        </ActionCard>
        <ActionCard title="Full Roster" description="All 15 Giants — domains and principles.">
          <RunButton label="View Roster" loading={loading} onClick={() => run(async () => {
            const r = await api.get('/api/v1/consciousness/council-of-giants/roster')
            return r.data
          })} />
        </ActionCard>
      </div>
    )
  }

  // ── Tab: Competitive Intel ────────────────────────────────────────────────
  function renderCompetitive() {
    return (
      <div className="space-y-3">
        <ActionCard title="Decode Competitor Strategy" description="Extract the full strategy DNA of a competitor.">
          <input
            value={inputText}
            onChange={e => setInputText(e.target.value)}
            placeholder="Company name..."
            className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white/80 outline-none mb-2"
          />
          <RunButton label="Decode" loading={loading} onClick={() => run(async () => {
            const r = await api.post('/api/v1/consciousness/competitor/decode', {
              company_name: inputText || 'Competitor Inc',
              pricing_page: 'enterprise pricing, contact us for details',
              about_page: 'We help enterprise companies integrate technology solutions',
              client_reviews: ['too expensive', 'complex to implement', 'slow support'],
              job_postings: ['Senior SDR', 'Enterprise Account Executive', 'Content Marketing Manager'],
              signals: {},
              sources: ['manual research'],
            })
            return r.data
          })} />
        </ActionCard>
        <ActionCard title="Competitive Briefing" description="Generate a full competitive briefing from decoded competitor profiles.">
          <RunButton label="Generate Briefing" loading={loading} onClick={() => run(async () => {
            const r = await api.post('/api/v1/consciousness/competitor/briefing', [
              {
                company_name: inputText || 'Competitor Inc',
                pricing_model: 'enterprise',
                target_market: 'mid-market',
                weaknesses: ['slow implementation', 'high price'],
                strengths: ['brand recognition'],
              },
            ])
            return r.data
          })} />
        </ActionCard>
        <ActionCard title="Competitive Stances" description="The 6 attack positions JARVIS can take.">
          <RunButton label="View Stances" loading={loading} onClick={() => run(async () => {
            const r = await api.get('/api/v1/consciousness/competitive-stances')
            return r.data
          })} />
        </ActionCard>
      </div>
    )
  }

  // ── Tab: Heart / Prospect Psychology ─────────────────────────────────────
  function renderHeart() {
    return (
      <div className="space-y-3">
        <ActionCard title="Profile a Prospect" description="Decode their emotional drivers and build the perfect approach.">
          <RunButton label="Profile VaultPay" loading={loading} onClick={() => run(async () => {
            const r = await api.post('/api/v1/consciousness/heart/profile-prospect', {
              lead_data: {
                id: 'vaultpay-001',
                company_name: 'VaultPay',
                industry: 'FinTech',
                contact_title: 'CEO',
                employee_count: 45,
                notes: 'Mentioned competitors are moving faster, wants to see ROI, asked about guarantees',
                tags: ['growth', 'scaling'],
              },
              interaction_history: [],
            })
            return r.data
          })} />
        </ActionCard>
        <ActionCard title="Relationship Health" description="Assess the health of a client relationship from interaction history.">
          <RunButton label="Assess (Demo)" loading={loading} onClick={() => run(async () => {
            const r = await api.post('/api/v1/consciousness/heart/relationship-health', [
              { type: 'email', direction: 'outbound', sentiment: 'positive', days_ago: 5 },
              { type: 'call', direction: 'inbound', sentiment: 'neutral', days_ago: 12 },
              { type: 'proposal', direction: 'outbound', sentiment: 'positive', days_ago: 20 },
            ])
            return r.data
          })} />
        </ActionCard>
        <ActionCard title="Emotional Drivers Reference" description="All 8 buying motivation profiles.">
          <RunButton label="View Drivers" loading={loading} onClick={() => run(async () => {
            const r = await api.get('/api/v1/consciousness/heart/emotional-drivers')
            return r.data
          })} />
        </ActionCard>
      </div>
    )
  }

  // ── Tab: Vision ───────────────────────────────────────────────────────────
  function renderVision() {
    return (
      <div className="space-y-3">
        <ActionCard title="Generate Horizon Map" description="H1/H2/H3 — where we act, build, and position.">
          <RunButton label="Generate Map" loading={loading} onClick={() => run(async () => {
            const r = await api.post('/api/v1/consciousness/vision/horizon-map', {
              clients_signed: 0,
              monthly_recurring_revenue: 0,
              hot_leads: 3,
              days_since_launch: 14,
            })
            return r.data
          })} />
        </ActionCard>
        <ActionCard title="Trajectory Assessment" description="Assess growth trajectory from historical monthly states.">
          <RunButton label="Assess Trajectory" loading={loading} onClick={() => run(async () => {
            const r = await api.post('/api/v1/consciousness/vision/trajectory', [
              { month: 1, clients_signed: 0, monthly_recurring_revenue: 0, hot_leads: 3 },
              { month: 2, clients_signed: 1, monthly_recurring_revenue: 3000, hot_leads: 7 },
            ])
            return r.data
          })} />
        </ActionCard>
        <ActionCard title="Compounding Assets" description="What compounds and how fast.">
          <RunButton label="View Assets" loading={loading} onClick={() => run(async () => {
            const r = await api.get('/api/v1/consciousness/vision/compounding-assets')
            return r.data
          })} />
        </ActionCard>
        <ActionCard title="Milestone Map" description="The trajectory from first client to $5M valuation.">
          <RunButton label="View Milestones" loading={loading} onClick={() => run(async () => {
            const r = await api.get('/api/v1/consciousness/vision/milestones')
            return r.data
          })} />
        </ActionCard>
      </div>
    )
  }

  // ── Tab: Offer Engine ─────────────────────────────────────────────────────
  function renderOffer() {
    return (
      <div className="space-y-3">
        <ActionCard title="Build Grand Slam Offer" description="Hormozi-grade offer construction for a lead.">
          <RunButton label="Build for VaultPay" loading={loading} onClick={() => run(async () => {
            const r = await api.post('/api/v1/consciousness/offer/build', {
              lead_data: {
                company_name: 'VaultPay',
                industry: 'FinTech',
                employee_count: 45,
                pain_points: ['manual reporting taking 8 hours/week', 'no automated lead follow-up'],
              },
              recommended_tier: 'GROWTH',
            })
            return r.data
          })} />
        </ActionCard>
        <ActionCard title="Auto-Select Tier" description="JARVIS recommends the right pricing tier for a lead.">
          <RunButton label="Select Tier (VaultPay)" loading={loading} onClick={() => run(async () => {
            const r = await api.post('/api/v1/consciousness/offer/select-tier', {
              company_name: 'VaultPay',
              industry: 'FinTech',
              employee_count: 45,
              annual_revenue_estimate: 2000000,
              pain_severity: 'high',
            })
            return r.data
          })} />
        </ActionCard>
        <ActionCard title="Pricing Tiers" description="All 4 Aliyar Solutions pricing structures.">
          <RunButton label="View Tiers" loading={loading} onClick={() => run(async () => {
            const r = await api.get('/api/v1/consciousness/offer/tiers')
            return r.data
          })} />
        </ActionCard>
        <ActionCard title="Handle Objection" description="Get the response framework for any objection.">
          <input
            value={inputText}
            onChange={e => setInputText(e.target.value)}
            placeholder="Objection type: too_expensive, not_sure_it_works, need_to_think..."
            className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white/80 outline-none mb-2"
          />
          <RunButton label="Get Response" loading={loading} onClick={() => run(async () => {
            const r = await api.get(`/api/v1/consciousness/offer/objection/${inputText || 'too_expensive'}`)
            return r.data
          })} />
        </ActionCard>
      </div>
    )
  }

  // ── Tab: Self-Upgrade ─────────────────────────────────────────────────────
  function renderUpgrade() {
    return (
      <div className="space-y-3">
        <ActionCard title="Weekly Upgrade Plan" description="JARVIS measures itself and generates a ranked improvement plan.">
          <RunButton label="Generate Plan" loading={loading} onClick={() => run(async () => {
            const r = await api.post('/api/v1/consciousness/upgrade/weekly-plan', {
              performance_data: {
                outreach_reply_rate: 4,
                proposal_close_rate: 0,
                delivery_on_time_rate: 1.0,
                lead_score_accuracy: 0.6,
                autonomous_task_rate: 0.65,
                client_retention_rate: 0,
                system_uptime: 0.99,
                competitive_win_rate: 0,
              },
              recent_failures: [],
            })
            return r.data
          })} />
        </ActionCard>
        <ActionCard title="Log Failure & Learn" description="Every failure becomes a principle.">
          <input
            value={inputText}
            onChange={e => setInputText(e.target.value)}
            placeholder="Failure type..."
            className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white/80 outline-none mb-2"
          />
          <Textarea value={inputText2} onChange={setInputText2} placeholder="Root cause and prevention principle (JSON: {failure_detail, root_cause, prevention_principle})" />
          <RunButton label="Log & Learn" loading={loading} onClick={() => {
            let parsed = {}
            try { parsed = JSON.parse(inputText2) } catch {}
            return run(async () => {
              const r = await api.post('/api/v1/consciousness/upgrade/log-failure', {
                failure_type: inputText || 'system_error',
                failure_detail: parsed.failure_detail || inputText2 || 'No detail provided',
                root_cause: parsed.root_cause || 'Unknown',
                prevention_principle: parsed.prevention_principle || 'Add monitoring',
              })
              return r.data
            })
          }} />
        </ActionCard>
        <ActionCard title="Dimension Deep Dive" description="Get the detailed upgrade plan for a specific dimension.">
          <input
            value={inputText}
            onChange={e => setInputText(e.target.value)}
            placeholder="Dimension: outreach, conversion, delivery, intelligence..."
            className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white/80 outline-none mb-2"
          />
          <RunButton label="Deep Dive" loading={loading} onClick={() => run(async () => {
            const r = await api.get(`/api/v1/consciousness/upgrade/dimension/${inputText || 'outreach'}`)
            return r.data
          })} />
        </ActionCard>
        <ActionCard title="Council of Giants Benchmarks" description="How JARVIS measures against the 15 Giants' standards.">
          <RunButton label="View Benchmarks" loading={loading} onClick={() => run(async () => {
            const r = await api.get('/api/v1/consciousness/upgrade/giants-benchmarks')
            return r.data
          })} />
        </ActionCard>
      </div>
    )
  }

  // ── Tab: Captain Profile ──────────────────────────────────────────────────
  function renderCaptain() {
    return (
      <div className="space-y-3">
        <ActionCard title="Captain Full Profile" description="JARVIS's deep intelligence on Captain's preferences and operating style.">
          <RunButton label="View Profile" loading={loading} onClick={() => run(async () => {
            const r = await api.get('/api/v1/consciousness/captain/profile')
            return r.data
          })} />
        </ActionCard>
        <ActionCard title="Active Priorities" description="What Captain is focused on right now.">
          <RunButton label="View Priorities" loading={loading} onClick={() => run(async () => {
            const r = await api.get('/api/v1/consciousness/captain/priorities')
            return r.data
          })} />
        </ActionCard>
        <ActionCard title="Never-Do List" description="The hard lines Captain has set — actions JARVIS must never take autonomously.">
          <RunButton label="View Never-Do List" loading={loading} onClick={() => run(async () => {
            const r = await api.get('/api/v1/consciousness/captain/never-do')
            return r.data
          })} />
        </ActionCard>
        <ActionCard title="Detect Captain State" description="Read recent messages to detect Captain's current operating mode.">
          <Textarea value={inputText} onChange={setInputText} placeholder='Recent messages (one per line)...' />
          <RunButton label="Detect State" loading={loading} onClick={() => run(async () => {
            const messages = inputText.split('\n').filter(Boolean)
            const r = await api.post('/api/v1/consciousness/captain/detect-state', { recent_messages: messages })
            return r.data
          })} />
        </ActionCard>
        <ActionCard title="Blind Spot Check" description="Check a decision for Captain's known blind spots.">
          <Textarea value={inputText2} onChange={setInputText2} placeholder='Describe the decision context...' />
          <RunButton label="Check" loading={loading} onClick={() => run(async () => {
            const r = await api.post('/api/v1/consciousness/captain/blind-spot-check', { decision_context: inputText2 })
            return r.data
          })} />
        </ActionCard>
      </div>
    )
  }

  const TAB_RENDER = {
    emotional:   renderEmotional,
    soul:        renderSoul,
    giants:      renderGiants,
    competitive: renderCompetitive,
    heart:       renderHeart,
    vision:      renderVision,
    offer:       renderOffer,
    upgrade:     renderUpgrade,
    captain:     renderCaptain,
  }

  let activeContent = null
  try {
    activeContent = TAB_RENDER[activeTab]?.() || null
  } catch (error) {
    activeContent = (
      <div className="rounded-2xl border border-red-400/20 bg-red-500/10 p-4 text-sm text-red-100">
        <p className="font-semibold">Consciousness view failed to render</p>
        <p className="mt-1 text-xs leading-relaxed text-red-100/80">
          {error?.message || 'Unknown render error'}
        </p>
      </div>
    )
  }

  return (
    <FrontierShell
      title="Consciousness Hub"
      subtitle="JARVIS Soul - Heart - Brain - The Complete Inner Operating System"
    >
      <div className="rounded-2xl border border-amber-400/20 bg-amber-500/10 p-3 mb-3 text-xs text-amber-100/90">
        Diagnostic console — most buttons here send fixed sample data (e.g. a demo
        "VaultPay" lead) to exercise each engine's logic in isolation. Results reflect
        that sample input, not your live pipeline. Use Revenue Intel, Leads, or CRM for
        real business figures.
      </div>
      {pageError && (
        <div className="rounded-2xl border border-red-400/20 bg-red-500/10 p-4 text-sm text-red-100">
          <p className="font-semibold">Consciousness page alert</p>
          <p className="mt-1 text-xs leading-relaxed text-red-100/80">{pageError}</p>
        </div>
      )}
      {/* Tab bar */}
      <div className="flex flex-wrap gap-1.5 mb-6 overflow-x-auto pb-1">
        {TABS.map(t => (
          <button
            key={t.key}
            onClick={() => { setActiveTab(t.key); setResult(null); setPageError(null) }}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all
              ${activeTab === t.key
                ? 'bg-jarvis-blue/20 border border-jarvis-blue/40 text-jarvis-blue'
                : 'bg-white/5 border border-white/10 text-white/50 hover:text-white/80 hover:bg-white/10'
              }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Active tab content */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 min-h-0">
        <div className="space-y-3">
          {activeContent}
        </div>
        <div>
          <ResultBox result={result} loading={loading} />
        </div>
      </div>
    </FrontierShell>
  )
}
