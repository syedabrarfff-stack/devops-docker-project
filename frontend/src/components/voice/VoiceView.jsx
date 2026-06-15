import React, { useCallback, useEffect, useState } from 'react'
import { Loader2, Mic, RefreshCw, Volume2, VolumeX } from 'lucide-react'
import { getJarvisVoiceBrief, getVoiceProviders } from '../../services/api'
import voiceService from '../../services/voice'
import api from '../../services/api'

export default function VoiceView() {
  const [brief, setBrief] = useState(null)
  const [providers, setProviders] = useState(null)
  const [speaking, setSpeaking] = useState(false)
  const [loading, setLoading] = useState(true)
  const [ttsText, setTtsText] = useState('')
  const [ttsLoading, setTtsLoading] = useState(false)
  const [ttsResult, setTtsResult] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    const [briefRes, provRes] = await Promise.allSettled([
      getJarvisVoiceBrief().catch(() => null),
      getVoiceProviders().catch(() => null),
    ])
    if (briefRes.status === 'fulfilled') setBrief(briefRes.value)
    if (provRes.status === 'fulfilled') setProviders(provRes.value)
    setLoading(false)
  }, [])

  useEffect(() => { load() }, [load])

  const speak = async () => {
    const text = brief?.briefing || brief?.text || 'JARVIS voice briefing not available. All systems operational.'
    setSpeaking(true)
    try {
      await voiceService.speak(text)
    } finally {
      setSpeaking(false)
    }
  }

  const speakCustom = async () => {
    if (!ttsText.trim()) return
    setSpeaking(true)
    try {
      await voiceService.speak(ttsText)
    } finally {
      setSpeaking(false)
    }
  }

  const testTtsApi = async () => {
    if (!ttsText.trim()) return
    setTtsLoading(true)
    setTtsResult(null)
    try {
      const r = await api.post('/api/v1/voice/tts', { text: ttsText })
      setTtsResult(r.data)
    } catch (err) {
      setTtsResult({ error: err.response?.data?.detail || err.message })
    }
    setTtsLoading(false)
  }

  const providerList = providers?.providers || (Array.isArray(providers) ? providers : [])
  const briefText = brief?.briefing || brief?.text

  return (
    <div className="min-h-[calc(100vh-3.5rem)] p-6 pb-10 space-y-6">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.22em] text-jarvis-cyan/70">Voice Layer</p>
          <h1 className="mt-2 text-3xl font-bold text-white">Voice Briefings</h1>
          <p className="mt-2 max-w-2xl text-sm text-gray-400">
            Voice readiness, TTS provider status, and briefing controls — ready for the ElevenLabs calling layer.
          </p>
        </div>
        <button type="button" onClick={load} disabled={loading} className="btn-primary inline-flex items-center justify-center gap-2">
          {loading ? <Loader2 size={15} className="animate-spin" /> : <RefreshCw size={15} />}
          Refresh
        </button>
      </header>

      {/* Provider status */}
      <section className="glass p-5">
        <h2 className="text-sm font-semibold text-white mb-4">TTS Provider Status</h2>
        {loading ? (
          <div className="flex items-center justify-center py-6 text-gray-500"><Loader2 size={18} className="animate-spin mr-2" />Loading…</div>
        ) : providerList.length > 0 ? (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
            {providerList.map(p => {
              const ok = p.available !== false && !p.error
              return (
                <div key={p.name || p.provider} className={`rounded-xl border p-4 ${ok ? 'border-green-500/20 bg-green-500/5' : 'border-red-500/20 bg-red-500/5'}`}>
                  <div className="flex items-center gap-2 mb-1">
                    {ok ? <Volume2 size={13} className="text-green-400" /> : <VolumeX size={13} className="text-red-400" />}
                    <span className="text-sm font-semibold text-white capitalize">{p.name || p.provider}</span>
                  </div>
                  <p className={`text-xs ${ok ? 'text-green-300' : 'text-red-300'}`}>{ok ? 'Available' : 'Unavailable'}</p>
                  {p.model && <p className="text-[10px] text-gray-500 mt-1">{p.model}</p>}
                  {p.note && <p className="text-[10px] text-gray-500 mt-1">{p.note}</p>}
                </div>
              )
            })}
          </div>
        ) : (
          <div className="rounded-xl border border-white/10 bg-white/5 p-4">
            <div className="flex items-center gap-2">
              <Volume2 size={13} className="text-green-400" />
              <span className="text-sm font-semibold text-white">Browser TTS</span>
            </div>
            <p className="text-xs text-green-300 mt-1">Available via Web Speech API</p>
            <p className="text-[10px] text-gray-500 mt-1">ElevenLabs and OpenAI TTS active when API keys are configured</p>
          </div>
        )}
      </section>

      {/* Voice briefing */}
      <section className="glass p-5">
        <h2 className="text-sm font-semibold text-white mb-1">JARVIS Voice Briefing</h2>
        <p className="text-xs text-gray-500 mb-4">Speak the current JARVIS operational briefing via browser TTS or configured voice provider.</p>

        {briefText && (
          <div className="mb-4 rounded-xl border border-white/10 bg-white/5 p-4">
            <p className="text-xs text-gray-400 leading-relaxed line-clamp-5">{briefText}</p>
          </div>
        )}

        <button
          type="button"
          onClick={speak}
          disabled={speaking}
          className="btn-primary inline-flex items-center gap-2"
        >
          {speaking ? <Loader2 size={15} className="animate-spin" /> : <Volume2 size={15} />}
          {speaking ? 'Speaking…' : 'Speak Briefing'}
        </button>
      </section>

      {/* TTS Test */}
      <section className="glass p-5">
        <h2 className="text-sm font-semibold text-white mb-1">TTS Test Console</h2>
        <p className="text-xs text-gray-500 mb-4">Enter any text to test voice synthesis via browser or the configured server-side TTS provider.</p>
        <textarea
          value={ttsText}
          onChange={e => setTtsText(e.target.value)}
          rows={3}
          placeholder="Enter text to synthesize…"
          className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none placeholder:text-gray-500 focus:border-jarvis-cyan/60 mb-3"
        />
        <div className="flex gap-3 flex-wrap">
          <button
            type="button"
            onClick={speakCustom}
            disabled={speaking || !ttsText.trim()}
            className="inline-flex items-center gap-2 rounded-xl border border-jarvis-cyan/40 bg-jarvis-cyan/10 px-4 py-2 text-sm font-medium text-jarvis-cyan hover:bg-jarvis-cyan/20 disabled:opacity-40 transition-colors"
          >
            {speaking ? <Loader2 size={14} className="animate-spin" /> : <Mic size={14} />}
            Speak (Browser)
          </button>
          <button
            type="button"
            onClick={testTtsApi}
            disabled={ttsLoading || !ttsText.trim()}
            className="inline-flex items-center gap-2 rounded-xl border border-jarvis-gold/40 bg-jarvis-gold/10 px-4 py-2 text-sm font-medium text-jarvis-gold hover:bg-jarvis-gold/20 disabled:opacity-40 transition-colors"
          >
            {ttsLoading ? <Loader2 size={14} className="animate-spin" /> : <Volume2 size={14} />}
            Test API TTS
          </button>
        </div>

        {ttsResult && (
          <div className={`mt-4 rounded-lg border p-3 text-sm ${
            ttsResult.error
              ? 'border-red-400/20 bg-red-400/10 text-red-200'
              : 'border-green-400/20 bg-green-400/10 text-green-200'
          }`}>
            {ttsResult.error ? ttsResult.error : (
              <div>
                <p className="font-medium">TTS response received</p>
                {ttsResult.provider && <p className="text-xs mt-1 opacity-70">Provider: {ttsResult.provider}</p>}
                {ttsResult.audio_url && (
                  <audio controls src={ttsResult.audio_url} className="mt-2 w-full" />
                )}
              </div>
            )}
          </div>
        )}
      </section>

      {/* Raw provider data */}
      {providers && (
        <section className="glass p-5">
          <h2 className="text-sm font-semibold text-white mb-3">Raw Provider Data</h2>
          <pre className="max-h-64 overflow-auto rounded-lg border border-white/10 bg-black/20 p-3 text-xs text-gray-300">
            {JSON.stringify(providers, null, 2)}
          </pre>
        </section>
      )}
    </div>
  )
}
