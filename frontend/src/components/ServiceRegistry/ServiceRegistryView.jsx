/**
 * ServiceRegistry View - Display all services in a list
 * Shows: code, name, division, status, metrics
 */

import React, { useState, useEffect } from 'react';
import useJarvisStore from '../../store/useJarvisStore';
import { listServices, deleteService } from '../../services/serviceRegistryApi';
import './ServiceRegistry.css';

export default function ServiceRegistryView() {
  const { tenant } = useJarvisStore();
  const [services, setServices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({
    status: 'all',
    division: 'all',
  });

  // Fetch services on mount
  useEffect(() => {
    const fetchServices = async () => {
      try {
        setLoading(true);
        const params = {};
        if (filters.status !== 'all') params.status_filter = filters.status;
        if (filters.division !== 'all') params.division = filters.division;

        const data = await listServices(tenant.id, params);
        setServices(data.services || []);
        setError(null);
      } catch (err) {
        setError(err.message);
        setServices([]);
      } finally {
        setLoading(false);
      }
    };

    fetchServices();
  }, [tenant.id, filters]);

  const handleDeleteService = async (serviceId) => {
    if (!window.confirm('Deprecate this service? This cannot be undone.')) {
      return;
    }

    try {
      await deleteService(serviceId, tenant.id);
      setServices(services.filter(s => s.id !== serviceId));
    } catch (err) {
      setError(`Failed to delete service: ${err.message}`);
    }
  };

  const getStatusBadge = (status) => {
    const badges = {
      active: 'badge-success',
      beta: 'badge-warning',
      deprecated: 'badge-danger',
      archived: 'badge-secondary',
    };
    return badges[status] || 'badge-secondary';
  };

  return (
    <div className="service-registry-view">
      <div className="view-header">
        <h1>Service Registry</h1>
        <p className="subtitle">Manage dynamic services and instances</p>
      </div>

      {/* Filters */}
      <div className="filters-bar">
        <select
          className="filter-select"
          value={filters.status}
          onChange={(e) => setFilters({ ...filters, status: e.target.value })}
        >
          <option value="all">All Status</option>
          <option value="active">Active</option>
          <option value="beta">Beta</option>
          <option value="deprecated">Deprecated</option>
        </select>

        <select
          className="filter-select"
          value={filters.division}
          onChange={(e) => setFilters({ ...filters, division: e.target.value })}
        >
          <option value="all">All Divisions</option>
          <option value="Revenue Operations">Revenue Operations</option>
          <option value="AI Automation">AI Automation</option>
          <option value="Cloud & DevOps">Cloud & DevOps</option>
          <option value="Security & Compliance">Security & Compliance</option>
          <option value="Intelligence & Data">Intelligence & Data</option>
          <option value="Digital Products">Digital Products</option>
          <option value="Strategic Intelligence">Strategic Intelligence</option>
        </select>

        <span className="service-count">{services.length} services</span>
      </div>

      {/* Loading/Error States */}
      {loading && <div className="loading-spinner">Loading services...</div>}
      {error && <div className="error-banner">{error}</div>}

      {/* Services Table */}
      {!loading && services.length > 0 && (
        <div className="services-table">
          <table>
            <thead>
              <tr>
                <th>Code</th>
                <th>Name</th>
                <th>Division</th>
                <th>Type</th>
                <th>Status</th>
                <th>Success Rate</th>
                <th>Avg Time</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {services.map((service) => (
                <tr key={service.id} className={`service-row status-${service.status}`}>
                  <td className="code-column">
                    <code>{service.code}</code>
                  </td>
                  <td className="name-column">
                    <a href={`#/service/${service.id}`} className="service-link">
                      {service.name}
                    </a>
                  </td>
                  <td>{service.division}</td>
                  <td>
                    <span className="service-type">{service.service_type}</span>
                  </td>
                  <td>
                    <span className={`badge ${getStatusBadge(service.status)}`}>
                      {service.status}
                    </span>
                  </td>
                  <td>
                    {service.success_rate ? (
                      <span className="metric">{service.success_rate.toFixed(1)}%</span>
                    ) : (
                      <span className="metric-none">-</span>
                    )}
                  </td>
                  <td>
                    {service.avg_execution_time_ms ? (
                      <span className="metric">{service.avg_execution_time_ms}ms</span>
                    ) : (
                      <span className="metric-none">-</span>
                    )}
                  </td>
                  <td className="actions-column">
                    <a href={`#/service/${service.id}`} className="btn-small btn-info">
                      View
                    </a>
                    {service.status !== 'deprecated' && (
                      <button
                        className="btn-small btn-danger"
                        onClick={() => handleDeleteService(service.id)}
                      >
                        Deprecate
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Empty State */}
      {!loading && services.length === 0 && (
        <div className="empty-state">
          <p>No services found</p>
          <a href="#/service/create" className="btn btn-primary">
            Create First Service
          </a>
        </div>
      )}
    </div>
  );
}
