/**
 * Real-time Monitoring API
 * Connects to backend metrics and displays live system state
 */

import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const monitoringApi = {
  // System Health
  getSystemHealth: async () => {
    return axios.get(`${API_BASE}/api/v1/health`);
  },

  getReadiness: async () => {
    return axios.get(`${API_BASE}/api/v1/readyz`);
  },

  // Operational IQ
  getOperationalIQ: async () => {
    return axios.get(`${API_BASE}/api/v1/monitoring/operational-iq`);
  },

  // Real-time Telemetry
  getTelemetry: async () => {
    return axios.get(`${API_BASE}/api/v1/monitoring/telemetry`);
  },

  // Alerts & Events
  getActiveAlerts: async (severity = null) => {
    const params = severity ? { severity } : {};
    return axios.get(`${API_BASE}/api/v1/monitoring/alerts`, { params });
  },

  acknowledgeAlert: async (alertId) => {
    return axios.post(`${API_BASE}/api/v1/monitoring/alerts/${alertId}/acknowledge`);
  },

  // Metrics
  getMetricsRange: async (metricName, start, end) => {
    return axios.get(`${API_BASE}/api/v1/monitoring/metrics/${metricName}`, {
      params: { start, end },
    });
  },

  // Performance
  getPerformanceMetrics: async () => {
    return axios.get(`${API_BASE}/api/v1/monitoring/performance`);
  },

  // Cost Tracking
  getCostMetrics: async (provider = null) => {
    const params = provider ? { provider } : {};
    return axios.get(`${API_BASE}/api/v1/monitoring/costs`, { params });
  },

  // Job Status
  getJobStatus: async () => {
    return axios.get(`${API_BASE}/api/v1/monitoring/jobs`);
  },

  // Agent Status
  getAgentStatus: async () => {
    return axios.get(`${API_BASE}/api/v1/monitoring/agents`);
  },

  // WebSocket Connection
  connectToLiveUpdates: (callbacks) => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws/monitoring`);

    ws.onopen = () => {
      console.log('Monitoring WebSocket connected');
      if (callbacks.onOpen) callbacks.onOpen();
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (callbacks.onMessage) callbacks.onMessage(data);
      } catch (e) {
        console.error('Failed to parse monitoring message:', e);
      }
    };

    ws.onerror = (error) => {
      console.error('Monitoring WebSocket error:', error);
      if (callbacks.onError) callbacks.onError(error);
    };

    ws.onclose = () => {
      console.log('Monitoring WebSocket closed');
      if (callbacks.onClose) callbacks.onClose();
    };

    return ws;
  },
};

export default monitoringApi;
