'use client';

import * as React from 'react';

export function AssetsTab() {
  return (
    <div className="cv-container p-6">
      <h3 className="text-lg font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>Kubernetes Assets</h3>
      <p className="text-sm" style={{ color: 'var(--text-tertiary)' }}>
        Inventory of clusters, namespaces, pods, and other Kubernetes resources.
      </p>
    </div>
  );
}
