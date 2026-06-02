import React, { useState } from 'react'
import { Search } from 'lucide-react'
import api from '../../services/api'
import OperationalView from '../common/OperationalView'

export default function DiscoveryView() {
  const [form, setForm] = useState({
    industry: 'AI automation',
    location: 'London',
    service_angle: 'workflow automation',
    limit: 10,
  })
  const [result, setResult] = useState(null)

  const discover = async () => {
    try {
      const response = await api.post('/api/v1/discovery/local-market', form)
      setResult(response.data)
    } catch (error) {
      setResult({ error: error.response?.data?.detail || error.message })
    }
  }

  return (
    <OperationalView
      eyebrow="Client Acquisition"
      title="Lead Discovery"
      description="Lead discovery controls, target industries, and daily discovery outputs before scoring and outreach."
      endpoints={[
        { key: 'industries', label: 'Target industries', path: '/api/v1/discovery/industries' },
        { key: 'today', label: 'Discovered leads today', path: '/api/v1/discover/leads/today' },
        { key: 'lead_stats', label: 'Lead stats', path: '/api/v1/leads/stats' },
      ]}
    >
      <section className="glass p-5">
        <h2 className="text-sm font-semibold text-white">Run local market discovery</h2>
        <div className="mt-4 grid grid-cols-1 md:grid-cols-4 gap-3">
          {Object.entries(form).map(([key, value]) => (
            <input
              key={key}
              value={value}
              onChange={(event) => setForm((current) => ({ ...current, [key]: event.target.value }))}
              placeholder={key}
              className="rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none placeholder:text-gray-500 focus:border-jarvis-cyan/60"
            />
          ))}
        </div>
        <button onClick={discover} className="btn-primary mt-4 inline-flex items-center gap-2">
          <Search size={15} /> Discover
        </button>
        {result && (
          <pre className="mt-4 max-h-64 overflow-auto rounded-lg border border-white/10 bg-black/20 p-3 text-xs text-gray-300">
            {JSON.stringify(result, null, 2)}
          </pre>
        )}
      </section>
    </OperationalView>
  )
}
