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

export default function RevenueIntelligence() {
  const [serviceType, setServiceType] = useState('ai_automation')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  const endpoints = useMemo(() => [
    { key: 'snapshot', label: 'Revenue snapshot', path: '/api/v1/revenue/snapshot', params: { tenant_id: DEFAULT_TENANT } },
    { key: 'mrr', label: 'MRR chart', path: '/api/v1/revenue/mrr-chart', params: { tenant_id: DEFAULT_TENANT, days: 365 } },
    { key: 'pipeline', label: 'Pipeline stats', path: '/api/v1/crm/deals/pipeline' },
    { key: 'forecast', label: 'Monte Carlo forecast', path: '/api/v1/intelligence/revenue-forecast', method: 'post', body: { tenant_id: DEFAULT_TENANT, iterations: 500, horizon_days: 90 } },
    { key: 'pricing', label: 'Pricing catalog', path: '/api/v1/intelligence/pricing/catalog' },
    { key: 'economics', label: 'Economics dashboard', path: '/api/v1/economics/dashboard', params: { tenant_id: DEFAULT_TENANT } },
  ], [])

  async function calculatePricing(event) {
    event.preventDefault()
    setLoading(true)
    try {
      const response = await api.post('/api/v1/intelligence/dynamic-pricing', {
        tenant_id: DEFAULT_TENANT,
        service_type: serviceType,
        context: { source: 'revenue_intelligence_room' },
      })
      setResult(response.data)
    } catch (error) {
      setResult({ error: error.response?.data?.detail || error.message })
    }
    setLoading(false)
  }

  return (
    <FrontierShell
      eyebrow="Revenue"
      title="Revenue Intelligence"
      description="Forecasts, pricing logic, economics, pipeline value, and profitability signals for the first-client mission."
      endpoints={endpoints}
    >
      {() => (
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
          <ActionCard title="Dynamic Pricing Check" subtitle="Use this after a prospect is serious. Pricing is not shown in first outreach or early follow-up emails.">
            <form onSubmit={calculatePricing} className="space-y-3">
              <Input value={serviceType} onChange={setServiceType} placeholder="Service type, for example ai_automation" />
              <RunButton loading={loading} disabled={!serviceType.trim()}>Calculate</RunButton>
            </form>
          </ActionCard>
          <ActionCard title="Latest pricing result" subtitle="Revenue result from the pricing engine.">
            <ResultBox result={result} />
          </ActionCard>
        </div>
      )}
    </FrontierShell>
  )
}
