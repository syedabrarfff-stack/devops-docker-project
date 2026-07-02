/**
 * ServiceCreation Form - Create new services
 * Supports template selection and customization
 */

import React, { useState } from 'react';
import useJarvisStore from '../../store/useJarvisStore';
import { createService } from '../../services/serviceRegistryApi';
import './ServiceRegistry.css';

const SERVICE_TYPES = ['autonomous', 'human_supervised', 'hybrid'];
const DIVISIONS = [
  'Revenue Operations',
  'AI Automation',
  'Cloud & DevOps',
  'Security & Compliance',
  'Intelligence & Data',
  'Digital Products',
  'Strategic Intelligence',
];

export default function ServiceCreationForm({ onSuccess }) {
  const { tenant } = useJarvisStore();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [formData, setFormData] = useState({
    code: '',
    name: '',
    division: DIVISIONS[0],
    description: '',
    service_type: 'autonomous',
    human_interface_executive: '',
    agent_layer: [],
    kpi_targets: [],
    metadata: {},
  });
  const [agentInput, setAgentInput] = useState('');
  const [kpiInput, setKpiInput] = useState('');

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData({
      ...formData,
      [name]: value,
    });
  };

  const handleAddAgent = () => {
    if (agentInput.trim()) {
      setFormData({
        ...formData,
        agent_layer: [...(formData.agent_layer || []), agentInput.trim()],
      });
      setAgentInput('');
    }
  };

  const handleRemoveAgent = (index) => {
    setFormData({
      ...formData,
      agent_layer: formData.agent_layer.filter((_, i) => i !== index),
    });
  };

  const handleAddKpi = () => {
    if (kpiInput.trim()) {
      setFormData({
        ...formData,
        kpi_targets: [...(formData.kpi_targets || []), kpiInput.trim()],
      });
      setKpiInput('');
    }
  };

  const handleRemoveKpi = (index) => {
    setFormData({
      ...formData,
      kpi_targets: formData.kpi_targets.filter((_, i) => i !== index),
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    // Validate required fields
    if (!formData.code.trim()) {
      setError('Service code is required');
      return;
    }
    if (!formData.name.trim()) {
      setError('Service name is required');
      return;
    }

    try {
      setLoading(true);
      await createService(formData, tenant.id);

      if (onSuccess) {
        onSuccess();
      } else {
        // Reset form
        setFormData({
          code: '',
          name: '',
          division: DIVISIONS[0],
          description: '',
          service_type: 'autonomous',
          human_interface_executive: '',
          agent_layer: [],
          kpi_targets: [],
          metadata: {},
        });
      }
    } catch (err) {
      setError(err.message || 'Failed to create service');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="service-creation-form">
      <div className="form-header">
        <h2>Create New Service</h2>
        <p>Add a new service to the dynamic registry</p>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <form onSubmit={handleSubmit} className="form-container">
        {/* Basic Information */}
        <fieldset className="form-section">
          <legend>Basic Information</legend>

          <div className="form-group">
            <label htmlFor="code">Service Code *</label>
            <input
              id="code"
              type="text"
              name="code"
              placeholder="e.g., SCOUT, HERALD"
              value={formData.code}
              onChange={handleInputChange}
              maxLength={50}
              required
            />
            <small>Unique identifier for this service</small>
          </div>

          <div className="form-group">
            <label htmlFor="name">Service Name *</label>
            <input
              id="name"
              type="text"
              name="name"
              placeholder="e.g., Lead Intelligence"
              value={formData.name}
              onChange={handleInputChange}
              maxLength={200}
              required
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="division">Division</label>
              <select
                id="division"
                name="division"
                value={formData.division}
                onChange={handleInputChange}
              >
                {DIVISIONS.map((div) => (
                  <option key={div} value={div}>
                    {div}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="service_type">Service Type</label>
              <select
                id="service_type"
                name="service_type"
                value={formData.service_type}
                onChange={handleInputChange}
              >
                {SERVICE_TYPES.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="description">Description</label>
            <textarea
              id="description"
              name="description"
              placeholder="What does this service do?"
              value={formData.description}
              onChange={handleInputChange}
              rows={4}
              maxLength={2000}
            />
          </div>

          <div className="form-group">
            <label htmlFor="human_interface_executive">Human Interface Executive</label>
            <input
              id="human_interface_executive"
              type="text"
              name="human_interface_executive"
              placeholder="e.g., Darren Mitchell"
              value={formData.human_interface_executive}
              onChange={handleInputChange}
              maxLength={200}
            />
          </div>
        </fieldset>

        {/* Agent Layer */}
        <fieldset className="form-section">
          <legend>Agent Layer</legend>
          <div className="form-group">
            <label>Capable Agents</label>
            <div className="array-input">
              <input
                type="text"
                placeholder="e.g., Email sequencing"
                value={agentInput}
                onChange={(e) => setAgentInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddAgent())}
              />
              <button
                type="button"
                className="btn-add"
                onClick={handleAddAgent}
              >
                Add
              </button>
            </div>
            {formData.agent_layer && formData.agent_layer.length > 0 && (
              <div className="tag-list">
                {formData.agent_layer.map((agent, idx) => (
                  <div key={idx} className="tag">
                    {agent}
                    <button
                      type="button"
                      className="tag-remove"
                      onClick={() => handleRemoveAgent(idx)}
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </fieldset>

        {/* KPI Targets */}
        <fieldset className="form-section">
          <legend>KPI Targets</legend>
          <div className="form-group">
            <label>Target KPIs</label>
            <div className="array-input">
              <input
                type="text"
                placeholder="e.g., 20 qualified discoveries/day"
                value={kpiInput}
                onChange={(e) => setKpiInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddKpi())}
              />
              <button
                type="button"
                className="btn-add"
                onClick={handleAddKpi}
              >
                Add
              </button>
            </div>
            {formData.kpi_targets && formData.kpi_targets.length > 0 && (
              <div className="tag-list">
                {formData.kpi_targets.map((kpi, idx) => (
                  <div key={idx} className="tag">
                    {kpi}
                    <button
                      type="button"
                      className="tag-remove"
                      onClick={() => handleRemoveKpi(idx)}
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </fieldset>

        {/* Form Actions */}
        <div className="form-actions">
          <button
            type="submit"
            className="btn btn-primary"
            disabled={loading}
          >
            {loading ? 'Creating...' : 'Create Service'}
          </button>
          <a href="#/services" className="btn btn-secondary">
            Cancel
          </a>
        </div>
      </form>
    </div>
  );
}
