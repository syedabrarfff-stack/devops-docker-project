import React, { useMemo } from 'react'
import { DEFAULT_TENANT, FrontierShell } from './FrontierShell'

export default function SystemHUD() {
  const endpoints = useMemo(() => [
    { key: 'rootHealth',     label: 'Root health',           path: '/health' },
    { key: 'apiHealth',      label: 'API health',            path: '/api/v1/health' },
    { key: 'readiness',      label: 'Deep readiness probe',  path: '/readyz' },
    { key: 'aiHealth',       label: 'AI provider health',    path: '/api/v1/ai-ops/health' },
    { key: 'costToday',      label: 'AI cost today',         path: '/api/v1/ai-ops/cost/today' },
    { key: 'costWeek',       label: 'AI cost this week',     path: '/api/v1/ai-ops/cost/week' },
    { key: 'scheduler',      label: 'Scheduler jobs',        path: '/api/v1/scheduler/jobs' },
    { key: 'email',          label: 'Email transport status', path: '/api/v1/gmail/status' },
    { key: 'commStatus',     label: 'Communication status',  path: '/api/v1/communication/status' },
    { key: 'voice',          label: 'Voice providers',       path: '/api/v1/voice/providers' },
    { key: 'ledger',         label: 'Civilization ledger',   path: '/api/v1/civilization/ledger', params: { tenant_id: DEFAULT_TENANT, limit: 10 } },
    { key: 'teamRegistry',   label: 'Team registry',         path: '/api/v1/team/members' },
    { key: 'leadStats',      label: 'Lead pipeline stats',   path: '/api/v1/leads/stats' },
    { key: 'connHub',        label: 'Connector hub status',  path: '/api/v1/connector-hub/status' },
    { key: 'systemHud',      label: 'AIONX system HUD',      path: '/api/v1/system/hud' },
    { key: 'frontier',       label: 'Frontier intelligence', path: '/api/v1/frontier/status' },
    { key: 'consciousness',  label: 'Consciousness snapshot', path: '/api/v1/consciousness/snapshot' },
    { key: 'catalogStats',   label: 'Service catalog',       path: '/api/v1/catalog/stats' },
  ], [])

  return (
    <FrontierShell
      eyebrow="Mission Control"
      title="System HUD"
      description="Full-stack machine truth for JARVIS: health, readiness, AI routing, email transport, WhatsApp, civilization ledger, team, leads, connectors, and consciousness layers — all in one view."
      endpoints={endpoints}
    />
  )
}
