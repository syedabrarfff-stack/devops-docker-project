import React, { useState, useEffect } from 'react';
import { AlertCircle, TrendingUp, Zap, Activity, BarChart3, RefreshCw } from 'lucide-react';
import useJarvisStore from '../../store/useJarvisStore';
import { getMonitoringMetrics } from '../../services/monitoringApi';
import './MonitoringDashboard.css';

/**
 * Customer-facing monitoring dashboard displaying:
 * - Real-time system health
 * - AI API costs by provider
 * - Cost trends and surge detection
 * - Operational metrics (approvals, jobs, providers)
 */
export default function MonitoringDashboard() {
  const [overview, setOverview] = useState(null);
  const [dailyCost, setDailyCost] = useState(null);
  const [weeklyCost, setWeeklyCost] = useState(null);
  const [providers, setProviders] = useState(null);
  const [approvals, setApprovals] = useState(null);
  const [jobs, setJobs] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const refreshMetrics = async () => {
    try {
      setLoading(true);
      const [overview, daily, weekly, providers, approvals, jobs] = await Promise.all([
        getMonitoringMetrics.getDashboardOverview(),
        getMonitoringMetrics.getAICostToday(),
        getMonitoringMetrics.getAICostHistory(7),
        getMonitoringMetrics.getAIProviders(),
        getMonitoringMetrics.getApprovals(),
        getMonitoringMetrics.getSchedulerJobs(),
      ]);

      setOverview(overview);
      setDailyCost(daily);
      setWeeklyCost(weekly);
      setProviders(providers);
      setApprovals(approvals);
      setJobs(jobs);
      setLastUpdate(new Date());
    } catch (error) {
      console.error('Failed to fetch monitoring metrics:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshMetrics();

    if (!autoRefresh) return;

    const interval = setInterval(refreshMetrics, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, [autoRefresh]);

  if (loading && !overview) {
    return (
      <div className="monitoring-dashboard loading">
        <div className="loading-spinner">
          <RefreshCw className="spin" size={32} />
          <p>Loading system metrics...</p>
        </div>
      </div>
    );
  }

  const healthScore = overview?.health?.score || 0;
  const healthLevel = healthScore >= 80 ? 'excellent' : healthScore >= 60 ? 'good' : healthScore >= 40 ? 'fair' : 'poor';

  return (
    <div className="monitoring-dashboard">
      <div className="dashboard-header">
        <div>
          <h1>System Monitoring</h1>
          <p className="subtitle">Real-time operational metrics and cost analytics</p>
        </div>
        <div className="header-controls">
          <button
            className="refresh-btn"
            onClick={refreshMetrics}
            disabled={loading}
            title="Refresh metrics"
          >
            <RefreshCw size={18} className={loading ? 'spin' : ''} />
            Refresh
          </button>
          <label className="auto-refresh">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            Auto-refresh (30s)
          </label>
        </div>
      </div>

      {lastUpdate && (
        <div className="last-update">
          Last updated: {lastUpdate.toLocaleTimeString()}
        </div>
      )}

      {/* Health Score Card */}
      <div className={`card health-card health-${healthLevel}`}>
        <div className="card-header">
          <Activity size={20} />
          <h2>System Health</h2>
        </div>
        <div className="health-score">
          <div className="score-circle">
            <span className="score-value">{Math.round(healthScore)}</span>
            <span className="score-max">/100</span>
          </div>
          <div className="health-details">
            <div className="health-status">{overview?.health?.interpretation || 'Analyzing...'}</div>
            {overview?.health?.components && (
              <div className="components">
                <div className="component">
                  <span>AI Providers:</span>
                  <strong>{overview.health.components.ai_providers || 0}</strong>
                </div>
                <div className="component">
                  <span>Database:</span>
                  <strong>{overview.health.components.database || 'unknown'}</strong>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* AI Costs Cards */}
      <div className="cards-row">
        <div className="card cost-card">
          <div className="card-header">
            <Zap size={20} />
            <h2>Today's AI Costs</h2>
          </div>
          <div className="cost-amount">
            ${(dailyCost?.total_cost_usd || 0).toFixed(2)}
          </div>
          {dailyCost?.surge_alert && (
            <div className="surge-alert">
              <AlertCircle size={16} />
              <span>Surge detected! Threshold: ${dailyCost.surge_threshold_usd}</span>
            </div>
          )}
          {dailyCost?.by_provider && Object.keys(dailyCost.by_provider).length > 0 && (
            <div className="provider-breakdown">
              {Object.entries(dailyCost.by_provider).map(([provider, data]) => (
                <div key={provider} className="breakdown-item">
                  <span className="provider-name">{provider}</span>
                  <span className="cost-value">${data.cost_usd.toFixed(4)}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="card cost-card weekly">
          <div className="card-header">
            <TrendingUp size={20} />
            <h2>7-Day Trend</h2>
          </div>
          <div className="cost-amount">
            ${(weeklyCost?.total_cost_usd || 0).toFixed(2)}
          </div>
          <div className="cost-details">
            <div className="detail">
              <span>Daily Average:</span>
              <strong>${(weeklyCost?.avg_daily_usd || 0).toFixed(2)}</strong>
            </div>
            <div className="detail">
              <span>Days Tracked:</span>
              <strong>{weeklyCost?.days || 0}</strong>
            </div>
          </div>
          {weeklyCost?.daily && weeklyCost.daily.length > 0 && (
            <div className="cost-chart">
              <div className="mini-chart">
                {weeklyCost.daily.map((day, idx) => (
                  <div
                    key={idx}
                    className="bar"
                    style={{
                      height: `${Math.max(
                        5,
                        (day.cost_usd / Math.max(...weeklyCost.daily.map(d => d.cost_usd), 1)) * 100
                      )}%`,
                    }}
                    title={`${day.date}: $${day.cost_usd}`}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* AI Providers Card */}
      <div className="cards-row">
        <div className="card providers-card">
          <div className="card-header">
            <Zap size={20} />
            <h2>AI Providers</h2>
          </div>
          <div className="providers-status">
            <div className="status-item">
              <span>Available</span>
              <strong className="available">{providers?.available || 0}</strong>
            </div>
            <div className="status-item">
              <span>Configured</span>
              <strong>{providers?.configured || 0}</strong>
            </div>
            <div className="status-item">
              <span>Total</span>
              <strong>{providers?.total || 0}</strong>
            </div>
          </div>
          {providers?.active_providers && providers.active_providers.length > 0 && (
            <div className="active-list">
              <h3>Active</h3>
              <div className="provider-list">
                {providers.active_providers.map((p) => (
                  <span key={p} className="provider-tag">{p}</span>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="card approvals-card">
          <div className="card-header">
            <AlertCircle size={20} />
            <h2>Approvals</h2>
          </div>
          <div className="approval-count">
            {approvals?.total_pending || 0}
          </div>
          <div className="approval-label">Pending Captain Approvals</div>
          {approvals?.by_risk_level && Object.keys(approvals.by_risk_level).length > 0 && (
            <div className="risk-breakdown">
              {Object.entries(approvals.by_risk_level)
                .sort(([, a], [, b]) => b - a)
                .map(([level, count]) => (
                  <div key={level} className={`risk-item risk-${level.toLowerCase()}`}>
                    <span>{level}</span>
                    <strong>{count}</strong>
                  </div>
                ))}
            </div>
          )}
        </div>
      </div>

      {/* Jobs Card */}
      {jobs && (
        <div className="card jobs-card">
          <div className="card-header">
            <BarChart3 size={20} />
            <h2>Scheduler Jobs</h2>
          </div>
          <div className="jobs-summary">
            <div className="summary-item">
              <span>Total Jobs</span>
              <strong>{jobs.total_jobs || 0}</strong>
            </div>
            <div className="summary-item">
              <span>Running</span>
              <strong className="running">{jobs.running || 0}</strong>
            </div>
            <div className="summary-item">
              <span>Paused</span>
              <strong>{jobs.paused || 0}</strong>
            </div>
          </div>
          {jobs.jobs && jobs.jobs.length > 0 && (
            <div className="jobs-list">
              <div className="jobs-header">
                <span>Job Name</span>
                <span>Trigger</span>
                <span>Next Run</span>
              </div>
              {jobs.jobs.slice(0, 10).map((job) => (
                <div key={job.id} className="job-row">
                  <span className="job-name">{job.name}</span>
                  <span className="job-trigger">{job.trigger}</span>
                  <span className="job-next-run">
                    {job.next_run
                      ? new Date(job.next_run).toLocaleTimeString()
                      : 'No scheduled run'}
                  </span>
                </div>
              ))}
              {jobs.jobs.length > 10 && (
                <div className="jobs-more">
                  +{jobs.jobs.length - 10} more jobs
                </div>
              )}
            </div>
          )}
        </div>
      )}

      <div className="dashboard-footer">
        <p className="footer-note">
          Metrics update every 30 seconds. Real-time monitoring of Aliyar Solutions JARVIS platform.
        </p>
      </div>
    </div>
  );
}
