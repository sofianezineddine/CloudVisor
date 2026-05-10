'use client';

import Link from 'next/link';
import { ArrowRight } from 'lucide-react';
import { useState } from 'react';

export default function CtaSection() {
  const [email, setEmail] = useState('');

  return (
    <section
      style={{
        background: 'linear-gradient(135deg, #0b1e3f 0%, #1a3a6b 40%, var(--accent) 100%)',
        padding: '80px 24px',
        display: 'flex',
        justifyContent: 'center',
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '640px',
          textAlign: 'center',
        }}
      >
        <h2
          style={{
            fontSize: '28px',
            fontWeight: 800,
            color: 'var(--text-inverse)',
            margin: '0 0 12px 0',
            letterSpacing: '-0.3px',
          }}
        >
          Ready to secure your cloud?
        </h2>
        <p
          style={{
            fontSize: '15px',
            color: 'rgba(255,255,255,0.75)',
            margin: '0 0 36px 0',
            lineHeight: 1.6,
          }}
        >
          Start your 14-day free trial. Connect your first cloud account in under 5 minutes.
          No credit card required.
        </p>

        {/* Email + CTA */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '12px',
            flexWrap: 'wrap',
          }}
        >
          <input
            type="email"
            placeholder="Enter your work email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            style={{
              height: '48px',
              width: '320px',
              maxWidth: '100%',
              padding: '0 16px',
              fontSize: '15px',
              color: 'var(--text-primary)',
              backgroundColor: 'var(--bg-surface)',
              border: '1px solid var(--border-default)',
              borderRadius: '4px',
              outline: 'none',
              fontFamily: "'Open Sans', sans-serif",
            }}
          />
          <Link
            href={email ? `/signup?email=${encodeURIComponent(email)}` : '/signup'}
            style={{
              height: '48px',
              padding: '0 28px',
              fontSize: '15px',
              fontWeight: 700,
              color: 'var(--btn-primary-text)',
              backgroundColor: 'var(--btn-primary-bg)',
              border: '1px solid var(--btn-primary-bg)',
              borderRadius: '4px',
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              textDecoration: 'none',
              transition: 'background-color 0.15s',
            }}
          >
            Start free trial
            <ArrowRight size={16} />
          </Link>
        </div>

        <p
          style={{
            fontSize: '12px',
            color: 'rgba(255,255,255,0.45)',
            marginTop: '16px',
          }}
        >
          Free 14-day trial. No credit card. Cancel anytime.
        </p>
      </div>
    </section>
  );
}
