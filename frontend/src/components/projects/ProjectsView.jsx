import React from 'react'
import OperationalView from '../common/OperationalView'

export default function ProjectsView() {
  return (
    <OperationalView
      eyebrow="Delivery"
      title="Project Tracker"
      description="Client projects, milestones, task queues, and delivery risk signals after a lead becomes a client."
      endpoints={[
        { key: 'tasks', label: 'Project and delivery tasks', path: '/api/v1/tasks/' },
        { key: 'deals', label: 'Open CRM deals', path: '/api/v1/crm/deals' },
        { key: 'pipeline', label: 'Pipeline stats', path: '/api/v1/crm/deals/pipeline' },
      ]}
    />
  )
}
