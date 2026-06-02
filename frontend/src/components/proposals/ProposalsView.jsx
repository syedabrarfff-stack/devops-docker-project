import React from 'react'
import OperationalView from '../common/OperationalView'

export default function ProposalsView() {
  return (
    <OperationalView
      eyebrow="Revenue"
      title="Proposal Center"
      description="Proposal records, generated PDF assets, approval status, and send readiness. Pricing stays internal until the client asks or becomes qualified."
      endpoints={[
        { key: 'governance_proposals', label: 'Governance proposal records', path: '/api/v1/governance/proposals' },
        { key: 'pending_approvals', label: 'Proposal approvals', path: '/api/v1/approvals', params: { status: 'pending' } },
      ]}
    />
  )
}
