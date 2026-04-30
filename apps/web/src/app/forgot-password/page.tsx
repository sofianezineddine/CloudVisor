'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { useRouter } from 'next/navigation';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8002';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/auth/forgot-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to send reset email');
      }

      setSuccess(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to send reset email');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen">
      {/* Left Side - Branding */}
      <div className="hidden lg:flex lg:w-1/2 bg-[var(--bg-sidebar)] flex-col justify-between p-12">
        <div>
          <div className="flex items-center gap-3 mb-12">
            <div className="w-10 h-10 bg-[var(--accent)] rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-xl">C</span>
            </div>
            <span className="text-2xl font-bold text-white">CloudVisor</span>
          </div>

          <div className="max-w-md">
            <h1 className="text-4xl font-bold text-white mb-6">
              Reset your password
            </h1>
            <p className="text-lg text-gray-300 mb-8">
              Enter your email address and we&apos;ll send you a link to reset your password.
            </p>
          </div>
        </div>

        <div className="text-gray-400 text-sm">
          © 2024 CloudVisor. All rights reserved.
        </div>
      </div>

      {/* Right Side - Form */}
      <div className="flex-1 flex items-center justify-center p-8 bg-[var(--bg-base)]">
        <div className="w-full max-w-md">
          <div className="mb-8">
            <h2 className="text-3xl font-bold text-[var(--text-primary)] mb-2">
              Forgot password?
            </h2>
            <p className="text-[var(--text-secondary)]">
              No worries, we&apos;ll send you reset instructions.
            </p>
          </div>

          {success ? (
            <div className="space-y-6">
              <div className="p-4 bg-[var(--success-bg)] border border-[var(--success-border)] rounded-lg">
                <div className="flex items-start gap-3">
                  <svg className="w-5 h-5 text-[var(--success)] mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <div>
                    <div className="font-medium text-[var(--success)]">Email sent!</div>
                    <div className="text-sm text-[var(--text-secondary)] mt-1">
                      Check your inbox for a password reset link.
                    </div>
                  </div>
                </div>
              </div>

              <Button
                onClick={() => router.push('/login')}
                className="w-full py-3 text-base"
              >
                Back to login
              </Button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-[var(--text-primary)] mb-2">
                  Email address
                </label>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="w-full px-4 py-3 border border-[var(--border-default)] rounded-lg focus:outline-none focus:ring-2 focus:ring-[var(--accent)] focus:border-transparent bg-[var(--bg-surface)] text-[var(--text-primary)]"
                  placeholder="you@company.com"
                />
              </div>

              {error && (
                <div className="p-4 bg-[var(--danger-bg)] border border-[var(--danger-border)] rounded-lg">
                  <div className="text-sm text-[var(--danger)]">{error}</div>
                </div>
              )}

              <Button type="submit" className="w-full py-3 text-base" disabled={loading}>
                {loading ? 'Sending...' : 'Send reset link'}
              </Button>

              <div className="text-center">
                <Link href="/login" className="text-sm text-[var(--accent)] hover:text-[var(--accent-hover)]">
                  ← Back to login
                </Link>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
