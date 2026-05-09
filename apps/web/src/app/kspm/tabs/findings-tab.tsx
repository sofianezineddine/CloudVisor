'use client';

import * as React from 'react';

export function FindingsTab() {
  return (
    <div className="cv-container p-6">
      <h3 className="text-lg font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>Kubernetes Findings</h3>
      <p className="text-sm" style={{ color: 'var(--text-tertiary)' }}>
        Detailed view of Kubernetes-related security findings and misconfigurations.
      </p>
    </div>
  );
}
