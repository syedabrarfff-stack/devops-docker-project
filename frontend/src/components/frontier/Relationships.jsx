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

export default function Relationships() {
  const [leadId, setLeadId] = useState('')
  const [nodeType, setNodeType] = useState('lead')
  const [nodeId, setNodeId] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  const endpoints = useMemo(() => [
    { key: 'graph', label: 'Relationship graph', path: '/api/v1/crm/relationship-graph', params: { tenant_id: DEFAULT_TENANT } },
    { key: 'contacts', label: 'CRM contacts', path: '/api/v1/crm/contacts', params: { limit: 50 } },
    { key: 'companies', label: 'CRM companies', path: '/api/v1/crm/companies', params: { limit: 50 } },
    { key: 'deals', label: 'CRM deals', path: '/api/v1/crm/deals', params: { limit: 50 } },
    { key: 'clients', label: 'Client records', path: '/api/v1/clients', params: { tenant_id: DEFAULT_TENANT, limit: 50 } },
  ], [])

  async function findWarmIntros(event) {
    event.preventDefault()
    setLoading(true)
    try {
      const response = await api.get(`/api/v1/crm/relationship-graph/warm-intros/${leadId}`, {
        params: { tenant_id: DEFAULT_TENANT },
      })
      setResult(response.data)
    } catch (error) {
      setResult({ error: error.response?.data?.detail || error.message })
    }
    setLoading(false)
  }

  async function addNode(event) {
    event.preventDefault()
    setLoading(true)
    try {
      const response = await api.post('/api/v1/crm/relationship-graph/node', {
        tenant_id: DEFAULT_TENANT,
        entity_type: nodeType,
        entity_id: nodeId,
        attributes: { source: 'dashboard' },
      })
      setResult(response.data)
    } catch (error) {
      setResult({ error: error.response?.data?.detail || error.message })
    }
    setLoading(false)
  }

  return (
    <FrontierShell
      eyebrow="CRM Graph"
      title="Relationships"
      description="The graph view of leads, clients, companies, contacts, deals, and possible warm introduction paths."
      endpoints={endpoints}
    >
      {() => (
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
          <ActionCard title="Warm Intro Search" subtitle="Enter a lead id to see whether JARVIS can find a relationship path.">
            <form onSubmit={findWarmIntros} className="space-y-3">
              <Input value={leadId} onChange={setLeadId} placeholder="Lead UUID" />
              <RunButton loading={loading} disabled={!leadId.trim()}>Search</RunButton>
            </form>
          </ActionCard>
          <ActionCard title="Add Graph Node" subtitle="Add a simple relationship node for manual bridge-building.">
            <form onSubmit={addNode} className="space-y-3">
              <Input value={nodeType} onChange={setNodeType} placeholder="Entity type" />
              <Input value={nodeId} onChange={setNodeId} placeholder="Entity id" />
              <RunButton loading={loading} disabled={!nodeType.trim() || !nodeId.trim()}>Add node</RunButton>
            </form>
          </ActionCard>
          <ActionCard title="Latest graph result" subtitle="Warm intro or node creation output.">
            <ResultBox result={result} />
          </ActionCard>
        </div>
      )}
    </FrontierShell>
  )
}
