import React, { useMemo, useState } from 'react'
import api from '../../services/api'
import {
  ActionCard,
  DEFAULT_TENANT,
  FrontierShell,
  ResultBox,
  RunButton,
  Textarea,
} from './FrontierShell'

export default function ExpertCouncil() {
  const [question, setQuestion] = useState('')
  const [context, setContext] = useState('')
  const [quick, setQuick] = useState(false)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  const endpoints = useMemo(() => [
    { key: 'sessions', label: 'Expert council sessions', path: '/api/v1/intelligence/expert-council/sessions', params: { tenant_id: DEFAULT_TENANT, limit: 10 } },
    { key: 'classicCouncil', label: 'Classic council health', path: '/api/v1/council/health' },
    { key: 'governance', label: 'Autonomous governance summary', path: '/api/v1/intelligence/governance/summary', params: { tenant_id: DEFAULT_TENANT } },
    { key: 'conscience', label: 'Conscience audit', path: '/api/v1/intelligence/conscience/audit', params: { tenant_id: DEFAULT_TENANT, days: 7 } },
  ], [])

  async function convene(event) {
    event.preventDefault()
    setLoading(true)
    let parsedContext = {}
    if (context.trim()) {
      try {
        parsedContext = JSON.parse(context)
      } catch {
        parsedContext = { notes: context }
      }
    }
    try {
      const response = await api.post('/api/v1/intelligence/expert-council', {
        tenant_id: DEFAULT_TENANT,
        question,
        context: parsedContext,
        quick,
      })
      setResult(response.data)
    } catch (error) {
      setResult({ error: error.response?.data?.detail || error.message })
    }
    setLoading(false)
  }

  return (
    <FrontierShell
      eyebrow="Decision Room"
      title="Expert Council"
      description="Five-agent strategic council for pricing, client objections, delivery risk, and high-leverage strategy."
      endpoints={endpoints}
    >
      {() => (
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
          <ActionCard title="Convene Expert Council" subtitle="Ask one decision-quality question. Include evidence, client context, or risk notes.">
            <form onSubmit={convene} className="space-y-3">
              <Textarea value={question} onChange={setQuestion} placeholder="What should Aliyar Solutions do, and what evidence should the council weigh?" maxLength={8000} />
              <Textarea value={context} onChange={setContext} rows={3} placeholder="Optional context as JSON or plain notes." maxLength={8000} />
              <label className="flex items-center gap-2 text-sm text-gray-300">
                <input type="checkbox" checked={quick} onChange={(event) => setQuick(event.target.checked)} />
                Quick council
              </label>
              <RunButton loading={loading} disabled={!question.trim()}>Convene</RunButton>
            </form>
          </ActionCard>
          <ActionCard title="Latest council output" subtitle="Recommendation, confidence, risks, and synthesis from the last session.">
            <ResultBox result={result} />
          </ActionCard>
        </div>
      )}
    </FrontierShell>
  )
}
