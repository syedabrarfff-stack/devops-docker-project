import React, { useMemo, useState } from 'react'
import api from '../../services/api'
import {
  ActionCard,
  DEFAULT_TENANT,
  FrontierShell,
  Input,
  ResultBox,
  RunButton,
} from './FrontierShell'

export default function WarRoom() {
  const [competitor, setCompetitor] = useState('Cognitiv+')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  const endpoints = useMemo(() => [
    { key: 'health', label: 'Emergency health', path: '/api/v1/emergency/health' },
    { key: 'incidents', label: 'Open incidents', path: '/api/v1/emergency/incidents' },
    { key: 'threats', label: 'Captain threats', path: '/api/v1/captain/threats', params: { tenant_id: DEFAULT_TENANT } },
    { key: 'warBrief', label: 'War-room brief', path: '/api/v1/captain/war-room-brief', params: { tenant_id: DEFAULT_TENANT } },
    { key: 'conscience', label: 'Conscience audit', path: '/api/v1/intelligence/conscience/audit', params: { tenant_id: DEFAULT_TENANT, days: 7 } },
    { key: 'approvals', label: 'Pending approvals', path: '/api/v1/approvals', params: { status: 'pending' } },
  ], [])

  async function runRedTeam(event) {
    event.preventDefault()
    setLoading(true)
    try {
      const response = competitor.trim()
        ? await api.post('/api/v1/intelligence/red-team/competitor', null, {
            params: { tenant_id: DEFAULT_TENANT, competitor_name: competitor },
          })
        : await api.post('/api/v1/intelligence/red-team/run', { tenant_id: DEFAULT_TENANT })
      setResult(response.data)
    } catch (error) {
      setResult({ error: error.response?.data?.detail || error.message })
    }
    setLoading(false)
  }

  return (
    <FrontierShell
      eyebrow="Protection"
      title="War Room"
      description="Incidents, threats, ethics checks, risk reviews, and red-team analysis for high-stakes decisions."
      endpoints={endpoints}
    >
      {() => (
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
          <ActionCard title="Run Red Team" subtitle="Analyze how a competitor or market force can attack our position.">
            <form onSubmit={runRedTeam} className="space-y-3">
              <Input value={competitor} onChange={setCompetitor} placeholder="Competitor name" />
              <RunButton loading={loading}>Analyze</RunButton>
            </form>
          </ActionCard>
          <ActionCard title="Latest red-team result" subtitle="Risk analysis returned by the intelligence layer.">
            <ResultBox result={result} />
          </ActionCard>
        </div>
      )}
    </FrontierShell>
  )
}
