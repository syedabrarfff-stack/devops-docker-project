/**
 * ServiceMetrics Visualization - Display metrics charts
 * Shows: success rate, execution time, cost, error rate over time
 */

import React, { useState, useEffect } from 'react';
import { getServiceMetrics } from '../../services/serviceRegistryApi';
import './ServiceRegistry.css';

export default function ServiceMetricsVisualization({ serviceId, tenantId }) {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [timeRange, setTimeRange] = useState(30); // days

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        setLoading(true);
        const data = await getServiceMetrics(serviceId, tenantId, timeRange);
        setMetrics(data);
        setError(null);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchMetrics();
  }, [serviceId, tenantId, timeRange]);

  if (loading) {
    return <div className="loading-spinner">Loading metrics...</div>;
  }

  if (!metrics) {
    return <div className="error-banner">No metrics available</div>;
  }

  const getStatusColor = (rate) => {
    if (rate >= 95) return '#10b981'; // green
    if (rate >= 90) return '#f59e0b'; // amber
    return '#ef4444'; // red
  };

  const calculateTrend = (current, previous) => {
    if (!previous) return 0;
    return ((current - previous) / previous) * 100;
  };

  return (
    <div className="service-metrics-visualization">
      <div className="metrics-header">
        <h2>Service Metrics</h2>
        <select
          className="time-range-select"
          value={timeRange}
          onChange={(e) => setTimeRange(parseInt(e.target.value))}
        >
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
        </select>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {/* Key Metrics Cards */}
      <div className="metrics-cards">
        <div className="metric-card large">
          <div className="metric-header">
            <span className="metric-name">Success Rate</span>
            {metrics.successRate && (
              <span
                className="metric-status"
                style={{ color: getStatusColor(metrics.successRate) }}
              >
                {metrics.successRate >= 95 ? '✓ Healthy' : '⚠ Warning'}
              </span>
            )}
          </div>
          <div className="metric-display">
            <span className="metric-value">
              {metrics.successRate ? `${metrics.successRate.toFixed(1)}%` : 'N/A'}
            </span>
            <svg className="metric-gauge" viewBox="0 0 100 100">
              <circle
                cx="50"
                cy="50"
                r="45"
                fill="none"
                stroke="#e5e7eb"
                strokeWidth="10"
              />
              <circle
                cx="50"
                cy="50"
                r="45"
                fill="none"
                stroke={getStatusColor(metrics.successRate || 0)}
                strokeWidth="10"
                strokeDasharray={`${(metrics.successRate || 0) * 2.827} 282.7`}
                transform="rotate(-90 50 50)"
              />
            </svg>
          </div>
          <div className="metric-meta">
            {metrics.totalExecutions && (
              <span>{metrics.totalExecutions.toLocaleString()} total executions</span>
            )}
          </div>
        </div>

        <div className="metric-card">
          <span className="metric-name">Execution Time</span>
          <span className="metric-value">
            {metrics.avgExecutionTimeMs ? `${metrics.avgExecutionTimeMs}ms` : 'N/A'}
          </span>
          <span className="metric-detail">average</span>
        </div>

        <div className="metric-card">
          <span className="metric-name">Error Rate</span>
          <span className="metric-value" style={{ color: metrics.errorRate > 5 ? '#ef4444' : '#10b981' }}>
            {metrics.errorRate ? `${metrics.errorRate.toFixed(2)}%` : 'N/A'}
          </span>
          <span className="metric-detail">
            {metrics.failedExecutions || 0} failures
          </span>
        </div>

        <div className="metric-card">
          <span className="metric-name">Daily Cost</span>
          <span className="metric-value">
            {metrics.dailyCost ? `$${metrics.dailyCost.toFixed(2)}` : 'N/A'}
          </span>
          <span className="metric-detail">
            {metrics.dailyCost && metrics.dailyCost * 30 > 0
              ? `~$${(metrics.dailyCost * 30).toFixed(2)}/month`
              : '-'}
          </span>
        </div>

        <div className="metric-card">
          <span className="metric-name">Active Users</span>
          <span className="metric-value">
            {metrics.activeUsers ? metrics.activeUsers.toLocaleString() : 'N/A'}
          </span>
          <span className="metric-detail">current</span>
        </div>

        <div className="metric-card">
          <span className="metric-name">Executions</span>
          <div className="execution-breakdown">
            <div className="execution-stat">
              <span className="stat-value success">
                {metrics.successfulExecutions || 0}
              </span>
              <span className="stat-label">successful</span>
            </div>
            <div className="execution-stat">
              <span className="stat-value error">
                {metrics.failedExecutions || 0}
              </span>
              <span className="stat-label">failed</span>
            </div>
          </div>
        </div>
      </div>

      {/* Chart Placeholder - in production, would use Chart.js or Recharts */}
      <section className="metrics-chart">
        <h3>Success Rate Trend (30 days)</h3>
        <div className="chart-placeholder">
          <p>📊 Chart visualization would display here</p>
          <p className="chart-note">
            In production, integrate Chart.js or Recharts for time-series visualization
          </p>
        </div>
      </section>

      {/* Execution Distribution */}
      <section className="execution-distribution">
        <h3>Execution Distribution</h3>
        <div className="distribution-bars">
          {metrics.totalExecutions > 0 && (
            <>
              <div className="bar-item">
                <span className="bar-label">Successful</span>
                <div className="bar-container">
                  <div
                    className="bar successful"
                    style={{
                      width: `${(metrics.successfulExecutions / metrics.totalExecutions) * 100}%`,
                    }}
                  />
                </div>
                <span className="bar-value">
                  {(
                    (metrics.successfulExecutions / metrics.totalExecutions) *
                    100
                  ).toFixed(1)}
                  %
                </span>
              </div>

              <div className="bar-item">
                <span className="bar-label">Failed</span>
                <div className="bar-container">
                  <div
                    className="bar failed"
                    style={{
                      width: `${(metrics.failedExecutions / metrics.totalExecutions) * 100}%`,
                    }}
                  />
                </div>
                <span className="bar-value">
                  {((metrics.failedExecutions / metrics.totalExecutions) * 100).toFixed(1)}%
                </span>
              </div>
            </>
          )}
        </div>
      </section>

      {/* Alerts/Recommendations */}
      {metrics.errorRate > 5 && (
        <div className="alert alert-warning">
          <strong>⚠️ Alert:</strong> Error rate is above 5%. Consider investigating recent deployments.
        </div>
      )}

      {metrics.avgExecutionTimeMs > 5000 && (
        <div className="alert alert-info">
          <strong>ℹ️ Note:</strong> Execution time is high. Optimization may improve throughput.
        </div>
      )}
    </div>
  );
}
