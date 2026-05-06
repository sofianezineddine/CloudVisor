'use client';

import * as React from 'react';
import { ProtectedRoute } from '@/components/protected-route';
import { SettingsLayout } from '@/components/settings-layout';

export default function SettingsRootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ProtectedRoute>
      <SettingsLayout>{children}</SettingsLayout>
    </ProtectedRoute>
  );
}
