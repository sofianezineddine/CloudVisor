'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAdminAuth } from '@/hooks/use-admin-auth';

export default function AdminRootPage() {
  const { isAuthenticated, isLoading } = useAdminAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading) {
      if (isAuthenticated) {
        router.replace('/admin/dashboard');
      } else {
        router.replace('/admin/login');
      }
    }
  }, [isLoading, isAuthenticated, router]);

  return (
    <div className="flex min-h-screen items-center justify-center" style={{ backgroundColor: 'var(--bg-base)' }}>
      <div className="text-center">
        <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-t-transparent" style={{ borderColor: 'var(--accent)', borderTopColor: 'transparent' }} />
        <p className="mt-4 text-sm" style={{ color: 'var(--text-secondary)' }}>Loading...</p>
      </div>
    </div>
  );
}
