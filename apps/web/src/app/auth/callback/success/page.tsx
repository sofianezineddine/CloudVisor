'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

export default function OAuthCallbackSuccessPage() {
  const [status, setStatus] = useState('Processing OAuth callback...');
  const router = useRouter();

  useEffect(() => {
    // Extract tokens from URL hash
    const hash = window.location.hash.substring(1);
    console.log('OAuth callback hash:', hash);
    const params = new URLSearchParams(hash);

    const accessToken = params.get('access_token');
    const refreshToken = params.get('refresh_token');

    console.log('Access token:', accessToken ? 'present' : 'missing');
    console.log('Refresh token:', refreshToken ? 'present' : 'missing');

    if (accessToken && refreshToken) {
      setStatus('Login successful! Redirecting to dashboard...');
      // Store tokens
      localStorage.setItem('access_token', accessToken);
      localStorage.setItem('refresh_token', refreshToken);

      // Clear the hash from URL
      window.history.replaceState(null, '', window.location.pathname);

      // Force a page reload to ensure AuthProvider picks up the new tokens
      // This is more reliable than trying to sync the auth context
      window.location.href = '/console';
    } else {
      setStatus('No tokens received. Redirecting to login...');
      console.error('Missing tokens in redirect URL');
      console.log('Full URL:', window.location.href);
      setTimeout(() => {
        window.location.assign('/login?error=oauth_failed');
      }, 2000);
    }
  }, [router]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--bg-base)]">
      <div className="text-center">
        <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-[var(--accent)] border-t-transparent" />
        <p className="mt-4 text-[var(--text-secondary)]">{status}</p>
      </div>
    </div>
  );
}
