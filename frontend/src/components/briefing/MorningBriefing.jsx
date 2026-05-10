import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Newspaper, RefreshCw, Brain, Clock, Globe, Loader } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { getMorningBriefing } from '../../services/api'
import voiceService from '../../services/voice'
import useJarvisStore from '../../store/useJarvisStore'

export default function MorningBriefing() {
  const { voiceActive } = useJarvisStore()
  const [briefing, setBriefing] = useState(null)
  const [loading, setLoading] = useState(false)
  const [lastFetched, setLastFetched] = useState(null)

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

  useEffect(() => { fetch() }, [])

  const timeOfDay = () => {
    const h = new Date().getHours()
    if (h < 12) return { label: 'Morning', emoji: '🌅' }
    if (h < 17) return { label: 'Afternoon', emoji: '☀️' }
    return { label: 'Evening', emoji: '🌙' }
  }
  const tod = timeOfDay()

  return (
    <div className="p-6 h-full overflow-y-auto no-scrollbar space-y-5">
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
          <button
            onClick={fetch}
            disabled={loading}
            className="btn-primary flex items-center gap-2"
          >
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </motion.div>

      {/* Briefing content */}
      {loading && !briefing && (
        <div className="flex flex-col items-center justify-center py-20 gap-4">
          <Loader size={32} className="text-jarvis-blue animate-spin" />
          <p className="text-white/40 text-sm">JARVIS preparing your briefing…</p>
        </div>
      )}

      {briefing && (
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
