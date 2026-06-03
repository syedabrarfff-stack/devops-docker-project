import React, { useMemo } from 'react'
import { DEFAULT_TENANT, FrontierShell } from './FrontierShell'

export default function SystemHUD() {
  const endpoints = useMemo(() => [
    { key: 'rootHealth', label: 'Root health', path: '/health' },
    { key: 'apiHealth', label: 'API health', path: '/api/v1/health' },
    { key: 'readiness', label: 'Readiness', path: '/readyz' },
    { key: 'aiHealth', label: 'AI provider health', path: '/api/v1/ai-ops/health' },
    { key: 'costToday', label: 'AI cost today', path: '/api/v1/ai-ops/cost/today' },
    { key: 'scheduler', label: 'Scheduler jobs', path: '/api/v1/scheduler/jobs' },
    { key: 'gmail', label: 'Gmail status', path: '/api/v1/gmail/status' },
    { key: 'voice', label: 'Voice providers', path: '/api/v1/voice/providers' },
    { key: 'ledger', label: 'Civilization ledger', path: '/api/v1/civilization/ledger', params: { tenant_id: DEFAULT_TENANT, limit: 25 } },
  ], [])

  return (
    <FrontierShell
      eyebrow="Runtime"
      title="System HUD"
      description="Machine truth for the JARVIS stack: health, readiness, scheduler, AI routing, Gmail, voice, and immutable operating ledger."
      endpoints={endpoints}
    />
  )
}
