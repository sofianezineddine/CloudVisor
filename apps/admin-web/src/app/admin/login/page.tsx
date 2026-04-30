'use client';

import { useState } from 'react';
import { useAdminAuth } from '@/hooks/use-admin-auth';
import { useRouter } from 'next/navigation';

export default function AdminLoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { login } = useAdminAuth();
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await login(email, password);
      router.push('/admin/dashboard');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const inputStyle = {
    width: '100%', height: '32px', padding: '0 8px',
    border: '1px solid var(--border-default)', borderRadius: '2px',
    backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)',
    fontSize: '14px', fontFamily: 'var(--font-sans)',
  };

  return (
    <div className="flex min-h-screen items-center justify-center" style={{ backgroundColor: 'var(--bg-base)' }}>
      <div className="w-full max-w-[360px]"
        style={{ backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border-default)', borderRadius: '2px', padding: '32px', boxShadow: 'var(--shadow-md)' }}
      >
        {/* Logo */}
        <div className="mb-6 flex flex-col items-center gap-2">
          <div className="flex h-10 w-10 items-center justify-center" style={{ backgroundColor: '#232f3e', borderRadius: '2px' }}>
            <span className="text-sm font-bold" style={{ color: '#ff9900' }}>CV</span>
          </div>
          <h1 className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>CloudVisor Admin</h1>
          <p className="text-sm text-center" style={{ color: 'var(--text-secondary)' }}>Platform administration</p>
        </div>

        {error && (
          <div className="mb-4 p-3 text-sm" style={{ borderLeft: '4px solid var(--critical)', backgroundColor: 'var(--critical-bg)', color: 'var(--critical)', borderRadius: '2px' }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Email</label>
            <input type="email" value={email} onChange={e => setEmail(e.target.value)} required
              placeholder="admin@cloudvisor.io" style={inputStyle}
              onFocus={e => (e.currentTarget.style.outline = '2px solid var(--accent)')}
              onBlur={e => (e.currentTarget.style.outline = 'none')}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Password</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)} required
              placeholder="••••••••" style={inputStyle}
              onFocus={e => (e.currentTarget.style.outline = '2px solid var(--accent)')}
              onBlur={e => (e.currentTarget.style.outline = 'none')}
            />
          </div>
          <button type="submit" disabled={loading}
            className="flex w-full items-center justify-center text-sm font-semibold transition-colors disabled:opacity-60"
            style={{ height: '32px', backgroundColor: '#ec7211', color: '#ffffff', border: '1px solid #ec7211', borderRadius: '2px', cursor: loading ? 'not-allowed' : 'pointer', marginTop: '8px' }}
            onMouseEnter={e => { if (!loading) (e.currentTarget.style.backgroundColor = '#eb5f07'); }}
            onMouseLeave={e => { if (!loading) (e.currentTarget.style.backgroundColor = '#ec7211'); }}
          >
            {loading ? 'Signing in...' : 'Sign in to Admin'}
          </button>
        </form>
      </div>
    </div>
  );
}
