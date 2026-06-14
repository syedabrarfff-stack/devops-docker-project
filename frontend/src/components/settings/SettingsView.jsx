import React, { useState, useEffect } from 'react'
import api from '../../services/api'

const TABS = ['governance', 'outreach', 'payments', 'integrations', 'ai']

const TAB_LABELS = {
  governance: 'Governance & Approvals',
  outreach: 'Outreach Operations',
  payments: 'Payment Methods',
  integrations: 'Integrations',
  ai: 'AI Providers'
}

function GovernanceTab() {
  const [settings, setSettings] = useState({
    auto_approve_proposal: 5000,
    auto_approve_invoice: 5000,
    auto_send_outreach: true,
  })
  const [saving, setSaving] = useState(false)

  const handleChange = (key, value) => {
    setSettings(s => ({ ...s, [key]: value }))
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await api.post('/api/v1/governance/settings', settings)
      alert('✓ Governance settings saved')
    } catch (e) {
      alert('Failed: ' + (e.response?.data?.detail || e.message))
    }
    setSaving(false)
  }

  return (
    <div className="space-y-5">
      <div className="glass rounded-xl p-5 border border-white/10">
        <h3 className="text-sm font-semibold text-white mb-4">Auto-Approval Thresholds</h3>
        <div className="space-y-3">
          <div>
            <label className="text-xs text-gray-400 block mb-1">Proposal auto-approve if ≤ $</label>
            <input
              type="number"
              value={settings.auto_approve_proposal}
              onChange={e => handleChange('auto_approve_proposal', parseFloat(e.target.value))}
              className="w-full bg-white/5 border border-white/10 rounded px-3 py-2 text-white"
            />
          </div>
          <div>
            <label className="text-xs text-gray-400 block mb-1">Invoice auto-approve if ≤ $</label>
            <input
              type="number"
              value={settings.auto_approve_invoice}
              onChange={e => handleChange('auto_approve_invoice', parseFloat(e.target.value))}
              className="w-full bg-white/5 border border-white/10 rounded px-3 py-2 text-white"
            />
          </div>
          <div className="flex items-center justify-between p-3 bg-white/5 rounded border border-white/10">
            <label className="text-xs text-gray-300">Auto-send outreach to warm leads</label>
            <input
              type="checkbox"
              checked={settings.auto_send_outreach}
              onChange={e => handleChange('auto_send_outreach', e.target.checked)}
              className="w-4 h-4"
            />
          </div>
        </div>
        <button
          onClick={handleSave}
          disabled={saving}
          className="mt-4 w-full px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded font-medium text-sm">
          {saving ? 'Saving...' : 'Save Governance Settings'}
        </button>
      </div>
    </div>
  )
}

function OutreachTab() {
  const [outreach, setOutreach] = useState({
    daily_send_cap: 48,
    domain_age_days: 365,
    outreach_paused: false,
    personalize_on_send: true,
  })
  const [saving, setSaving] = useState(false)

  const handleChange = (key, value) => {
    setOutreach(s => ({ ...s, [key]: value }))
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await api.post('/api/v1/governance/outreach-settings', outreach)
      alert('✓ Outreach settings saved')
    } catch (e) {
      alert('Failed: ' + (e.response?.data?.detail || e.message))
    }
    setSaving(false)
  }

  return (
    <div className="space-y-5">
      <div className="glass rounded-xl p-5 border border-white/10">
        <h3 className="text-sm font-semibold text-white mb-4">Outreach Operations</h3>
        <div className="space-y-3">
          <div>
            <label className="text-xs text-gray-400 block mb-1">Daily send cap (emails)</label>
            <input
              type="number"
              value={outreach.daily_send_cap}
              onChange={e => handleChange('daily_send_cap', parseInt(e.target.value))}
              className="w-full bg-white/5 border border-white/10 rounded px-3 py-2 text-white"
            />
          </div>
          <div>
            <label className="text-xs text-gray-400 block mb-1">Min domain age (days)</label>
            <input
              type="number"
              value={outreach.domain_age_days}
              onChange={e => handleChange('domain_age_days', parseInt(e.target.value))}
              className="w-full bg-white/5 border border-white/10 rounded px-3 py-2 text-white"
            />
          </div>
          <div className="flex items-center justify-between p-3 bg-white/5 rounded border border-white/10">
            <label className="text-xs text-gray-300">Personalize on send</label>
            <input
              type="checkbox"
              checked={outreach.personalize_on_send}
              onChange={e => handleChange('personalize_on_send', e.target.checked)}
              className="w-4 h-4"
            />
          </div>
          <div className="flex items-center justify-between p-3 bg-red-500/10 rounded border border-red-500/20">
            <label className="text-xs text-red-300 font-semibold">⚠ Pause all outreach</label>
            <input
              type="checkbox"
              checked={outreach.outreach_paused}
              onChange={e => handleChange('outreach_paused', e.target.checked)}
              className="w-4 h-4"
            />
          </div>
        </div>
        <button
          onClick={handleSave}
          disabled={saving}
          className="mt-4 w-full px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded font-medium text-sm">
          {saving ? 'Saving...' : 'Save Outreach Settings'}
        </button>
      </div>
    </div>
  )
}

function PaymentsTab() {
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    load()
  }, [])

  async function load() {
    try {
      const data = await api.get('/api/v1/governance/payment-methods').then(r => r.data)
      setStatus(data)
    } catch (e) {
      console.error(e)
    }
    setLoading(false)
  }

  if (loading) return <div className="text-gray-500 text-sm p-4">Loading...</div>

  return (
    <div className="space-y-4">
      {['stripe', 'bank_transfer', 'wise', 'paypal'].map(method => {
        const configured = status?.[method]?.configured
        const label = {
          stripe: '💳 Stripe',
          bank_transfer: '🏦 Bank Transfer',
          wise: '💱 Wise',
          paypal: '🅿️ PayPal'
        }[method]

        return (
          <div key={method} className="glass rounded-xl p-4 border border-white/10">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-white">{label}</p>
                <p className="text-xs text-gray-500 mt-1">
                  {configured ? '✓ Configured & active' : '○ Not configured'}
                </p>
              </div>
              <div className={`w-3 h-3 rounded-full ${configured ? 'bg-green-500' : 'bg-gray-600'}`} />
            </div>
          </div>
        )
      })}
      <p className="text-xs text-gray-500 mt-4">Payment method configuration requires environment variables. Update .env and restart.</p>
    </div>
  )
}

function IntegrationsTab() {
  const [integrations, setIntegrations] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    load()
  }, [])

  async function load() {
    try {
      const data = await api.get('/api/v1/ai-ops/credentials').then(r => r.data)
      setIntegrations(data)
    } catch (e) {
      console.error(e)
    }
    setLoading(false)
  }

  if (loading) return <div className="text-gray-500 text-sm p-4">Loading...</div>

  const services = [
    { name: 'Slack', key: 'slack_webhook_url' },
    { name: 'AWS SES', key: 'ses_from_email' },
    { name: 'Apollo.io', key: 'apollo_api_key' },
    { name: 'Google Maps', key: 'google_maps_api_key' },
    { name: 'Notion', key: 'notion_api_key' },
  ]

  return (
    <div className="space-y-3">
      {services.map(svc => {
        const configured = integrations?.[svc.key]
        return (
          <div key={svc.name} className="glass rounded-xl p-4 border border-white/10 flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-white">{svc.name}</p>
              <p className="text-xs text-gray-500">
                {configured ? '✓ API key set' : '○ Requires configuration'}
              </p>
            </div>
            <div className={`w-3 h-3 rounded-full ${configured ? 'bg-green-500' : 'bg-yellow-600'}`} />
          </div>
        )
      })}
      <p className="text-xs text-gray-500 mt-4">Set API keys in .env file. Secrets are never stored in the browser.</p>
    </div>
  )
}

function AITab() {
  const [providers, setProviders] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    load()
  }, [])

  async function load() {
    try {
      const data = await api.get('/api/v1/ai-ops/provider-health').then(r => r.data)
      setProviders(data)
    } catch (e) {
      console.error(e)
    }
    setLoading(false)
  }

  if (loading) return <div className="text-gray-500 text-sm p-4">Loading...</div>

  const providerList = [
    { name: 'Claude (Anthropic)', id: 'claude' },
    { name: 'GPT-4 (OpenAI)', id: 'openai' },
    { name: 'Gemini (Google)', id: 'gemini' },
    { name: 'DeepSeek', id: 'deepseek' },
    { name: 'Groq', id: 'groq' },
  ]

  return (
    <div className="space-y-3">
      {providerList.map(p => {
        const health = providers?.[p.id]
        const status = health?.status
        const color = status === 'healthy' ? 'green' : status === 'error' ? 'red' : 'yellow'

        return (
          <div key={p.id} className={`glass rounded-xl p-4 border border-${color}-500/20 flex items-center justify-between`}>
            <div>
              <p className="text-sm font-medium text-white">{p.name}</p>
              <p className={`text-xs mt-1 ${status === 'healthy' ? 'text-green-400' : status === 'error' ? 'text-red-400' : 'text-yellow-400'}`}>
                {status === 'healthy' ? '✓ Operational' : status === 'error' ? '✗ Unavailable' : '⚠ Degraded'}
              </p>
            </div>
            <div className={`w-3 h-3 rounded-full bg-${color}-500`} />
          </div>
        )
      })}
    </div>
  )
}

export default function SettingsView() {
  const [activeTab, setActiveTab] = useState('governance')

  return (
    <div className="min-h-screen bg-black text-white p-6">
      <div className="max-w-2xl mx-auto">
        <div className="mb-8">
          <p className="text-xs text-gray-500 uppercase tracking-wider">System</p>
          <h1 className="text-3xl font-black mt-2">Settings & Configuration</h1>
          <p className="text-sm text-gray-400 mt-2">Control JARVIS operations, integrations, and autonomous behavior.</p>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 border-b border-white/10 overflow-x-auto pb-4">
          {TABS.map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 text-sm font-medium rounded transition-colors whitespace-nowrap ${
                activeTab === tab
                  ? 'bg-blue-600 text-white'
                  : 'bg-white/5 hover:bg-white/10 text-gray-400'
              }`}
            >
              {TAB_LABELS[tab]}
            </button>
          ))}
        </div>

        {/* Content */}
        <div>
          {activeTab === 'governance' && <GovernanceTab />}
          {activeTab === 'outreach' && <OutreachTab />}
          {activeTab === 'payments' && <PaymentsTab />}
          {activeTab === 'integrations' && <IntegrationsTab />}
          {activeTab === 'ai' && <AITab />}
        </div>
      </div>
    </div>
  )
}
