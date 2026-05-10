// Web Speech API — TTS + STT (free, browser-native)

const WAKE_WORD = 'jarvis'

class VoiceService {
  constructor() {
    this.recognition = null
    this.synthesis = window.speechSynthesis
    this.onWakeWord = null
    this.onTranscript = null
    this.continuous = false
  }

  get supported() {
    return 'SpeechRecognition' in window || 'webkitSpeechRecognition' in window
  }

  speak(text, { rate = 0.95, pitch = 0.9, volume = 1.0 } = {}) {
    if (!this.synthesis) return
    this.synthesis.cancel()
    const utt = new SpeechSynthesisUtterance(text)
    utt.rate   = rate
    utt.pitch  = pitch
    utt.volume = volume

    // Prefer a deep male voice
    const voices = this.synthesis.getVoices()
    const preferred = voices.find(
      (v) => v.name.includes('David') || v.name.includes('Google UK English Male') || v.name.includes('Alex')
    )
    if (preferred) utt.voice = preferred
    this.synthesis.speak(utt)
    return utt
  }

  startListening({ continuous = false, onResult, onEnd } = {}) {
    if (!this.supported) return
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition
    this.recognition = new SR()
    this.recognition.continuous = continuous
    this.recognition.interimResults = false
    this.recognition.lang = 'en-US'

    this.recognition.onresult = (e) => {
      const transcript = Array.from(e.results)
        .map((r) => r[0].transcript)
        .join(' ')
        .trim()
        .toLowerCase()

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
        setTimeout(() => this.recognition?.start(), 300)
      }
    }

    this.recognition.onerror = (e) => {
      if (e.error !== 'no-speech') console.warn('Speech error:', e.error)
    }

    this.continuous = continuous
    this.recognition.start()
  }

  stopListening() {
    this.continuous = false
    this.recognition?.stop()
    this.recognition = null
  }

  stopSpeaking() {
    this.synthesis?.cancel()
  }
}

export const voiceService = new VoiceService()
export default voiceService
