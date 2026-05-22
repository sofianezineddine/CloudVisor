'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8002';

/**
 * OAuth callback success page.
 *
 * The backend redirects here with a short-lived one-time exchange code:
 *   /auth/callback/success?code=<exchange_code>
 *
 * We POST that code to /auth/oauth/exchange which:
 * 1. Validates the code
 * 2. Sets HttpOnly cookies (cv_access, cv_refresh, cv_csrf, cv_session)
 * 3. Returns user info (no tokens in response body)
 *
 * Tokens are NEVER accessible to JavaScript — they're in HttpOnly cookies.
 */
export default function OAuthCallbackSuccessPage() {
  const [status, setStatus] = useState('Completing sign-in…');
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const exchangeCode = searchParams.get('code');
    const errorParam = searchParams.get('error');

    if (errorParam) {
      setStatus('Authentication failed. Redirecting to login…');
      setTimeout(() => router.replace(`/login?error=${encodeURIComponent(errorParam)}`), 2000);
      return;
    }

    if (!exchangeCode) {
      setStatus('Missing exchange code. Redirecting to login…');
      setTimeout(() => router.replace('/login?error=missing_code'), 2000);
      return;
    }

    // Exchange the one-time code — server sets HttpOnly cookies in response
    fetch(`${API_BASE_URL}/auth/oauth/exchange`, {
      method: 'POST',
      credentials: 'include', // IMPORTANT: receive Set-Cookie from server
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code: exchangeCode }),
    })
      .then(async (res) => {
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: 'Exchange failed' }));
          throw new Error(err.detail || 'Token exchange failed');
        }
        return res.json();
      })
      .then((data) => {
        // Store only non-sensitive user display data in localStorage
        if (data?.user) {
          localStorage.setItem('cloudvisor-user', JSON.stringify({
            id: data.user.id,
            organization_id: data.user.organization_id,
            organization_name: data.user.organization_name,
            role: data.user.role,
            name: `${data.user.first_name || ''} ${data.user.last_name || ''}`.trim(),
            email: data.user.email,
          }));
        }

        setStatus('Sign-in successful! Redirecting…');
        // Full reload so AuthProvider detects the cv_session cookie
        window.location.href = '/console';
      })
      .catch((err) => {
        console.error('OAuth exchange failed:', err);
        setStatus('Authentication failed. Redirecting to login…');
        setTimeout(() => router.replace('/login?error=oauth_failed'), 2000);
      });
  }, [searchParams, router]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--bg-base)]">
      <div className="text-center">
        <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-[var(--accent)] border-t-transparent" />
        <p className="mt-4 text-sm" style={{ color: 'var(--text-secondary)' }}>{status}</p>
      </div>
    </div>
  );
}
