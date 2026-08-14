/**
 * Integration tests for Service Registry components
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock the API
jest.mock('../../../services/serviceRegistryApi', () => ({
  listServices: jest.fn(),
  getService: jest.fn(),
  createService: jest.fn(),
  updateService: jest.fn(),
  deleteService: jest.fn(),
  testService: jest.fn(),
  rolloutService: jest.fn(),
  getServiceMetrics: jest.fn(),
}));

// Mock the store
jest.mock('../../../store/useJarvisStore', () => ({
  __esModule: true,
  default: () => ({
    tenant: { id: 'test-tenant-123' },
  }),
}));

import {
  ServiceRegistryView,
  ServiceCreationForm,
  ServiceManagementDashboard,
  ServiceMetricsVisualization,
  ServiceDependencyGraph,
} from '../index';
import * as api from '../../../services/serviceRegistryApi';

const mockService = {
  id: 'service-1',
  code: 'SCOUT',
  name: 'Lead Intelligence',
  division: 'Revenue Operations',
  status: 'active',
  service_type: 'autonomous',
  description: 'Finds and scores prospects',
  success_rate: 95.5,
  avg_execution_time_ms: 250,
  agent_layer: ['Lead discovery', 'ICP scoring'],
  kpi_targets: ['20 qualified discoveries/day'],
};

const mockMetrics = {
  serviceId: 'service-1',
  totalExecutions: 1000,
  successfulExecutions: 955,
  failedExecutions: 45,
  successRate: 95.5,
  avgExecutionTimeMs: 250,
  errorRate: 4.5,
  dailyCost: 50.0,
  activeUsers: 42,
};

describe('ServiceRegistryView', () => {
  it('renders service list', async () => {
    api.listServices.mockResolvedValue({
      services: [mockService],
      divisions: { 'Revenue Operations': 1 },
    });

    render(<ServiceRegistryView />);

    await waitFor(() => {
      expect(screen.getByText('Service Registry')).toBeInTheDocument();
    });
  });

  it('displays loading state', () => {
    api.listServices.mockImplementationOnce(
      () => new Promise(() => {}) // Never resolves
    );

    render(<ServiceRegistryView />);
    expect(screen.getByText(/loading services/i)).toBeInTheDocument();
  });

  it('displays error state', async () => {
    api.listServices.mockRejectedValue(new Error('API Error'));

    render(<ServiceRegistryView />);

    await waitFor(() => {
      expect(screen.getByText(/API Error/i)).toBeInTheDocument();
    });
  });

  it('filters services by status', async () => {
    api.listServices.mockResolvedValue({
      services: [mockService],
      divisions: {},
    });

    render(<ServiceRegistryView />);

    const statusSelect = screen.getByDisplayValue('All Status');
    fireEvent.change(statusSelect, { target: { value: 'active' } });

    await waitFor(() => {
      expect(api.listServices).toHaveBeenCalledWith('test-tenant-123', {
        status_filter: 'active',
      });
    });
  });

  it('allows deleting a service', async () => {
    api.listServices.mockResolvedValue({
      services: [mockService],
      divisions: {},
    });
    api.deleteService.mockResolvedValue({});

    render(<ServiceRegistryView />);

    await waitFor(() => {
      expect(screen.getByText('SCOUT')).toBeInTheDocument();
    });

    const deprecateButton = screen.getByText('Deprecate');
    window.confirm = jest.fn(() => true);

    fireEvent.click(deprecateButton);

    await waitFor(() => {
      expect(api.deleteService).toHaveBeenCalledWith(
        'service-1',
        'test-tenant-123'
      );
    });
  });
});

describe('ServiceCreationForm', () => {
  it('renders form with required fields', () => {
    render(<ServiceCreationForm />);

    expect(screen.getByLabelText(/Service Code/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Service Name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Division/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Service Type/i)).toBeInTheDocument();
  });

  it('validates required fields', async () => {
    render(<ServiceCreationForm />);

    const submitButton = screen.getByText(/Create Service/i);
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(
        screen.getByText(/Service code is required/i)
      ).toBeInTheDocument();
    });
  });

  it('submits form with valid data', async () => {
    api.createService.mockResolvedValue(mockService);

    const onSuccess = jest.fn();
    render(<ServiceCreationForm onSuccess={onSuccess} />);

    const codeInput = screen.getByPlaceholderText(/e.g., SCOUT/i);
    const nameInput = screen.getByPlaceholderText(/e.g., Lead Intelligence/i);

    fireEvent.change(codeInput, { target: { value: 'TEST-SERVICE' } });
    fireEvent.change(nameInput, { target: { value: 'Test Service' } });

    const submitButton = screen.getByText(/Create Service/i);
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(api.createService).toHaveBeenCalled();
      expect(onSuccess).toHaveBeenCalled();
    });
  });

  it('allows adding agent layer items', async () => {
    render(<ServiceCreationForm />);

    const agentInput = screen.getByPlaceholderText(/e.g., Email sequencing/i);
    const addButton = screen.getByText('Add').parentElement.querySelector('.btn-add');

    fireEvent.change(agentInput, { target: { value: 'Test Agent' } });
    fireEvent.click(addButton);

    await waitFor(() => {
      expect(screen.getByText('Test Agent')).toBeInTheDocument();
    });
  });
});

describe('ServiceManagementDashboard', () => {
  it('loads and displays service details', async () => {
    api.getService.mockResolvedValue(mockService);

    render(<ServiceManagementDashboard serviceId="service-1" />);

    await waitFor(() => {
      expect(screen.getByText('Lead Intelligence')).toBeInTheDocument();
      expect(screen.getByText('SCOUT')).toBeInTheDocument();
    });
  });

  it('allows editing service', async () => {
    api.getService.mockResolvedValue(mockService);
    api.updateService.mockResolvedValue({
      ...mockService,
      name: 'Updated Name',
    });

    render(<ServiceManagementDashboard serviceId="service-1" />);

    await waitFor(() => {
      expect(screen.getByText('Lead Intelligence')).toBeInTheDocument();
    });

    const editButton = screen.getByText(/Edit/i);
    fireEvent.click(editButton);

    const nameInput = screen.getByDisplayValue('Lead Intelligence');
    fireEvent.change(nameInput, { target: { value: 'Updated Name' } });

    const saveButton = screen.getByText(/Save/i);
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(api.updateService).toHaveBeenCalled();
    });
  });

  it('runs service test', async () => {
    api.getService.mockResolvedValue(mockService);
    api.testService.mockResolvedValue({
      status: 'success',
      duration_ms: 150,
      message: 'Test passed',
    });

    window.alert = jest.fn();

    render(<ServiceManagementDashboard serviceId="service-1" />);

    await waitFor(() => {
      expect(screen.getByText('Lead Intelligence')).toBeInTheDocument();
    });

    const testButton = screen.getByText(/Run Test/i);
    fireEvent.click(testButton);

    await waitFor(() => {
      expect(api.testService).toHaveBeenCalledWith(
        'service-1',
        { test_mode: 'dry_run' },
        'test-tenant-123'
      );
    });
  });

  it('initiates service rollout', async () => {
    api.getService.mockResolvedValue(mockService);
    api.rolloutService.mockResolvedValue({
      deployment_id: 'deploy-123',
      status: 'pending',
    });

    window.alert = jest.fn();

    render(<ServiceManagementDashboard serviceId="service-1" />);

    await waitFor(() => {
      expect(screen.getByText('Lead Intelligence')).toBeInTheDocument();
    });

    const instancesInput = screen.getByPlaceholderText(
      /e.g., SCOUT-US, SCOUT-EU/i
    );
    const deployButton = screen.getByText(/Deploy/i);

    fireEvent.change(instancesInput, { target: { value: 'SCOUT-US' } });
    fireEvent.click(deployButton);

    await waitFor(() => {
      expect(api.rolloutService).toHaveBeenCalled();
    });
  });
});

describe('ServiceMetricsVisualization', () => {
  it('loads and displays metrics', async () => {
    api.getServiceMetrics.mockResolvedValue(mockMetrics);

    render(
      <ServiceMetricsVisualization
        serviceId="service-1"
        tenantId="test-tenant-123"
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/Success Rate/i)).toBeInTheDocument();
    });
  });

  it('displays metrics cards with values', async () => {
    api.getServiceMetrics.mockResolvedValue(mockMetrics);

    render(
      <ServiceMetricsVisualization
        serviceId="service-1"
        tenantId="test-tenant-123"
      />
    );

    await waitFor(() => {
      expect(screen.getByText('95.5%')).toBeInTheDocument(); // success rate
      expect(screen.getByText('250ms')).toBeInTheDocument(); // execution time
    });
  });

  it('changes time range', async () => {
    api.getServiceMetrics.mockResolvedValue(mockMetrics);

    render(
      <ServiceMetricsVisualization
        serviceId="service-1"
        tenantId="test-tenant-123"
      />
    );

    const timeRangeSelect = screen.getByDisplayValue('Last 30 days');
    fireEvent.change(timeRangeSelect, { target: { value: 90 } });

    await waitFor(() => {
      expect(api.getServiceMetrics).toHaveBeenCalledWith(
        'service-1',
        'test-tenant-123',
        90
      );
    });
  });

  it('shows alerts for high error rates', async () => {
    api.getServiceMetrics.mockResolvedValue({
      ...mockMetrics,
      errorRate: 15.0,
    });

    render(
      <ServiceMetricsVisualization
        serviceId="service-1"
        tenantId="test-tenant-123"
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/Error rate is above 5%/i)).toBeInTheDocument();
    });
  });
});

describe('ServiceDependencyGraph', () => {
  it('loads and displays dependencies', async () => {
    api.listServices.mockResolvedValue({
      services: [mockService],
      divisions: {},
    });

    render(<ServiceDependencyGraph tenantId="test-tenant-123" />);

    await waitFor(() => {
      expect(screen.getByText('Service Dependency Map')).toBeInTheDocument();
    });
  });

  it('displays service selector', async () => {
    api.listServices.mockResolvedValue({
      services: [mockService],
      divisions: {},
    });

    render(<ServiceDependencyGraph tenantId="test-tenant-123" />);

    await waitFor(() => {
      expect(screen.getByDisplayValue(/SCOUT/i)).toBeInTheDocument();
    });
  });

  it('toggles critical dependencies filter', async () => {
    api.listServices.mockResolvedValue({
      services: [mockService],
      divisions: {},
    });

    render(<ServiceDependencyGraph tenantId="test-tenant-123" />);

    await waitFor(() => {
      const checkbox = screen.getByRole('checkbox');
      fireEvent.click(checkbox);
      expect(checkbox).toBeChecked();
    });
  });
});
