import React, { useEffect, useState } from 'react'
import { Volume2 } from 'lucide-react'
import { getJarvisVoiceBrief, getVoiceProviders } from '../../services/api'
import voiceService from '../../services/voice'
import OperationalView from '../common/OperationalView'

export default function VoiceView() {
  const [brief, setBrief] = useState(null)
  const [providers, setProviders] = useState(null)
  const [speaking, setSpeaking] = useState(false)

  useEffect(() => {
    Promise.allSettled([getJarvisVoiceBrief(), getVoiceProviders()]).then(([briefing, providerList]) => {
      if (briefing.status === 'fulfilled') setBrief(briefing.value)
      if (providerList.status === 'fulfilled') setProviders(providerList.value)
    })
  }, [])

  const speak = async () => {
    const text = brief?.briefing || brief?.text || 'Voice briefing is not available yet.'
    setSpeaking(true)
    try {
      await voiceService.speak(text)
    } finally {
      setSpeaking(false)
    }
  }

  return (
    <OperationalView
      eyebrow="Voice Layer"
      title="Voice Briefings"
      description="Voice readiness, provider status, and briefing controls for the future ElevenLabs calling layer."
      endpoints={[
        { key: 'voice_providers', label: 'Voice providers', path: '/api/v1/voice/providers' },
        { key: 'voice_brief', label: 'Voice briefing', path: '/api/v1/jarvis/voice-brief' },
        { key: 'greeting', label: 'JARVIS greeting', path: '/api/v1/jarvis/greeting' },
      ]}
    >
      <section className="glass p-5">
        <h2 className="text-sm font-semibold text-white">Voice control</h2>
        <p className="mt-1 text-xs text-gray-400">Provider snapshot: {providers ? 'loaded' : 'not loaded'}</p>
        <button onClick={speak} disabled={speaking} className="btn-primary mt-4 inline-flex items-center gap-2">
          <Volume2 size={15} /> {speaking ? 'Speaking' : 'Speak briefing'}
        </button>
      </section>
    </OperationalView>
  )
}
