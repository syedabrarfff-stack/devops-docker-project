import React, { useState, useRef, useCallback, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

// ── Colour maps ──────────────────────────────────────────────────────────────
const ORIGIN_STYLE = {
  USA:    { bg: 'bg-blue-500/10',   border: 'border-blue-500/30',   text: 'text-blue-300',   glow: 'shadow-blue-500/20'   },
  CHINA:  { bg: 'bg-red-500/10',    border: 'border-red-500/30',    text: 'text-red-300',    glow: 'shadow-red-500/20'    },
  EUROPE: { bg: 'bg-indigo-500/10', border: 'border-indigo-500/30', text: 'text-indigo-300', glow: 'shadow-indigo-500/20' },
  GLOBAL: { bg: 'bg-emerald-500/10',border: 'border-emerald-500/30',text: 'text-emerald-300',glow: 'shadow-emerald-500/20'},
}

const ORIGIN_LABEL = {
  USA:    '🇺🇸 United States',
  CHINA:  '🇨🇳 China',
  EUROPE: '🇫🇷 Europe',
  GLOBAL: '🌐 Global',
}

// ── Static swarm definition (mirrors backend SWARM_MEMBERS) ──────────────────
const SWARM = [
  { id:'claude-sonnet-bedrock', name:'Claude Sonnet (AWS)',  origin:'USA',    flag:'🇺🇸', lab:'Anthropic / AWS',       role:'Cloud Architect' },
  { id:'gpt-4o',                name:'GPT-4o',               origin:'USA',    flag:'🇺🇸', lab:'OpenAI',                role:'Market Analyst' },
  { id:'llama-4-maverick',      name:'Llama 4 Maverick',     origin:'USA',    flag:'🇺🇸', lab:'Meta / NVIDIA NIM',     role:'Open-Source Powerhouse' },
  { id:'llama-4-scout',         name:'Llama 4 Scout',        origin:'USA',    flag:'🇺🇸', lab:'Meta / NVIDIA NIM',     role:'Speed Intelligence' },
  { id:'llama-3-3-groq',        name:'Llama 3.3 70B',        origin:'USA',    flag:'🇺🇸', lab:'Meta / Groq',           role:'Ultra-Fast Reasoning' },
  { id:'llama-3-3-nim',         name:'Llama 3.3 (NIM)',      origin:'USA',    flag:'🇺🇸', lab:'Meta / NVIDIA NIM',     role:'GPU-Accelerated' },
  { id:'deepseek-v4-pro',       name:'DeepSeek V4 Pro',      origin:'CHINA',  flag:'🇨🇳', lab:'DeepSeek / NIM',        role:'Deep Reasoning' },
  { id:'deepseek-v4-flash',     name:'DeepSeek V4 Flash',    origin:'CHINA',  flag:'🇨🇳', lab:'DeepSeek / NIM',        role:'Fast Intelligence' },
  { id:'kimi-k2',               name:'Kimi K2.6',            origin:'CHINA',  flag:'🇨🇳', lab:'MoonshotAI / NIM',      role:'Long-Context' },
  { id:'qwen-25-coder',         name:'Qwen 2.5 Coder',       origin:'CHINA',  flag:'🇨🇳', lab:'Alibaba / NIM',         role:'Code Specialist' },
  { id:'minimax-m3',            name:'MiniMax M3',           origin:'CHINA',  flag:'🇨🇳', lab:'MiniMax / NIM',         role:'Creative AI' },
  { id:'glm-4',                 name:'GLM-4',                origin:'CHINA',  flag:'🇨🇳', lab:'ZhipuAI (Tsinghua)',    role:'Academic Reasoning' },
  { id:'mistral-medium-nim',    name:'Mistral Medium 3',     origin:'EUROPE', flag:'🇫🇷', lab:'Mistral / NIM',         role:'European AI' },
  { id:'mistral-large',         name:'Mistral Large',        origin:'EUROPE', flag:'🇫🇷', lab:'Mistral AI',            role:'Risk Analyst' },
  { id:'gemini-pro',            name:'Gemini 1.5 Pro',       origin:'GLOBAL', flag:'🌐', lab:'Google DeepMind',        role:'Research & Knowledge' },
]
const SYNTHESIZER = { id:'claude-opus', name:'Claude Opus 4', lab:'Anthropic', role:'Supreme Synthesizer', flag:'🇺🇸' }

// ── Utility ──────────────────────────────────────────────────────────────────
function sse(text) {
  return text.split('\n').map((l, i) => <span key={i}>{l}<br/></span>)
}
function msLabel(ms) {
  return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`
}

// ── Components ───────────────────────────────────────────────────────────────

function ModelCard({ member, status }) {
  const s = ORIGIN_STYLE[member.origin] || ORIGIN_STYLE.GLOBAL
  const idle    = status === 'idle'
  const pinging = status === 'pinging'
  const done    = status === 'done'
  const failed  = status === 'failed'

  return (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.92 }}
      animate={{ opacity: 1, scale: 1 }}
      className={`
        relative rounded-xl border p-3 transition-all duration-300
        ${s.bg} ${s.border}
        ${done    ? `shadow-lg ${s.glow}` : ''}
        ${pinging ? 'animate-pulse' : ''}
        ${failed  ? 'opacity-40' : ''}
      `}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-1.5 mb-0.5">
            <span className="text-sm leading-none">{member.flag}</span>
            <span className={`text-xs font-bold truncate ${s.text}`}>{member.name}</span>
          </div>
          <p className="text-[10px] text-white/40 truncate">{member.role}</p>
        </div>
        <div className="shrink-0">
          {idle     && <div className="w-2 h-2 rounded-full bg-white/20 mt-0.5" />}
          {pinging  && <div className="w-2 h-2 rounded-full bg-yellow-400 animate-ping mt-0.5" />}
          {done     && <span className="text-green-400 text-sm">✓</span>}
          {failed   && <span className="text-red-400 text-sm">✗</span>}
        </div>
      </div>
      {status?.elapsed_ms && (
        <p className="text-[10px] text-white/30 mt-1">{msLabel(status.elapsed_ms)}</p>
      )}
    </motion.div>
  )
}

function RegionGroup({ origin, members, statuses }) {
  const s = ORIGIN_STYLE[origin] || ORIGIN_STYLE.GLOBAL
  const doneCount = members.filter(m => statuses[m.id] === 'done').length
  const total = members.length

  return (
    <div className={`rounded-2xl border p-4 ${s.bg} ${s.border}`}>
      <div className="flex items-center justify-between mb-3">
        <p className={`text-xs font-bold uppercase tracking-widest ${s.text}`}>
          {ORIGIN_LABEL[origin]}
        </p>
        <span className={`text-xs font-mono ${s.text}`}>{doneCount}/{total}</span>
      </div>
      <div className="grid grid-cols-2 gap-2">
        {members.map(m => (
          <ModelCard key={m.id} member={m} status={
            statuses[m.id] === 'done'   ? { ...statuses[m.id + '_meta'], ...{} } :
            statuses[m.id] === 'failed' ? 'failed' :
            statuses[m.id] === 'pinging' ? 'pinging' : 'idle'
          } />
        ))}
      </div>
    </div>
  )
}

function VerdictPanel({ verdict, active, total, elapsed }) {
  const sections = verdict.split(/^## /m).filter(Boolean)
  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-amber-500/30 bg-amber-500/5 p-6"
    >
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-bold text-amber-300">OMEGA VERDICT</h3>
          <p className="text-xs text-white/40">{active}/{total} models · {msLabel(elapsed)}</p>
        </div>
        <div className="text-2xl">⚡</div>
      </div>
      <div className="space-y-4">
        {sections.map((sec, i) => {
          const [heading, ...body] = sec.split('\n')
          return (
            <div key={i}>
              <p className="text-xs font-bold uppercase tracking-widest text-amber-400/70 mb-1">
                {heading.trim()}
              </p>
              <div className="text-sm text-white/80 leading-relaxed whitespace-pre-wrap">
                {body.join('\n').trim()}
              </div>
            </div>
          )
        })}
      </div>
    </motion.div>
  )
}

function ProgressBar({ done, total }) {
  const pct = total > 0 ? Math.round((done / total) * 100) : 0
  return (
    <div className="w-full">
      <div className="flex justify-between text-xs text-white/40 mb-1">
        <span>Global swarm responding</span>
        <span>{done}/{total} · {pct}%</span>
      </div>
      <div className="h-1.5 rounded-full bg-white/10 overflow-hidden">
        <motion.div
          className="h-full rounded-full bg-gradient-to-r from-blue-500 via-red-500 to-amber-500"
          animate={{ width: `${pct}%` }}
          transition={{ ease: 'linear' }}
        />
      </div>
    </div>
  )
}

// ── Quick-fire prompts ────────────────────────────────────────────────────────
const QUICK = [
  { label: 'AI market 2025', q: 'What are the top 3 AI market opportunities Aliyar Solutions should chase in 2025?' },
  { label: 'Price our AI stack', q: 'Recommend a pricing strategy for Aliyar Solutions AI automation retainer services targeting global SMBs.' },
  { label: 'Outcompete rivals', q: 'What competitive advantage should Aliyar Solutions build to outcompete local and global AI agencies?' },
  { label: 'Scale to $1M', q: 'Design a 90-day action plan for Aliyar Solutions to reach $1M annual recurring revenue.' },
]

// ── Main dashboard ────────────────────────────────────────────────────────────
export default function OmegaDashboard() {
  const [question, setQuestion]   = useState('')
  const [running, setRunning]     = useState(false)
  const [statuses, setStatuses]   = useState({}) // id → 'pinging'|'done'|'failed'
  const [metaMap, setMetaMap]     = useState({}) // id → event data
  const [progress, setProgress]   = useState({ done: 0, total: 0 })
  const [verdict, setVerdict]     = useState(null)
  const [elapsed, setElapsed]     = useState(0)
  const [phase, setPhase]         = useState('idle') // idle|running|synthesizing|done|error
  const [errorMsg, setErrorMsg]   = useState(null)
  const startTs = useRef(0)
  const elapsedInterval = useRef(null)

  // Group members by origin
  const byOrigin = {}
  for (const m of SWARM) {
    if (!byOrigin[m.origin]) byOrigin[m.origin] = []
    byOrigin[m.origin].push(m)
  }
  const ORIGINS = ['USA', 'CHINA', 'EUROPE', 'GLOBAL']

  const reset = useCallback(() => {
    setStatuses({})
    setMetaMap({})
    setProgress({ done: 0, total: 0 })
    setVerdict(null)
    setElapsed(0)
    setPhase('idle')
    setErrorMsg(null)
    clearInterval(elapsedInterval.current)
  }, [])

  const ignite = useCallback(async (q) => {
    const qFinal = (q || question).trim()
    if (!qFinal || running) return
    reset()
    setRunning(true)
    setPhase('running')
    startTs.current = Date.now()

    // Mark all as pinging
    const initStatuses = {}
    for (const m of SWARM) initStatuses[m.id] = 'pinging'
    setStatuses(initStatuses)
    setProgress({ done: 0, total: SWARM.length })

    // Tick elapsed timer
    elapsedInterval.current = setInterval(() => {
      setElapsed(Date.now() - startTs.current)
    }, 200)

    try {
      const resp = await fetch('/api/v1/omega/ignite', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'text/event-stream' },
        body: JSON.stringify({ question: qFinal }),
      })

      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`)
      }

      const reader = resp.body.getReader()
      const decoder = new TextDecoder()
      let buf = ''

      while (true) {
        const { done: streamDone, value } = await reader.read()
        if (streamDone) break
        buf += decoder.decode(value, { stream: true })

        const lines = buf.split('\n')
        buf = lines.pop() // keep incomplete line

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          let event
          try { event = JSON.parse(line.slice(6)) } catch { continue }

          if (event.type === 'member_done') {
            setStatuses(prev => ({ ...prev, [event.id]: event.success ? 'done' : 'failed' }))
            setMetaMap(prev => ({ ...prev, [event.id]: event }))
            setProgress({ done: event.done, total: event.total })
          } else if (event.type === 'synthesis_start') {
            setPhase('synthesizing')
            setStatuses(prev => {
              // mark remaining pinging ones as failed
              const next = { ...prev }
              for (const m of SWARM) {
                if (next[m.id] === 'pinging') next[m.id] = 'failed'
              }
              return next
            })
          } else if (event.type === 'result') {
            clearInterval(elapsedInterval.current)
            setElapsed(Date.now() - startTs.current)
            setVerdict(event.verdict)
            setPhase('done')
          } else if (event.type === 'error') {
            setErrorMsg(event.message)
            setPhase('error')
          } else if (event.type === 'done') {
            setPhase(p => p === 'synthesizing' ? 'error' : p)
          }
        }
      }
    } catch (err) {
      setErrorMsg(err.message)
      setPhase('error')
      clearInterval(elapsedInterval.current)
    } finally {
      setRunning(false)
    }
  }, [question, running, reset])

  useEffect(() => () => clearInterval(elapsedInterval.current), [])

  const PHASE_LABEL = {
    idle:        null,
    running:     '⚡ Global swarm active — models responding live',
    synthesizing:'🧠 Claude Opus synthesising global intelligence…',
    done:        '✅ OMEGA verdict delivered',
    error:       '⚠ Swarm encountered errors',
  }

  return (
    <div className="min-h-screen bg-[#080c10] text-white p-6 font-sans">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-1">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 via-red-500 to-amber-500 flex items-center justify-center text-sm font-black">
            Ω
          </div>
          <h1 className="text-2xl font-black tracking-tight">JARVIS OMEGA</h1>
          <span className="text-xs font-mono text-white/30 border border-white/10 rounded px-2 py-0.5">
            {SWARM.length} models · 4 continents
          </span>
        </div>
        <p className="text-sm text-white/40 ml-11">
          Global intelligence swarm — US, China, Europe &amp; DeepMind firing in parallel
        </p>
      </div>

      {/* Query bar */}
      <div className="mb-6">
        <div className="flex gap-3 mb-3">
          <input
            className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-white/30 focus:outline-none focus:border-white/25 transition"
            placeholder="Ask the global swarm anything — strategy, pricing, market analysis, technology…"
            value={question}
            onChange={e => setQuestion(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !e.shiftKey && ignite()}
            disabled={running}
          />
          <button
            onClick={() => running ? null : ignite()}
            disabled={running || !question.trim()}
            className={`
              px-6 py-3 rounded-xl text-sm font-bold transition-all
              ${running
                ? 'bg-amber-500/20 text-amber-300 cursor-not-allowed'
                : 'bg-gradient-to-r from-blue-600 to-amber-600 hover:from-blue-500 hover:to-amber-500 text-white shadow-xl'
              }
            `}
          >
            {running ? '⚡ Running' : 'Ignite'}
          </button>
        </div>

        {/* Quick prompts */}
        <div className="flex flex-wrap gap-2">
          {QUICK.map(({ label, q }) => (
            <button
              key={label}
              onClick={() => { setQuestion(q); ignite(q) }}
              disabled={running}
              className="text-xs px-3 py-1.5 rounded-lg border border-white/10 bg-white/5 hover:bg-white/10 text-white/60 hover:text-white/90 transition disabled:opacity-40"
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Phase status bar */}
      <AnimatePresence>
        {phase !== 'idle' && (
          <motion.div
            key="phasebar"
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="mb-5"
          >
            {phase !== 'done' && (
              <div className="mb-3">
                <ProgressBar done={progress.done} total={progress.total} />
              </div>
            )}
            {PHASE_LABEL[phase] && (
              <p className="text-xs text-white/50">{PHASE_LABEL[phase]}</p>
            )}
            {phase === 'error' && errorMsg && (
              <p className="text-xs text-red-400 mt-1">Error: {errorMsg}</p>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Synthesizer indicator */}
      <AnimatePresence>
        {phase === 'synthesizing' && (
          <motion.div
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0 }}
            className="mb-5 rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 flex items-center gap-3"
          >
            <div className="w-8 h-8 rounded-full bg-amber-500/20 flex items-center justify-center animate-pulse text-amber-400 font-black text-sm">
              Ω
            </div>
            <div>
              <p className="text-sm font-bold text-amber-300">
                {SYNTHESIZER.flag} {SYNTHESIZER.name} — {SYNTHESIZER.role}
              </p>
              <p className="text-xs text-white/40">
                Processing {progress.done}/{progress.total} global intelligence inputs…
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Verdict */}
      <AnimatePresence>
        {verdict && phase === 'done' && (
          <div className="mb-6">
            <VerdictPanel verdict={verdict} active={progress.done} total={progress.total} elapsed={elapsed} />
          </div>
        )}
      </AnimatePresence>

      {/* World grid */}
      {phase !== 'idle' && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
          {ORIGINS.map(origin => {
            const members = byOrigin[origin] || []
            if (!members.length) return null

            // Build status map for this group
            const groupStatuses = {}
            for (const m of members) {
              const st = statuses[m.id]
              if (st === 'done') {
                groupStatuses[m.id] = { ...metaMap[m.id] }
              } else {
                groupStatuses[m.id] = st || 'idle'
              }
            }

            const s = ORIGIN_STYLE[origin] || ORIGIN_STYLE.GLOBAL
            const doneCount = members.filter(m => statuses[m.id] === 'done').length

            return (
              <div key={origin} className={`rounded-2xl border p-4 ${s.bg} ${s.border}`}>
                <div className="flex items-center justify-between mb-3">
                  <p className={`text-xs font-bold uppercase tracking-widest ${s.text}`}>
                    {ORIGIN_LABEL[origin]}
                  </p>
                  <span className={`text-xs font-mono ${s.text}`}>{doneCount}/{members.length}</span>
                </div>
                <div className="space-y-2">
                  {members.map(m => {
                    const st = statuses[m.id]
                    const meta = metaMap[m.id]
                    const isDone    = st === 'done'
                    const isFailed  = st === 'failed'
                    const isPinging = st === 'pinging'

                    return (
                      <motion.div
                        key={m.id}
                        layout
                        className={`
                          relative rounded-xl border p-2.5 transition-all duration-300
                          ${s.bg} ${s.border}
                          ${isDone    ? `shadow-md` : ''}
                          ${isFailed  ? 'opacity-35' : ''}
                        `}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <div className="min-w-0">
                            <div className="flex items-center gap-1.5">
                              <span className="text-xs">{m.flag}</span>
                              <span className={`text-[11px] font-semibold truncate ${isDone ? 'text-white' : 'text-white/50'}`}>
                                {m.name}
                              </span>
                            </div>
                            <p className="text-[9px] text-white/30 truncate mt-0.5">{m.role}</p>
                          </div>
                          <div className="shrink-0 flex items-center gap-1">
                            {meta?.elapsed_ms && isDone && (
                              <span className="text-[9px] text-white/25 font-mono">{msLabel(meta.elapsed_ms)}</span>
                            )}
                            {isPinging && <span className="w-1.5 h-1.5 rounded-full bg-yellow-400 animate-ping inline-block" />}
                            {isDone    && <span className={`text-xs font-bold ${s.text}`}>✓</span>}
                            {isFailed  && <span className="text-xs text-red-400">✗</span>}
                          </div>
                        </div>
                      </motion.div>
                    )
                  })}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Idle state */}
      {phase === 'idle' && (
        <div className="mt-12 text-center">
          <div className="inline-flex flex-col items-center gap-4">
            <div className="relative">
              <div className="w-20 h-20 rounded-full bg-gradient-to-br from-blue-600/20 via-red-600/20 to-amber-600/20 flex items-center justify-center text-4xl font-black text-white/20 border border-white/10">
                Ω
              </div>
              <div className="absolute inset-0 rounded-full bg-gradient-to-br from-blue-500/5 to-amber-500/5 blur-xl" />
            </div>
            <div>
              <p className="text-white/30 text-sm font-semibold">
                {SWARM.length} models ready · {Object.keys(byOrigin).length} continents · 1 verdict
              </p>
              <p className="text-white/15 text-xs mt-1">
                🇺🇸 Anthropic · OpenAI · Meta  |  🇨🇳 DeepSeek · Kimi · Qwen · MiniMax  |  🇫🇷 Mistral  |  🌐 Google
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
