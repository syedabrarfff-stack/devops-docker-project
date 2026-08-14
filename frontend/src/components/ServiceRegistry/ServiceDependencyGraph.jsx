/**
 * ServiceDependency Graph - Visualize service-to-service dependencies
 * Shows: dependency relationships, critical paths, impact analysis
 */

import React, { useState, useEffect } from 'react';
import { listServices } from '../../services/serviceRegistryApi';
import './ServiceRegistry.css';

export default function ServiceDependencyGraph({ tenantId }) {
  const [services, setServices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedService, setSelectedService] = useState(null);
  const [showCriticalOnly, setShowCriticalOnly] = useState(false);

  useEffect(() => {
    const fetchServices = async () => {
      try {
        setLoading(true);
        const data = await listServices(tenantId);
        setServices(data.services || []);
        if (data.services && data.services.length > 0) {
          setSelectedService(data.services[0].id);
        }
        setError(null);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchServices();
  }, [tenantId]);

  if (loading) {
    return <div className="loading-spinner">Loading dependency graph...</div>;
  }

  const getSelectedService = () =>
    services.find((s) => s.id === selectedService);

  const getDependencies = () => {
    const selected = getSelectedService();
    if (!selected || !selected.dependencies) {
      return [];
    }

    // Parse dependencies from JSON
    const deps = Array.isArray(selected.dependencies)
      ? selected.dependencies
      : [];

    return showCriticalOnly
      ? deps.filter((d) => d.is_critical)
      : deps;
  };

  const dependencies = getDependencies();

  return (
    <div className="service-dependency-graph">
      <div className="graph-header">
        <h2>Service Dependency Map</h2>
        <p className="subtitle">Visualize service relationships and impact analysis</p>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div className="graph-controls">
        <div className="control-group">
          <label htmlFor="service-select">Select Service:</label>
          <select
            id="service-select"
            value={selectedService || ''}
            onChange={(e) => setSelectedService(e.target.value)}
          >
            {services.map((service) => (
              <option key={service.id} value={service.id}>
                {service.code} - {service.name}
              </option>
            ))}
          </select>
        </div>

        <label className="checkbox-control">
          <input
            type="checkbox"
            checked={showCriticalOnly}
            onChange={(e) => setShowCriticalOnly(e.target.checked)}
          />
          Show critical dependencies only
        </label>
      </div>

      {/* Selected Service Info */}
      {getSelectedService() && (
        <section className="graph-section">
          <h3>Selected Service</h3>
          <div className="service-node primary">
            <div className="node-header">
              <code>{getSelectedService().code}</code>
              <span className={`badge badge-${getSelectedService().status}`}>
                {getSelectedService().status}
              </span>
            </div>
            <div className="node-details">
              <p className="node-name">{getSelectedService().name}</p>
              <p className="node-division">{getSelectedService().division}</p>
              {getSelectedService().description && (
                <p className="node-description">
                  {getSelectedService().description}
                </p>
              )}
            </div>
          </div>
        </section>
      )}

      {/* Dependencies */}
      <section className="graph-section">
        <h3>
          Dependencies
          {dependencies.length > 0 && (
            <span className="dependency-count">({dependencies.length})</span>
          )}
        </h3>

        {dependencies.length === 0 ? (
          <div className="empty-message">
            {showCriticalOnly
              ? 'No critical dependencies found'
              : 'No dependencies found'}
          </div>
        ) : (
          <div className="dependencies-list">
            {dependencies.map((dep, idx) => {
              const depService = services.find(
                (s) => s.code === dep.depends_on_service_id
              );
              return (
                <div key={idx} className={`dependency-item critical-${dep.is_critical}`}>
                  <div className="dependency-arrow">→</div>
                  <div className="dependency-service">
                    {depService ? (
                      <>
                        <div className="service-code">{depService.code}</div>
                        <div className="service-name">{depService.name}</div>
                      </>
                    ) : (
                      <div className="service-unknown">
                        {dep.depends_on_service_id}
                      </div>
                    )}
                  </div>
                  <div className="dependency-type">
                    <span className="type-badge">{dep.dependency_type || 'operational'}</span>
                  </div>
                  {dep.is_critical && (
                    <div className="critical-flag">⚠️ CRITICAL</div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* Reverse Dependencies (What depends on this service) */}
      <section className="graph-section">
        <h3>Dependent Services</h3>
        <p className="section-hint">Services that depend on {getSelectedService()?.code}</p>

        {(() => {
          const reverseDeps = services.filter((s) => {
            if (!s.dependencies || !Array.isArray(s.dependencies)) return false;
            return s.dependencies.some((d) =>
              d.depends_on_service_id === selectedService
            );
          });

          if (reverseDeps.length === 0) {
            return <div className="empty-message">No services depend on this</div>;
          }

          return (
            <div className="reverse-dependencies">
              {reverseDeps.map((service) => (
                <div key={service.id} className="reverse-dep-item">
                  <div className="service-code">{service.code}</div>
                  <div className="service-name">{service.name}</div>
                  <span className={`badge badge-${service.status}`}>
                    {service.status}
                  </span>
                </div>
              ))}
            </div>
          );
        })()}
      </section>

      {/* Impact Analysis */}
      <section className="graph-section impact-section">
        <h2>Impact Analysis</h2>
        <div className="impact-card">
          <h4>If this service fails:</h4>
          {(() => {
            const criticalDeps = dependencies.filter((d) => d.is_critical);
            const reverseDeps = services.filter((s) => {
              if (!s.dependencies || !Array.isArray(s.dependencies)) return false;
              return s.dependencies.some((d) =>
                d.depends_on_service_id === selectedService &&
                d.is_critical
              );
            });

            return (
              <ul>
                {criticalDeps.length > 0 && (
                  <li>
                    🔴 This service will fail (depends on{' '}
                    {criticalDeps.length} critical service
                    {criticalDeps.length !== 1 ? 's' : ''})
                  </li>
                )}
                {reverseDeps.length > 0 && (
                  <li>
                    🔴 {reverseDeps.length} service
                    {reverseDeps.length !== 1 ? 's' : ''} will be affected
                  </li>
                )}
                {criticalDeps.length === 0 && reverseDeps.length === 0 && (
                  <li>✓ This is an independent service</li>
                )}
              </ul>
            );
          })()}
        </div>
      </section>

      {/* Legend */}
      <div className="graph-legend">
        <div className="legend-item">
          <span className="legend-marker primary">◆</span>
          <span>Selected Service</span>
        </div>
        <div className="legend-item">
          <span className="legend-marker secondary">◆</span>
          <span>Dependent Service</span>
        </div>
        <div className="legend-item">
          <span className="legend-marker">⚠️</span>
          <span>Critical Dependency</span>
        </div>
      </div>
    </div>
  );
}
