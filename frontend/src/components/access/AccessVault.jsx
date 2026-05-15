import React, { useEffect, useMemo, useState } from 'react'
import { CheckCircle2, KeyRound, Lock, RefreshCw, Save, Trash2, XCircle } from 'lucide-react'
import { bootstrapCredentials, getCredentialStatus, revokeCredential, saveCredential } from '../../services/api'

const shell = 'glass rounded-xl border border-white/[0.07] bg-white/[0.03]'
const input = 'w-full rounded-lg border border-white/10 bg-white/[0.05] px-3 py-2 text-sm text-white outline-none placeholder:text-white/25 focus:border-jarvis-blue/50'

function CredentialRow({ item, onSave, onRevoke, saving }) {
  const [value, setValue] = useState('')
  return (
    <div className="rounded-lg border border-white/[0.06] bg-white/[0.03] p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <p className="text-sm font-semibold text-white">{item.label}</p>
            {item.configured
              ? <span className="inline-flex items-center gap-1 rounded-full border border-emerald-400/20 bg-emerald-400/10 px-2 py-0.5 text-[11px] text-emerald-300"><CheckCircle2 size={11} /> Connected</span>
              : <span className="inline-flex items-center gap-1 rounded-full border border-amber-400/20 bg-amber-400/10 px-2 py-0.5 text-[11px] text-amber-300"><XCircle size={11} /> Missing</span>}
          </div>
          <p className="mt-1 text-xs text-white/40">{item.description}</p>
          <p className="mt-2 text-[11px] text-white/25">Unlocks: {item.required_for.join(', ')}</p>
          {item.masked_value && <p className="mt-1 text-[11px] text-jarvis-blue">Stored: {item.masked_value}</p>}
        </div>
        <span className="rounded-full border border-white/10 px-2 py-1 text-[11px] text-white/35">{item.category}</span>
      </div>
      <div className="mt-4 flex flex-col gap-3 md:flex-row">
        <input
          className={input}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          type={item.secret ? 'password' : 'text'}
          placeholder={item.configured ? 'Paste a new value to replace current access' : `Paste ${item.key}`}
        />
        <button
          onClick={() => { onSave(item.key, value); setValue('') }}
          disabled={!value.trim() || saving}
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-jarvis-blue px-4 py-2 text-sm font-semibold text-black disabled:opacity-40"
        >
          <Save size={14} /> Save
        </button>
        {item.configured && (
          <button
            onClick={() => onRevoke(item.key)}
            disabled={saving}
            className="inline-flex items-center justify-center gap-2 rounded-lg border border-red-400/20 bg-red-400/10 px-4 py-2 text-sm text-red-200 disabled:opacity-40"
          >
            <Trash2 size={14} /> Revoke
          </button>
        )}
      </div>
    </div>
  )
}

export default function AccessVault() {
  const [credentials, setCredentials] = useState([])
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [filter, setFilter] = useState('All')

  const load = async () => {
    const data = await getCredentialStatus()
    setCredentials(data.credentials || [])
  }

  useEffect(() => { load() }, [])

  const categories = useMemo(() => ['All', ...Array.from(new Set(credentials.map(c => c.category)))], [credentials])
  const visible = filter === 'All' ? credentials : credentials.filter(c => c.category === filter)

  const handleSave = async (key, value) => {
    setSaving(true)
    setMessage('')
    try {
      await saveCredential({ key, value })
      setMessage(`${key} stored securely. Jarvis can use it without asking broadly again.`)
      await load()
    } catch (err) {
      setMessage(err.response?.data?.detail || err.message)
    }
    setSaving(false)
  }

  const handleRevoke = async (key) => {
    setSaving(true)
    setMessage('')
    try {
      await revokeCredential(key)
      setMessage(`${key} revoked.`)
      await load()
    } catch (err) {
      setMessage(err.response?.data?.detail || err.message)
    }
    setSaving(false)
  }

  const handleBootstrap = async () => {
    setSaving(true)
    setMessage('')
    try {
      const data = await bootstrapCredentials()
      setMessage(`Jarvis imported ${data.imported?.length || 0} existing server credentials. Remaining missing: ${(data.skipped || []).join(', ') || 'none'}.`)
      await load()
    } catch (err) {
      setMessage(err.response?.data?.detail || err.message)
    }
    setSaving(false)
  }

  const configured = credentials.filter(c => c.configured).length

  return (
    <div className="h-full overflow-y-auto p-6 space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Access Vault</h1>
          <p className="mt-1 text-sm text-white/45">Give Jarvis access once. Secrets are encrypted server-side and never displayed back.</p>
        </div>
        <button onClick={load} className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/[0.04] px-3 py-2 text-sm text-white/65 hover:text-white">
          <RefreshCw size={15} /> Refresh
        </button>
        <button onClick={handleBootstrap} disabled={saving} className="inline-flex items-center gap-2 rounded-lg bg-jarvis-blue px-3 py-2 text-sm font-semibold text-black disabled:opacity-50">
          <KeyRound size={15} /> Let Jarvis Import Existing Access
        </button>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className={`${shell} p-4`}>
          <div className="flex items-center gap-2 text-sm font-semibold text-white"><Lock size={16} className="text-jarvis-blue" /> Secure Store</div>
          <p className="mt-3 text-2xl font-bold text-white">{configured}/{credentials.length}</p>
          <p className="text-xs text-white/35">credentials configured</p>
        </div>
        <div className={`${shell} p-4 md:col-span-2`}>
          <div className="flex items-center gap-2 text-sm font-semibold text-white"><KeyRound size={16} className="text-jarvis-blue" /> Standing Permission</div>
          <p className="mt-3 text-sm leading-relaxed text-white/55">Jarvis may auto-run safe work: research, discovery, enrichment, CRM updates, diagnostics, scoring, drafts, and n8n workflow checks. External sending, payments, deletes, credential changes, contracts, and high-risk production actions still require Captain approval.</p>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {categories.map(category => (
          <button
            key={category}
            onClick={() => setFilter(category)}
            className={`rounded-lg border px-3 py-1.5 text-xs ${filter === category ? 'border-jarvis-blue/40 bg-jarvis-blue/15 text-jarvis-blue' : 'border-white/10 bg-white/[0.03] text-white/45 hover:text-white/70'}`}
          >
            {category}
          </button>
        ))}
      </div>

      {message && (
        <div className={`${shell} p-3 text-sm ${message.toLowerCase().includes('error') || message.toLowerCase().includes('unsupported') ? 'text-red-200' : 'text-emerald-200'}`}>
          {message}
        </div>
      )}

      <div className="space-y-3">
        {visible.map(item => (
          <CredentialRow key={item.key} item={item} onSave={handleSave} onRevoke={handleRevoke} saving={saving} />
        ))}
      </div>
    </div>
  )
}
