import React, { useMemo, useState } from 'react'
import api from '../../services/api'
import {
  ActionCard,
  DEFAULT_TENANT,
  FrontierShell,
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

  const endpoints = useMemo(() => [
    { key: 'situation', label: 'Situation report', path: '/api/v1/captain/situation', params: { tenant_id: DEFAULT_TENANT } },
    { key: 'threats', label: 'Threat scan', path: '/api/v1/captain/threats', params: { tenant_id: DEFAULT_TENANT } },
    { key: 'actions', label: 'Predicted next actions', path: '/api/v1/captain/predict-actions', params: { tenant_id: DEFAULT_TENANT } },
    { key: 'state', label: 'Captain state', path: '/api/v1/captain/state', params: { tenant_id: DEFAULT_TENANT } },
    { key: 'decisionLoad', label: 'Decision load', path: '/api/v1/captain/decision-load', params: { tenant_id: DEFAULT_TENANT } },
    { key: 'warRoom', label: 'War-room brief', path: '/api/v1/captain/war-room-brief', params: { tenant_id: DEFAULT_TENANT } },
  ], [])

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
