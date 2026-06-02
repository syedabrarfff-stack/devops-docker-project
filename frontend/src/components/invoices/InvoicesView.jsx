import React from 'react'
import OperationalView from '../common/OperationalView'

export default function InvoicesView() {
  return (
    <OperationalView
      eyebrow="Finance"
      title="Invoice Center"
      description="Invoice generation, send status, payment status, and revenue receipts for Aliyar Solutions."
      endpoints={[
        { key: 'governance_invoices', label: 'Governance invoice records', path: '/api/v1/governance/invoices' },
        { key: 'revenue_snapshot', label: 'Revenue snapshot', path: '/api/v1/revenue/snapshot' },
      ]}
    />
  )
}
