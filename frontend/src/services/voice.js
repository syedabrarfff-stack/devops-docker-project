/**
 * JARVIS Voice Engine
 * - Always-listening mode with barge-in (interrupt JARVIS mid-speech)
 * - Backend TTS (OpenAI onyx → ElevenLabs → Edge TTS) with browser fallback
 * - Contextual greeting on app open
 * - Mobile-optimised continuous recognition
 */

const ELEVENLABS_API_KEY = import.meta.env.VITE_ELEVENLABS_API_KEY || null
const ELEVENLABS_VOICE_ID = import.meta.env.VITE_ELEVENLABS_VOICE_ID || 'onwK4e9ZLuTAKqWW03F9'

const BASE_URL = import.meta.env.DEV ? 'http://localhost:8000' : ''

class VoiceEngine {
  constructor() {
    this.recognition = null
    this.synthesis = window.speechSynthesis
    this._speaking = false
    this._listening = false
    this._continuous = false
    this._audioEl = null

    // Callbacks
    this.onTranscript = null      // fired when user finishes speaking
    this.onInterimResult = null   // fired during speech (show live text)
    this.onStateChange = null     // fired when listening/speaking state changes
    this.onError = null
  }

  get isSpeaking() { return this._speaking }
  get isListening() { return this._listening }

  get supported() {
    return 'SpeechRecognition' in window || 'webkitSpeechRecognition' in window
  }

  // ── TTS — speak text ───────────────────────────────────────────────────────

  async speak(text, { onStart, onEnd } = {}) {
    if (!text) return
    const clean = text
      .replace(/\*\*/g, '')
      .replace(/\*/g, '')
      .replace(/#{1,6}\s/g, '')
      .replace(/`/g, '')
      .replace(/\n\n/g, '. ')
      .replace(/\n/g, ' ')
      .trim()

    this._speaking = true
    this._notify()
    if (onStart) onStart()

    // Try backend TTS first (OpenAI onyx → ElevenLabs), then browser fallback
    const backendOk = await this._speakBackend(clean)
    if (!backendOk) {
      if (ELEVENLABS_API_KEY) {
        await this._speakElevenLabs(clean)
      } else {
        await this._speakBrowser(clean)
      }
    }

    this._speaking = false
    this._notify()
    if (onEnd) onEnd()
  }

  stopSpeaking() {
    this._speaking = false
    // Stop ElevenLabs audio
    if (this._audioEl) {
      this._audioEl.pause()
      this._audioEl.src = ''
      this._audioEl = null
    }
    // Stop browser TTS
    this.synthesis?.cancel()
    this._notify()
  }

  async _speakBackend(text) {
    try {
      const res = await fetch(`${BASE_URL}/api/v1/voice/tts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, provider: 'auto' }),
        signal: AbortSignal.timeout(25000),
      })
      if (!res.ok) return false
      const data = await res.json()
      if (!data.audio_base64) return false
      const url = `data:${data.mime_type};base64,${data.audio_base64}`
      await this._playAudio(url)
      return true
    } catch {
      return false
    }
  }

  async _speakElevenLabs(text) {
    try {
      const res = await fetch(
        `https://api.elevenlabs.io/v1/text-to-speech/${ELEVENLABS_VOICE_ID}/stream`,
        {
          method: 'POST',
          headers: {
            'xi-api-key': ELEVENLABS_API_KEY,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            text,
            model_id: 'eleven_turbo_v2_5',
            voice_settings: { stability: 0.5, similarity_boost: 0.8, style: 0.2, use_speaker_boost: true },
          }),
        }
      )
      if (!res.ok) throw new Error('ElevenLabs error')
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      await this._playAudio(url)
    } catch {
      await this._speakBrowser(text)
    }
  }

  _playAudio(url) {
    return new Promise((resolve) => {
      this._audioEl = new Audio(url)
      this._audioEl.onended = () => { URL.revokeObjectURL(url); resolve() }
      this._audioEl.onerror = () => resolve()
      this._audioEl.play().catch(resolve)
    })
  }

  _speakBrowser(text) {
    return new Promise((resolve) => {
      if (!this.synthesis) return resolve()
      this.synthesis.cancel()

      const chunks = this._chunkText(text, 200)
      let idx = 0

      const speakNext = () => {
        if (idx >= chunks.length || !this._speaking) return resolve()
        const utt = new SpeechSynthesisUtterance(chunks[idx++])
        utt.rate = 0.92
        utt.pitch = 0.88
        utt.volume = 1.0

        const voices = this.synthesis.getVoices()
        const preferred = voices.find(v =>
          v.name.includes('Google UK English Male') ||
          v.name.includes('Daniel') ||
          v.name.includes('Arthur') ||
          v.name.includes('David')
        )
        if (preferred) utt.voice = preferred

        utt.onend = speakNext
        utt.onerror = speakNext
        this.synthesis.speak(utt)
      }

      speakNext()
    })
  }

  _chunkText(text, maxLen) {
    const sentences = text.match(/[^.!?]+[.!?]*/g) || [text]
    const chunks = []
    let current = ''
    for (const s of sentences) {
      if ((current + s).length > maxLen && current) {
        chunks.push(current.trim())
        current = s
      } else {
        current += s
      }
    }
    if (current.trim()) chunks.push(current.trim())
    return chunks.length ? chunks : [text]
  }

  // ── STT — listen ───────────────────────────────────────────────────────────

  startListening({ continuous = false, onResult, onInterim, onEnd } = {}) {
    if (!this.supported || this._listening) return
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition
    this.recognition = new SR()
    this.recognition.continuous = continuous
    this.recognition.interimResults = true
    this.recognition.lang = 'en-US'
    this.recognition.maxAlternatives = 1

    this._listening = true
    this._continuous = continuous
    this._notify()

    this.recognition.onresult = (e) => {
      let interim = ''
      let final = ''
      for (const result of e.results) {
        if (result.isFinal) final += result[0].transcript
        else interim += result[0].transcript
      }

      // Barge-in: if user speaks while JARVIS is talking, stop immediately
      if (this._speaking && (interim || final)) {
        this.stopSpeaking()
      }

      if (interim && onInterim) onInterim(interim)
      if (final) {
        const text = final.trim()
        if (text && onResult) onResult(text)
        if (this.onTranscript) this.onTranscript(text)
      }
    }

    this.recognition.onend = () => {
      if (this._continuous && this._listening) {
        // Auto-restart for always-on mode
        setTimeout(() => {
          try { this.recognition?.start() } catch {}
        }, 300)
      } else {
        this._listening = false
        this._notify()
        if (onEnd) onEnd()
      }
    }

    this.recognition.onerror = (e) => {
      if (e.error === 'no-speech') return
      if (e.error === 'aborted') return
      if (this.onError) this.onError(e.error)
    }

    try {
      this.recognition.start()
    } catch {}
  }

  stopListening() {
    this._continuous = false
    this._listening = false
    try { this.recognition?.stop() } catch {}
    this.recognition = null
    this._notify()
  }

  // ── Always-on mode ─────────────────────────────────────────────────────────

  startAlwaysOn({ onResult } = {}) {
    this.startListening({
      continuous: true,
      onResult,
    })
  }

  stopAlwaysOn() {
    this.stopListening()
  }

  // ── Internal ───────────────────────────────────────────────────────────────

  _notify() {
    if (this.onStateChange) {
      this.onStateChange({ speaking: this._speaking, listening: this._listening })
    }
  }
}

export const voiceService = new VoiceEngine()
export default voiceService
