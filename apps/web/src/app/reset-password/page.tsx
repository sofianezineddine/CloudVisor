'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { Shield, CheckCircle2, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { authAPI } from '@/lib/api/auth';

export default function ResetPasswordPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get('token');

  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    document.title = 'Reset Password - CloudVisor';
    if (!token) {
      setError('Invalid or missing reset token. Please request a new password reset link.');
    }
  }, [token]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;

    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await authAPI.resetPassword(token, password);
      setSuccess(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to reset password. The link may have expired.');
    } finally {
      setLoading(false);
    }
  };

  const inputStyle: React.CSSProperties = {
    width: '100%',
    height: '32px',
    padding: '0 8px',
    border: '1px solid var(--border-strong)',
    borderRadius: '2px',
    fontSize: '14px',
    color: 'var(--text-primary)',
    backgroundColor: 'var(--bg-surface)',
    outline: 'none',
    fontFamily: "'Open Sans', sans-serif",
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        backgroundColor: 'var(--bg-base)',
        fontFamily: "'Open Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px',
      }}
    >
      {/* Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '32px' }}>
        <div
          style={{
            width: '40px',
            height: '40px',
            backgroundColor: 'var(--bg-sidebar)',
            borderRadius: '6px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Shield style={{ width: '22px', height: '22px', color: 'var(--accent)' }} />
        </div>
        <span style={{ fontSize: '22px', fontWeight: '700', color: 'var(--bg-sidebar)', letterSpacing: '-0.3px' }}>
          CloudVisor
        </span>
      </div>

      {/* Card */}
      <div
        style={{
          width: '100%',
          maxWidth: '400px',
          backgroundColor: 'var(--bg-surface)',
          border: '1px solid var(--border-default)',
          borderRadius: 'var(--radius-container)',
          padding: '28px 32px 24px',
          boxShadow: '0 1px 4px rgba(0,28,36,0.10)',
        }}
      >
        <h1 style={{ fontSize: '20px', fontWeight: '700', color: 'var(--text-primary)', marginBottom: '4px' }}>
          Set new password
        </h1>
        <p style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '20px' }}>
          Enter your new password below.
        </p>

        {success ? (
          <div style={{ textAlign: 'center' }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                padding: '12px 16px',
                borderRadius: '8px',
                backgroundColor: 'var(--success-bg)',
                border: '1px solid var(--success)',
                marginBottom: '20px',
              }}
            >
              <CheckCircle2 style={{ width: '20px', height: '20px', color: 'var(--success)', flexShrink: 0 }} />
              <div>
                <p style={{ fontSize: '14px', fontWeight: '600', color: 'var(--success)' }}>
                  Password reset successfully
                </p>
                <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>
                  You can now sign in with your new password.
                </p>
              </div>
            </div>
            <Button
              onClick={() => router.push('/login')}
              style={{ width: '100%' }}
            >
              Go to Sign In
            </Button>
          </div>
        ) : (
          <form onSubmit={handleSubmit}>
            {error && (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '8px',
                  marginBottom: '16px',
                  padding: '10px 12px',
                  borderLeft: '4px solid var(--critical)',
                  backgroundColor: 'var(--critical-bg)',
                  color: 'var(--critical)',
                  fontSize: '13px',
                  borderRadius: '2px',
                }}
              >
                <AlertTriangle style={{ width: '16px', height: '16px', flexShrink: 0, marginTop: '1px' }} />
                {error}
              </div>
            )}

            <div style={{ marginBottom: '16px' }}>
              <label
                style={{
                  display: 'block',
                  fontSize: '14px',
                  fontWeight: '700',
                  color: 'var(--text-primary)',
                  marginBottom: '6px',
                }}
              >
                New password
              </label>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                autoComplete="new-password"
                autoFocus
                placeholder="Min. 8 characters"
                style={inputStyle}
                onFocus={e => {
                  e.currentTarget.style.border = '1px solid var(--accent)';
                  e.currentTarget.style.boxShadow = '0 0 0 2px var(--accent-dim)';
                }}
                onBlur={e => {
                  e.currentTarget.style.border = '1px solid var(--border-strong)';
                  e.currentTarget.style.boxShadow = 'none';
                }}
              />
            </div>

            <div style={{ marginBottom: '20px' }}>
              <label
                style={{
                  display: 'block',
                  fontSize: '14px',
                  fontWeight: '700',
                  color: 'var(--text-primary)',
                  marginBottom: '6px',
                }}
              >
                Confirm new password
              </label>
              <input
                type="password"
                value={confirmPassword}
                onChange={e => setConfirmPassword(e.target.value)}
                required
                autoComplete="new-password"
                placeholder="Re-enter password"
                style={{
                  ...inputStyle,
                  border: `1px solid ${confirmPassword && confirmPassword !== password ? 'var(--critical)' : 'var(--border-strong)'}`,
                }}
                onFocus={e => {
                  e.currentTarget.style.border = '1px solid var(--accent)';
                  e.currentTarget.style.boxShadow = '0 0 0 2px var(--accent-dim)';
                }}
                onBlur={e => {
                  e.currentTarget.style.border = `1px solid ${confirmPassword && confirmPassword !== password ? 'var(--critical)' : 'var(--border-strong)'}`;
                  e.currentTarget.style.boxShadow = 'none';
                }}
              />
              {confirmPassword && confirmPassword !== password && (
                <p style={{ fontSize: '12px', color: 'var(--critical)', marginTop: '4px' }}>
                  Passwords do not match.
                </p>
              )}
            </div>

            <button
              type="submit"
              disabled={loading || !token || !password || password !== confirmPassword}
              style={{
                width: '100%',
                height: '34px',
                backgroundColor: 'var(--btn-primary-bg)',
                color: 'var(--btn-primary-text)',
                border: '1px solid var(--btn-primary-bg)',
                borderRadius: '2px',
                fontSize: '14px',
                fontWeight: '700',
                cursor: loading ? 'not-allowed' : 'pointer',
                opacity: loading || !token ? 0.75 : 1,
                transition: 'background-color 0.1s',
              }}
              onMouseEnter={e => { if (!loading) e.currentTarget.style.backgroundColor = 'var(--btn-primary-hover)'; }}
              onMouseLeave={e => { if (!loading) e.currentTarget.style.backgroundColor = 'var(--btn-primary-bg)'; }}
            >
              {loading ? 'Resetting…' : 'Reset password'}
            </button>
          </form>
        )}

        <div style={{ marginTop: '16px', textAlign: 'center' }}>
          <Link
            href="/login"
            style={{ fontSize: '13px', color: 'var(--accent)', textDecoration: 'none' }}
            onMouseEnter={e => (e.currentTarget.style.textDecoration = 'underline')}
            onMouseLeave={e => (e.currentTarget.style.textDecoration = 'none')}
          >
            ← Back to sign in
          </Link>
        </div>
      </div>

      {/* Footer */}
      <p style={{ marginTop: '24px', fontSize: '12px', color: 'var(--text-secondary)' }}>
        © 2026 CloudVisor, Inc. All rights reserved.
      </p>
    </div>
  );
}
