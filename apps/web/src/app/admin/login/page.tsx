'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Shield } from 'lucide-react';
import { authAPI } from '@/lib/api/auth';

export default function AdminLoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const tokens = await authAPI.adminLogin(email, password);
      localStorage.setItem('admin_access_token', tokens.access_token);
      localStorage.setItem('admin_refresh_token', tokens.refresh_token);
      router.push('/admin/dashboard');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--bg-base)]">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-[var(--radius-container)] bg-[var(--accent)]">
            <Shield className="h-6 w-6 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">Admin Access</h1>
          <p className="mt-2 text-sm text-[var(--text-secondary)]">Enter your credentials to manage the platform</p>
        </div>

        <form onSubmit={handleSubmit} className="rounded-[var(--radius-container)] border border-[var(--border-default)] bg-[var(--bg-surface)] p-6">
          {error && (
            <div className="mb-4 rounded-md bg-[var(--critical-dim)] p-3 text-sm text-[var(--critical)]">
              {error}
            </div>
          )}

          <div className="mb-4">
            <label className="mb-2 block text-sm font-medium text-[var(--text-primary)]">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full rounded-md border border-[var(--border-default)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
              placeholder="admin@cloudvisor.io"
            />
          </div>

          <div className="mb-6">
            <label className="mb-2 block text-sm font-medium text-[var(--text-primary)]">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full rounded-md border border-[var(--border-default)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
              placeholder="••••••••"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-[var(--radius-button)] bg-[var(--btn-primary-bg)] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[var(--btn-primary-hover)] disabled:opacity-50"
          >
            {loading ? 'Signing in...' : 'Sign in'}
          </button>
        </form>

        <div className="mt-4 text-center">
          <a href="/" className="text-sm text-[var(--accent)] hover:underline">← Back to tenant dashboard</a>
        </div>
      </div>
    </div>
  );
}
