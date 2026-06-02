import React, { useState } from 'react'
import { Loader2, Send } from 'lucide-react'
import api from '../../services/api'
import OperationalView from '../common/OperationalView'

export default function CouncilView() {
  const [question, setQuestion] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  const convene = async () => {
    if (!question.trim()) return
    setLoading(true)
    try {
      const response = await api.post('/api/v1/council/convene', {
        question,
        context: {},
        council_type: 'standard',
      })
      setResult(response.data)
      setQuestion('')
    } catch (error) {
      setResult({ error: error.response?.data?.detail || error.message })
    }
    setLoading(false)
  }

  return (
    <OperationalView
      eyebrow="Decision Intelligence"
      title="Council Sessions"
      description="Session history, model health, and new strategy questions routed through the weighted council."
      endpoints={[
        { key: 'health', label: 'Council health', path: '/api/v1/council/health' },
        { key: 'sessions', label: 'Recent sessions', path: '/api/v1/council/sessions' },
      ]}
    >
      <section className="glass p-5">
        <h2 className="text-sm font-semibold text-white">New council question</h2>
        <p className="mt-1 text-xs text-gray-400">Use this for pricing, proposal, client objection, delivery risk, or strategic decisions.</p>
        <div className="mt-4 flex flex-col gap-3 lg:flex-row">
          <textarea
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            rows={3}
            placeholder="Ask the council what decision should be made and include the evidence Captain has."
            className="min-h-24 flex-1 rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none placeholder:text-gray-500 focus:border-jarvis-cyan/60"
          />
          <button onClick={convene} disabled={loading || !question.trim()} className="btn-primary min-w-36">
            {loading ? <Loader2 size={15} className="mx-auto animate-spin" /> : <span className="inline-flex items-center gap-2"><Send size={15} /> Convene</span>}
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
