import React from 'react'
import OperationalView from '../common/OperationalView'

export default function IntelView() {
  return (
    <OperationalView
      eyebrow="Market Awareness"
      title="Market Intelligence"
      description="Market pulse, technology radar, competitor profiles, and recommendations that inform revenue decisions."
      endpoints={[
        { key: 'pulse', label: 'Intelligence pulse', path: '/api/v1/intelligence/pulse' },
        { key: 'radar', label: 'Technology radar', path: '/api/v1/intelligence/radar' },
        { key: 'recommendations', label: 'Recommendations', path: '/api/v1/intelligence/recommendations' },
      ]}
    />
  )
}
