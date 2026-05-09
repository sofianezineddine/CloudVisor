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
      setTimeout(() => router.replace('/login'), 3000);
      return;
    }

    // Redirect to backend to exchange the authorization code for tokens.
    // This is an intentional external redirect — the backend will redirect back
    // to /auth/callback/success with tokens in the URL hash.
    const provider = state || 'github';
    window.location.href = `${API_BASE_URL}/auth/callback/${provider}?code=${encodeURIComponent(code)}&state=${encodeURIComponent(provider)}`;
  }, [searchParams, router]);

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--bg-base)]">
        <div className="text-center">
          <p className="text-lg font-semibold" style={{ color: 'var(--critical)' }}>
            {error}
          </p>
          <p className="mt-2 text-sm" style={{ color: 'var(--text-secondary)' }}>
            Redirecting to login...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--bg-base)]">
      <div className="text-center">
        <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-[var(--accent)] border-t-transparent" />
        <p className="mt-4 text-sm" style={{ color: 'var(--text-secondary)' }}>
          Completing sign in with GitHub...
        </p>
      </div>
    </div>
  );
}
