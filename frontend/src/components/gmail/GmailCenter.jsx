import { useState, useEffect } from 'react'
import { getGmailStatus, getGmailInbox, getGmailStats, fetchGmailInbox, markEmailRead, sendEmail } from '../../services/api'

const CATEGORY_STYLES = {
  client_reply:  { bg: 'bg-green-500/20',  text: 'text-green-400',  label: 'Client Reply' },
  new_inquiry:   { bg: 'bg-blue-500/20',   text: 'text-blue-400',   label: 'New Inquiry' },
  follow_up:     { bg: 'bg-yellow-500/20', text: 'text-yellow-400', label: 'Follow Up' },
  spam:          { bg: 'bg-red-500/20',    text: 'text-red-400',    label: 'Spam' },
  notification:  { bg: 'bg-slate-500/20',  text: 'text-slate-400',  label: 'Notification' },
  other:         { bg: 'bg-slate-500/20',  text: 'text-slate-400',  label: 'Other' },
}

const SENTIMENT_COLORS = {
  positive: 'text-green-400',
  neutral:  'text-slate-400',
  negative: 'text-red-400',
  urgent:   'text-orange-400',
}

export default function GmailCenter() {
  const [status, setStatus] = useState(null)
  const [stats, setStats] = useState(null)
  const [messages, setMessages] = useState([])
  const [selected, setSelected] = useState(null)
  const [filter, setFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const [fetching, setFetching] = useState(false)
  const [tab, setTab] = useState('inbox') // inbox | compose
  const [compose, setCompose] = useState({ to: '', subject: '', body: '' })
  const [sending, setSending] = useState(false)
  const [sendSuccess, setSendSuccess] = useState(false)

  useEffect(() => {
    loadAll()
  }, [])

  async function loadAll() {
    setLoading(true)
    try {
      const [s, inboxData] = await Promise.all([
        getGmailStatus().catch(() => null),
        getGmailInbox(filter || null, null, 50).catch(() => ({ messages: [], stats: {} })),
      ])
      setStatus(s)
      setMessages(inboxData.messages || [])
      setStats(inboxData.stats || {})
    } catch (e) {} finally {
      setLoading(false)
    }
  }

  async function handleFetch() {
    setFetching(true)
    try {
      await fetchGmailInbox()
      await loadAll()
    } catch (e) {} finally {
      setFetching(false)
    }
  }

  async function handleSelect(msg) {
    setSelected(msg)
    if (!msg.is_read) {
      await markEmailRead(msg.id).catch(() => {})
      setMessages(prev => prev.map(m => m.id === msg.id ? { ...m, is_read: true } : m))
    }
  }

  async function handleSend() {
    if (!compose.to || !compose.subject || !compose.body) return
    setSending(true)
    try {
      await sendEmail(compose.to, compose.subject, compose.body)
      setSendSuccess(true)
      setCompose({ to: '', subject: '', body: '' })
      setTimeout(() => setSendSuccess(false), 3000)
    } catch (e) {} finally {
      setSending(false)
    }
  }

  const filtered = filter
    ? messages.filter(m => m.category === filter)
    : messages

  return (
    <div className="h-full flex flex-col overflow-hidden p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Executive Email Center</h1>
          <p className="text-slate-400 text-sm mt-0.5">
            {status?.address || 'Not configured'} · JARVIS monitors every executive email
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs ${status?.connected ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
            <div className={`w-1.5 h-1.5 rounded-full ${status?.connected ? 'bg-green-400 animate-pulse' : 'bg-red-400'}`} />
            {status?.connected ? 'Connected' : 'Not Connected'}
          </div>
          <button
            onClick={handleFetch}
            disabled={fetching}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg text-sm transition-colors"
          >
            {fetching ? 'Fetching...' : 'Fetch New'}
          </button>
          <button
            onClick={() => setTab(tab === 'compose' ? 'inbox' : 'compose')}
            className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg text-sm transition-colors"
          >
            {tab === 'compose' ? '← Inbox' : 'Compose'}
          </button>
        </div>
      </div>

      {/* Stats Row */}
      {stats && (
        <div className="grid grid-cols-5 gap-3 mb-4">
          {[
            { label: 'Total', value: stats.total || 0, color: 'text-white' },
            { label: 'Unread', value: stats.unread || 0, color: 'text-blue-400' },
            { label: 'Need Action', value: stats.needs_action || 0, color: 'text-orange-400' },
            { label: 'Client Replies', value: stats.client_replies || 0, color: 'text-green-400' },
            { label: 'New Inquiries', value: stats.new_inquiries || 0, color: 'text-purple-400' },
          ].map(s => (
            <div key={s.label} className="bg-slate-800/60 border border-slate-700/30 rounded-xl p-3 text-center">
              <p className={`text-xl font-bold ${s.color}`}>{s.value}</p>
              <p className="text-slate-500 text-xs mt-0.5">{s.label}</p>
            </div>
          ))}
        </div>
      )}

      {tab === 'compose' ? (
        /* Compose */
        <div className="flex-1 overflow-y-auto no-scrollbar">
          <div className="max-w-2xl bg-slate-800/60 border border-slate-700/50 rounded-xl p-6 space-y-4">
            <h2 className="text-white font-semibold">New Email</h2>
            <div>
              <label className="text-slate-400 text-xs mb-1 block">To</label>
              <input value={compose.to} onChange={e => setCompose(p => ({...p, to: e.target.value}))}
                placeholder="recipient@email.com"
                className="w-full bg-slate-900/60 border border-slate-600/50 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-blue-500/50" />
            </div>
            <div>
              <label className="text-slate-400 text-xs mb-1 block">Subject</label>
              <input value={compose.subject} onChange={e => setCompose(p => ({...p, subject: e.target.value}))}
                placeholder="Subject line"
                className="w-full bg-slate-900/60 border border-slate-600/50 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-blue-500/50" />
            </div>
            <div>
              <label className="text-slate-400 text-xs mb-1 block">Message</label>
              <textarea value={compose.body} onChange={e => setCompose(p => ({...p, body: e.target.value}))}
                placeholder="Write your message..."
                rows={8}
                className="w-full bg-slate-900/60 border border-slate-600/50 rounded-lg px-3 py-2.5 text-white text-sm resize-none focus:outline-none focus:border-blue-500/50" />
            </div>
            <button onClick={handleSend} disabled={sending || !compose.to || !compose.subject || !compose.body}
              className="px-6 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-40 text-white rounded-lg text-sm font-medium transition-colors">
              {sending ? 'Sending...' : sendSuccess ? 'Sent ✓' : 'Send from Joseph David'}
            </button>
          </div>
        </div>
      ) : (
        /* Inbox */
        <div className="flex-1 flex gap-4 overflow-hidden">
          {/* Message List */}
          <div className="w-96 flex flex-col overflow-hidden">
            {/* Category Filter */}
            <div className="flex gap-1.5 mb-3 flex-wrap">
              {['', 'client_reply', 'new_inquiry', 'needs_action'].map(f => (
                <button key={f} onClick={() => setFilter(f)}
                  className={`px-3 py-1 rounded-lg text-xs transition-colors ${filter === f ? 'bg-blue-600 text-white' : 'bg-slate-800 text-slate-400 hover:text-white'}`}>
                  {f === '' ? 'All' : f === 'needs_action' ? 'Needs Action' : CATEGORY_STYLES[f]?.label || f}
                </button>
              ))}
            </div>

            <div className="flex-1 overflow-y-auto no-scrollbar space-y-1.5">
              {loading ? (
                Array(5).fill(0).map((_, i) => <div key={i} className="h-16 bg-slate-800/40 rounded-lg animate-pulse" />)
              ) : filtered.length === 0 ? (
                <div className="text-center py-12">
                  <p className="text-slate-500 text-sm">No emails yet</p>
                  <p className="text-slate-600 text-xs mt-1">Click "Fetch New" to check inbox</p>
                </div>
              ) : filtered.map(msg => (
                <div key={msg.id}
                  onClick={() => handleSelect(msg)}
                  className={`p-3 rounded-lg cursor-pointer transition-all border ${
                    selected?.id === msg.id
                      ? 'bg-blue-600/20 border-blue-500/30'
                      : 'bg-slate-800/40 border-slate-700/20 hover:bg-slate-800/60'
                  }`}>
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <p className={`text-sm truncate ${msg.is_read ? 'text-slate-400' : 'text-white font-medium'}`}>
                      {msg.from_name || msg.from_email}
                    </p>
                    {msg.needs_action && <div className="w-2 h-2 rounded-full bg-orange-400 flex-shrink-0 mt-1" />}
                  </div>
                  <p className="text-slate-300 text-xs truncate mb-1">{msg.subject}</p>
                  <div className="flex items-center gap-2">
                    {msg.category && CATEGORY_STYLES[msg.category] && (
                      <span className={`text-xs px-1.5 py-0.5 rounded ${CATEGORY_STYLES[msg.category].bg} ${CATEGORY_STYLES[msg.category].text}`}>
                        {CATEGORY_STYLES[msg.category].label}
                      </span>
                    )}
                    <span className="text-slate-600 text-xs">
                      {msg.received_at ? new Date(msg.received_at).toLocaleDateString() : ''}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Message Detail */}
          <div className="flex-1 bg-slate-800/40 border border-slate-700/30 rounded-xl overflow-hidden flex flex-col">
            {selected ? (
              <>
                <div className="p-5 border-b border-slate-700/30">
                  <h3 className="text-white font-semibold text-lg mb-2">{selected.subject}</h3>
                  <div className="flex items-center gap-4 text-sm">
                    <span className="text-slate-400">From: <span className="text-slate-200">{selected.from_name} ({selected.from_email})</span></span>
                    {selected.received_at && (
                      <span className="text-slate-500">{new Date(selected.received_at).toLocaleString()}</span>
                    )}
                  </div>
                  {/* JARVIS Analysis */}
                  {(selected.ai_summary || selected.ai_action) && (
                    <div className="mt-3 p-3 bg-blue-500/10 border border-blue-500/20 rounded-lg">
                      <p className="text-blue-400 text-xs font-medium mb-1">JARVIS Analysis</p>
                      {selected.ai_summary && <p className="text-slate-300 text-sm">{selected.ai_summary}</p>}
                      {selected.ai_action && (
                        <p className="text-blue-300 text-xs mt-1">Recommended: {selected.ai_action}</p>
                      )}
                      {selected.sentiment && (
                        <p className={`text-xs mt-1 ${SENTIMENT_COLORS[selected.sentiment] || 'text-slate-400'}`}>
                          Sentiment: {selected.sentiment}
                        </p>
                      )}
                    </div>
                  )}
                </div>
                <div className="flex-1 overflow-y-auto no-scrollbar p-5">
                  <p className="text-slate-200 text-sm leading-relaxed whitespace-pre-wrap">
                    {selected.body_text || selected.snippet || '(No text content)'}
                  </p>
                </div>
                <div className="p-4 border-t border-slate-700/30 flex gap-2">
                  <button
                    onClick={() => { setCompose({ to: selected.from_email, subject: `Re: ${selected.subject}`, body: '' }); setTab('compose') }}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm transition-colors"
                  >
                    Reply
                  </button>
                  {selected.lead_id && (
                    <span className="px-3 py-2 bg-green-500/20 text-green-400 rounded-lg text-xs flex items-center">
                      Linked to Lead #{selected.lead_id}
                    </span>
                  )}
                </div>
              </>
            ) : (
              <div className="flex-1 flex items-center justify-center">
                <div className="text-center">
                  <p className="text-slate-500">Select an email to read</p>
                  <p className="text-slate-600 text-xs mt-1">JARVIS has analysed every message</p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
