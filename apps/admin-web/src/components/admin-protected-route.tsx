'use client';

import { useAdminAuth } from '@/hooks/use-admin-auth';
import { useRouter, usePathname } from 'next/navigation';
import { useEffect } from 'react';

export function AdminProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAdminAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/admin/login');
    }
  }, [isLoading, isAuthenticated, router, pathname]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[hsl(var(--bg-base))]">
        <div className="text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-[hsl(var(--accent))] border-t-transparent" />
          <p className="mt-4 text-sm text-[hsl(var(--text-secondary))]">Loading admin dashboard...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return <>{children}</>;
}
