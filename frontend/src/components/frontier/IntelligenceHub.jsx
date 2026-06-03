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

export default function IntelligenceHub() {
  const [draft, setDraft] = useState('')
  const [learning, setLearning] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  const endpoints = useMemo(() => [
    { key: 'assessment', label: 'Self assessment', path: '/api/v1/intelligence/self-assessment', params: { tenant_id: DEFAULT_TENANT } },
    { key: 'flywheel', label: 'Flywheel score', path: '/api/v1/intelligence/flywheel', params: { tenant_id: DEFAULT_TENANT } },
    { key: 'projection', label: 'Flywheel projection', path: '/api/v1/intelligence/flywheel/projection', params: { tenant_id: DEFAULT_TENANT, months: 12 } },
    { key: 'health', label: 'Client health scoring', path: '/api/v1/intelligence/client-health', params: { tenant_id: DEFAULT_TENANT } },
    { key: 'competitors', label: 'Competitor intelligence', path: '/api/v1/intelligence/competitors', params: { tenant_id: DEFAULT_TENANT } },
    { key: 'learnings', label: 'Outreach learnings', path: '/api/v1/intelligence/outreach-learnings', params: { tenant_id: DEFAULT_TENANT, limit: 50 } },
    { key: 'innovation', label: 'Innovation queue', path: '/api/v1/innovation/queue', params: { tenant_id: DEFAULT_TENANT } },
    { key: 'milestones', label: 'Civilization milestones', path: '/api/v1/civilization/milestones', params: { tenant_id: DEFAULT_TENANT, limit: 50 } },
  ], [])

  async function enhanceDraft(event) {
    event.preventDefault()
    setLoading(true)
    try {
      const response = await api.post('/api/v1/intelligence/cialdini/enhance', {
        tenant_id: DEFAULT_TENANT,
        email_draft: draft,
      })
      setResult(response.data)
    } catch (error) {
      setResult({ error: error.response?.data?.detail || error.message })
    }
    setLoading(false)
  }

  async function teachJarvis(event) {
    event.preventDefault()
    setLoading(true)
    try {
      const response = await api.post('/api/v1/intelligence/teach', {
        tenant_id: DEFAULT_TENANT,
        title: 'Captain manual learning',
        learning,
        category: 'outreach_intelligence',
        score: 90,
      })
      setResult(response.data)
    } catch (error) {
      setResult({ error: error.response?.data?.detail || error.message })
    }
    setLoading(false)
  }

  return (
    <FrontierShell
      eyebrow="Intelligence"
      title="Intelligence Hub"
      description="Self-assessment, flywheel, client health, competitors, persuasion engineering, learnings, innovation, and company memory."
      endpoints={endpoints}
    >
      {() => (
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
          <ActionCard title="Enhance Outreach Draft" subtitle="Improves a draft using persuasion principles while keeping pricing gated.">
            <form onSubmit={enhanceDraft} className="space-y-3">
              <Textarea value={draft} onChange={setDraft} placeholder="Paste an outreach draft to improve." />
              <RunButton loading={loading} disabled={!draft.trim()}>Enhance</RunButton>
            </form>
          </ActionCard>
          <ActionCard title="Teach JARVIS" subtitle="Add a field learning from a call, email, objection, or client conversation.">
            <form onSubmit={teachJarvis} className="space-y-3">
              <Textarea value={learning} onChange={setLearning} placeholder="Example: prospects in dental clinics respond better to missed-call revenue framing." />
              <RunButton loading={loading} disabled={!learning.trim()}>Teach</RunButton>
            </form>
          </ActionCard>
          <ActionCard title="Latest intelligence result" subtitle="Output from the last enhancement or learning action.">
            <ResultBox result={result} />
          </ActionCard>
        </div>
      )}
    </FrontierShell>
  )
}
