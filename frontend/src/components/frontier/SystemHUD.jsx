import React, { useMemo, useState } from 'react'
import api from '../../services/api'
import {
  ActionCard,
  DEFAULT_TENANT,
  FrontierShell,
  ResultBox,
  RunButton,
} from './FrontierShell'

export default function SystemHUD() {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

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
    { key: 'connHubOutputs', label: 'Connector hub outputs', path: '/api/v1/connector-hub/outputs', params: { tenant_id: DEFAULT_TENANT } },
    { key: 'connHubBridge',  label: 'Connector bridge health', path: '/api/v1/connector-hub/bridge-health' },
    { key: 'systemHud',      label: 'AIONX system HUD',      path: '/api/v1/system/hud' },
    { key: 'frontier',       label: 'Frontier intelligence', path: '/api/v1/frontier/status' },
    { key: 'consciousness',  label: 'Consciousness snapshot', path: '/api/v1/consciousness/snapshot' },
    { key: 'catalogStats',   label: 'Service catalog',       path: '/api/v1/catalog/stats' },
    { key: 'syncTelegramInfo', label: 'Telegram webhook info', path: '/api/v1/sync/telegram/webhook/info' },
    { key: 'aiPulse',         label: 'AI ops pulse',          path: '/api/v1/ai-ops/pulse' },
    { key: 'aiRouting',       label: 'AI routing table',      path: '/api/v1/ai-ops/routing-table' },
    { key: 'aiGovernance',    label: 'AI governance',         path: '/api/v1/ai-ops/governance' },
    { key: 'aiTestBedrock',   label: 'Test Bedrock',          path: '/api/v1/ai-ops/test-bedrock' },
  ], [])

  async function run(label, fn) {
    setLoading(true)
    try {
      const r = await fn()
      setResult({ label, ...r.data })
    } catch (err) {
      setResult({ label, error: err.response?.data?.detail || err.message })
    }
    setLoading(false)
  }

  return (
    <FrontierShell
      eyebrow="Mission Control"
      title="System HUD"
      description="Full-stack machine truth for JARVIS: health, readiness, AI routing, email transport, WhatsApp, civilization ledger, team, leads, connectors, and consciousness layers — all in one view."
      endpoints={endpoints}
    >
      {() => (
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            <ActionCard title="Connector Hub — Ingest" subtitle="Trigger daily connector ingestion: pull data from all active connectors into JARVIS memory.">
              <RunButton
                loading={loading}
                onClick={() => run('Ingest', () => api.post('/api/v1/connector-hub/ingest', { tenant_id: DEFAULT_TENANT }))}
              >
                Run Ingest
              </RunButton>
            </ActionCard>

            <ActionCard title="Connector Hub — Market Intelligence" subtitle="Generate market intelligence from the latest ingested connector data.">
              <RunButton
                loading={loading}
                onClick={() => run('Market Intelligence', () => api.post('/api/v1/connector-hub/intelligence', { tenant_id: DEFAULT_TENANT }))}
              >
                Generate Intelligence
              </RunButton>
            </ActionCard>

            <ActionCard title="Connector Hub — Council Review" subtitle="Send latest connector outputs to the AI Council for quality gate and approval.">
              <RunButton
                loading={loading}
                onClick={() => run('Council Review', () => api.post('/api/v1/connector-hub/council-review', { tenant_id: DEFAULT_TENANT }))}
              >
                Run Council Review
              </RunButton>
            </ActionCard>

            <ActionCard title="Register Telegram Webhook" subtitle="Register the JARVIS Telegram bot webhook with the Telegram API (run once after deploy).">
              <RunButton
                loading={loading}
                onClick={() => run('Telegram Webhook', () => api.post('/api/v1/sync/telegram/webhook/register', {}))}
              >
                Register Webhook
              </RunButton>
            </ActionCard>

            <ActionCard title="Initialize Civilization Ledger" subtitle="Bootstrap the JARVIS civilization ledger for this tenant. Run once during initial setup.">
              <RunButton
                loading={loading}
                onClick={() => run('Civilization Init', () => api.post('/api/v1/civilization/initialize', {}))}
              >
                Initialize Ledger
              </RunButton>
            </ActionCard>

            <ActionCard title="Self-Heal Now" subtitle="Run the JARVIS autonomous self-healing cycle immediately: reset open circuit breakers, refill lead pipeline, resurrect missing scheduler jobs, verify Redis.">
              <RunButton
                loading={loading}
                onClick={() => run('Self-Heal', () => api.post('/api/v1/system/self-heal'))}
              >
                Run Self-Heal
              </RunButton>
            </ActionCard>

            <ActionCard title="Reset AI Provider" subtitle="Reset circuit breaker for a specific AI provider (claude, gpt-4o, gemini, etc.) after a failure.">
              <div className="space-y-2">
                <select
                  id="providerSelect"
                  className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white outline-none focus:border-jarvis-cyan/60"
                  defaultValue="claude"
                >
                  {['claude', 'gpt-4o', 'gemini-pro', 'deepseek', 'groq', 'mistral'].map(p => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </select>
                <RunButton
                  loading={loading}
                  onClick={() => {
                    const provider = document.getElementById('providerSelect').value
                    run(`Reset ${provider}`, () => api.post(`/api/v1/ai-ops/health/${provider}/reset`))
                  }}
                >
                  Reset Provider
                </RunButton>
              </div>
            </ActionCard>
          </div>

          <ActionCard title="Latest action result" subtitle="Output from the last HUD operation.">
            <ResultBox result={result} />
          </ActionCard>
        </div>
      )}
    </FrontierShell>
  )
}
