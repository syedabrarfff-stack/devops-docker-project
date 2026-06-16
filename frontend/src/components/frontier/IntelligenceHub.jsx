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
  const [innovationTitle, setInnovationTitle] = useState('')
  const [innovationDesc, setInnovationDesc] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  const endpoints = useMemo(() => [
    { key: 'assessment', label: 'Self assessment', path: '/api/v1/intelligence/self-assessment', params: { tenant_id: DEFAULT_TENANT } },
    { key: 'recommendations', label: 'System recommendations', path: '/api/v1/intelligence/recommendations', params: { tenant_id: DEFAULT_TENANT } },
    { key: 'pulse', label: 'Intelligence pulse', path: '/api/v1/intelligence/pulse', params: { tenant_id: DEFAULT_TENANT } },
    { key: 'radar', label: 'Tech radar', path: '/api/v1/intelligence/radar', params: { tenant_id: DEFAULT_TENANT } },
    { key: 'reports', label: 'Intelligence reports', path: '/api/v1/intelligence/reports', params: { tenant_id: DEFAULT_TENANT } },
    { key: 'flywheel', label: 'Flywheel score', path: '/api/v1/intelligence/flywheel', params: { tenant_id: DEFAULT_TENANT } },
    { key: 'projection', label: 'Flywheel projection', path: '/api/v1/intelligence/flywheel/projection', params: { tenant_id: DEFAULT_TENANT, months: 12 } },
    { key: 'health', label: 'Client health scoring', path: '/api/v1/intelligence/client-health', params: { tenant_id: DEFAULT_TENANT } },
    { key: 'competitors', label: 'Competitor intelligence', path: '/api/v1/intelligence/competitors', params: { tenant_id: DEFAULT_TENANT } },
    { key: 'learnings', label: 'Outreach learnings', path: '/api/v1/intelligence/outreach-learnings', params: { tenant_id: DEFAULT_TENANT, limit: 50 } },
    { key: 'govSummary', label: 'Governance summary', path: '/api/v1/intelligence/governance/summary', params: { tenant_id: DEFAULT_TENANT } },
    { key: 'innovation', label: 'Innovation queue', path: '/api/v1/innovation/queue', params: { tenant_id: DEFAULT_TENANT } },
    { key: 'milestones', label: 'Civilization milestones', path: '/api/v1/civilization/milestones', params: { tenant_id: DEFAULT_TENANT, limit: 50 } },
    { key: 'economics', label: 'Economics dashboard', path: '/api/v1/economics/dashboard', params: { tenant_id: DEFAULT_TENANT } },
    { key: 'marketPulse', label: 'Market pulse', path: '/api/v1/intel/market-pulse', params: { tenant_id: DEFAULT_TENANT } },
    { key: 'cascadeEvents', label: 'Cascade events', path: '/api/v1/intelligence/cascade/events' },
    { key: 'brainArtifacts', label: 'Brain artifacts', path: '/api/v1/brain/artifacts' },
    { key: 'brainRecall', label: 'Brain recall (top 20)', path: '/api/v1/brain/recall', params: { limit: 20 } },
    { key: 'brainWhatWorked', label: 'Brain — what worked', path: '/api/v1/brain/what-worked' },
    { key: 'agentsProposals', label: 'Agent proposals', path: '/api/v1/agents/proposals', params: { tenant_id: DEFAULT_TENANT } },
    { key: 'agentsCapacity', label: 'Agent capacity', path: '/api/v1/agents/capacity' },
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

  async function proposeInnovation(event) {
    event.preventDefault()
    setLoading(true)
    try {
      const response = await api.post('/api/v1/innovation/propose', {
        tenant_id: DEFAULT_TENANT,
        title: innovationTitle,
        description: innovationDesc,
        impact_score: 80,
        feasibility_score: 75,
        proposed_by: 'CAPTAIN',
      })
      setResult(response.data)
      setInnovationTitle('')
      setInnovationDesc('')
    } catch (error) {
      setResult({ error: error.response?.data?.detail || error.message })
    }
    setLoading(false)
  }

  return (
    <FrontierShell
      eyebrow="Intelligence"
      title="Intelligence Hub"
      description="Self-assessment, flywheel, client health, competitors, persuasion engineering, learnings, innovation, recommendations, pulse, and radar."
      endpoints={endpoints}
    >
      {() => (
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            <ActionCard title="Run Radar Scan" subtitle="Actively scan technology trends and classify emerging tools for Aliyar Solutions.">
              <RunButton
                loading={loading}
                onClick={async (e) => {
                  e.preventDefault(); setLoading(true)
                  try {
                    const r = await api.post('/api/v1/intelligence/radar/scan', { tenant_id: DEFAULT_TENANT })
                    setResult(r.data)
                  } catch (err) { setResult({ error: err.response?.data?.detail || err.message }) }
                  setLoading(false)
                }}
              >
                Run Radar Scan
              </RunButton>
            </ActionCard>
            <ActionCard title="Generate Intelligence Report" subtitle="AI-generated market intelligence report for the current pipeline.">
              <RunButton
                loading={loading}
                onClick={async (e) => {
                  e.preventDefault(); setLoading(true)
                  try {
                    const r = await api.post('/api/v1/intelligence/reports/generate', { tenant_id: DEFAULT_TENANT })
                    setResult(r.data)
                  } catch (err) { setResult({ error: err.response?.data?.detail || err.message }) }
                  setLoading(false)
                }}
              >
                Generate Report
              </RunButton>
            </ActionCard>
          </div>
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
            <ActionCard title="Propose Innovation" subtitle="Add a new improvement idea to the JARVIS innovation queue for evaluation.">
              <form onSubmit={proposeInnovation} className="space-y-3">
                <Textarea value={innovationTitle} onChange={setInnovationTitle} placeholder="Innovation title (e.g. 'Auto-tag leads by industry on import')" />
                <Textarea value={innovationDesc} onChange={setInnovationDesc} placeholder="Describe the improvement and expected impact." />
                <RunButton loading={loading} disabled={!innovationTitle.trim() || !innovationDesc.trim()}>Propose</RunButton>
              </form>
            </ActionCard>
          </div>
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
            <ActionCard title="Seed Innovation Queue" subtitle="Populate the innovation queue with starter improvement ideas for JARVIS.">
              <RunButton
                loading={loading}
                onClick={async (e) => {
                  e.preventDefault(); setLoading(true)
                  try {
                    const r = await api.post('/api/v1/innovation/seed', { tenant_id: DEFAULT_TENANT })
                    setResult(r.data)
                  } catch (err) { setResult({ error: err.response?.data?.detail || err.message }) }
                  setLoading(false)
                }}
              >
                Seed Queue
              </RunButton>
            </ActionCard>
            <ActionCard title="Weekly Innovation Review" subtitle="Run the AI-driven weekly review of queued innovation items.">
              <RunButton
                loading={loading}
                onClick={async (e) => {
                  e.preventDefault(); setLoading(true)
                  try {
                    const r = await api.post('/api/v1/innovation/weekly-review', { tenant_id: DEFAULT_TENANT })
                    setResult(r.data)
                  } catch (err) { setResult({ error: err.response?.data?.detail || err.message }) }
                  setLoading(false)
                }}
              >
                Run Weekly Review
              </RunButton>
            </ActionCard>
            <ActionCard title="Mark Innovation Deployed" subtitle="Record that a queued innovation item has been shipped to production.">
              <form onSubmit={async (e) => {
                e.preventDefault()
                const itemId = e.target.querySelector('input').value.trim()
                if (!itemId) return
                setLoading(true)
                try {
                  const r = await api.post(`/api/v1/innovation/${itemId}/deployed`, { tenant_id: DEFAULT_TENANT })
                  setResult(r.data)
                } catch (err) { setResult({ error: err.response?.data?.detail || err.message }) }
                setLoading(false)
              }} className="space-y-3">
                <input name="item_id" placeholder="Innovation item ID (UUID)"
                  className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none placeholder:text-white/30 focus:border-jarvis-cyan/60 transition-colors" />
                <RunButton loading={loading}>Mark Deployed</RunButton>
              </form>
            </ActionCard>
          </div>
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
            <ActionCard title="Trigger Intelligence Cascade" subtitle="Fire a cross-system intelligence synchronization cascade event.">
              <RunButton
                loading={loading}
                onClick={async (e) => {
                  e.preventDefault(); setLoading(true)
                  try {
                    const r = await api.post('/api/v1/intelligence/cascade/trigger', { tenant_id: DEFAULT_TENANT })
                    setResult(r.data)
                  } catch (err) { setResult({ error: err.response?.data?.detail || err.message }) }
                  setLoading(false)
                }}
              >
                Trigger Cascade
              </RunButton>
            </ActionCard>

            <ActionCard title="Store Brain Artifact" subtitle="Add a strategic insight or learning artifact to JARVIS long-term brain.">
              <form onSubmit={async (e) => {
                e.preventDefault()
                const content = e.target.querySelector('textarea').value.trim()
                if (!content) return
                setLoading(true)
                try {
                  const r = await api.post('/api/v1/brain/artifacts', { content, tenant_id: DEFAULT_TENANT })
                  setResult(r.data)
                  e.target.reset()
                } catch (err) { setResult({ error: err.response?.data?.detail || err.message }) }
                setLoading(false)
              }} className="space-y-3">
                <textarea placeholder="Strategic insight or learning to store in JARVIS brain…"
                  className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none placeholder:text-white/30 focus:border-jarvis-cyan/60 h-24 resize-none transition-colors" />
                <RunButton loading={loading}>Store Artifact</RunButton>
              </form>
            </ActionCard>

            <ActionCard title="Approve Agent Proposal" subtitle="Approve a proposal that an AI agent has escalated for Captain review.">
              <form onSubmit={async (e) => {
                e.preventDefault()
                const proposalId = e.target.querySelector('input').value.trim()
                if (!proposalId) return
                setLoading(true)
                try {
                  const r = await api.post(`/api/v1/agents/proposals/${proposalId}/approve`, { tenant_id: DEFAULT_TENANT })
                  setResult(r.data)
                } catch (err) { setResult({ error: err.response?.data?.detail || err.message }) }
                setLoading(false)
              }} className="space-y-3">
                <input placeholder="Proposal ID (UUID)"
                  className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none placeholder:text-white/30 focus:border-jarvis-cyan/60 transition-colors" />
                <RunButton loading={loading}>Approve Proposal</RunButton>
              </form>
            </ActionCard>
          </div>

          <ActionCard title="Latest intelligence result" subtitle="Output from the last action.">
            <ResultBox result={result} />
          </ActionCard>
        </div>
      )}
    </FrontierShell>
  )
}
