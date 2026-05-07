import React, { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, Mic, MicOff, Bot, User, Loader, Zap, ChevronDown } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { sendChat } from '../../services/api'
import voiceService from '../../services/voice'
import useJarvisStore from '../../store/useJarvisStore'

const PROVIDERS = [
  { value: '', label: 'Auto Route' },
  { value: 'anthropic', label: 'Claude (Anthropic)' },
  { value: 'openai', label: 'GPT-4o (OpenAI)' },
  { value: 'google', label: 'Gemini (Google)' },
  { value: 'deepseek', label: 'DeepSeek' },
  { value: 'groq', label: 'Llama/Groq' },
]

const Message = ({ msg }) => {
  const isJarvis = msg.role === 'assistant'
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className={`flex gap-3 ${isJarvis ? '' : 'flex-row-reverse'}`}
    >
      {/* Avatar */}
      <div className={`w-8 h-8 rounded-lg flex-shrink-0 flex items-center justify-center
                        ${isJarvis
                          ? 'bg-jarvis-blue/15 border border-jarvis-blue/25'
                          : 'bg-jarvis-purple/15 border border-jarvis-purple/25'}`}>
        {isJarvis ? <Bot size={14} className="text-jarvis-blue" /> : <User size={14} className="text-purple-400" />}
      </div>

      {/* Bubble */}
      <div className={`max-w-[75%] rounded-xl px-4 py-3 text-sm leading-relaxed
                        ${isJarvis
                          ? 'bg-white/[0.04] border border-white/[0.07] text-white/85'
                          : 'bg-jarvis-purple/10 border border-jarvis-purple/20 text-white/85'}`}>
        {isJarvis ? (
          <ReactMarkdown
            components={{
              code: ({ children }) => (
                <code className="bg-white/10 rounded px-1 py-0.5 font-mono text-xs text-jarvis-blue">
                  {children}
                </code>
              ),
              pre: ({ children }) => (
                <pre className="bg-black/40 rounded-lg p-3 my-2 overflow-x-auto font-mono text-xs text-green-300">
                  {children}
                </pre>
              ),
            }}
          >
            {msg.content}
          </ReactMarkdown>
        ) : (
          <p>{msg.content}</p>
        )}
        <div className="flex items-center justify-between mt-2 gap-3">
          {msg.model && (
            <span className="text-[10px] text-white/25 font-mono">{msg.model}</span>
          )}
          {msg.timestamp && (
            <span className="text-[10px] text-white/20 ml-auto">
              {new Date(msg.timestamp).toLocaleTimeString()}
            </span>
          )}
        </div>
      </div>
    </motion.div>
  )
}

export default function ChatInterface() {
  const { sessionId, voiceActive } = useJarvisStore()
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      role: 'assistant',
      content: "Good day, Captain. I'm JARVIS — your autonomous AI operating system. How may I assist Aliyar Solutions today?",
      timestamp: new Date().toISOString(),
    }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [provider, setProvider] = useState('')
  const [listening, setListening] = useState(false)
  const bottomRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const send = async (text = input) => {
    const msg = text.trim()
    if (!msg || loading) return
    setInput('')
    setLoading(true)

    const userMsg = { id: Date.now(), role: 'user', content: msg, timestamp: new Date().toISOString() }
    setMessages((m) => [...m, userMsg])

    const history = messages
      .filter((m) => m.id !== 'welcome')
      .map(({ role, content }) => ({ role, content }))

    try {
      const data = await sendChat({
        message: msg,
        session_id: sessionId,
        auto_route: !provider,
        force_provider: provider || null,
        history: history.slice(-10),
      })

      const aiMsg = {
        id: Date.now() + 1,
        role: 'assistant',
        content: data.response,
        model: data.model_used,
        task_type: data.task_type,
        timestamp: new Date().toISOString(),
      }
      setMessages((m) => [...m, aiMsg])

      if (voiceActive) {
        voiceService.speak(data.response.slice(0, 500))
      }
    } catch (err) {
      setMessages((m) => [...m, {
        id: Date.now() + 1,
        role: 'assistant',
        content: 'JARVIS systems temporarily unavailable. Please check the backend connection, Captain.',
        timestamp: new Date().toISOString(),
      }])
    } finally {
      setLoading(false)
    }
  }

  const toggleVoiceInput = () => {
    if (listening) {
      voiceService.stopListening()
      setListening(false)
    } else {
      setListening(true)
      voiceService.startListening({
        continuous: false,
        onResult: (transcript) => {
          setInput(transcript)
          setListening(false)
          setTimeout(() => send(transcript), 200)
        },
        onEnd: () => setListening(false),
      })
    }
  }

  return (
    <div className="flex flex-col h-full p-6 gap-4">
      {/* Provider selector */}
      <div className="flex items-center gap-3">
        <span className="text-xs text-white/40">AI Provider:</span>
        <div className="relative">
          <select
            value={provider}
            onChange={(e) => setProvider(e.target.value)}
            className="appearance-none bg-white/[0.04] border border-white/[0.10] rounded-lg
                       pl-3 pr-8 py-1.5 text-xs text-white/70 cursor-pointer outline-none
                       hover:border-white/20 focus:border-jarvis-blue/50"
          >
            {PROVIDERS.map((p) => (
              <option key={p.value} value={p.value} className="bg-gray-900">{p.label}</option>
            ))}
          </select>
          <ChevronDown size={12} className="absolute right-2 top-1/2 -translate-y-1/2 text-white/30 pointer-events-none" />
        </div>
        <span className="text-[10px] text-white/25 font-mono ml-auto">session: {sessionId.slice(-12)}</span>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto no-scrollbar space-y-4 glass p-4 rounded-xl border border-white/[0.06]">
        {messages.map((m) => <Message key={m.id} msg={m} />)}
        {loading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex gap-3"
          >
            <div className="w-8 h-8 rounded-lg bg-jarvis-blue/15 border border-jarvis-blue/25
                            flex items-center justify-center">
              <Bot size={14} className="text-jarvis-blue" />
            </div>
            <div className="glass px-4 py-3 rounded-xl border border-white/[0.07]">
              <div className="flex gap-1 items-center">
                {[0,1,2].map((i) => (
                  <motion.span
                    key={i}
                    animate={{ y: [0, -4, 0] }}
                    transition={{ delay: i * 0.15, repeat: Infinity, duration: 0.6 }}
                    className="w-1.5 h-1.5 rounded-full bg-jarvis-blue/60"
                  />
                ))}
                <span className="ml-2 text-xs text-white/30 font-mono">JARVIS thinking…</span>
              </div>
            </div>
          </motion.div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div className="flex gap-3">
        <div className="flex-1 glass flex items-center gap-2 px-4 py-3 rounded-xl border border-white/[0.10]
                        focus-within:border-jarvis-blue/40 transition-colors">
          <input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && send()}
            placeholder="Ask JARVIS anything…"
            className="flex-1 bg-transparent text-sm text-white/80 placeholder:text-white/25 outline-none"
          />
          {input && (
            <button onClick={() => setInput('')} className="text-white/25 hover:text-white/50 text-xs">✕</button>
          )}
        </div>

        <button
          onClick={toggleVoiceInput}
          className={`p-3 rounded-xl border transition-all ${
            listening
              ? 'bg-jarvis-blue/20 border-jarvis-blue/50 text-jarvis-blue'
              : 'glass border-white/[0.10] text-white/40 hover:text-white/70'
          }`}
        >
          {listening
            ? <motion.span animate={{ scale: [1,1.2,1] }} transition={{ repeat: Infinity, duration: 0.7 }}>
                <Mic size={18} />
              </motion.span>
            : <MicOff size={18} />}
        </button>

        <motion.button
          whileTap={{ scale: 0.95 }}
          onClick={() => send()}
          disabled={!input.trim() || loading}
          className="px-5 py-3 rounded-xl bg-jarvis-blue/15 border border-jarvis-blue/30
                     text-jarvis-blue transition-all hover:bg-jarvis-blue/25 hover:border-jarvis-blue/50
                     disabled:opacity-30 disabled:cursor-not-allowed flex items-center gap-2"
        >
          {loading ? <Loader size={16} className="animate-spin" /> : <Send size={16} />}
        </motion.button>
      </div>
    </div>
  )
}
