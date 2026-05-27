'use client';

import * as React from 'react';
import { ConfigProvider } from '@/app/config-provider';
import { ProtectedRoute } from '@/components/protected-route';
import { AppLayout } from '@/components/layout';
import { AIOpsWSProvider } from '@/components/aiops/ws-provider';
import './aiops-theme.css';

// ─── AIOps Layout ────────────────────────────────────────────────────────────
// Wraps AIOps pages with:
// 1. CloudVisor app shell (header, sidebar, footer)
// 2. Auth protection
// 3. ConfigProvider for Keep UI components
// 4. .aiops-scope CSS class for Tremor theme overrides

export default function AIOpsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ProtectedRoute>
      <AppLayout>
        <div className="aiops-scope h-full">
          <ConfigProvider config={{
            AUTH_TYPE: 'NOAUTH',
            PUSHER_DISABLED: false,
            PUSHER_HOST: process.env.NEXT_PUBLIC_PUSHER_HOST || 'localhost',
            PUSHER_PORT: parseInt(process.env.NEXT_PUBLIC_PUSHER_PORT || '6001'),
            PUSHER_APP_KEY: process.env.NEXT_PUBLIC_PUSHER_KEY || 'cloudvisor-key',
            PUSHER_CLUSTER: undefined,
            API_URL: process.env.NEXT_PUBLIC_API_GATEWAY_URL
              ? `${process.env.NEXT_PUBLIC_API_GATEWAY_URL}/v1/keep`
              : 'http://localhost/v1/keep',
            API_URL_CLIENT: process.env.NEXT_PUBLIC_API_URL_CLIENT || 'http://localhost/v1/keep',
            POSTHOG_KEY: undefined,
            POSTHOG_HOST: undefined,
            POSTHOG_DISABLED: 'true',
            SENTRY_DISABLED: 'true',
            READ_ONLY: false,
            OPEN_AI_API_KEY_SET: true,
            NOISY_ALERTS_ENABLED: false,
            KEEP_DOCS_URL: 'https://docs.keephq.dev',
            KEEP_CONTACT_US_URL: 'https://slack.keephq.dev/',
            KEEP_HIDE_SENSITIVE_FIELDS: false,
            KEEP_WORKFLOW_DEBUG: false,
            HIDE_NAVBAR_DEDUPLICATION: false,
            HIDE_NAVBAR_WORKFLOWS: false,
            HIDE_NAVBAR_SERVICE_TOPOLOGY: false,
            HIDE_NAVBAR_MAPPING: false,
            HIDE_NAVBAR_EXTRACTION: false,
            HIDE_NAVBAR_MAINTENANCE_WINDOW: false,
            HIDE_NAVBAR_AI_PLUGINS: false,
            KEEP_TICKETING_ENABLED: false,
            KEEP_WF_LIST_EXTENDED_INFO: false,
            ALERT_SIDEBAR_FIELDS: ['service','source','description','message','fingerprint','url','incidents','timeline','relatedServices'],
          }}>
            <AIOpsWSProvider>
              {children}
            </AIOpsWSProvider>
          </ConfigProvider>
        </div>
      </AppLayout>
    </ProtectedRoute>
  );
}
