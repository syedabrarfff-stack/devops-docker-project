/**
 * ServiceManagement Dashboard - Manage individual service
 * Shows: details, metrics, instances, dependencies, actions
 */

import React, { useState, useEffect } from 'react';
import useJarvisStore from '../../store/useJarvisStore';
import {
  getService,
  updateService,
  testService,
  rolloutService,
} from '../../services/serviceRegistryApi';
import './ServiceRegistry.css';

const STATUS_OPTIONS = ['active', 'beta', 'deprecated', 'archived'];

export default function ServiceManagementDashboard({ serviceId }) {
  const { tenant } = useJarvisStore();
  const [service, setService] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [editing, setEditing] = useState(false);
  const [editData, setEditData] = useState({});
  const [testRunning, setTestRunning] = useState(false);
  const [rolloutRunning, setRolloutRunning] = useState(false);
  const [targetInstances, setTargetInstances] = useState('');

  // Fetch service on mount
  useEffect(() => {
    const fetchService = async () => {
      try {
        setLoading(true);
        const data = await getService(serviceId, tenant.id);
        setService(data);
        setEditData(data);
        setError(null);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchService();
  }, [serviceId, tenant.id]);

  const handleUpdateService = async () => {
    try {
      const updatePayload = {
        name: editData.name !== service.name ? editData.name : undefined,
        status: editData.status !== service.status ? editData.status : undefined,
        description: editData.description !== service.description ? editData.description : undefined,
      };

      // Remove undefined fields
      Object.keys(updatePayload).forEach(
        (key) => updatePayload[key] === undefined && delete updatePayload[key]
      );

      const updated = await updateService(serviceId, updatePayload, tenant.id);
      setService(updated);
      setEditing(false);
      setError(null);
    } catch (err) {
      setError(`Failed to update service: ${err.message}`);
    }
  };

  const handleTestService = async () => {
    try {
      setTestRunning(true);
      const result = await testService(
        serviceId,
        { test_mode: 'dry_run' },
        tenant.id
      );

      alert(`Test Result: ${result.message}\nDuration: ${result.duration_ms}ms`);
      setError(null);
    } catch (err) {
      setError(`Test failed: ${err.message}`);
    } finally {
      setTestRunning(false);
    }
  };

  const handleRolloutService = async () => {
    if (!targetInstances.trim()) {
      setError('Please specify target instances');
      return;
    }

    try {
      setRolloutRunning(true);
      const instances = targetInstances
        .split(',')
        .map((i) => i.trim())
        .filter((i) => i);

      const result = await rolloutService(
        serviceId,
        {
          target_instances: instances,
          rollback_on_error: true,
        },
        tenant.id
      );

      alert(`Rollout initiated. Deployment ID: ${result.deployment_id}`);
      setTargetInstances('');
      setError(null);
    } catch (err) {
      setError(`Rollout failed: ${err.message}`);
    } finally {
      setRolloutRunning(false);
    }
  };

  if (loading) {
    return <div className="loading-spinner">Loading service...</div>;
  }

  if (!service) {
    return <div className="error-banner">Service not found</div>;
  }

  return (
    <div className="service-management-dashboard">
      <div className="dashboard-header">
        <h1>{service.name}</h1>
        <div className="header-meta">
          <code>{service.code}</code>
          <span className={`badge badge-${service.status}`}>{service.status}</span>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {/* Service Overview */}
      <section className="dashboard-section">
        <h2>Service Details</h2>
        {editing ? (
          <div className="edit-form">
            <div className="form-group">
              <label>Name</label>
              <input
                type="text"
                value={editData.name}
                onChange={(e) => setEditData({ ...editData, name: e.target.value })}
              />
            </div>

            <div className="form-group">
              <label>Description</label>
              <textarea
                value={editData.description || ''}
                onChange={(e) => setEditData({ ...editData, description: e.target.value })}
                rows={4}
              />
            </div>

            <div className="form-group">
              <label>Status</label>
              <select
                value={editData.status}
                onChange={(e) => setEditData({ ...editData, status: e.target.value })}
              >
                {STATUS_OPTIONS.map((status) => (
                  <option key={status} value={status}>
                    {status}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-actions">
              <button className="btn btn-primary" onClick={handleUpdateService}>
                Save
              </button>
              <button
                className="btn btn-secondary"
                onClick={() => {
                  setEditing(false);
                  setEditData(service);
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <div className="service-info">
            <div className="info-row">
              <span className="label">Code:</span>
              <code>{service.code}</code>
            </div>
            <div className="info-row">
              <span className="label">Name:</span>
              <span>{service.name}</span>
            </div>
            <div className="info-row">
              <span className="label">Division:</span>
              <span>{service.division}</span>
            </div>
            <div className="info-row">
              <span className="label">Type:</span>
              <span>{service.service_type}</span>
            </div>
            {service.description && (
              <div className="info-row">
                <span className="label">Description:</span>
                <span>{service.description}</span>
              </div>
            )}
            {service.human_interface_executive && (
              <div className="info-row">
                <span className="label">HIA:</span>
                <span>{service.human_interface_executive}</span>
              </div>
            )}

            <button className="btn btn-secondary" onClick={() => setEditing(true)}>
              Edit
            </button>
          </div>
        )}
      </section>

      {/* Metrics Summary */}
      <section className="dashboard-section">
        <h2>Performance Metrics</h2>
        <div className="metrics-grid">
          <div className="metric-card">
            <span className="metric-label">Success Rate</span>
            <span className="metric-value">
              {service.success_rate ? `${service.success_rate.toFixed(1)}%` : '-'}
            </span>
          </div>
          <div className="metric-card">
            <span className="metric-label">Avg Execution Time</span>
            <span className="metric-value">
              {service.avg_execution_time_ms ? `${service.avg_execution_time_ms}ms` : '-'}
            </span>
          </div>
          <div className="metric-card">
            <span className="metric-label">Monthly Cost</span>
            <span className="metric-value">
              {service.monthly_cost ? `$${service.monthly_cost.toFixed(2)}` : '-'}
            </span>
          </div>
          <div className="metric-card">
            <span className="metric-label">Version</span>
            <span className="metric-value">{service.version}</span>
          </div>
        </div>
      </section>

      {/* Agent Layer & KPIs */}
      {(service.agent_layer || service.kpi_targets) && (
        <section className="dashboard-section">
          <h2>Configuration</h2>
          {service.agent_layer && (
            <div className="config-section">
              <h3>Agent Layer</h3>
              <div className="tag-list">
                {service.agent_layer.map((agent, idx) => (
                  <span key={idx} className="tag">
                    {agent}
                  </span>
                ))}
              </div>
            </div>
          )}
          {service.kpi_targets && (
            <div className="config-section">
              <h3>KPI Targets</h3>
              <div className="tag-list">
                {service.kpi_targets.map((kpi, idx) => (
                  <span key={idx} className="tag">
                    {kpi}
                  </span>
                ))}
              </div>
            </div>
          )}
        </section>
      )}

      {/* Testing & Deployment */}
      <section className="dashboard-section">
        <h2>Testing & Deployment</h2>
        <div className="actions-grid">
          <div className="action-card">
            <h3>Test Service</h3>
            <p>Run validation tests before deployment</p>
            <button
              className="btn btn-info"
              onClick={handleTestService}
              disabled={testRunning}
            >
              {testRunning ? 'Testing...' : 'Run Test'}
            </button>
          </div>

          <div className="action-card">
            <h3>Deploy Service</h3>
            <p>Rollout to target instances</p>
            <div className="form-group">
              <input
                type="text"
                placeholder="e.g., SCOUT-US, SCOUT-EU"
                value={targetInstances}
                onChange={(e) => setTargetInstances(e.target.value)}
              />
            </div>
            <button
              className="btn btn-success"
              onClick={handleRolloutService}
              disabled={rolloutRunning}
            >
              {rolloutRunning ? 'Deploying...' : 'Deploy'}
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
