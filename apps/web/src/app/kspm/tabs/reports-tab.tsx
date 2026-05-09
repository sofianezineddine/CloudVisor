'use client';

import * as React from 'react';

export function ReportsTab() {
  return (
    <div className="cv-container p-6">
      <h3 className="text-lg font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>Kubernetes Reports</h3>
      <p className="text-sm" style={{ color: 'var(--text-tertiary)' }}>
        Access Kubernetes security and compliance reports.
      </p>
    </div>
  );
}
