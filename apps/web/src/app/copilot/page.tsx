'use client';

import * as React from 'react';
import { AppLayout } from '@/components/layout';
import { ProtectedRoute } from '@/components/protected-route';

export default function CopilotPage() {
  React.useEffect(() => {
    document.title = 'CloudVisor Q - CloudVisor';
  }, []);

  return (
    <ProtectedRoute>
      <AppLayout breadcrumbs={[{ text: 'Home', href: '/console' }, { text: 'CloudVisor Q' }]}>
        <div className="space-y-6">
          <div>
            <h1 className="text-h1" style={{ color: 'var(--text-primary)' }}>CloudVisor Q</h1>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              AI-powered security copilot
            </p>
          </div>
          <div className="cv-container p-12 text-center">
            <p className="text-sm" style={{ color: 'var(--text-tertiary)' }}>
              CloudVisor Q copilot coming soon
            </p>
          </div>
        </div>
      </AppLayout>
    </ProtectedRoute>
  );
}
