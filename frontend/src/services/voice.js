// Web Speech API — TTS + STT (free, browser-native)

const WAKE_WORD = 'jarvis'
const INTERRUPT_WORDS = ['wait', 'stop', 'pause', 'enough', 'hold on', 'be quiet']

class VoiceService {
  constructor() {
    this.recognition = null
    this.synthesis = window.speechSynthesis
    this.apiBase = import.meta.env.DEV ? 'http://localhost:8000' : ''
    this.onWakeWord = null
    this.onTranscript = null
    this.continuous = false
    this.selectedVoice = null
    this.voicesReady = false
    this.currentQueue = []
    this.currentAudio = null
    this.isSpeaking = false

    if (this.synthesis) {
      this.loadVoices()
      this.synthesis.onvoiceschanged = () => this.loadVoices()
    }
  }

  get supported() {
    return 'SpeechRecognition' in window || 'webkitSpeechRecognition' in window
  }

  get speechSupported() {
    return 'speechSynthesis' in window
  }

  loadVoices() {
    if (!this.synthesis) return []
    const voices = this.synthesis.getVoices()
    const preferredNames = [
      'Microsoft Ryan Online',
      'Microsoft Ryan',
      'Microsoft Andrew Online',
      'Microsoft Andrew',
      'Microsoft Guy Online',
      'Microsoft Guy',
      'Microsoft Christopher Online',
      'Microsoft Christopher',
      'Microsoft Thomas',
      'Google UK English Male',
      'Google UK English',
      'Microsoft George',
      'Microsoft David',
      'Daniel',
      'Microsoft Mark',
      'Alex',
      'Google US English',
    ]

    this.selectedVoice =
      voices.find((voice) => /natural|neural|online/i.test(`${voice.name} ${voice.voiceURI}`) && voice.lang?.toLowerCase().startsWith('en')) ||
      preferredNames.map((name) => voices.find((voice) => voice.name.includes(name))).find(Boolean) ||
      voices.find((voice) => voice.lang?.toLowerCase() === 'en-gb') ||
      voices.find((voice) => voice.lang?.toLowerCase() === 'en-us') ||
      voices.find((voice) => voice.lang?.toLowerCase().startsWith('en')) ||
      voices[0] ||
      null

    this.voicesReady = voices.length > 0
    return voices
  }

  cleanForSpeech(text = '') {
    return String(text)
      .replace(/```[\s\S]*?```/g, 'I have prepared a code block for review.')
      .replace(/`([^`]+)`/g, '$1')
      .replace(/\[(.*?)\]\((.*?)\)/g, '$1')
      .replace(/[#*_>~]/g, '')
      .replace(/\bAPI\b/g, 'A P I')
      .replace(/\bCRM\b/g, 'C R M')
      .replace(/\bSSL\b/g, 'S S L')
      .replace(/\bAWS\b/g, 'A W S')
      .replace(/\bUI\b/g, 'U I')
      .replace(/\s+/g, ' ')
      .trim()
  }

  inferDeliveryProfile(text = '') {
    const t = String(text).toLowerCase()
    if (/(urgent|down|failed|error|risk|approval|payment|contract|production|security)/.test(t)) {
      return { rate: 0.88, pitch: 0.86, volume: 1.0, pause: 300 }
    }
    if (/(strategy|vision|scale|revenue|architecture|plan|decision)/.test(t)) {
      return { rate: 0.9, pitch: 0.88, volume: 1.0, pause: 300 }
    }
    if (/(done|healthy|green|working|ready|connected)/.test(t)) {
      return { rate: 0.92, pitch: 0.9, volume: 0.98, pause: 240 }
    }
    return { rate: 0.9, pitch: 0.88, volume: 1.0, pause: 280 }
  }

  splitForSpeech(text, maxChunk = 190) {
    const cleaned = this.cleanForSpeech(text)
    const sentences = cleaned.match(/[^.!?]+[.!?]?/g) || [cleaned]
    const chunks = []
    let current = ''

    for (const sentence of sentences) {
      const next = `${current} ${sentence}`.trim()
      if (next.length > maxChunk && current) {
        chunks.push(current)
        current = sentence.trim()
      } else {
        current = next
      }
    }
    if (current) chunks.push(current)
    return chunks
  }

  async speakWithAdvancedVoice(text, options = {}) {
    if (localStorage.getItem('jarvis_advanced_voice') === 'false') return false

    const speechText = this.cleanForSpeech(text).slice(0, options.maxChars ?? 2400)
    if (!speechText) return false

    const response = await fetch(`${this.apiBase}/api/v1/voice/speak`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: speechText,
        mood: options.mood || 'briefing',
        provider: options.provider || 'auto',
      }),
    })

    if (!response.ok) return false

    const data = await response.json()
    this.stopSpeaking()
    this.currentAudio = new Audio(`data:${data.mime_type};base64,${data.audio_base64}`)
    this.currentAudio.preload = 'auto'
    this.currentAudio.volume = options.volume ?? 1
    this.isSpeaking = true
    this.currentAudio.onended = () => {
      this.isSpeaking = false
      this.currentAudio = null
    }
    this.currentAudio.onerror = () => {
      this.isSpeaking = false
      this.currentAudio = null
    }
    await this.currentAudio.play()
    return true
  }

  speakWithBrowserVoice(text, options = {}) {
    if (!this.synthesis) return
    this.synthesis.cancel()
    this.loadVoices()

    const maxChars = options.maxChars ?? 1400
    const speechText = this.cleanForSpeech(text).slice(0, maxChars)
    if (!speechText) return null

    const profile = { ...this.inferDeliveryProfile(speechText), ...options }
    this.currentQueue = this.splitForSpeech(speechText)
    this.isSpeaking = true

    const speakNext = () => {
      if (!this.currentQueue.length) {
        this.isSpeaking = false
        return
      }

      const chunk = this.currentQueue.shift()
      const utt = new SpeechSynthesisUtterance(chunk)
      utt.rate = profile.rate
      utt.pitch = profile.pitch
      utt.volume = profile.volume
      utt.lang = this.selectedVoice?.lang || 'en-GB'

      if (this.selectedVoice) utt.voice = this.selectedVoice

      utt.onend = () => {
        window.setTimeout(speakNext, profile.pause)
      }

      utt.onerror = () => {
        this.isSpeaking = false
      }

      this.synthesis.speak(utt)
    }

    speakNext()
    return true
  }

  speak(text, options = {}) {
    this.speakWithAdvancedVoice(text, options).then((played) => {
      if (!played) this.speakWithBrowserVoice(text, options)
    }).catch(() => {
      this.speakWithBrowserVoice(text, options)
    })
    return true
  }

  startListening({ continuous = false, onResult, onEnd, onInterrupt, onError } = {}) {
    if (!this.supported) return false
    this.stopListening()
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition
    this.recognition = new SR()
    this.recognition.continuous = continuous
    this.recognition.interimResults = true
    this.recognition.lang = 'en-GB'
    this.recognition.maxAlternatives = 3

    this.recognition.onresult = (e) => {
      const transcript = Array.from(e.results)
        .filter((result) => result.isFinal)
        .map((r) => r[0].transcript)
        .join(' ')
        .trim()
        .toLowerCase()

      if (!transcript) return

      if (INTERRUPT_WORDS.some((word) => transcript.includes(word))) {
        this.stopSpeaking()
        if (onInterrupt) onInterrupt(transcript)
        else if (onResult) onResult(transcript)
        return
      }

      if (transcript.includes(WAKE_WORD) && this.onWakeWord) {
        this.onWakeWord(transcript)
      } else if (onResult) {
        onResult(transcript)
      }
    }

    this.recognition.onend = () => {
      if (onEnd) onEnd()
      // Restart for wake-word monitoring
      if (continuous && this.continuous) {
        setTimeout(() => {
          try {
            this.recognition?.start()
          } catch (error) {
            if (onError) onError(error)
          }
        }, 300)
      }
    }

    this.recognition.onerror = (e) => {
      if (e.error !== 'no-speech') console.warn('Speech error:', e.error)
      if (['not-allowed', 'service-not-allowed', 'audio-capture'].includes(e.error)) {
        this.continuous = false
      }
      if (onError) onError(e)
    }

    this.continuous = continuous
    try {
      this.recognition.start()
      return true
    } catch (error) {
      this.continuous = false
      if (onError) onError(error)
      return false
    }
  }

  stopListening() {
    this.continuous = false
    this.recognition?.stop()
    this.recognition = null
  }

  stopSpeaking() {
    this.currentQueue = []
    this.isSpeaking = false
    if (this.currentAudio) {
      this.currentAudio.pause()
      this.currentAudio.currentTime = 0
      this.currentAudio = null
    }
    this.synthesis?.cancel()
  }
}

export const voiceService = new VoiceService()
export default voiceService
