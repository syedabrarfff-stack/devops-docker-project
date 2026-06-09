import React, { useEffect, useState } from 'react'
import { Loader2, MessageCircle, Radio, RefreshCw, Send, ShieldCheck } from 'lucide-react'
import { api } from '../../services/api'

function StatusPill({ ok, label }) {
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-bold ${
      ok
        ? 'border-green-300/30 bg-green-400/10 text-green-300'
        : 'border-amber-300/30 bg-amber-400/10 text-amber-200'
    }`}>
      {label}
    </span>
  )
}

function Panel({ title, subtitle, icon: Icon, children, action }) {
  return (
    <section className="glass p-5">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className="rounded-xl border border-white/10 bg-white/5 p-2 text-jarvis-cyan">
            <Icon size={16} />
          </div>
          <div>
            <h2 className="text-sm font-bold text-white">{title}</h2>
            <p className="mt-1 text-xs leading-5 text-gray-500">{subtitle}</p>
          </div>
        </div>
        {action}
      </div>
      {children}
    </section>
  )
}

function TransportCard({ title, data, children }) {
  const connected = !!data?.connected
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.18em] text-white/35">{title}</p>
          <p className="mt-2 text-lg font-black text-white">{data?.identity || data?.from_email || data?.instance || 'Not configured'}</p>
        </div>
        <StatusPill ok={connected} label={connected ? 'LIVE' : 'BLOCKED'} />
      </div>
      <p className="mt-3 text-xs leading-5 text-white/60">
        {data?.required_action || data?.human_message || data?.blocker_code || 'Transport status is being checked.'}
      </p>
      {children}
    </div>
  )
}

export default function CommunicationHub() {
  const [status, setStatus] = useState(null)
  const [events, setEvents] = useState([])
  const [qr, setQr] = useState(null)
  const [pairingNumber, setPairingNumber] = useState('')
  const [number, setNumber] = useState('')
  const [text, setText] = useState('AIONX transport layer online.')
  const [busy, setBusy] = useState(false)
  const [lastAction, setLastAction] = useState(null)
  const [notice, setNotice] = useState(null)

  const errorText = (error, fallback) => (
    error?.response?.data?.detail
    || error?.response?.data?.message
    || error?.message
    || fallback
  )

  async function load() {
    setBusy(true)
    try {
      const [s, e] = await Promise.all([
        api.get('/api/v1/communication/status').then((r) => r.data),
        api.get('/api/v1/communication/events', { params: { limit: 25 } }).then((r) => r.data),
      ])
      setStatus(s)
      setEvents(e.events || [])
    } catch (error) {
      setNotice({ tone: 'error', text: errorText(error, 'Communication status failed to load.') })
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => { load() }, [])

  async function createInstance() {
    setBusy(true)
    try {
      const result = await api.post('/api/v1/communication/whatsapp/instance').then((r) => r.data)
      setLastAction(result)
      setNotice({ tone: 'success', text: result?.message || 'WhatsApp instance request completed.' })
      await load()
    } catch (error) {
      const text = errorText(error, 'WhatsApp instance creation failed.')
      setLastAction({ error: text })
      setNotice({ tone: 'error', text })
    } finally {
      setBusy(false)
    }
  }

  async function getQr() {
    setBusy(true)
    try {
      const params = pairingNumber ? { number: pairingNumber } : undefined
      const result = await api.get('/api/v1/communication/whatsapp/qr', { params }).then((r) => r.data)
      setQr(result)
      setLastAction(result)
      setNotice({ tone: 'success', text: result?.required_action || 'WhatsApp pairing payload retrieved.' })
    } catch (error) {
      const text = errorText(error, 'WhatsApp QR retrieval failed.')
      setLastAction({ error: text })
      setNotice({ tone: 'error', text })
    } finally {
      setBusy(false)
    }
  }

  async function configureWebhook() {
    setBusy(true)
    try {
      const result = await api.post('/api/v1/communication/whatsapp/webhook/configure').then((r) => r.data)
      setLastAction(result)
      setNotice({ tone: 'success', text: result?.message || 'WhatsApp webhook configuration completed.' })
      await load()
    } catch (error) {
      const text = errorText(error, 'WhatsApp webhook configuration failed.')
      setLastAction({ error: text })
      setNotice({ tone: 'error', text })
    } finally {
      setBusy(false)
    }
  }

  async function sendTest() {
    if (!number || !text) return
    setBusy(true)
    try {
      const result = await api.post('/api/v1/communication/whatsapp/send-text', { number, text }).then((r) => r.data)
      setLastAction(result)
      setNotice({ tone: 'success', text: result?.message || 'WhatsApp test message sent.' })
      await load()
    } catch (error) {
      const text = errorText(error, 'WhatsApp test message failed.')
      setLastAction({ error: text })
      setNotice({ tone: 'error', text })
    } finally {
      setBusy(false)
    }
  }

  const qrPayload = qr?.data || qr
  const qrImage = qrPayload?.base64 || qrPayload?.qrcode?.base64 || qrPayload?.qrcode || qrPayload?.code
  const pairingCode = qrPayload?.pairingCode

  return (
    <div className="h-full min-h-0 overflow-y-auto p-6 pb-28 space-y-6">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.22em] text-jarvis-cyan/70">Transport Layer</p>
          <h1 className="mt-2 text-3xl font-bold text-white">Communication Hub</h1>
          <p className="mt-2 max-w-3xl text-sm text-gray-400">
            AWS SES and Bahrain WhatsApp Business as native AIONX transport surfaces. The 33-stage pipeline remains unchanged.
          </p>
        </div>
        <button onClick={load} disabled={busy} className="btn-primary inline-flex items-center gap-2">
          {busy ? <Loader2 size={15} className="animate-spin" /> : <RefreshCw size={15} />}
          Refresh
        </button>
      </header>

      {notice && (
        <div className={`rounded-xl border p-3 text-sm ${
          notice.tone === 'error'
            ? 'border-red-300/25 bg-red-500/10 text-red-100'
            : 'border-emerald-300/25 bg-emerald-500/10 text-emerald-100'
        }`}>
          <div className="flex items-start justify-between gap-3">
            <p>{notice.text}</p>
            <button onClick={() => setNotice(null)} className="text-xs opacity-60 hover:opacity-100">Dismiss</button>
          </div>
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <TransportCard title="AWS SES Primary Outreach" data={status?.ses}>
          <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
            <div className="rounded-lg border border-white/10 bg-black/20 p-3">
              <p className="text-white/40">Provider</p>
              <p className="mt-1 font-bold text-white">SES</p>
            </div>
            <div className="rounded-lg border border-white/10 bg-black/20 p-3">
              <p className="text-white/40">Send mode</p>
              <p className="mt-1 font-bold text-white">{status?.ses?.send_mode || 'unknown'}</p>
            </div>
          </div>
        </TransportCard>

        <TransportCard title="Bahrain WhatsApp Business" data={status?.whatsapp}>
          <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
            <div className="rounded-lg border border-white/10 bg-black/20 p-3">
              <p className="text-white/40">Instance</p>
              <p className="mt-1 font-bold text-white">{status?.whatsapp?.instance || 'jarvis-main'}</p>
            </div>
            <div className="rounded-lg border border-white/10 bg-black/20 p-3">
              <p className="text-white/40">Auto reply</p>
              <p className="mt-1 font-bold text-white">{status?.whatsapp?.auto_reply_enabled ? 'enabled' : 'governed draft'}</p>
            </div>
          </div>
        </TransportCard>
      </div>

      <Panel
        title="WhatsApp Pairing Control"
        subtitle="Create the Evolution instance, configure the internal webhook, then scan QR from Bahrain WhatsApp Business Linked Devices."
        icon={MessageCircle}
        action={<StatusPill ok={status?.whatsapp?.connected} label={status?.whatsapp?.connected ? 'PAIRED' : 'PAIRING REQUIRED'} />}
      >
        <div className="flex flex-wrap gap-2">
          <button onClick={createInstance} disabled={busy} className="btn-primary">Create Instance</button>
          <button onClick={configureWebhook} disabled={busy} className="btn-primary">Configure Webhook</button>
          <button onClick={getQr} disabled={busy} className="btn-primary">Retrieve QR</button>
        </div>
        <div className="mt-3 grid gap-3 lg:grid-cols-[320px_auto_1fr]">
          <input
            value={pairingNumber}
            onChange={(e) => setPairingNumber(e.target.value)}
            placeholder="Optional Bahrain WhatsApp number, e.g. 973xxxxxxxx"
            className="rounded-xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-white outline-none focus:border-jarvis-cyan/40"
          />
          <button onClick={getQr} disabled={busy} className="btn-primary">Retrieve Pairing Code</button>
          <p className="self-center text-xs leading-5 text-white/45">
            If QR returns empty, enter the WhatsApp Business number and use the pairing code fallback.
          </p>
        </div>
        {qr?.required_action && (
          <div className="mt-4 rounded-xl border border-amber-300/20 bg-amber-400/10 p-4 text-sm text-amber-100">
            {qr.required_action}
          </div>
        )}
        {pairingCode && (
          <div className="mt-4 rounded-xl border border-green-300/20 bg-green-400/10 p-4">
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-green-200/70">WhatsApp Pairing Code</p>
            <p className="mt-2 select-all text-3xl font-black tracking-[0.2em] text-white">{pairingCode}</p>
          </div>
        )}
        {qrImage && (
          <div className="mt-4 rounded-xl border border-white/10 bg-black/20 p-4">
            <p className="mb-3 text-xs font-bold uppercase tracking-[0.18em] text-white/45">QR Payload</p>
            {String(qrImage).startsWith('data:image') || String(qrImage).startsWith('iVBOR') ? (
              <img
                alt="WhatsApp pairing QR"
                className="max-h-80 rounded-lg bg-white p-3"
                src={String(qrImage).startsWith('data:image') ? qrImage : `data:image/png;base64,${qrImage}`}
              />
            ) : (
              <pre className="max-h-80 overflow-auto text-xs text-gray-300">{JSON.stringify(qrPayload, null, 2)}</pre>
            )}
          </div>
        )}
      </Panel>

      <Panel
        title="Governed Test Message"
        subtitle="Sends through Evolution API and records the event in the communication ledger."
        icon={Send}
      >
        <div className="grid gap-3 lg:grid-cols-[260px_1fr_auto]">
          <input value={number} onChange={(e) => setNumber(e.target.value)} placeholder="973xxxxxxxx"
            className="rounded-xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-white outline-none focus:border-jarvis-cyan/40" />
          <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Message"
            className="rounded-xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-white outline-none focus:border-jarvis-cyan/40" />
          <button onClick={sendTest} disabled={busy || !number || !text} className="btn-primary inline-flex items-center gap-2">
            <Send size={14} />
            Send
          </button>
        </div>
      </Panel>

      <Panel
        title="Native AIONX Routing"
        subtitle="Every inbound WhatsApp reply feeds the same organism: Digital Twin, psychology, Decision Memory, Council awareness, Human Interface persona, and flywheel."
        icon={ShieldCheck}
      >
        <div className="grid gap-2 md:grid-cols-4">
          {(status?.architecture_route?.whatsapp || '').split(' -> ').map((step) => (
            <div key={step} className="rounded-xl border border-white/10 bg-white/[0.03] p-3 text-xs font-semibold text-white/75">{step}</div>
          ))}
        </div>
      </Panel>

      <Panel title="Communication Ledger" subtitle="Unified SES and WhatsApp events for learning, memory, and audit." icon={Radio}>
        <div className="mb-4 grid gap-3 md:grid-cols-4">
          <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
            <p className="text-xs text-white/40">Email outbound</p>
            <p className="mt-1 text-2xl font-black text-white">{status?.counts?.EMAIL?.OUTBOUND || 0}</p>
          </div>
          <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
            <p className="text-xs text-white/40">Email inbound</p>
            <p className="mt-1 text-2xl font-black text-white">{status?.counts?.EMAIL?.INBOUND || 0}</p>
          </div>
          <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
            <p className="text-xs text-white/40">WhatsApp outbound</p>
            <p className="mt-1 text-2xl font-black text-white">{status?.counts?.WHATSAPP?.OUTBOUND || 0}</p>
          </div>
          <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
            <p className="text-xs text-white/40">WhatsApp inbound</p>
            <p className="mt-1 text-2xl font-black text-white">{status?.counts?.WHATSAPP?.INBOUND || 0}</p>
          </div>
        </div>
        <div className="space-y-2">
          {events.length === 0 ? (
            <p className="rounded-xl border border-white/10 bg-white/[0.03] p-4 text-sm text-gray-500">No communication events logged yet.</p>
          ) : events.map((event) => (
            <div key={event.id} className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-bold text-white">{event.channel} - {event.direction}</p>
                  <p className="mt-1 text-xs text-gray-500">{event.from || 'unknown'} to {event.to || 'unknown'} - {event.status}</p>
                </div>
                <p className="text-xs text-white/35">{event.created_at}</p>
              </div>
              <p className="mt-2 text-sm text-white/65">{event.preview || 'No message body.'}</p>
            </div>
          ))}
        </div>
      </Panel>

      {lastAction && (
        <pre className="max-h-96 overflow-auto rounded-xl border border-cyan-200/15 bg-cyan-500/[0.06] p-4 text-xs text-cyan-100/80">
          {JSON.stringify(lastAction, null, 2)}
        </pre>
      )}
    </div>
  )
}
