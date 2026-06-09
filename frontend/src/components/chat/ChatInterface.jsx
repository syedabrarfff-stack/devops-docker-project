import React, { useState, useRef, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, Mic, MicOff, Volume2, VolumeX, Loader, Zap, ChevronDown, Radio } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { jarvisChat } from '../../services/api'
import voiceService from '../../services/voice'
import useJarvisStore from '../../store/useJarvisStore'

const TASK_TYPES = [
  { value: 'FAST',         label: 'Fast',       desc: 'Quick answers' },
  { value: 'REASONING',    label: 'Deep Think',  desc: 'Complex analysis' },
  { value: 'STRATEGY',     label: 'Strategy',   desc: 'Business decisions' },
  { value: 'RESEARCH',     label: 'Research',   desc: 'Market intel' },
  { value: 'CODE',         label: 'Code',       desc: 'Technical work' },
]

// ── Message bubble ────────────────────────────────────────────────────────────

const Message = ({ msg, onSpeak }) => {
  const isJarvis = msg.role === 'assistant'
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={`flex gap-3 ${isJarvis ? '' : 'flex-row-reverse'}`}
    >
      {/* Avatar */}
      <div className={`w-8 h-8 rounded-xl flex-shrink-0 flex items-center justify-center text-xs font-bold
                        ${isJarvis
                          ? 'bg-jarvis-blue/20 border border-jarvis-blue/40 text-jarvis-blue'
                          : 'bg-purple-500/20 border border-purple-400/30 text-purple-300'}`}>
        {isJarvis ? 'J' : 'C'}
      </div>

      {/* Bubble */}
      <div className={`max-w-[78%] rounded-2xl px-4 py-3 text-sm leading-relaxed relative group
                        ${isJarvis
                          ? 'bg-white/[0.04] border border-white/[0.08] text-white/85 rounded-tl-sm'
                          : 'bg-jarvis-blue/10 border border-jarvis-blue/20 text-white/85 rounded-tr-sm'}`}>
        {isJarvis ? (
          <>
            <ReactMarkdown
              components={{
                p: ({ children }) => <p className="mb-1 last:mb-0">{children}</p>,
                code: ({ children }) => (
                  <code className="bg-black/40 rounded px-1.5 py-0.5 font-mono text-xs text-jarvis-blue">{children}</code>
                ),
                pre: ({ children }) => (
                  <pre className="bg-black/40 rounded-xl p-3 my-2 overflow-x-auto font-mono text-xs text-green-300 border border-white/10">{children}</pre>
                ),
                ul: ({ children }) => <ul className="list-disc ml-4 space-y-0.5">{children}</ul>,
                ol: ({ children }) => <ol className="list-decimal ml-4 space-y-0.5">{children}</ol>,
                strong: ({ children }) => <strong className="text-white font-semibold">{children}</strong>,
              }}
            >
              {msg.content}
            </ReactMarkdown>
            {/* Speak button */}
            <button
              onClick={() => onSpeak(msg.content)}
              className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity
                         p-1 rounded-lg bg-white/5 hover:bg-jarvis-blue/20 text-white/30 hover:text-jarvis-blue"
            >
              <Volume2 size={12} />
            </button>
          </>
        ) : (
          <p>{msg.content}</p>
        )}
        <div className="flex items-center gap-2 mt-1.5">
          {msg.model && (
            <span className="text-[10px] text-white/20 font-mono">{msg.model}</span>
          )}
          {msg.provider && (
            <span className="text-[10px] text-white/15 font-mono">- {msg.provider}</span>
          )}
          <span className="text-[10px] text-white/15 ml-auto">
            {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        </div>
      </div>
    </motion.div>
  )
}

// ── Typing indicator ──────────────────────────────────────────────────────────

const Typing = () => (
  <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="flex gap-3">
    <div className="w-8 h-8 rounded-xl bg-jarvis-blue/20 border border-jarvis-blue/40 flex items-center justify-center text-xs font-bold text-jarvis-blue">J</div>
    <div className="glass px-4 py-3 rounded-2xl rounded-tl-sm border border-white/[0.08]">
      <div className="flex gap-1.5 items-center">
        {[0, 1, 2].map((i) => (
          <motion.span
            key={i}
            animate={{ y: [0, -5, 0], opacity: [0.4, 1, 0.4] }}
            transition={{ delay: i * 0.18, repeat: Infinity, duration: 0.7 }}
            className="w-1.5 h-1.5 rounded-full bg-jarvis-blue"
          />
        ))}
        <span className="ml-2 text-[11px] text-white/25 font-mono tracking-wide">JARVIS processing...</span>
      </div>
    </div>
  </motion.div>
)

// ── Main component ────────────────────────────────────────────────────────────

export default function ChatInterface() {
  const { sessionId, voiceActive, setVoiceActive, voiceListening, setVoiceListening } = useJarvisStore()

  const [messages, setMessages] = useState([
    {
      id: 'init',
      role: 'assistant',
      content: "Online, Captain. Core runtime is live; production subsystems are being verified. What are we working on?",
      timestamp: new Date().toISOString(),
    }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [taskType, setTaskType] = useState('FAST')
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [interimText, setInterimText] = useState('')
  const [voiceMode, setVoiceMode] = useState(false) // always-on voice mode

  const bottomRef = useRef(null)
  const inputRef = useRef(null)
  const hasGreeted = useRef(false)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  // Voice state callbacks
  useEffect(() => {
    voiceService.onStateChange = ({ speaking, listening }) => {
      setIsSpeaking(speaking)
      setVoiceListening(listening)
    }
    return () => { voiceService.onStateChange = null }
  }, [])

  // Auto-greet on first open if voice is active
  useEffect(() => {
    if (voiceActive && !hasGreeted.current) {
      hasGreeted.current = true
      const hour = new Date().getHours()
      const greeting = hour < 12 ? 'Good morning, Captain.'
        : hour < 17 ? 'Good afternoon, Captain.'
        : hour < 21 ? 'Good evening, Captain.'
        : 'Still up, Captain.'
      voiceService.speak(`${greeting} JARVIS is online. Core runtime is live and production subsystems are being verified. What do you need?`)
    }
  }, [voiceActive])

  // ── Send message ──────────────────────────────────────────────────────────

  const send = useCallback(async (text) => {
    const msg = (text || input).trim()
    if (!msg || loading) return
    setInput('')
    setInterimText('')
    setLoading(true)

    const userMsg = { id: Date.now(), role: 'user', content: msg, timestamp: new Date().toISOString() }
    setMessages(m => [...m, userMsg])

    const history = messages
      .filter(m => m.id !== 'init')
      .slice(-12)
      .map(({ role, content }) => ({ role, content }))

    try {
      const data = await jarvisChat(msg, taskType, history, sessionId)
      const response = data.response || "Captain, I seem to be having a moment. Try again."

      const aiMsg = {
        id: Date.now() + 1,
        role: 'assistant',
        content: response,
        model: data.model,
        provider: data.provider,
        task_type: data.task_type,
        timestamp: new Date().toISOString(),
      }
      setMessages(m => [...m, aiMsg])

      // Speak response if voice is active
      if (voiceActive) {
        const speakText = response.length > 600 ? response.slice(0, 600) + '...' : response
        await voiceService.speak(speakText, {
          onStart: () => setIsSpeaking(true),
          onEnd: () => setIsSpeaking(false),
        })
      }
    } catch {
      setMessages(m => [...m, {
        id: Date.now() + 1,
        role: 'assistant',
        content: "I've lost contact with the AI systems for a moment, Captain. Check the backend connection.",
        timestamp: new Date().toISOString(),
      }])
    } finally {
      setLoading(false)
    }
  }, [input, loading, messages, sessionId, taskType, voiceActive])

  // ── Single-shot voice input ───────────────────────────────────────────────

  const toggleVoiceInput = () => {
    if (voiceListening && !voiceMode) {
      voiceService.stopListening()
      setVoiceListening(false)
      return
    }
    voiceService.startListening({
      continuous: false,
      onResult: (transcript) => {
        setInterimText('')
        send(transcript)
      },
      onInterim: (t) => setInterimText(t),
      onEnd: () => { setInterimText(''); setVoiceListening(false) },
    })
  }

  // ── Always-on voice mode ──────────────────────────────────────────────────

  const toggleVoiceMode = () => {
    if (voiceMode) {
      voiceService.stopAlwaysOn()
      setVoiceMode(false)
      setVoiceActive(false)
    } else {
      setVoiceMode(true)
      setVoiceActive(true)
      voiceService.startAlwaysOn({
        onResult: (transcript) => {
          setInterimText('')
          send(transcript)
        },
      })
      voiceService.onTranscript = null
    }
  }

  const handleSpeak = (text) => {
    if (isSpeaking) {
      voiceService.stopSpeaking()
    } else {
      voiceService.speak(text)
    }
  }

  return (
    <div className="flex h-full min-h-0 flex-col gap-3 p-4 pb-24">

      {/* Header controls */}
      <div className="flex items-center gap-3 px-1">
        {/* Task type selector */}
        <div className="flex gap-1 bg-white/[0.03] border border-white/[0.07] rounded-xl p-1">
          {TASK_TYPES.map(t => (
            <button
              key={t.value}
              onClick={() => setTaskType(t.value)}
              title={t.desc}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                taskType === t.value
                  ? 'bg-jarvis-blue/20 text-jarvis-blue border border-jarvis-blue/30'
                  : 'text-white/35 hover:text-white/60'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        <div className="ml-auto flex items-center gap-2">
          {/* Speaking indicator */}
          {isSpeaking && (
            <motion.div
              animate={{ opacity: [0.5, 1, 0.5] }}
              transition={{ repeat: Infinity, duration: 1.2 }}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-jarvis-blue/10 border border-jarvis-blue/20"
            >
              <Volume2 size={12} className="text-jarvis-blue" />
              <span className="text-[11px] text-jarvis-blue font-medium">Speaking</span>
            </motion.div>
          )}

          {/* Always-on voice mode toggle */}
          <button
            onClick={toggleVoiceMode}
            title={voiceMode ? 'Disable always-on listening' : 'Enable always-on listening'}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium border transition-all ${
              voiceMode
                ? 'bg-green-500/15 border-green-400/30 text-green-400'
                : 'bg-white/[0.04] border-white/[0.10] text-white/40 hover:text-white/70'
            }`}
          >
            <Radio size={12} className={voiceMode ? 'animate-pulse' : ''} />
            {voiceMode ? 'Listening' : 'Always-On'}
          </button>

          {/* Stop speaking */}
          {isSpeaking && (
            <button
              onClick={() => voiceService.stopSpeaking()}
              className="p-2 rounded-xl bg-red-500/10 border border-red-400/20 text-red-400 hover:bg-red-500/20"
            >
              <VolumeX size={14} />
            </button>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto no-scrollbar space-y-4 glass p-4 rounded-2xl border border-white/[0.06]">
        {messages.map(m => <Message key={m.id} msg={m} onSpeak={handleSpeak} />)}
        {loading && <Typing />}

        {/* Interim voice text */}
        <AnimatePresence>
          {interimText && (
            <motion.div
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="flex justify-end"
            >
              <div className="px-4 py-2 rounded-2xl rounded-tr-sm bg-white/[0.03] border border-white/[0.06] text-white/35 text-sm italic max-w-[70%]">
                {interimText}...
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div className="flex gap-2">
        <div className={`flex-1 flex items-center gap-2 px-4 py-3 rounded-2xl border transition-colors
                         ${voiceListening
                           ? 'bg-jarvis-blue/5 border-jarvis-blue/40'
                           : 'glass border-white/[0.10] focus-within:border-jarvis-blue/40'}`}>
          <input
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !e.shiftKey && send()}
            placeholder={voiceListening ? 'Listening...' : voiceMode ? 'Just speak, Captain...' : 'Message JARVIS...'}
            className="flex-1 bg-transparent text-sm text-white/80 placeholder:text-white/25 outline-none"
          />
          {input && (
            <button onClick={() => setInput('')} className="text-white/20 hover:text-white/50 text-xs leading-none">x</button>
          )}
        </div>

        {/* Single-shot mic */}
        <button
          onClick={toggleVoiceInput}
          disabled={voiceMode}
          className={`p-3 rounded-2xl border transition-all ${
            voiceListening && !voiceMode
              ? 'bg-jarvis-blue/20 border-jarvis-blue/50 text-jarvis-blue'
              : 'glass border-white/[0.10] text-white/40 hover:text-white/70 disabled:opacity-20'
          }`}
        >
          {voiceListening && !voiceMode
            ? <motion.span animate={{ scale: [1, 1.2, 1] }} transition={{ repeat: Infinity, duration: 0.7 }}>
                <Mic size={18} />
              </motion.span>
            : <MicOff size={18} />}
        </button>

        {/* Send */}
        <motion.button
          whileTap={{ scale: 0.95 }}
          onClick={() => send()}
          disabled={(!input.trim() && !loading) || loading}
          className="px-5 py-3 rounded-2xl bg-jarvis-blue/15 border border-jarvis-blue/30 text-jarvis-blue
                     transition-all hover:bg-jarvis-blue/25 hover:border-jarvis-blue/50
                     disabled:opacity-30 disabled:cursor-not-allowed"
        >
          {loading ? <Loader size={16} className="animate-spin" /> : <Send size={16} />}
        </motion.button>
      </div>

      {/* Voice mode active banner */}
      <AnimatePresence>
        {voiceMode && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="flex items-center justify-center gap-2 py-1.5"
          >
            {[...Array(5)].map((_, i) => (
              <motion.div
                key={i}
                animate={{ scaleY: [0.3, 1, 0.3] }}
                transition={{ repeat: Infinity, duration: 0.9, delay: i * 0.12 }}
                className="w-1 bg-jarvis-blue/60 rounded-full"
                style={{ height: 16 }}
              />
            ))}
            <span className="text-[11px] text-white/30 font-mono ml-1">always listening - say anything</span>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
