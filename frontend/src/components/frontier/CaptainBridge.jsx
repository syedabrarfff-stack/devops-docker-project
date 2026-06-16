import React, { useMemo, useState } from 'react'
import api from '../../services/api'
import {
  ActionCard,
  DEFAULT_TENANT,
  FrontierShell,
  Input,
  ResultBox,
  RunButton,
  Textarea,
} from './FrontierShell'

export default function CaptainBridge() {
  const [leadText, setLeadText] = useState('')
  const [brainDump, setBrainDump] = useState('')
  const [emailThread, setEmailThread] = useState('')
  const [decision, setDecision] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [clientForm, setClientForm] = useState({
    company_name: '', contact_name: '', email: '', package_tier: 'growth', mrr_usd: '',
  })
  const [clientLoading, setClientLoading] = useState(false)

  const setClient = (k) => (v) => setClientForm(f => ({ ...f, [k]: v }))

  const submitClient = async (e) => {
    e.preventDefault()
    if (!clientForm.company_name.trim()) return
    setClientLoading(true)
    try {
      const response = await api.post('/api/v1/clients', {
        company_name: clientForm.company_name.trim(),
        contact_name: clientForm.contact_name.trim() || undefined,
        email: clientForm.email.trim() || undefined,
        package_tier: clientForm.package_tier || undefined,
        mrr_usd: parseFloat(clientForm.mrr_usd) || 0,
        status: 'active',
        tenant_id: DEFAULT_TENANT,
      })
      setResult(response.data)
      setClientForm({ company_name: '', contact_name: '', email: '', package_tier: 'growth', mrr_usd: '' })
    } catch (error) {
      setResult({ error: error.response?.data?.detail || error.message })
    }
    setClientLoading(false)
  }

  const endpoints = useMemo(() => [
    { key: 'situation', label: 'Situation report', path: '/api/v1/captain/situation', params: { tenant_id: DEFAULT_TENANT } },
    { key: 'threats', label: 'Threat scan', path: '/api/v1/captain/threats', params: { tenant_id: DEFAULT_TENANT } },
    { key: 'actions', label: 'Predicted next actions', path: '/api/v1/captain/predict-actions', params: { tenant_id: DEFAULT_TENANT } },
    { key: 'state', label: 'Captain state', path: '/api/v1/captain/state', params: { tenant_id: DEFAULT_TENANT } },
    { key: 'decisionLoad', label: 'Decision load', path: '/api/v1/captain/decision-load', params: { tenant_id: DEFAULT_TENANT } },
    { key: 'warRoom', label: 'War-room brief', path: '/api/v1/captain/war-room-brief', params: { tenant_id: DEFAULT_TENANT } },
    { key: 'pilotStatus', label: 'Pilot mode status', path: '/api/v1/pilot/status', params: { tenant_id: DEFAULT_TENANT } },
    { key: 'mirrorProfile', label: 'Captain mirror profile', path: '/api/v1/captain/mirror/profile', params: { tenant_id: DEFAULT_TENANT } },
    { key: 'mirrorPatterns', label: 'Captain decision patterns', path: '/api/v1/captain/mirror/patterns', params: { tenant_id: DEFAULT_TENANT } },
    { key: 'experiments', label: 'Active experiments', path: '/api/v1/experiments', params: { tenant_id: DEFAULT_TENANT } },
    { key: 'serviceConcepts', label: 'Service concepts', path: '/api/v1/services/concepts', params: { tenant_id: DEFAULT_TENANT } },
  ], [])

  const [mirrorDecision, setMirrorDecision] = useState({ decision: '', context: '', outcome: '', confidence: 8 })
  const [mirrorPredictQ, setMirrorPredictQ] = useState('')
  const [expForm, setExpForm] = useState({ name: '', hypothesis: '', variant_a: '', variant_b: '' })

  async function submit(path, body) {
    setLoading(true)
    try {
      const response = await api.post(path, { ...body, tenant_id: DEFAULT_TENANT })
      setResult(response.data)
    } catch (error) {
      setResult({ error: error.response?.data?.detail || error.message })
    }
    setLoading(false)
  }

  return (
    <FrontierShell
      eyebrow="Captain Bridge"
      title="Captain Bridge"
      description="Bring raw leads, email threads, brain dumps, and hard decisions into JARVIS so the operating system converts them into structured action."
      endpoints={endpoints}
    >
      {() => (
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
          <ActionCard title="Bring a Lead" subtitle="Paste the messy opportunity text Captain found. JARVIS parses it into a lead record and next actions.">
            <form onSubmit={(event) => { event.preventDefault(); submit('/api/v1/captain/bring-lead', { raw_input: leadText }) }}>
              <Textarea value={leadText} onChange={setLeadText} placeholder="Company, domain, contact, problem, notes, service interest..." />
              <RunButton loading={loading} disabled={!leadText.trim()}>Process lead</RunButton>
            </form>
          </ActionCard>

          <ActionCard title="Brain Dump" subtitle="Turn Captain notes into tasks, insights, leads, decisions, and follow-ups.">
            <form onSubmit={(event) => { event.preventDefault(); submit('/api/v1/captain/brain-dump', { text: brainDump }) }}>
              <Textarea value={brainDump} onChange={setBrainDump} placeholder="Paste thoughts, plans, worries, client notes, or market observations." />
              <RunButton loading={loading} disabled={!brainDump.trim()}>Structure notes</RunButton>
            </form>
          </ActionCard>

          <ActionCard title="Email Intelligence" subtitle="Paste a client email thread and JARVIS extracts asks, objections, buying signals, and next step.">
            <form onSubmit={(event) => { event.preventDefault(); submit('/api/v1/captain/email-import', { email_thread: emailThread }) }}>
              <Textarea value={emailThread} onChange={setEmailThread} placeholder="Paste raw email thread here." />
              <RunButton loading={loading} disabled={!emailThread.trim()}>Extract intelligence</RunButton>
            </form>
          </ActionCard>

          <ActionCard title="Decision Pushback" subtitle="Ask JARVIS whether a planned decision should proceed, slow down, or require Captain approval.">
            <form onSubmit={(event) => { event.preventDefault(); submit('/api/v1/captain/evaluate-decision', { decision, context: {} }) }}>
              <Textarea value={decision} onChange={setDecision} placeholder="Example: send live outreach to 20 healthcare leads today." />
              <RunButton loading={loading} disabled={!decision.trim()}>Evaluate</RunButton>
            </form>
          </ActionCard>

          <ActionCard title="Onboard New Client" subtitle="Register a won deal as a live client. MRR posts immediately to the Revenue Dashboard.">
            <form onSubmit={submitClient} className="space-y-2">
              <Input value={clientForm.company_name} onChange={setClient('company_name')} placeholder="Company name *" />
              <div className="grid grid-cols-2 gap-2">
                <Input value={clientForm.contact_name} onChange={setClient('contact_name')} placeholder="Contact name" />
                <Input value={clientForm.email} onChange={setClient('email')} placeholder="Email" />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <select
                  value={clientForm.package_tier}
                  onChange={e => setClient('package_tier')(e.target.value)}
                  className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none focus:border-jarvis-cyan/60"
                >
                  {['starter', 'growth', 'enterprise', 'custom'].map(t => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
                <Input value={clientForm.mrr_usd} onChange={setClient('mrr_usd')} placeholder="Monthly MRR ($)" />
              </div>
              <RunButton loading={clientLoading} disabled={!clientForm.company_name.trim()}>Activate Client</RunButton>
            </form>
          </ActionCard>

          <ActionCard
            title="Seed Demo Data"
            subtitle="One-click: populate the Revenue Command Center with 8 clients, 25 pipeline leads, and 90 days of MRR history. Idempotent — safe to run again."
          >
            <div className="space-y-3">
              <p className="text-xs text-white/40">
                Creates realistic Aliyar Solutions demo data so the dashboard is live and impressive for any prospect call. Skips records that already exist.
              </p>
              <button
                type="button"
                disabled={loading}
                onClick={() => submit('/api/v1/captain/seed-demo', {})}
                className="w-full rounded border border-emerald-500/40 bg-emerald-500/10 px-4 py-2 text-sm font-semibold text-emerald-300 hover:bg-emerald-500/20 disabled:opacity-40 transition-colors"
              >
                {loading ? 'Seeding…' : 'Seed Demo Data →'}
              </button>
            </div>
          </ActionCard>

          <ActionCard title="Activate Pilot Mode" subtitle="Enable JARVIS autonomous pilot — activates self-directed outreach, lead scoring, and decision-making for this tenant.">
            <div className="space-y-3">
              <p className="text-xs text-white/40">
                Pilot mode lets JARVIS run full autonomous cycles: discover leads, send outreach, score pipeline, and escalate only when Captain approval is required.
              </p>
              <button
                type="button"
                disabled={loading}
                onClick={() => submit('/api/v1/pilot/activate', {})}
                className="w-full rounded border border-jarvis-cyan/40 bg-jarvis-cyan/10 px-4 py-2 text-sm font-semibold text-jarvis-cyan hover:bg-jarvis-cyan/20 disabled:opacity-40 transition-colors"
              >
                {loading ? 'Activating…' : 'Activate Pilot Mode →'}
              </button>
            </div>
          </ActionCard>

          <ActionCard title="Record Mirror Decision" subtitle="Log a Captain decision so JARVIS learns your thinking patterns and can predict future choices.">
            <form onSubmit={(e) => { e.preventDefault(); submit('/api/v1/captain/mirror/record', { decision: mirrorDecision.decision, context: mirrorDecision.context, outcome: mirrorDecision.outcome, confidence: parseInt(mirrorDecision.confidence) }) }} className="space-y-2">
              <Textarea value={mirrorDecision.decision} onChange={v => setMirrorDecision(p => ({ ...p, decision: v }))} placeholder="What decision did you make?" />
              <Textarea value={mirrorDecision.context} onChange={v => setMirrorDecision(p => ({ ...p, context: v }))} placeholder="What was the context or rationale?" />
              <Input value={mirrorDecision.outcome} onChange={v => setMirrorDecision(p => ({ ...p, outcome: v }))} placeholder="Outcome (e.g. won, declined, deferred)" />
              <RunButton loading={loading} disabled={!mirrorDecision.decision.trim()}>Record Decision</RunButton>
            </form>
          </ActionCard>

          <ActionCard title="Mirror: Predict Decision" subtitle="JARVIS uses your past decision patterns to predict what you would do in a new scenario.">
            <form onSubmit={(e) => { e.preventDefault(); submit('/api/v1/captain/mirror/predict', { scenario: mirrorPredictQ }) }} className="space-y-2">
              <Textarea value={mirrorPredictQ} onChange={setMirrorPredictQ} placeholder="Describe a scenario: e.g. a $5K/mo lead in healthcare who wants to start next week but hasn't signed." />
              <RunButton loading={loading} disabled={!mirrorPredictQ.trim()}>Predict Decision</RunButton>
            </form>
          </ActionCard>

          <ActionCard title="Create A/B Experiment" subtitle="Set up an outreach experiment to test two variants and track what converts better.">
            <form onSubmit={(e) => { e.preventDefault(); submit('/api/v1/experiments', { name: expForm.name, hypothesis: expForm.hypothesis, variants: [{ label: 'A', content: expForm.variant_a }, { label: 'B', content: expForm.variant_b }] }) }} className="space-y-2">
              <Input value={expForm.name} onChange={v => setExpForm(p => ({ ...p, name: v }))} placeholder="Experiment name (e.g. dental_pain_vs_roi_hook)" />
              <Input value={expForm.hypothesis} onChange={v => setExpForm(p => ({ ...p, hypothesis: v }))} placeholder="Hypothesis: Version B gets 2x reply rate because..." />
              <Textarea value={expForm.variant_a} onChange={v => setExpForm(p => ({ ...p, variant_a: v }))} placeholder="Variant A — current control message" />
              <Textarea value={expForm.variant_b} onChange={v => setExpForm(p => ({ ...p, variant_b: v }))} placeholder="Variant B — challenger message" />
              <RunButton loading={loading} disabled={!expForm.name.trim() || !expForm.variant_a.trim()}>Create Experiment</RunButton>
            </form>
          </ActionCard>

          <div className="xl:col-span-2">
            <ActionCard title="Latest result" subtitle="Output from the last Captain Bridge action.">
              <ResultBox result={result} />
            </ActionCard>
          </div>
        </div>
      )}
    </FrontierShell>
  )
}
