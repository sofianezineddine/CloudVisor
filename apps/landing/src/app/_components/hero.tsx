'use client';

import Link from 'next/link';
import { Shield, ArrowRight, ChevronRight } from 'lucide-react';

export default function Hero() {
  return (
    <>
      <style>{`
        @media (max-width: 768px) {
          .landing-hero-row { flex-direction: column !important; text-align: center !important; }
          .landing-hero-visual { margin-top: 48px !important; width: 100% !important; max-width: 360px !important; }
          .landing-hero-ctas { justify-content: center !important; }
          .landing-hero-headline { font-size: 32px !important; }
        }
      `}</style>

      <section
        style={{
          position: 'relative',
          overflow: 'hidden',
          background: 'linear-gradient(135deg, #0b1e3f 0%, #1a3a6b 40%, var(--accent) 100%)',
          padding: '80px 24px 100px',
          display: 'flex',
          justifyContent: 'center',
        }}
      >
        {/* Abstract background circles */}
        <div style={{ position: 'absolute', inset: 0, overflow: 'hidden', pointerEvents: 'none' }}>
          {[320, 260, 200, 140, 80].map((size, i) => (
            <div
              key={i}
              style={{
                position: 'absolute',
                bottom: `-${size / 2.5}px`,
                right: `-${size / 4}px`,
                width: `${size}px`,
                height: `${size}px`,
                borderRadius: '50%',
                border: `1px solid rgba(26,115,232,${0.04 + i * 0.03})`,
                transform: 'translate(0, 0)',
              }}
            />
          ))}
          {[280, 230, 180, 130, 80].map((size, i) => (
            <div
              key={`b-${i}`}
              style={{
                position: 'absolute',
                bottom: `-${size / 3}px`,
                right: `${60 + i * 50}px`,
                width: `${size}px`,
                height: `${size}px`,
                borderRadius: '50%',
                border: `1px solid rgba(255,255,255,${0.02 + i * 0.02})`,
                transform: 'translate(0, 0)',
              }}
            />
          ))}
          <Shield
            style={{
              position: 'absolute',
              bottom: '20%',
              right: '15%',
              width: '280px',
              height: '280px',
              color: 'rgba(255,255,255,0.04)',
            }}
          />
        </div>

        {/* Content */}
        <div
          className="landing-hero-row"
          style={{
            width: '100%',
            maxWidth: '1280px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '48px',
            position: 'relative',
            zIndex: 1,
          }}
        >
          {/* Text */}
          <div style={{ flex: 1, maxWidth: '620px' }}>
            <div
              style={{
                display: 'inline-block',
                fontSize: '11px',
                fontWeight: 600,
                letterSpacing: '1.5px',
                textTransform: 'uppercase',
                color: 'rgba(255,255,255,0.55)',
                marginBottom: '20px',
                padding: '4px 12px',
                border: '1px solid rgba(255,255,255,0.15)',
                borderRadius: '99px',
              }}
            >
              Cloud-Native Application Protection Platform
            </div>
            <h1
              className="landing-hero-headline"
              style={{
                fontSize: '44px',
                fontWeight: 800,
                lineHeight: 1.15,
                color: 'var(--text-inverse)',
                margin: '0 0 20px 0',
                letterSpacing: '-0.5px',
              }}
            >
              Protect Everything You Build and Run in the Cloud
            </h1>
            <p
              style={{
                fontSize: '16px',
                lineHeight: 1.6,
                color: 'rgba(255,255,255,0.82)',
                margin: '0 0 36px 0',
                maxWidth: '520px',
              }}
            >
              AI-powered cloud security from code to runtime. Detect misconfigurations,
              vulnerabilities, and threats across AWS, Azure, GCP, and OCI — before
              they reach production.
            </p>

            {/* CTAs */}
            <div
              className="landing-hero-ctas"
              style={{ display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}
            >
              <Link
                href="/signup"
                style={{
                  height: '44px',
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
              <button
                style={{
                  height: '44px',
                  padding: '0 28px',
                  fontSize: '15px',
                  fontWeight: 600,
                  color: 'var(--text-inverse)',
                  backgroundColor: 'transparent',
                  border: '1px solid rgba(255,255,255,0.3)',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px',
                  transition: 'border-color 0.15s, background-color 0.15s',
                }}
              >
                View demo
                <ChevronRight size={16} />
              </button>
            </div>

            <p
              style={{
                fontSize: '12px',
                color: 'rgba(255,255,255,0.5)',
                marginTop: '16px',
              }}
            >
              No credit card required. 14-day free trial.
            </p>
          </div>

          {/* Visual placeholder */}
          <div
            className="landing-hero-visual"
            style={{
              width: '420px',
              flexShrink: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <div
              style={{
                width: '100%',
                aspectRatio: '1',
                maxWidth: '380px',
                borderRadius: '16px',
                background: 'rgba(255,255,255,0.05)',
                border: '1px solid rgba(255,255,255,0.08)',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '16px',
                padding: '40px',
              }}
            >
              <Shield style={{ width: '80px', height: '80px', color: 'rgba(255,255,255,0.25)' }} />
              <div style={{ display: 'flex', gap: '12px' }}>
                {['AWS', 'Azure', 'GCP', 'OCI'].map((p) => (
                  <span
                    key={p}
                    style={{
                      fontSize: '11px',
                      fontWeight: 600,
                      color: 'rgba(255,255,255,0.55)',
                      padding: '4px 10px',
                      borderRadius: '99px',
                      border: '1px solid rgba(255,255,255,0.12)',
                    }}
                  >
                    {p}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
