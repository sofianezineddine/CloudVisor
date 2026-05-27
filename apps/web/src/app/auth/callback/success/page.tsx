'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

import { authAPI } from '@/lib/api/auth';

/**
 * OAuth callback success page.
 *
 * Flow:
 * 1. Backend redirects here with ?code=<exchange_code>
 * 2. We POST to /auth/oauth/exchange (same origin via nginx — relative URL)
 * 3. Server sets HttpOnly cookies (cv_access, cv_refresh) in response
 * 4. We set cv_session cookie (JS-readable session indicator)
 * 5. Redirect to /console
 *
 * NO tokens are stored in localStorage — everything is in HttpOnly cookies.
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

    // Exchange code via authAPI — uses relative URL (/auth/oauth/exchange)
    // All API calls go through nginx on the same origin — no CORS issues.
    authAPI.exchangeOAuthCode(exchangeCode)
      .then((data) => {
        // authAPI.exchangeOAuthCode already parsed the JSON response
        // Server set HttpOnly cookies (cv_access, cv_refresh) in the response

        // Set session indicator cookie (non-HttpOnly, JS-readable)
        document.cookie = 'cv_session=1; path=/; max-age=3600; samesite=lax';

        // Note: The exchange endpoint returns TokenResponse (no user object).
        // User profile is fetched separately by AuthProvider via /auth/me.
        // Store ONLY non-sensitive display data (name, org) — NO tokens
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
        window.location.href = '/console';
      })
      .catch((err) => {
        console.error('OAuth exchange failed:', err instanceof Error ? err.message : err);
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
