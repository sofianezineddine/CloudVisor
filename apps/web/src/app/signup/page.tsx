'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Shield } from 'lucide-react';
import { useAuth } from '@/hooks/use-auth';
import { useRouter } from 'next/navigation';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8002';

export default function SignupPage() {
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [company, setCompany] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [agreed, setAgreed] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { register } = useAuth();
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await register({
        email,
        password,
        organization_name: company,
        first_name: firstName.trim(),
        last_name: lastName.trim(),
      });
      router.push('/console');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to create account. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const inputStyle = (hasError = false): React.CSSProperties => ({
    width: '100%',
    height: '32px',
    padding: '0 8px',
    border: `1px solid ${hasError ? 'var(--critical)' : 'var(--border-strong)'}`,
    borderRadius: '2px',
    fontSize: '14px',
    color: 'var(--text-primary)',
    backgroundColor: 'var(--bg-surface)',
    outline: 'none',
    fontFamily: "'Open Sans', sans-serif",
  });

  const handleFocus = (e: React.FocusEvent<HTMLInputElement>) => {
    e.currentTarget.style.border = '1px solid var(--accent)';
    e.currentTarget.style.boxShadow = '0 0 0 2px var(--accent-dim)';
  };

  const handleBlur = (e: React.FocusEvent<HTMLInputElement>) => {
    e.currentTarget.style.border = '1px solid var(--border-strong)';
    e.currentTarget.style.boxShadow = 'none';
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        backgroundColor: 'var(--bg-base)',
        fontFamily: "'Open Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* Top utility bar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'flex-end',
          alignItems: 'center',
          gap: '24px',
          padding: '10px 24px',
          fontSize: '13px',
          color: 'var(--text-primary)',
        }}
      >
        <button style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '13px', color: 'var(--text-primary)' }}>
          Provide feedback
        </button>
        <button
          style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '13px', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '4px' }}
        >
          Multi-session disabled
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path d="M2 4l4 4 4-4" stroke="var(--text-primary)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
        <button
          style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '13px', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '4px' }}
        >
          English
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path d="M2 4l4 4 4-4" stroke="var(--text-primary)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
      </div>

      {/* Logo */}
      <div style={{ display: 'flex', justifyContent: 'center', padding: '16px 0 24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '40px',
              height: '40px',
              backgroundColor: 'var(--aws-nav-bg)',
              borderRadius: '6px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Shield style={{ width: '22px', height: '22px', color: 'var(--accent)' }} />
          </div>
          <span style={{ fontSize: '22px', fontWeight: '700', color: 'var(--aws-nav-bg)', letterSpacing: '-0.3px' }}>
            CloudVisor
          </span>
        </div>
      </div>

      {/* Main content: form + promo panel */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'flex-start',
          gap: '0',
          padding: '0 24px 40px',
          flex: 1,
        }}
      >
        {/* Sign Up Card */}
        <div
          style={{
            width: '100%',
            maxWidth: '400px',
            backgroundColor: 'var(--bg-surface)',
            border: '1px solid var(--border-default)',
            borderRadius: '4px',
            padding: '28px 32px 24px',
            boxShadow: '0 1px 4px rgba(0,28,36,0.10)',
            marginRight: '24px',
          }}
        >
          <h1 style={{ fontSize: '20px', fontWeight: '700', color: 'var(--text-primary)', marginBottom: '4px' }}>
            Create your account
          </h1>
          <p style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '20px' }}>
            Start your 14-day free trial. No credit card required.
          </p>

          {/* Error */}
          {error && (
            <div
              style={{
                marginBottom: '16px',
                padding: '10px 12px',
                borderLeft: '4px solid var(--critical)',
                backgroundColor: 'var(--critical-bg)',
                color: 'var(--critical)',
                fontSize: '13px',
                borderRadius: '2px',
              }}
            >
              {error}
            </div>
          )}

          {/* OAuth buttons */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '16px' }}>
            <button
              type="button"
              onClick={() => (window.location.href = `${API_BASE_URL}/auth/oauth/google/authorize`)}
              style={{
                width: '100%',
                height: '34px',
                backgroundColor: 'var(--bg-surface)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-strong)',
                borderRadius: '2px',
                fontSize: '14px',
                fontWeight: '400',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                transition: 'background-color 0.1s',
              }}
              onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-base)')}
              onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'var(--bg-surface)')}
            >
              <svg width="16" height="16" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              Continue with Google
            </button>

            <button
              type="button"
              onClick={() => (window.location.href = `${API_BASE_URL}/auth/oauth/github/authorize`)}
              style={{
                width: '100%',
                height: '34px',
                backgroundColor: 'var(--bg-surface)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-strong)',
                borderRadius: '2px',
                fontSize: '14px',
                fontWeight: '400',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                transition: 'background-color 0.1s',
              }}
              onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-base)')}
              onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'var(--bg-surface)')}
            >
              <svg width="16" height="16" fill="var(--text-primary)" viewBox="0 0 24 24">
                <path d="M12.5.75C6.146.75 1 5.896 1 12.25c0 5.089 3.292 9.387 7.863 10.91.575.101.79-.244.79-.546 0-.273-.014-1.178-.014-2.142-2.889.532-3.636-.704-3.866-1.35-.13-.331-.69-1.352-1.18-1.625-.402-.216-.977-.748-.014-.762.906-.014 1.553.834 1.769 1.179 1.035 1.74 2.688 1.25 3.349.948.1-.747.402-1.25.733-1.538-2.559-.287-5.232-1.279-5.232-5.678 0-1.25.445-2.285 1.178-3.09-.115-.288-.517-1.467.115-3.048 0 0 .963-.302 3.163 1.179.92-.259 1.897-.388 2.875-.388.977 0 1.955.13 2.875.388 2.2-1.495 3.162-1.179 3.162-1.179.633 1.581.23 2.76.115 3.048.733.805 1.179 1.825 1.179 3.09 0 4.413-2.688 5.39-5.247 5.678.417.36.776 1.05.776 2.128 0 1.538-.014 2.774-.014 3.162 0 .302.216.662.79.547C20.709 21.637 24 17.324 24 12.25 24 5.896 18.854.75 12.5.75Z"/>
              </svg>
              Continue with GitHub
            </button>
          </div>

          {/* OR divider */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
            <div style={{ flex: 1, height: '1px', backgroundColor: 'var(--border-default)' }} />
            <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>OR</span>
            <div style={{ flex: 1, height: '1px', backgroundColor: 'var(--border-default)' }} />
          </div>

          {/* Registration form */}
          <form onSubmit={handleSubmit}>
            {/* First + Last name row */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '12px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '14px', fontWeight: '700', color: 'var(--text-primary)', marginBottom: '6px' }}>
                  First name
                </label>
                <input
                  type="text"
                  value={firstName}
                  onChange={e => setFirstName(e.target.value)}
                  required
                  autoComplete="given-name"
                  placeholder="John"
                  style={inputStyle()}
                  onFocus={handleFocus}
                  onBlur={handleBlur}
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '14px', fontWeight: '700', color: 'var(--text-primary)', marginBottom: '6px' }}>
                  Last name
                </label>
                <input
                  type="text"
                  value={lastName}
                  onChange={e => setLastName(e.target.value)}
                  required
                  autoComplete="family-name"
                  placeholder="Doe"
                  style={inputStyle()}
                  onFocus={handleFocus}
                  onBlur={handleBlur}
                />
              </div>
            </div>

            {/* Work email */}
            <div style={{ marginBottom: '12px' }}>
              <label style={{ display: 'block', fontSize: '14px', fontWeight: '700', color: 'var(--text-primary)', marginBottom: '6px' }}>
                Work email
              </label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
                autoComplete="email"
                placeholder="you@company.com"
                style={inputStyle()}
                onFocus={handleFocus}
                onBlur={handleBlur}
              />
            </div>

            {/* Company name */}
            <div style={{ marginBottom: '12px' }}>
              <label style={{ display: 'block', fontSize: '14px', fontWeight: '700', color: 'var(--text-primary)', marginBottom: '6px' }}>
                Company name
              </label>
              <input
                type="text"
                value={company}
                onChange={e => setCompany(e.target.value)}
                required
                autoComplete="organization"
                placeholder="Acme Inc."
                style={inputStyle()}
                onFocus={handleFocus}
                onBlur={handleBlur}
              />
            </div>

            {/* Password */}
            <div style={{ marginBottom: '12px' }}>
              <label style={{ display: 'block', fontSize: '14px', fontWeight: '700', color: 'var(--text-primary)', marginBottom: '6px' }}>
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                autoComplete="new-password"
                placeholder="Min. 8 characters"
                style={inputStyle()}
                onFocus={handleFocus}
                onBlur={handleBlur}
              />
            </div>

            {/* Confirm password */}
            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', fontSize: '14px', fontWeight: '700', color: 'var(--text-primary)', marginBottom: '6px' }}>
                Confirm password
              </label>
              <input
                type="password"
                value={confirmPassword}
                onChange={e => setConfirmPassword(e.target.value)}
                required
                autoComplete="new-password"
                placeholder="Re-enter password"
                style={inputStyle(!!confirmPassword && confirmPassword !== password)}
                onFocus={handleFocus}
                onBlur={handleBlur}
              />
              {confirmPassword && confirmPassword !== password && (
                <p style={{ fontSize: '12px', color: 'var(--critical)', marginTop: '4px' }}>
                  Passwords do not match.
                </p>
              )}
            </div>

            {/* Terms checkbox */}
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', marginBottom: '16px' }}>
              <input
                id="terms"
                type="checkbox"
                checked={agreed}
                onChange={e => setAgreed(e.target.checked)}
                required
                style={{ marginTop: '2px', accentColor: 'var(--accent)', width: '14px', height: '14px', flexShrink: 0 }}
              />
              <label htmlFor="terms" style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
                I agree to the{' '}
                <Link href="/terms" style={{ color: 'var(--accent)', textDecoration: 'none' }}
                  onMouseEnter={e => (e.currentTarget.style.textDecoration = 'underline')}
                  onMouseLeave={e => (e.currentTarget.style.textDecoration = 'none')}
                >
                  Terms of Service
                </Link>
                {' '}and{' '}
                <Link href="/privacy" style={{ color: 'var(--accent)', textDecoration: 'none' }}
                  onMouseEnter={e => (e.currentTarget.style.textDecoration = 'underline')}
                  onMouseLeave={e => (e.currentTarget.style.textDecoration = 'none')}
                >
                  Privacy Policy
                </Link>
              </label>
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={loading || !agreed}
              style={{
                width: '100%',
                height: '34px',
                backgroundColor: loading || !agreed ? 'var(--warning)' : 'var(--btn-primary-bg)',
                color: 'var(--btn-primary-text)',
                border: '1px solid var(--btn-primary-bg)',
                borderRadius: '2px',
                fontSize: '14px',
                fontWeight: '700',
                cursor: loading || !agreed ? 'not-allowed' : 'pointer',
                opacity: loading || !agreed ? 0.75 : 1,
                transition: 'background-color 0.1s',
              }}
              onMouseEnter={e => { if (!loading && agreed) e.currentTarget.style.backgroundColor = 'var(--btn-primary-hover)'; }}
              onMouseLeave={e => { if (!loading && agreed) e.currentTarget.style.backgroundColor = 'var(--btn-primary-bg)'; }}
            >
              {loading ? 'Creating account…' : 'Create account'}
            </button>
          </form>

          {/* Sign in link */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', margin: '16px 0 12px' }}>
            <div style={{ flex: 1, height: '1px', backgroundColor: 'var(--border-default)' }} />
            <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>OR</span>
            <div style={{ flex: 1, height: '1px', backgroundColor: 'var(--border-default)' }} />
          </div>

          <button
            type="button"
            onClick={() => router.push('/login')}
            style={{
              width: '100%',
              height: '34px',
              backgroundColor: 'var(--bg-surface)',
              color: 'var(--text-primary)',
              border: '1px solid var(--border-strong)',
              borderRadius: '2px',
              fontSize: '14px',
              fontWeight: '400',
              cursor: 'pointer',
              transition: 'background-color 0.1s',
            }}
            onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-base)')}
            onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'var(--bg-surface)')}
          >
            Already have an account? Sign in
          </button>

          {/* Legal footer */}
          <p style={{ marginTop: '20px', fontSize: '11px', color: 'var(--text-secondary)', textAlign: 'center', lineHeight: '1.6' }}>
            By continuing, you agree to{' '}
            <a href="#" style={{ color: 'var(--accent)' }}>CloudVisor Terms of Service</a>
            {' '}and the{' '}
            <a href="#" style={{ color: 'var(--accent)' }}>Privacy Notice</a>.
            This site uses essential cookies. See our{' '}
            <a href="#" style={{ color: 'var(--accent)' }}>Cookie Notice</a>
            {' '}for more information.
          </p>
        </div>

        {/* Promo panel */}
        <div
          style={{
            width: '380px',
            height: '480px',
            borderRadius: '4px',
            overflow: 'hidden',
            background: 'linear-gradient(135deg, #0b1e3f 0%, #1a3a6b 40%, var(--accent) 100%)',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'flex-start',
            padding: '32px',
            position: 'relative',
          }}
        >
          {/* Abstract background circles — bottom half */}
          <div style={{ position: 'absolute', inset: 0, overflow: 'hidden', pointerEvents: 'none' }}>
            {[280, 220, 160, 100, 50].map((size, i) => (
              <div
                key={i}
                style={{
                  position: 'absolute',
                  top: '75%',
                  left: '50%',
                  transform: 'translate(-50%, -50%)',
                  width: `${size}px`,
                  height: `${size}px`,
                  borderRadius: '50%',
                  border: `1px solid rgba(255,255,255,${0.06 + i * 0.04})`,
                  backgroundColor: `rgba(26,115,232,${0.04 + i * 0.03})`,
                }}
              />
            ))}
            {/* Shield watermark */}
            <div style={{ position: 'absolute', top: '75%', left: '50%', transform: 'translate(-50%, -50%)', opacity: 0.10 }}>
              <Shield style={{ width: '100px', height: '100px', color: 'var(--bg-surface)' }} />
            </div>
          </div>

          {/* Feature list */}
          <div style={{ position: 'relative', zIndex: 1 }}>
            <h2 style={{ fontSize: '22px', fontWeight: '700', color: 'var(--bg-surface)', marginBottom: '12px', lineHeight: '1.3' }}>
              CloudVisor Security Agent
            </h2>
            <p style={{ fontSize: '14px', color: 'rgba(255,255,255,0.85)', lineHeight: '1.6', marginBottom: '20px' }}>
              Proactively secure your cloud infrastructure throughout the development lifecycle with AI-powered threat detection.
            </p>

            {/* Feature bullets */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '24px' }}>
              {[
                'CSPM across AWS, Azure, GCP & OCI',
                '500+ built-in security rules',
                'Real-time threat detection & response',
                'Compliance: SOC 2, PCI-DSS, HIPAA, CIS',
                'AI-powered risk prioritization',
              ].map((feature, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <div
                    style={{
                      width: '16px',
                      height: '16px',
                      borderRadius: '50%',
                      backgroundColor: 'rgba(255,255,255,0.20)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                    }}
                  >
                    <svg width="8" height="8" viewBox="0 0 8 8" fill="none">
                      <path d="M1 4l2 2 4-4" stroke="var(--bg-surface)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  </div>
                  <span style={{ fontSize: '13px', color: 'rgba(255,255,255,0.90)' }}>{feature}</span>
                </div>
              ))}
            </div>

            <a
              href="#"
              style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '14px', fontWeight: '600', color: 'var(--bg-surface)', textDecoration: 'none' }}
              onMouseEnter={e => (e.currentTarget.style.textDecoration = 'underline')}
              onMouseLeave={e => (e.currentTarget.style.textDecoration = 'none')}
            >
              Learn more about CloudVisor
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M3 8h10M9 4l4 4-4 4" stroke="var(--bg-surface)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </a>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div
        style={{
          textAlign: 'center',
          padding: '16px',
          fontSize: '12px',
          color: 'var(--text-secondary)',
          borderTop: '1px solid var(--border-default)',
          backgroundColor: 'var(--bg-base)',
        }}
      >
        © 2026 CloudVisor, Inc. or its affiliates. All rights reserved.
      </div>
    </div>
  );
}
