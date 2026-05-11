import { useState, useEffect, useRef } from 'react'
import { getAllAgentTeams, getTeamActivity, chatWithAgent, chatWithTeam } from '../../services/api'

export default function AgentOpsCenter() {
  const [teams, setTeams] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedTeam, setSelectedTeam] = useState(null)
  const [selectedAgent, setSelectedAgent] = useState(null)
  const [chatTarget, setChatTarget] = useState(null) // { type: 'agent'|'team', id, name }
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const [activity, setActivity] = useState(null)
  const [activityLoading, setActivityLoading] = useState(false)
  const [view, setView] = useState('grid') // grid | team | chat
  const chatEndRef = useRef(null)

  useEffect(() => {
    loadTeams()
  }, [])

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function loadTeams() {
    try {
      const data = await getAllAgentTeams()
      setTeams(data.teams || [])
    } catch (e) {
      console.error('Failed to load teams', e)
    } finally {
      setLoading(false)
    }
  }

  async function openTeam(team) {
    setSelectedTeam(team)
    setSelectedAgent(null)
    setView('team')
    setActivityLoading(true)
    try {
      const data = await getTeamActivity(team.team_id)
      setActivity(data)
    } catch (e) {
      setActivity(null)
    } finally {
      setActivityLoading(false)
    }
  }

  function openChat(type, id, name, role = '') {
    setChatTarget({ type, id, name, role })
    setMessages([{
      role: 'system',
      content: type === 'agent'
        ? `Connected to ${name}. Ask them anything about their work.`
        : `Connected to ${name}. The team is ready to brief you.`
    }])
    setView('chat')
  }

  async function sendMessage() {
    if (!input.trim() || chatLoading) return
    const msg = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'captain', content: msg }])
    setChatLoading(true)
    try {
      let data
      if (chatTarget.type === 'agent') {
        data = await chatWithAgent(chatTarget.id, msg)
        setMessages(prev => [...prev, { role: 'agent', content: data.agent_response, name: data.agent_name }])
      } else {
        data = await chatWithTeam(chatTarget.id, msg)
        setMessages(prev => [...prev, { role: 'agent', content: data.team_response, name: data.team_name }])
      }
    } catch (e) {
      setMessages(prev => [...prev, { role: 'error', content: 'Connection interrupted. Retry.' }])
    } finally {
      setChatLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-slate-400 text-sm">Loading Agent Operations Center...</p>
        </div>
      </div>
    )
  }

  const totalAgents = teams.reduce((sum, t) => sum + (t.agent_count || 0), 0)

  return (
    <div className="h-full flex flex-col overflow-hidden p-6">
    <div className="flex-1 overflow-y-auto no-scrollbar space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Agent Operations Center</h1>
          <p className="text-slate-400 text-sm mt-1">
            {teams.length} teams · {totalAgents} agents · All operational
          </p>
        </div>
        <div className="flex gap-2">
          {view !== 'grid' && (
            <button
              onClick={() => { setView('grid'); setSelectedTeam(null); setSelectedAgent(null); setChatTarget(null) }}
              className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-lg text-sm transition-colors"
            >
              ← All Teams
            </button>
          )}
          {view === 'team' && selectedTeam && (
            <button
              onClick={() => openChat('team', selectedTeam.team_id, selectedTeam.team_name)}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm transition-colors"
            >
              Talk to {selectedTeam.team_name}
            </button>
          )}
        </div>
      </div>

      {/* Grid View — all teams */}
      {view === 'grid' && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {teams.map(team => (
            <TeamCard key={team.team_id} team={team} onOpen={openTeam} onChat={openChat} />
          ))}
        </div>
      )}

      {/* Team Detail View */}
      {view === 'team' && selectedTeam && (
        <TeamDetail
          team={selectedTeam}
          activity={activity}
          activityLoading={activityLoading}
          onChatAgent={openChat}
          onChatTeam={() => openChat('team', selectedTeam.team_id, selectedTeam.team_name)}
        />
      )}

      {/* Chat View */}
      {view === 'chat' && chatTarget && (
        <ChatPane
          target={chatTarget}
          messages={messages}
          input={input}
          loading={chatLoading}
          chatEndRef={chatEndRef}
          onInputChange={setInput}
          onSend={sendMessage}
          onBack={() => {
            if (selectedTeam) setView('team')
            else setView('grid')
          }}
        />
      )}
    </div>
    </div>
  )
}

function TeamCard({ team, onOpen, onChat }) {
  return (
    <div
      className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-5 hover:border-slate-600 transition-all cursor-pointer group"
      style={{ borderLeftColor: team.color, borderLeftWidth: 3 }}
      onClick={() => onOpen(team)}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <span className="text-2xl">{team.icon}</span>
          <div>
            <h3 className="text-white font-semibold text-sm">{team.team_name}</h3>
            <p className="text-slate-500 text-xs">{team.manager}</p>
          </div>
        </div>
        <span className="bg-green-500/20 text-green-400 text-xs px-2 py-0.5 rounded-full">
          {team.agent_count} active
        </span>
      </div>

      <div className="space-y-1.5 mb-4">
        {(team.agents || []).map(agent => (
          <div key={agent.id} className="flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-green-400 flex-shrink-0" />
            <span className="text-slate-400 text-xs truncate">{agent.name}</span>
          </div>
        ))}
      </div>

      <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          onClick={(e) => { e.stopPropagation(); onOpen(team) }}
          className="flex-1 py-1.5 bg-slate-700 hover:bg-slate-600 text-slate-300 text-xs rounded-lg transition-colors"
        >
          View Team
        </button>
        <button
          onClick={(e) => { e.stopPropagation(); onChat('team', team.team_id, team.team_name) }}
          className="flex-1 py-1.5 text-white text-xs rounded-lg transition-colors"
          style={{ backgroundColor: team.color + '33', border: `1px solid ${team.color}66` }}
        >
          Talk to Team
        </button>
      </div>
    </div>
  )
}

function TeamDetail({ team, activity, activityLoading, onChatAgent, onChatTeam }) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Agents */}
      <div className="lg:col-span-2 space-y-4">
        <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-5">
          <div className="flex items-center gap-3 mb-5">
            <span className="text-3xl">{team.icon}</span>
            <div>
              <h2 className="text-white text-lg font-bold">{team.team_name}</h2>
              <p className="text-slate-400 text-sm">Manager: {team.manager}</p>
            </div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {(team.agents || []).map(agent => (
              <AgentCard key={agent.id} agent={agent} teamColor={team.color} onChat={onChatAgent} />
            ))}
          </div>
        </div>
      </div>

      {/* Activity */}
      <div className="space-y-4">
        <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-5">
          <h3 className="text-white font-semibold mb-4">Recent Activity</h3>
          {activityLoading ? (
            <div className="space-y-2">
              {[1,2,3].map(i => (
                <div key={i} className="h-4 bg-slate-700 rounded animate-pulse" />
              ))}
            </div>
          ) : activity ? (
            <div className="space-y-3">
              {(activity.recent_activity || []).map((item, i) => (
                <div key={i} className="flex gap-3">
                  <div className="w-1.5 h-1.5 rounded-full bg-blue-400 mt-1.5 flex-shrink-0" />
                  <p className="text-slate-300 text-xs leading-relaxed">{item}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-slate-500 text-sm">No activity data</p>
          )}
        </div>

        <button
          onClick={onChatTeam}
          className="w-full py-3 text-white font-medium rounded-xl transition-colors text-sm"
          style={{ backgroundColor: team.color }}
        >
          Brief Me — {team.team_name}
        </button>
      </div>
    </div>
  )
}

function AgentCard({ agent, teamColor, onChat }) {
  return (
    <div className="bg-slate-900/50 border border-slate-700/30 rounded-lg p-4 hover:border-slate-600/50 transition-all group">
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-green-400" />
          <span className="text-white text-sm font-medium">{agent.name}</span>
        </div>
      </div>
      <p className="text-slate-400 text-xs mb-3 leading-relaxed">{agent.role}</p>
      <button
        onClick={() => onChat('agent', agent.id, agent.name, agent.role)}
        className="w-full py-1.5 text-xs text-white rounded-lg opacity-0 group-hover:opacity-100 transition-opacity"
        style={{ backgroundColor: teamColor + '44', border: `1px solid ${teamColor}66` }}
      >
        Talk to {agent.name.split(' — ')[0]}
      </button>
    </div>
  )
}

function ChatPane({ target, messages, input, loading, chatEndRef, onInputChange, onSend, onBack }) {
  function handleKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      onSend()
    }
  }

  return (
    <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl flex flex-col" style={{ height: '70vh' }}>
      {/* Chat header */}
      <div className="flex items-center justify-between p-4 border-b border-slate-700/50">
        <div className="flex items-center gap-3">
          <div className="w-2.5 h-2.5 rounded-full bg-green-400 animate-pulse" />
          <div>
            <p className="text-white font-medium text-sm">{target.name}</p>
            {target.role && <p className="text-slate-400 text-xs">{target.role}</p>}
          </div>
        </div>
        <button onClick={onBack} className="text-slate-400 hover:text-white text-sm transition-colors">
          ← Back
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, i) => {
          if (msg.role === 'system') {
            return (
              <div key={i} className="text-center">
                <span className="text-slate-500 text-xs bg-slate-900/50 px-3 py-1 rounded-full">
                  {msg.content}
                </span>
              </div>
            )
          }
          if (msg.role === 'captain') {
            return (
              <div key={i} className="flex justify-end">
                <div className="max-w-[80%] bg-blue-600/30 border border-blue-500/30 rounded-xl rounded-tr-sm px-4 py-3">
                  <p className="text-xs text-blue-400 mb-1">Captain</p>
                  <p className="text-white text-sm leading-relaxed">{msg.content}</p>
                </div>
              </div>
            )
          }
          if (msg.role === 'agent') {
            return (
              <div key={i} className="flex justify-start">
                <div className="max-w-[85%] bg-slate-700/50 border border-slate-600/30 rounded-xl rounded-tl-sm px-4 py-3">
                  <p className="text-xs text-slate-400 mb-1">{msg.name || target.name}</p>
                  <p className="text-slate-100 text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                </div>
              </div>
            )
          }
          return (
            <div key={i} className="text-center">
              <span className="text-red-400 text-xs">{msg.content}</span>
            </div>
          )
        })}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-slate-700/50 border border-slate-600/30 rounded-xl rounded-tl-sm px-4 py-3">
              <div className="flex gap-1.5 items-center">
                <div className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-slate-700/50">
        <div className="flex gap-3">
          <textarea
            value={input}
            onChange={(e) => onInputChange(e.target.value)}
            onKeyDown={handleKey}
            placeholder={`Message ${target.name.split(' — ')[0]}...`}
            rows={1}
            className="flex-1 bg-slate-900/60 border border-slate-600/50 rounded-xl px-4 py-3 text-white text-sm resize-none focus:outline-none focus:border-blue-500/50 placeholder-slate-500"
          />
          <button
            onClick={onSend}
            disabled={!input.trim() || loading}
            className="px-5 py-3 bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-xl text-sm font-medium transition-colors flex-shrink-0"
          >
            Send
          </button>
        </div>
        <p className="text-slate-600 text-xs mt-2">Enter to send · Shift+Enter for new line</p>
      </div>
    </div>
  )
}
