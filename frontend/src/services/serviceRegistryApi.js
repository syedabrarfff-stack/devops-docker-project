/**
 * Service Registry API helpers
 * Wraps all service registry endpoints
 */

import api from './api';

const SERVICE_REGISTRY_PREFIX = '/services';

/**
 * Create a new service
 */
export const createService = async (serviceData, tenantId) => {
  const response = await api.post(
    `${SERVICE_REGISTRY_PREFIX}/create`,
    serviceData,
    {
      params: { tenant_id: tenantId },
    }
  );
  return response.data;
};

/**
 * Get all services with optional filtering
 */
export const listServices = async (tenantId, options = {}) => {
  const params = {
    tenant_id: tenantId,
    ...options,
  };

  const response = await api.get(`${SERVICE_REGISTRY_PREFIX}/registry`, {
    params,
  });
  return response.data;
};

/**
 * Get single service by ID
 */
export const getService = async (serviceId, tenantId) => {
  const response = await api.get(`${SERVICE_REGISTRY_PREFIX}/${serviceId}`, {
    params: { tenant_id: tenantId },
  });
  return response.data;
};

/**
 * Update service properties
 */
export const updateService = async (serviceId, updateData, tenantId) => {
  const response = await api.patch(
    `${SERVICE_REGISTRY_PREFIX}/${serviceId}`,
    updateData,
    {
      params: { tenant_id: tenantId },
    }
  );
  return response.data;
};

/**
 * Delete (soft delete) a service
 */
export const deleteService = async (serviceId, tenantId) => {
  const response = await api.delete(
    `${SERVICE_REGISTRY_PREFIX}/${serviceId}`,
    {
      params: { tenant_id: tenantId },
    }
  );
  return response.data;
};

/**
 * Test a service before deployment
 */
export const testService = async (serviceId, testConfig, tenantId) => {
  const response = await api.post(
    `${SERVICE_REGISTRY_PREFIX}/${serviceId}/test`,
    testConfig,
    {
      params: { tenant_id: tenantId },
    }
  );
  return response.data;
};

/**
 * Rollout/deploy a service to instances
 */
export const rolloutService = async (serviceId, rolloutConfig, tenantId) => {
  const response = await api.post(
    `${SERVICE_REGISTRY_PREFIX}/${serviceId}/rollout`,
    rolloutConfig,
    {
      params: { tenant_id: tenantId },
    }
  );
  return response.data;
};

/**
 * Get service metrics
 */
export const getServiceMetrics = async (serviceId, tenantId, days = 30) => {
  // This would call a separate metrics endpoint
  // For now, returning mock data structure
  return {
    serviceId,
    metricDate: new Date(),
    totalExecutions: 0,
    successfulExecutions: 0,
    failedExecutions: 0,
    successRate: 100,
    avgExecutionTimeMs: 0,
    errorRate: 0,
    dailyCost: 0,
    activeUsers: 0,
  };
};

export default {
  createService,
  listServices,
  getService,
  updateService,
  deleteService,
  testService,
  rolloutService,
  getServiceMetrics,
};
