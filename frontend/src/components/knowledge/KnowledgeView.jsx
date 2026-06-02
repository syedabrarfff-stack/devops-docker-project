import React, { useState } from 'react'
import { Search } from 'lucide-react'
import api from '../../services/api'
import OperationalView from '../common/OperationalView'

export default function KnowledgeView() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState(null)

  const search = async () => {
    if (!query.trim()) return
    try {
      const response = await api.get('/api/v1/knowledge/search', { params: { q: query } })
      setResults(response.data)
    } catch (error) {
      setResults({ error: error.response?.data?.detail || error.message })
    }
  }

  return (
    <OperationalView
      eyebrow="Operating Knowledge"
      title="Knowledge Base"
      description="SOPs, operating lessons, reusable delivery patterns, and searchable Aliyar Solutions knowledge."
      endpoints={[
        { key: 'stats', label: 'Knowledge stats', path: '/api/v1/knowledge/stats' },
        { key: 'sops', label: 'SOP library', path: '/api/v1/knowledge/sops' },
        { key: 'learnings', label: 'Learnings', path: '/api/v1/knowledge/learnings' },
      ]}
    >
      <section className="glass p-5">
        <h2 className="text-sm font-semibold text-white">Search knowledge</h2>
        <div className="mt-4 flex gap-3">
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search SOPs, delivery lessons, client notes, or operating rules"
            className="flex-1 rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none placeholder:text-gray-500 focus:border-jarvis-cyan/60"
          />
          <button onClick={search} className="btn-primary inline-flex items-center gap-2">
            <Search size={15} /> Search
          </button>
        </div>
        {results && (
          <pre className="mt-4 max-h-64 overflow-auto rounded-lg border border-white/10 bg-black/20 p-3 text-xs text-gray-300">
            {JSON.stringify(results, null, 2)}
          </pre>
        )}
      </section>
    </OperationalView>
  )
}
