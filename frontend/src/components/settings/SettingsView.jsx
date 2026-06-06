import React from 'react'
import OperationalView from '../common/OperationalView'

export default function SettingsView() {
  return (
    <OperationalView
      eyebrow="Configuration"
      title="Tenant Settings"
      description="Tenant configuration, API-key status, provider readiness, and production settings. Secret values are never exposed in the browser."
      endpoints={[
        { key: 'ai_credentials', label: 'AI credential status', path: '/api/v1/ai-ops/credentials' },
        { key: 'ai_routing', label: 'AI routing table', path: '/api/v1/ai-ops/routing-table' },
        { key: 'email_status', label: 'Executive email status', path: '/api/v1/gmail/status' },
        { key: 'system_health', label: 'Emergency health', path: '/api/v1/emergency/health' },
      ]}
    />
  )
}
