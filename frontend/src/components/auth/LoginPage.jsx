import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { AlertTriangle, Loader2, Lock, Shield, User, Zap } from 'lucide-react'

const CAPTAIN_USER = 'captain'
const CAPTAIN_PASS = 'nuhabrar7'

export default function LoginPage({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [blink, setBlink] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)

    await new Promise((r) => setTimeout(r, 600))

    if (
      username.trim().toLowerCase() === CAPTAIN_USER &&
      password === CAPTAIN_PASS
    ) {
      localStorage.setItem('jarvis_auth', JSON.stringify({ user: 'captain', at: Date.now() }))
      onLogin()
    } else {
      setBlink(true)
      setTimeout(() => setBlink(false), 400)
      setError('Access denied. Verify your credentials.')
    }
    setLoading(false)
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#03080f] relative overflow-hidden">
      {/* Ambient glows */}
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute -top-40 left-1/2 -translate-x-1/2 h-[40rem] w-[40rem] rounded-full bg-[#0057FF]/10 blur-[120px]" />
        <div className="absolute bottom-0 left-1/4 h-[30rem] w-[30rem] rounded-full bg-[#00C8FF]/6 blur-[100px]" />
        <div className="absolute top-1/3 right-0 h-[20rem] w-[20rem] rounded-full bg-[#FFB700]/5 blur-[90px]" />
      </div>

      {/* Grid overlay */}
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage: 'linear-gradient(rgba(0,200,255,1) 1px, transparent 1px), linear-gradient(90deg, rgba(0,200,255,1) 1px, transparent 1px)',
          backgroundSize: '64px 64px',
        }}
      />

      {/* Scanline */}
      <div className="pointer-events-none absolute inset-0 scanline" />

      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className={`relative z-10 w-full max-w-md px-4 transition-all ${blink ? 'scale-[0.99]' : ''}`}
      >
        {/* Header logo */}
        <div className="mb-8 flex flex-col items-center gap-4 text-center">
          <div className="relative">
            <div className="h-20 w-20 rounded-2xl border border-[#0057FF]/40 bg-gradient-to-br from-[#0057FF]/20 to-[#00C8FF]/10 flex items-center justify-center shadow-[0_0_40px_rgba(0,87,255,0.3)]">
              <Zap size={36} className="text-[#00C8FF]" />
            </div>
            <span className="absolute -top-1 -right-1 h-3 w-3 rounded-full bg-green-400 shadow-[0_0_8px_rgba(74,222,128,0.8)] animate-pulse" />
          </div>
          <div>
            <p className="text-[10px] font-bold tracking-[0.45em] text-[#00C8FF]/70 uppercase">Aliyar Solutions</p>
            <h1 className="mt-1 text-2xl font-black tracking-[0.08em] text-white">JARVIS</h1>
            <p className="text-xs uppercase tracking-[0.3em] text-white/40 mt-0.5">Command Center</p>
          </div>
        </div>

        {/* Login card */}
        <div className="rounded-2xl border border-white/10 bg-white/[0.04] backdrop-blur-xl shadow-2xl shadow-black/60 p-8">
          <div className="mb-6 flex items-center gap-2">
            <Shield size={14} className="text-[#00C8FF]" />
            <p className="text-xs uppercase tracking-[0.22em] text-white/50">Secure Access</p>
          </div>

          {error && (
            <motion.div
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              className="mb-5 flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3"
            >
              <AlertTriangle size={14} className="text-red-300 shrink-0" />
              <p className="text-xs text-red-200">{error}</p>
            </motion.div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="mb-2 block text-[11px] uppercase tracking-[0.2em] text-white/40">
                Identity
              </label>
              <div className="relative">
                <User size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-white/30" />
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="Username"
                  autoComplete="username"
                  autoFocus
                  required
                  className="w-full rounded-xl border border-white/10 bg-white/[0.06] pl-10 pr-4 py-3 text-sm text-white placeholder-white/20 outline-none transition focus:border-[#00C8FF]/50 focus:ring-1 focus:ring-[#00C8FF]/30"
                />
              </div>
            </div>

            <div>
              <label className="mb-2 block text-[11px] uppercase tracking-[0.2em] text-white/40">
                Passphrase
              </label>
              <div className="relative">
                <Lock size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-white/30" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  autoComplete="current-password"
                  required
                  className="w-full rounded-xl border border-white/10 bg-white/[0.06] pl-10 pr-4 py-3 text-sm text-white placeholder-white/20 outline-none transition focus:border-[#00C8FF]/50 focus:ring-1 focus:ring-[#00C8FF]/30"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="mt-2 w-full rounded-xl bg-gradient-to-r from-[#0057FF] to-[#00C8FF] py-3.5 text-sm font-bold tracking-[0.1em] text-white shadow-[0_4px_24px_rgba(0,87,255,0.4)] transition hover:shadow-[0_4px_32px_rgba(0,200,255,0.5)] disabled:opacity-60 flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  Authenticating...
                </>
              ) : (
                'Enter Command Center'
              )}
            </button>
          </form>

          <p className="mt-6 text-center text-[11px] text-white/20">
            Restricted system — authorized personnel only
          </p>
        </div>

        {/* Footer */}
        <p className="mt-5 text-center text-[10px] tracking-[0.18em] text-white/20 uppercase">
          JARVIS v9 · Aliyar Solutions · {new Date().getFullYear()}
        </p>
      </motion.div>
    </div>
  )
}
