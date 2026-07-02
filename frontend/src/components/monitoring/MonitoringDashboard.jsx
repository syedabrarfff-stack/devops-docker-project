import React, { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  Cpu,
  DollarSign,
  Loader2,
  RefreshCw,
  Zap,
  Server,
  Activity,
} from 'lucide-react'
import api from '../../services/api'

const REFRESH_INTERVAL = 30000 // 30 seconds

function formatNumber(value) {
  if (!value) return '0'
  if (typeof value === 'number') return value.toLocaleString()
  return String(value).toLocaleString()
}

function formatMoney(value) {
  const n = Number(value || 0)
  if (n >= 1000) return `$${(n / 1000).toFixed(2)}K`
  return `$${n.toFixed(2)}`
}

function StatusBadge({ status, label }) {
  const isHealthy = status === 'ok' || status === 'healthy' || status === 'ready' || status === 'operational'
  return (
    <div className={`px-3 py-1 rounded-full text-xs font-semibold flex items-center gap-2
      ${isHealthy
        ? 'bg-green-400/20 border border-green-400/30 text-green-300'
        : 'bg-red-400/20 border border-red-400/30 text-red-300'
      }`}>
      <div className={`w-2 h-2 rounded-full ${isHealthy ? 'bg-green-400' : 'bg-red-400'}`} />
      {label || status}
    </div>
  )
}

function MetricCard({ icon: Icon, label, value, detail, color = 'cyan' }) {
  const colorClasses = {
    cyan: 'border-jarvis-cyan/30 bg-jarvis-cyan/10',
    gold: 'border-jarvis-gold/30 bg-jarvis-gold/10',
    blue: 'border-jarvis-blue/30 bg-jarvis-blue/10',
  }[color] || 'border-jarvis-cyan/30 bg-jarvis-cyan/10'

  return (
    <div className={`rounded-2xl border ${colorClasses} p-4 backdrop-blur-xl`}>
      <div className="flex items-start justify-between mb-3">
        <div>
          <p className="text-white/60 text-sm font-medium">{label}</p>
          <p className="text-white text-2xl font-bold mt-1">{value}</p>
          {detail && <p className="text-white/40 text-xs mt-1">{detail}</p>}
        </div>
        <div className={`p-2 rounded-lg ${colorClasses}`}>
          <Icon size={20} className="text-jarvis-cyan" />
        </div>
      </div>
    </div>
  )
}

function HealthCheck({ label, status, detail }) {
  const isHealthy = status === 'ok' || status === 'healthy' || status === 'ready' || status === 'operational'
  return (
    <div className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02] border border-white/10">
      <div className="flex items-center gap-3 flex-1">
        {isHealthy ? (
          <CheckCircle2 size={18} className="text-green-400" />
        ) : (
          <AlertTriangle size={18} className="text-red-400" />
        )}
        <div className="flex-1">
          <p className="text-white/80 text-sm">{label}</p>
          {detail && <p className="text-white/40 text-xs">{detail}</p>}
        </div>
      </div>
      <StatusBadge status={status} />
    </div>
  )
}

export default function MonitoringDashboard() {
  const [data, setData] = useState({
    health: null,
    aiHealth: null,
    costToday: null,
    scheduler: null,
    loading: true,
    error: null,
    lastUpdate: null,
  })

  async function fetchData() {
    try {
      setData(prev => ({ ...prev, loading: true, error: null }))

      // Fetch all monitoring data in parallel
      const [healthRes, aiHealthRes, costRes, schedulerRes] = await Promise.allSettled([
        api.get('/health'),
        api.get('/api/v1/ai-ops/health'),
        api.get('/api/v1/ai-ops/cost/today'),
        api.get('/api/v1/scheduler/jobs'),
      ])

      const health = healthRes.status === 'fulfilled' ? healthRes.value.data : null
      const aiHealth = aiHealthRes.status === 'fulfilled' ? aiHealthRes.value.data : null
      const costToday = costRes.status === 'fulfilled' ? costRes.value.data : null
      const scheduler = schedulerRes.status === 'fulfilled' ? schedulerRes.value.data : null

      setData(prev => ({
        ...prev,
        health,
        aiHealth,
        costToday,
        scheduler,
        loading: false,
        lastUpdate: new Date(),
      }))
    } catch (err) {
      console.error('Monitoring fetch error:', err)
      setData(prev => ({
        ...prev,
        error: err.message || 'Failed to fetch monitoring data',
        loading: false,
      }))
    }
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, REFRESH_INTERVAL)
    return () => clearInterval(interval)
  }, [])

  const { health, aiHealth, costToday, scheduler, loading, error, lastUpdate } = data

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-jarvis-dark to-slate-900 p-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-2">
          <h1 className="text-3xl font-bold text-white">System Monitoring</h1>
          <div className="flex items-center gap-3">
            <button
              onClick={fetchData}
              className="p-2 rounded-lg bg-white/10 hover:bg-white/20 text-white/60 hover:text-white transition"
              title="Refresh now"
            >
              <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
            </button>
            {lastUpdate && (
              <span className="text-white/40 text-sm">
                Last updated: {lastUpdate.toLocaleTimeString()}
              </span>
            )}
          </div>
        </div>
        <p className="text-white/50">Real-time system health, AI costs, and operational status</p>
      </div>

      {/* Error State */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-6 p-4 rounded-lg bg-red-400/20 border border-red-400/30 text-red-300"
        >
          <p className="text-sm">{error}</p>
        </motion.div>
      )}

      {loading && !health ? (
        <div className="flex items-center justify-center min-h-96">
          <div className="flex flex-col items-center gap-4">
            <Loader2 size={32} className="text-jarvis-cyan animate-spin" />
            <p className="text-white/60">Loading monitoring data...</p>
          </div>
        </div>
      ) : (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
          {/* Key Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <MetricCard
              icon={DollarSign}
              label="AI Cost Today"
              value={costToday?.total_cost ? formatMoney(costToday.total_cost) : '$0.00'}
              detail={`${costToday?.request_count || 0} requests`}
              color="gold"
            />
            <MetricCard
              icon={Cpu}
              label="Active Providers"
              value={aiHealth?.providers ? Object.keys(aiHealth.providers).length : 0}
              detail="AI provider instances"
              color="cyan"
            />
            <MetricCard
              icon={Activity}
              label="Scheduler Jobs"
              value={scheduler?.total || 0}
              detail={`${scheduler?.active || 0} active`}
              color="blue"
            />
            <MetricCard
              icon={Zap}
              label="System Status"
              value={health?.status === 'ok' ? 'Healthy' : 'Degraded'}
              detail={health?.uptime ? `Uptime: ${health.uptime}` : 'Monitoring...'}
              color={health?.status === 'ok' ? 'cyan' : 'gold'}
            />
          </div>

          {/* System Health Section */}
          {health && (
            <div className="rounded-2xl border border-white/10 bg-white/[0.02] backdrop-blur-xl p-6">
              <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                <Server size={20} />
                System Health
              </h2>
              <div className="space-y-3">
                <HealthCheck
                  label="API Health"
                  status={health.status}
                  detail={health.api_health?.status}
                />
                <HealthCheck
                  label="Database Connection"
                  status={health.database?.status}
                  detail={health.database?.detail}
                />
                <HealthCheck
                  label="Redis Cache"
                  status={health.redis?.status}
                  detail={health.redis?.detail}
                />
              </div>
            </div>
          )}

          {/* AI Provider Health */}
          {aiHealth?.providers && (
            <div className="rounded-2xl border border-white/10 bg-white/[0.02] backdrop-blur-xl p-6">
              <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                <Cpu size={20} />
                AI Provider Status
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {Object.entries(aiHealth.providers).map(([provider, status]) => (
                  <HealthCheck
                    key={provider}
                    label={provider.charAt(0).toUpperCase() + provider.slice(1)}
                    status={status.circuit_breaker_status || 'ok'}
                    detail={`Requests: ${status.request_count || 0}`}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Cost Breakdown */}
          {costToday && (
            <div className="rounded-2xl border border-white/10 bg-white/[0.02] backdrop-blur-xl p-6">
              <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                <DollarSign size={20} />
                AI Cost Breakdown Today
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {costToday.by_provider && Object.entries(costToday.by_provider).map(([provider, cost]) => (
                  <div key={provider} className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02] border border-white/10">
                    <span className="text-white/70 text-sm capitalize">{provider}</span>
                    <span className="text-white font-semibold">{formatMoney(cost)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Scheduler Jobs */}
          {scheduler && (
            <div className="rounded-2xl border border-white/10 bg-white/[0.02] backdrop-blur-xl p-6">
              <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                <Clock size={20} />
                Scheduler Status
              </h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="p-3 rounded-lg bg-white/[0.02] border border-white/10">
                  <p className="text-white/60 text-sm">Total Jobs</p>
                  <p className="text-white text-2xl font-bold">{scheduler.total || 0}</p>
                </div>
                <div className="p-3 rounded-lg bg-white/[0.02] border border-white/10">
                  <p className="text-white/60 text-sm">Active</p>
                  <p className="text-green-400 text-2xl font-bold">{scheduler.active || 0}</p>
                </div>
                <div className="p-3 rounded-lg bg-white/[0.02] border border-white/10">
                  <p className="text-white/60 text-sm">Paused</p>
                  <p className="text-amber-400 text-2xl font-bold">{scheduler.paused || 0}</p>
                </div>
                <div className="p-3 rounded-lg bg-white/[0.02] border border-white/10">
                  <p className="text-white/60 text-sm">Failed</p>
                  <p className="text-red-400 text-2xl font-bold">{scheduler.failed || 0}</p>
                </div>
              </div>
            </div>
          )}

          {/* Auto-refresh notice */}
          <div className="flex items-center gap-2 text-white/40 text-sm">
            <Activity size={16} className="animate-pulse text-jarvis-cyan" />
            <span>Auto-refreshing every 30 seconds</span>
          </div>
        </motion.div>
      )}
    </div>
  )
}
