'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8002';

/**
 * Google OAuth callback page.
 *
 * Google is configured to redirect here (FRONTEND_URL/auth/callback/google).
 * We receive the raw OAuth code + state nonce from Google, then forward them
 * to the backend's /auth/callback/google endpoint which:
 *   1. Verifies the state nonce against Redis
 *   2. Exchanges the code for a Google access token
 *   3. Fetches user info from Google
 *   4. Creates/updates the user in the DB
 *   5. Redirects to /auth/callback/success?code=<exchange_code>
 *
 * The exchange_code is then consumed by /auth/callback/success to get JWT tokens.
 */
export default function GoogleCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);
  const didRun = useRef(false);

  useEffect(() => {
    // Prevent double-execution in React StrictMode
    if (didRun.current) return;
    didRun.current = true;

    const errorParam = searchParams.get('error');
    if (errorParam) {
      setError(`Google sign-in failed: ${errorParam}`);
      setTimeout(() => router.replace(`/login?error=${encodeURIComponent(errorParam)}`), 2000);
      return;
    }

    const code = searchParams.get('code');
    const state = searchParams.get('state');

    if (!code) {
      setError('Missing authorization code from Google.');
      setTimeout(() => router.replace('/login?error=missing_code'), 2000);
      return;
    }

    // Forward the raw OAuth code + state to the backend callback endpoint.
    // The backend will verify the state nonce, exchange the code, and redirect
    // to /auth/callback/success?code=<exchange_code>
    const params = new URLSearchParams({ code });
    if (state) params.set('state', state);

    window.location.href = `${API_BASE_URL}/auth/callback/google?${params.toString()}`;
  }, [searchParams, router]);

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--bg-base)]">
        <div className="text-center">
          <p className="text-lg font-semibold" style={{ color: 'var(--critical)' }}>{error}</p>
          <p className="mt-2 text-sm" style={{ color: 'var(--text-secondary)' }}>Redirecting to login…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--bg-base)]">
      <div className="text-center">
        <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-[var(--accent)] border-t-transparent" />
        <p className="mt-4 text-sm" style={{ color: 'var(--text-secondary)' }}>
          Completing sign in with Google…
        </p>
      </div>
    </div>
  );
}
