import React, { useState } from 'react'
import { Search } from 'lucide-react'
import api from '../../services/api'
import OperationalView from '../common/OperationalView'

export default function MemoryView() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])

  const recall = async () => {
    if (!query.trim()) return
    const response = await api.get('/api/v1/memory/recall', { params: { query, limit: 20 } })
    setResults(response.data || [])
  }

  return (
    <OperationalView
      eyebrow="Organizational Memory"
      title="Memory Browser"
      description="Working, operational, and strategic memory access for cross-agent context and long-term decisions."
      endpoints={[
        { key: 'context', label: 'Current memory context', path: '/api/v1/memory/context' },
        { key: 'instructions', label: 'Stored instructions', path: '/api/v1/memory/instructions' },
        { key: 'jarvis_stats', label: 'JARVIS memory stats', path: '/api/v1/jarvis/memory/stats' },
      ]}
    >
      <section className="glass p-5">
        <h2 className="text-sm font-semibold text-white">Recall memory</h2>
        <div className="mt-4 flex gap-3">
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search decisions, leads, clients, outcomes, or instructions"
            className="flex-1 rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none placeholder:text-gray-500 focus:border-jarvis-cyan/60"
          />
          <button onClick={recall} className="btn-primary inline-flex items-center gap-2">
            <Search size={15} /> Search
          </button>
        </div>
        {results.length > 0 && (
          <pre className="mt-4 max-h-64 overflow-auto rounded-lg border border-white/10 bg-black/20 p-3 text-xs text-gray-300">
            {JSON.stringify(results, null, 2)}
          </pre>
        )}
      </section>
    </OperationalView>
  )
}
