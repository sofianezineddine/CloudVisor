'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Shield, Menu, X } from 'lucide-react';

const NAV_LINKS = [
  { label: 'Features', href: '#services' },
  { label: 'Solutions', href: '#capabilities' },
  { label: 'How It Works', href: '#how-it-works' },
];

export default function LandingNavbar() {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <>
      <style>{`
        @media (max-width: 768px) {
          .landing-nav-links { display: none !important; }
          .landing-nav-ctas { display: none !important; }
          .landing-nav-menu-btn { display: flex !important; }
        }
        @media (min-width: 769px) {
          .landing-nav-mobile { display: none !important; }
        }
      `}</style>

      <nav
        style={{
          position: 'sticky',
          top: 0,
          zIndex: 100,
          height: '56px',
          backgroundColor: 'var(--aws-nav-bg)',
          borderBottom: '1px solid var(--aws-nav-border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '0 24px',
        }}
      >
        <div
          style={{
            width: '100%',
            maxWidth: '1280px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          {/* Logo */}
          <Link
            href="/"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              textDecoration: 'none',
              flexShrink: 0,
            }}
          >
            <div
              style={{
                width: '36px',
                height: '36px',
                backgroundColor: 'rgba(255,255,255,0.08)',
                borderRadius: '6px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Shield style={{ width: '20px', height: '20px', color: 'var(--accent)' }} />
            </div>
            <span
              style={{
                fontSize: '18px',
                fontWeight: 700,
                color: 'var(--text-inverse)',
                letterSpacing: '-0.3px',
              }}
            >
              CloudVisor
            </span>
          </Link>

          {/* Desktop nav links */}
          <div
            className="landing-nav-links"
            style={{ display: 'flex', alignItems: 'center', gap: '32px' }}
          >
            {NAV_LINKS.map((link) => (
              <a
                key={link.href}
                href={link.href}
                style={{
                  fontSize: '14px',
                  color: 'var(--aws-nav-text)',
                  textDecoration: 'none',
                  fontWeight: 400,
                  transition: 'color 0.15s',
                }}
                onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--text-inverse)'; }}
                onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--aws-nav-text)'; }}
              >
                {link.label}
              </a>
            ))}
          </div>

          {/* Desktop CTA buttons */}
          <div
            className="landing-nav-ctas"
            style={{ display: 'flex', alignItems: 'center', gap: '12px' }}
          >
            <Link
              href="/login"
              style={{
                height: '34px',
                padding: '0 16px',
                fontSize: '14px',
                fontWeight: 600,
                color: 'var(--aws-nav-text)',
                backgroundColor: 'transparent',
                border: '1px solid var(--aws-nav-border)',
                borderRadius: '2px',
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                textDecoration: 'none',
                transition: 'background-color 0.1s, color 0.1s',
              }}
            >
              Sign In
            </Link>
            <Link
              href="/signup"
              style={{
                height: '34px',
                padding: '0 16px',
                fontSize: '14px',
                fontWeight: 600,
                color: 'var(--btn-primary-text)',
                backgroundColor: 'var(--btn-primary-bg)',
                border: '1px solid var(--btn-primary-bg)',
                borderRadius: '2px',
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                textDecoration: 'none',
                transition: 'background-color 0.1s',
              }}
            >
              Start Free Trial
            </Link>
          </div>

          {/* Mobile menu button */}
          <button
            className="landing-nav-menu-btn"
            onClick={() => setMenuOpen(!menuOpen)}
            style={{
              display: 'none',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              color: 'var(--aws-nav-text)',
              padding: '4px',
            }}
            aria-label="Toggle menu"
          >
            {menuOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
        </div>
      </nav>

      {/* Mobile menu dropdown */}
      {menuOpen && (
        <div
          className="landing-nav-mobile"
          style={{
            position: 'fixed',
            top: '56px',
            left: 0,
            right: 0,
            zIndex: 99,
            backgroundColor: 'var(--aws-nav-bg)',
            borderBottom: '1px solid var(--aws-nav-border)',
            padding: '16px 24px 24px',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px',
          }}
        >
          {NAV_LINKS.map((link) => (
            <a
              key={link.href}
              href={link.href}
              onClick={() => setMenuOpen(false)}
              style={{
                fontSize: '16px',
                color: 'var(--aws-nav-text)',
                textDecoration: 'none',
                fontWeight: 400,
              }}
            >
              {link.label}
            </a>
          ))}
          <div style={{ display: 'flex', gap: '12px', marginTop: '8px' }}>
            <Link
              href="/login"
              onClick={() => setMenuOpen(false)}
              style={{
                flex: 1,
                height: '40px',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '14px',
                fontWeight: 600,
                color: 'var(--aws-nav-text)',
                backgroundColor: 'transparent',
                border: '1px solid var(--aws-nav-border)',
                borderRadius: '2px',
                textDecoration: 'none',
              }}
            >
              Sign In
            </Link>
            <Link
              href="/signup"
              onClick={() => setMenuOpen(false)}
              style={{
                flex: 1,
                height: '40px',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '14px',
                fontWeight: 600,
                color: 'var(--btn-primary-text)',
                backgroundColor: 'var(--btn-primary-bg)',
                border: '1px solid var(--btn-primary-bg)',
                borderRadius: '2px',
                textDecoration: 'none',
              }}
            >
              Start Free Trial
            </Link>
          </div>
        </div>
      )}
    </>
  );
}
