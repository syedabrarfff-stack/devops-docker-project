import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Newspaper, RefreshCw, Brain, Clock, Globe, Loader, Zap, Sparkles } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { getMorningBriefing } from '../../services/api'
import api from '../../services/api'
import voiceService from '../../services/voice'
import useJarvisStore from '../../store/useJarvisStore'

export default function MorningBriefing() {
  const { voiceActive } = useJarvisStore()
  const [briefing, setBriefing] = useState(null)
  const [loading, setLoading] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [aiBriefing, setAiBriefing] = useState(null)
  const [aiBriefingLoading, setAiBriefingLoading] = useState(false)
  const [lastFetched, setLastFetched] = useState(null)
  const [activeTab, setActiveTab] = useState('standard')
  const [debriefResult, setDebriefResult] = useState(null)
  const [debriefing, setDebriefing] = useState(false)
  const [preBriefResult, setPreBriefResult] = useState(null)
  const [preBriefing, setPreBriefing] = useState(false)
  const [preBriefTopic, setPreBriefTopic] = useState('')

  const fetch = async () => {
    setLoading(true)
    try {
      const data = await getMorningBriefing()
      setBriefing(data)
      setLastFetched(new Date())
      if (voiceActive && data?.briefing) {
        const excerpt = data.briefing.replace(/[#*`]/g, '').slice(0, 600)
        voiceService.speak(excerpt)
      }
    } catch {
      setBriefing({ greeting: 'Good day, Captain.', briefing: 'Unable to fetch briefing. Backend may be offline.' })
    } finally {
      setLoading(false)
    }
  }

  const forceGenerate = async () => {
    setGenerating(true)
    try {
      const r = await api.post('/api/v1/briefing/generate', {})
      setBriefing(r.data)
      setLastFetched(new Date())
      setActiveTab('standard')
    } catch (err) {
      setBriefing({ greeting: 'Good day, Captain.', briefing: err.response?.data?.detail || err.message })
    } finally {
      setGenerating(false)
    }
  }

  const fetchAiBriefing = async () => {
    setAiBriefingLoading(true)
    try {
      const r = await api.get('/api/v1/briefing/morning-ai')
      setAiBriefing(r.data)
      setActiveTab('ai')
    } catch (err) {
      setAiBriefing({ briefing: err.response?.data?.detail || err.message })
    } finally {
      setAiBriefingLoading(false)
    }
  }

  const runDebrief = async () => {
    setDebriefing(true)
    try {
      const r = await api.post('/api/v1/briefing/debrief', {})
      setDebriefResult(r.data)
    } catch (err) {
      setDebriefResult({ error: err.response?.data?.detail || err.message })
    }
    setDebriefing(false)
  }

  const runPreBrief = async () => {
    setPreBriefing(true)
    try {
      const r = await api.post('/api/v1/briefing/pre-brief', { topic: preBriefTopic || undefined })
      setPreBriefResult(r.data)
    } catch (err) {
      setPreBriefResult({ error: err.response?.data?.detail || err.message })
    }
    setPreBriefing(false)
  }

  useEffect(() => { fetch() }, [])

  const timeOfDay = () => {
    const h = new Date().getHours()
    if (h < 12) return { label: 'Morning', emoji: '🌅' }
    if (h < 17) return { label: 'Afternoon', emoji: '☀️' }
    return { label: 'Evening', emoji: '🌙' }
  }
  const tod = timeOfDay()

  return (
    <div className="p-6 pb-28 h-full min-h-0 overflow-y-auto no-scrollbar space-y-5">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass p-5 border border-jarvis-blue/15"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-jarvis-blue/10 border border-jarvis-blue/20">
              <Newspaper size={18} className="text-jarvis-blue" />
            </div>
            <div>
              <h2 className="font-bold text-white">
                {tod.emoji} Good {tod.label}, Captain
              </h2>
              <p className="text-xs text-white/40 mt-0.5">
                {new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={fetchAiBriefing}
              disabled={aiBriefingLoading}
              className="flex items-center gap-1.5 rounded-xl border border-purple-500/30 bg-purple-500/10 px-3 py-1.5 text-xs font-bold text-purple-300 hover:bg-purple-500/20 disabled:opacity-40 transition-colors"
            >
              <Sparkles size={12} className={aiBriefingLoading ? 'animate-pulse' : ''} />
              AI Brief
            </button>
            <button
              onClick={forceGenerate}
              disabled={generating}
              className="flex items-center gap-1.5 rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-1.5 text-xs font-bold text-amber-300 hover:bg-amber-500/20 disabled:opacity-40 transition-colors"
            >
              <Zap size={12} className={generating ? 'animate-pulse' : ''} />
              {generating ? 'Generating…' : 'Force Generate'}
            </button>
            <button
              onClick={fetch}
              disabled={loading}
              className="btn-primary flex items-center gap-2"
            >
              <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
              Refresh
            </button>
          </div>
        </div>
      </motion.div>

      {/* Tabs */}
      {(briefing || aiBriefing) && (
        <div className="flex gap-2">
          <button
            onClick={() => setActiveTab('standard')}
            className={`px-4 py-1.5 rounded-xl text-xs font-bold transition-colors ${activeTab === 'standard' ? 'bg-jarvis-blue/20 border border-jarvis-blue/40 text-jarvis-blue' : 'border border-white/10 text-white/40 hover:text-white/60'}`}
          >
            Standard
          </button>
          <button
            onClick={() => setActiveTab('ai')}
            className={`px-4 py-1.5 rounded-xl text-xs font-bold transition-colors ${activeTab === 'ai' ? 'bg-purple-500/20 border border-purple-500/40 text-purple-300' : 'border border-white/10 text-white/40 hover:text-white/60'}`}
          >
            AI Enhanced
          </button>
        </div>
      )}

      {/* Briefing content */}
      {loading && !briefing && (
        <div className="flex flex-col items-center justify-center py-20 gap-4">
          <Loader size={32} className="text-jarvis-blue animate-spin" />
          <p className="text-white/40 text-sm">JARVIS preparing your briefing…</p>
        </div>
      )}

      {aiBriefingLoading && (
        <div className="flex flex-col items-center justify-center py-10 gap-3">
          <Sparkles size={24} className="text-purple-400 animate-pulse" />
          <p className="text-white/40 text-sm">AI generating enhanced briefing…</p>
        </div>
      )}

      {activeTab === 'standard' && briefing && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="glass p-6 border border-white/[0.07]"
        >
          {briefing.greeting && (
            <div className="flex items-start gap-3 mb-5 pb-5 border-b border-white/[0.06]">
              <div className="w-8 h-8 rounded-lg bg-jarvis-blue/15 border border-jarvis-blue/25
                              flex items-center justify-center flex-shrink-0">
                <Brain size={14} className="text-jarvis-blue" />
              </div>
              <p className="text-white/70 text-sm leading-relaxed italic">"{briefing.greeting}"</p>
            </div>
          )}

          <div className="prose prose-invert prose-sm max-w-none
                          [&>h1]:text-jarvis-blue [&>h1]:text-base [&>h1]:font-bold [&>h1]:mb-3
                          [&>h2]:text-white/80 [&>h2]:text-sm [&>h2]:font-semibold [&>h2]:mb-2
                          [&>h3]:text-white/60 [&>h3]:text-xs [&>h3]:font-medium [&>h3]:mb-2
                          [&>p]:text-white/60 [&>p]:text-sm [&>p]:leading-relaxed
                          [&>ul]:space-y-1 [&>ul>li]:text-white/55 [&>ul>li]:text-sm
                          [&>strong]:text-white/80">
            <ReactMarkdown>{briefing.briefing || briefing.message || 'No briefing available.'}</ReactMarkdown>
          </div>
        </motion.div>
      )}

      {activeTab === 'ai' && aiBriefing && !aiBriefingLoading && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass p-6 border border-purple-500/20"
        >
          <div className="flex items-center gap-2 mb-4 pb-4 border-b border-white/[0.06]">
            <Sparkles size={14} className="text-purple-400" />
            <p className="text-xs font-bold text-purple-300 uppercase tracking-wider">AI-Enhanced Briefing</p>
          </div>
          <div className="prose prose-invert prose-sm max-w-none
                          [&>h1]:text-purple-300 [&>h1]:text-base [&>h1]:font-bold [&>h1]:mb-3
                          [&>h2]:text-white/80 [&>h2]:text-sm [&>h2]:font-semibold [&>h2]:mb-2
                          [&>p]:text-white/60 [&>p]:text-sm [&>p]:leading-relaxed
                          [&>ul]:space-y-1 [&>ul>li]:text-white/55 [&>ul>li]:text-sm
                          [&>strong]:text-white/80">
            <ReactMarkdown>{aiBriefing.briefing || aiBriefing.message || JSON.stringify(aiBriefing, null, 2)}</ReactMarkdown>
          </div>
        </motion.div>
      )}

      {/* Debrief & Pre-Brief */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="glass p-5 border border-white/[0.06] space-y-3">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-white/50">Daily Debrief</p>
            <p className="text-xs text-white/30 mt-0.5">JARVIS reviews what happened today and logs learnings.</p>
          </div>
          <button
            onClick={runDebrief}
            disabled={debriefing}
            className="w-full rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-2 text-xs font-bold text-amber-300 hover:bg-amber-500/20 disabled:opacity-40 transition-colors"
          >
            {debriefing ? 'Running…' : '📋 Run Daily Debrief'}
          </button>
          {debriefResult && (
            <pre className="max-h-40 overflow-auto rounded-lg border border-white/10 bg-black/20 p-2.5 text-[10px] text-gray-300">
              {JSON.stringify(debriefResult, null, 2)}
            </pre>
          )}
        </div>

        <div className="glass p-5 border border-white/[0.06] space-y-3">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-white/50">Pre-Meeting Brief</p>
            <p className="text-xs text-white/30 mt-0.5">JARVIS prepares context on a topic for your next meeting.</p>
          </div>
          <input
            value={preBriefTopic}
            onChange={e => setPreBriefTopic(e.target.value)}
            placeholder="Meeting topic (optional)"
            className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white placeholder-gray-600 text-xs focus:outline-none focus:border-blue-500/40"
          />
          <button
            onClick={runPreBrief}
            disabled={preBriefing}
            className="w-full rounded-xl border border-blue-500/30 bg-blue-500/10 px-4 py-2 text-xs font-bold text-blue-300 hover:bg-blue-500/20 disabled:opacity-40 transition-colors"
          >
            {preBriefing ? 'Preparing…' : '🎯 Run Pre-Brief'}
          </button>
          {preBriefResult && (
            <pre className="max-h-40 overflow-auto rounded-lg border border-white/10 bg-black/20 p-2.5 text-[10px] text-gray-300">
              {JSON.stringify(preBriefResult, null, 2)}
            </pre>
          )}
        </div>
      </div>

      {/* Info strip */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { icon: Clock, label: 'Last Updated', value: lastFetched?.toLocaleTimeString() || '—' },
          { icon: Globe, label: 'Markets Active', value: 'USA · UK · AU · NZ' },
          { icon: Brain, label: 'AI Briefing', value: 'Claude Sonnet 4.6' },
        ].map(({ icon: Icon, label, value }) => (
          <div key={label} className="glass p-4 border border-white/[0.06] flex items-center gap-3">
            <Icon size={14} className="text-white/30" />
            <div>
              <p className="text-[10px] text-white/30 uppercase tracking-wider">{label}</p>
              <p className="text-xs text-white/60 mt-0.5 font-mono">{value}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
