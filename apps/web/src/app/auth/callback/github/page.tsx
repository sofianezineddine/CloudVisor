'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8002';

export default function GitHubCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const code = searchParams.get('code');
    const state = searchParams.get('state');

    if (!code) {
      setError('Missing authorization code');
      setTimeout(() => router.push('/login'), 3000);
      return;
    }

    // Redirect to backend callback to exchange code for tokens
    const provider = state || 'github';
    window.location.href = `${API_BASE_URL}/auth/callback/${provider}?code=${code}&state=${provider}`;
  }, [searchParams, router]);

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--bg-base)]">
        <div className="text-center">
          <div className="text-red-500 text-lg font-semibold">Error: {error}</div>
          <p className="mt-2 text-[var(--text-secondary)]">Redirecting to login...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--bg-base)]">
      <div className="text-center">
        <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-[var(--accent)] border-t-transparent" />
        <p className="mt-4 text-[var(--text-secondary)]">Completing sign in with GitHub...</p>
      </div>
    </div>
  );
}
