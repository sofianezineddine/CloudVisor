'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useAuth } from '@/hooks/use-auth';
import { useRouter, useSearchParams } from 'next/navigation';
import { Shield } from 'lucide-react';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8002';

type UserType = 'admin' | 'iam';

export default function LoginPage() {
  const [userType, setUserType] = useState<UserType>('admin');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [mfaCode, setMfaCode] = useState('');
  const [step, setStep] = useState<'email' | 'password'>('email');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { login } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirect = searchParams.get('redirect') || '/console';

  const handleNext = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;
    setStep('password');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await login(email, password, mfaCode || undefined);
      router.push(redirect);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Incorrect email or password. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        backgroundColor: '#f8f8f5',
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
          color: '#16191f',
        }}
      >
        <button
          style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '13px', color: '#16191f' }}
        >
          Provide feedback
        </button>
        <button
          style={{
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            fontSize: '13px',
            color: '#16191f',
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
          }}
        >
          Multi-session disabled
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path d="M2 4l4 4 4-4" stroke="#16191f" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
        <button
          style={{
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            fontSize: '13px',
            color: '#16191f',
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
          }}
        >
          English
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path d="M2 4l4 4 4-4" stroke="#16191f" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
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
              backgroundColor: '#0b1e3f',
              borderRadius: '6px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Shield style={{ width: '22px', height: '22px', color: '#1a73e8' }} />
          </div>
          <span
            style={{
              fontSize: '22px',
              fontWeight: '700',
              color: '#0b1e3f',
              letterSpacing: '-0.3px',
            }}
          >
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
        {/* Sign In Card */}
        <div
          style={{
            width: '100%',
            maxWidth: '380px',
            backgroundColor: '#ffffff',
            border: '1px solid #d5dbdb',
            borderRadius: '4px',
            padding: '28px 32px 24px',
            boxShadow: '0 1px 4px rgba(0,28,36,0.10)',
            marginRight: '24px',
          }}
        >
          <h1
            style={{
              fontSize: '20px',
              fontWeight: '700',
              color: '#16191f',
              marginBottom: '4px',
            }}
          >
            Sign In
          </h1>

          {step === 'email' ? (
            <>
              <p style={{ fontSize: '14px', color: '#16191f', marginBottom: '16px' }}>
                Access your CloudVisor account by user type.
              </p>

              {/* User type selector */}
              <div style={{ marginBottom: '20px' }}>
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    marginBottom: '8px',
                    fontSize: '14px',
                    color: '#16191f',
                  }}
                >
                  User type{' '}
                  <button
                    style={{
                      background: 'none',
                      border: 'none',
                      cursor: 'pointer',
                      color: '#0073bb',
                      fontSize: '14px',
                      padding: 0,
                      textDecoration: 'none',
                    }}
                    onMouseEnter={e => (e.currentTarget.style.textDecoration = 'underline')}
                    onMouseLeave={e => (e.currentTarget.style.textDecoration = 'none')}
                  >
                    (not sure?)
                  </button>
                </div>

                {/* Admin user option */}
                <label
                  style={{
                    display: 'block',
                    border: `1px solid ${userType === 'admin' ? '#0073bb' : '#d5dbdb'}`,
                    borderRadius: '4px',
                    padding: '10px 12px',
                    marginBottom: '8px',
                    cursor: 'pointer',
                    backgroundColor: userType === 'admin' ? '#f0f8ff' : '#ffffff',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                    <input
                      type="radio"
                      name="userType"
                      value="admin"
                      checked={userType === 'admin'}
                      onChange={() => setUserType('admin')}
                      style={{ marginTop: '2px', accentColor: '#0073bb' }}
                    />
                    <div>
                      <div style={{ fontSize: '14px', fontWeight: '600', color: '#16191f' }}>
                        Admin user
                      </div>
                      <div style={{ fontSize: '12px', color: '#545b64', marginTop: '2px' }}>
                        Account owner that performs tasks requiring unrestricted access.
                      </div>
                    </div>
                  </div>
                </label>

                {/* IAM user option */}
                <label
                  style={{
                    display: 'block',
                    border: `1px solid ${userType === 'iam' ? '#0073bb' : '#d5dbdb'}`,
                    borderRadius: '4px',
                    padding: '10px 12px',
                    cursor: 'pointer',
                    backgroundColor: userType === 'iam' ? '#f0f8ff' : '#ffffff',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                    <input
                      type="radio"
                      name="userType"
                      value="iam"
                      checked={userType === 'iam'}
                      onChange={() => setUserType('iam')}
                      style={{ marginTop: '2px', accentColor: '#0073bb' }}
                    />
                    <div>
                      <div style={{ fontSize: '14px', fontWeight: '600', color: '#16191f' }}>
                        IAM user
                      </div>
                      <div style={{ fontSize: '12px', color: '#545b64', marginTop: '2px' }}>
                        User within an account that performs daily tasks.
                      </div>
                    </div>
                  </div>
                </label>
              </div>

              {/* Email field */}
              <form onSubmit={handleNext}>
                <div style={{ marginBottom: '16px' }}>
                  <label
                    style={{
                      display: 'block',
                      fontSize: '14px',
                      fontWeight: '700',
                      color: '#16191f',
                      marginBottom: '6px',
                    }}
                  >
                    Email address
                  </label>
                  <input
                    type="email"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                    required
                    autoComplete="email"
                    placeholder="username@example.com"
                    style={{
                      width: '100%',
                      height: '32px',
                      padding: '0 8px',
                      border: '1px solid #aab7b8',
                      borderRadius: '2px',
                      fontSize: '14px',
                      color: '#16191f',
                      backgroundColor: '#ffffff',
                      outline: 'none',
                    }}
                    onFocus={e => {
                      e.currentTarget.style.border = '1px solid #0073bb';
                      e.currentTarget.style.boxShadow = '0 0 0 2px rgba(0,115,187,0.20)';
                    }}
                    onBlur={e => {
                      e.currentTarget.style.border = '1px solid #aab7b8';
                      e.currentTarget.style.boxShadow = 'none';
                    }}
                  />
                </div>

                {/* Next button */}
                <button
                  type="submit"
                  style={{
                    width: '100%',
                    height: '34px',
                    backgroundColor: '#ec7211',
                    color: '#ffffff',
                    border: '1px solid #ec7211',
                    borderRadius: '2px',
                    fontSize: '14px',
                    fontWeight: '700',
                    cursor: 'pointer',
                    transition: 'background-color 0.1s',
                  }}
                  onMouseEnter={e => (e.currentTarget.style.backgroundColor = '#eb5f07')}
                  onMouseLeave={e => (e.currentTarget.style.backgroundColor = '#ec7211')}
                >
                  Next
                </button>
              </form>

              {/* Divider */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  margin: '16px 0',
                }}
              >
                <div style={{ flex: 1, height: '1px', backgroundColor: '#d5dbdb' }} />
                <span style={{ fontSize: '13px', color: '#545b64' }}>OR</span>
                <div style={{ flex: 1, height: '1px', backgroundColor: '#d5dbdb' }} />
              </div>

              {/* OAuth buttons */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '12px' }}>
                {/* Google */}
                <button
                  type="button"
                  onClick={() => (window.location.href = `${API_BASE_URL}/auth/oauth/google/authorize`)}
                  style={{
                    width: '100%',
                    height: '34px',
                    backgroundColor: '#ffffff',
                    color: '#16191f',
                    border: '1px solid #aab7b8',
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
                  onMouseEnter={e => (e.currentTarget.style.backgroundColor = '#f2f3f3')}
                  onMouseLeave={e => (e.currentTarget.style.backgroundColor = '#ffffff')}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24">
                    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                  </svg>
                  Continue with Google
                </button>

                {/* GitHub */}
                <button
                  type="button"
                  onClick={() => (window.location.href = `${API_BASE_URL}/auth/oauth/github/authorize`)}
                  style={{
                    width: '100%',
                    height: '34px',
                    backgroundColor: '#ffffff',
                    color: '#16191f',
                    border: '1px solid #aab7b8',
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
                  onMouseEnter={e => (e.currentTarget.style.backgroundColor = '#f2f3f3')}
                  onMouseLeave={e => (e.currentTarget.style.backgroundColor = '#ffffff')}
                >
                  <svg width="16" height="16" fill="#16191f" viewBox="0 0 24 24">
                    <path d="M12.5.75C6.146.75 1 5.896 1 12.25c0 5.089 3.292 9.387 7.863 10.91.575.101.79-.244.79-.546 0-.273-.014-1.178-.014-2.142-2.889.532-3.636-.704-3.866-1.35-.13-.331-.69-1.352-1.18-1.625-.402-.216-.977-.748-.014-.762.906-.014 1.553.834 1.769 1.179 1.035 1.74 2.688 1.25 3.349.948.1-.747.402-1.25.733-1.538-2.559-.287-5.232-1.279-5.232-5.678 0-1.25.445-2.285 1.178-3.09-.115-.288-.517-1.467.115-3.048 0 0 .963-.302 3.163 1.179.92-.259 1.897-.388 2.875-.388.977 0 1.955.13 2.875.388 2.2-1.495 3.162-1.179 3.162-1.179.633 1.581.23 2.76.115 3.048.733.805 1.179 1.825 1.179 3.09 0 4.413-2.688 5.39-5.247 5.678.417.36.776 1.05.776 2.128 0 1.538-.014 2.774-.014 3.162 0 .302.216.662.79.547C20.709 21.637 24 17.324 24 12.25 24 5.896 18.854.75 12.5.75Z"/>
                  </svg>
                  Continue with GitHub
                </button>
              </div>

              {/* Second divider */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  margin: '4px 0 12px',
                }}
              >
                <div style={{ flex: 1, height: '1px', backgroundColor: '#d5dbdb' }} />
                <span style={{ fontSize: '13px', color: '#545b64' }}>OR</span>
                <div style={{ flex: 1, height: '1px', backgroundColor: '#d5dbdb' }} />
              </div>

              {/* Sign up */}
              <button
                type="button"
                onClick={() => router.push('/signup')}
                style={{
                  width: '100%',
                  height: '34px',
                  backgroundColor: '#ffffff',
                  color: '#16191f',
                  border: '1px solid #aab7b8',
                  borderRadius: '2px',
                  fontSize: '14px',
                  fontWeight: '400',
                  cursor: 'pointer',
                  transition: 'background-color 0.1s',
                }}
                onMouseEnter={e => (e.currentTarget.style.backgroundColor = '#f2f3f3')}
                onMouseLeave={e => (e.currentTarget.style.backgroundColor = '#ffffff')}
              >
                New to CloudVisor? Sign up
              </button>
            </>
          ) : (
            /* Password step */
            <>
              <p style={{ fontSize: '14px', color: '#545b64', marginBottom: '4px' }}>
                Signing in as
              </p>
              <p
                style={{
                  fontSize: '14px',
                  fontWeight: '600',
                  color: '#16191f',
                  marginBottom: '20px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                }}
              >
                {email}
                <button
                  onClick={() => { setStep('email'); setError(null); }}
                  style={{
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    color: '#0073bb',
                    fontSize: '13px',
                    padding: 0,
                  }}
                  onMouseEnter={e => (e.currentTarget.style.textDecoration = 'underline')}
                  onMouseLeave={e => (e.currentTarget.style.textDecoration = 'none')}
                >
                  Change
                </button>
              </p>

              {error && (
                <div
                  style={{
                    marginBottom: '16px',
                    padding: '10px 12px',
                    borderLeft: '4px solid #d13212',
                    backgroundColor: '#fdf3f1',
                    color: '#d13212',
                    fontSize: '13px',
                    borderRadius: '2px',
                  }}
                >
                  {error}
                </div>
              )}

              <form onSubmit={handleSubmit}>
                <div style={{ marginBottom: '16px' }}>
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      marginBottom: '6px',
                    }}
                  >
                    <label
                      style={{ fontSize: '14px', fontWeight: '700', color: '#16191f' }}
                    >
                      Password
                    </label>
                    <Link
                      href="/forgot-password"
                      style={{ fontSize: '13px', color: '#0073bb', textDecoration: 'none' }}
                      onMouseEnter={e => (e.currentTarget.style.textDecoration = 'underline')}
                      onMouseLeave={e => (e.currentTarget.style.textDecoration = 'none')}
                    >
                      Forgot password?
                    </Link>
                  </div>
                  <input
                    type="password"
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    required
                    autoComplete="current-password"
                    autoFocus
                    style={{
                      width: '100%',
                      height: '32px',
                      padding: '0 8px',
                      border: '1px solid #aab7b8',
                      borderRadius: '2px',
                      fontSize: '14px',
                      color: '#16191f',
                      backgroundColor: '#ffffff',
                      outline: 'none',
                    }}
                    onFocus={e => {
                      e.currentTarget.style.border = '1px solid #0073bb';
                      e.currentTarget.style.boxShadow = '0 0 0 2px rgba(0,115,187,0.20)';
                    }}
                    onBlur={e => {
                      e.currentTarget.style.border = '1px solid #aab7b8';
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
                      color: '#16191f',
                      marginBottom: '6px',
                    }}
                  >
                    MFA Code{' '}
                    <span style={{ fontWeight: '400', color: '#545b64' }}>(optional)</span>
                  </label>
                  <input
                    type="text"
                    value={mfaCode}
                    onChange={e => setMfaCode(e.target.value)}
                    autoComplete="one-time-code"
                    placeholder="6-digit code"
                    style={{
                      width: '100%',
                      height: '32px',
                      padding: '0 8px',
                      border: '1px solid #aab7b8',
                      borderRadius: '2px',
                      fontSize: '14px',
                      color: '#16191f',
                      backgroundColor: '#ffffff',
                      outline: 'none',
                    }}
                    onFocus={e => {
                      e.currentTarget.style.border = '1px solid #0073bb';
                      e.currentTarget.style.boxShadow = '0 0 0 2px rgba(0,115,187,0.20)';
                    }}
                    onBlur={e => {
                      e.currentTarget.style.border = '1px solid #aab7b8';
                      e.currentTarget.style.boxShadow = 'none';
                    }}
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  style={{
                    width: '100%',
                    height: '34px',
                    backgroundColor: loading ? '#f5a623' : '#ec7211',
                    color: '#ffffff',
                    border: '1px solid #ec7211',
                    borderRadius: '2px',
                    fontSize: '14px',
                    fontWeight: '700',
                    cursor: loading ? 'not-allowed' : 'pointer',
                    opacity: loading ? 0.8 : 1,
                    transition: 'background-color 0.1s',
                  }}
                  onMouseEnter={e => { if (!loading) e.currentTarget.style.backgroundColor = '#eb5f07'; }}
                  onMouseLeave={e => { if (!loading) e.currentTarget.style.backgroundColor = '#ec7211'; }}
                >
                  {loading ? 'Signing in…' : 'Sign in'}
                </button>
              </form>
            </>
          )}

          {/* Footer legal text */}
          <p
            style={{
              marginTop: '20px',
              fontSize: '11px',
              color: '#545b64',
              textAlign: 'center',
              lineHeight: '1.6',
            }}
          >
            By continuing, you agree to{' '}
            <a href="#" style={{ color: '#0073bb' }}>CloudVisor Terms of Service</a>
            {' '}and the{' '}
            <a href="#" style={{ color: '#0073bb' }}>Privacy Notice</a>.
            This site uses essential cookies. See our{' '}
            <a href="#" style={{ color: '#0073bb' }}>Cookie Notice</a>
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
            background: 'linear-gradient(135deg, #0b1e3f 0%, #1a3a6b 40%, #1a73e8 100%)',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'flex-start',
            padding: '32px',
            position: 'relative',
          }}
        >
          {/* Abstract background circles — bottom half */}
          <div
            style={{
              position: 'absolute',
              inset: 0,
              overflow: 'hidden',
              pointerEvents: 'none',
            }}
          >
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
            {/* Shield icon watermark */}
            <div
              style={{
                position: 'absolute',
                top: '75%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                opacity: 0.10,
              }}
            >
              <Shield style={{ width: '100px', height: '100px', color: '#ffffff' }} />
            </div>
          </div>

          {/* Promo text */}
          <div style={{ position: 'relative', zIndex: 1 }}>
            <h2
              style={{
                fontSize: '22px',
                fontWeight: '700',
                color: '#ffffff',
                marginBottom: '12px',
                lineHeight: '1.3',
              }}
            >
              CloudVisor Security Agent
            </h2>
            <p
              style={{
                fontSize: '14px',
                color: 'rgba(255,255,255,0.85)',
                lineHeight: '1.6',
                marginBottom: '20px',
              }}
            >
              Proactively secure your cloud infrastructure throughout the development lifecycle with AI-powered threat detection.
            </p>
            <a
              href="/signup"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '14px',
                fontWeight: '600',
                color: '#ffffff',
                textDecoration: 'none',
              }}
              onMouseEnter={e => (e.currentTarget.style.textDecoration = 'underline')}
              onMouseLeave={e => (e.currentTarget.style.textDecoration = 'none')}
            >
              Start a free trial
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M3 8h10M9 4l4 4-4 4" stroke="#ffffff" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
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
          color: '#545b64',
          borderTop: '1px solid #d5dbdb',
          backgroundColor: '#f8f8f5',
        }}
      >
        © 2026 CloudVisor, Inc. or its affiliates. All rights reserved.
      </div>
    </div>
  );
}
