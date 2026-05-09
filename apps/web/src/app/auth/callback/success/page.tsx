'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

export default function OAuthCallbackSuccessPage() {
  const [status, setStatus] = useState('Processing OAuth callback...');
  const router = useRouter();

  useEffect(() => {
    // Extract tokens from URL hash (set by backend OAuth callback)
    const hash = window.location.hash.substring(1);
    const params = new URLSearchParams(hash);

    const accessToken = params.get('access_token');
    const refreshToken = params.get('refresh_token');

    if (accessToken && refreshToken) {
      setStatus('Login successful! Redirecting to dashboard...');

      // Store tokens
      localStorage.setItem('access_token', accessToken);
      localStorage.setItem('refresh_token', refreshToken);

      // Clear the hash from URL to avoid tokens appearing in browser history
      window.history.replaceState(null, '', window.location.pathname);

      // Full reload so AuthProvider picks up the new tokens from localStorage
      window.location.href = '/console';
    } else {
      setStatus('Authentication failed. Redirecting to login...');
      setTimeout(() => {
        router.replace('/login?error=oauth_failed');
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
