import React, { useState } from 'react'
import { FileText } from 'lucide-react'
import api from '../../services/api'
import OperationalView from '../common/OperationalView'

export default function ResearchView() {
  const [topic, setTopic] = useState('')
  const [result, setResult] = useState(null)

  const generate = async () => {
    if (!topic.trim()) return
    try {
      const response = await api.post('/api/v1/intelligence/reports/generate', {
        topic,
        category: 'market',
      })
      setResult(response.data)
      setTopic('')
    } catch (error) {
      setResult({ error: error.response?.data?.detail || error.message })
    }
  }

  return (
    <OperationalView
      eyebrow="Research"
      title="Research Reports"
      description="Generated research reports, technology radar context, and market evidence for proposals and strategic decisions."
      endpoints={[
        { key: 'reports', label: 'Recent reports', path: '/api/v1/intelligence/reports' },
        { key: 'radar', label: 'Tech radar viewer', path: '/api/v1/intelligence/radar' },
      ]}
    >
      <section className="glass p-5">
        <h2 className="text-sm font-semibold text-white">Generate research report</h2>
        <div className="mt-4 flex gap-3">
          <input
            value={topic}
            onChange={(event) => setTopic(event.target.value)}
            placeholder="Research topic"
            className="flex-1 rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none placeholder:text-gray-500 focus:border-jarvis-cyan/60"
          />
          <button onClick={generate} className="btn-primary inline-flex items-center gap-2">
            <FileText size={15} /> Generate
          </button>
        </div>
        {result && (
          <pre className="mt-4 max-h-64 overflow-auto rounded-lg border border-white/10 bg-black/20 p-3 text-xs text-gray-300">
            {JSON.stringify(result, null, 2)}
          </pre>
        )}
      </section>
    </OperationalView>
  )
}
