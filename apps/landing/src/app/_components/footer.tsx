'use client';

import Link from 'next/link';
import { Shield } from 'lucide-react';

const FOOTER_COLUMNS = [
  {
    title: 'Product',
    links: [
      { label: 'Features', href: '#services' },
      { label: 'Integrations', href: '#' },
      { label: 'Pricing', href: '#' },
      { label: 'Changelog', href: '#' },
    ],
  },
  {
    title: 'Company',
    links: [
      { label: 'About', href: '#' },
      { label: 'Careers', href: '#' },
      { label: 'Blog', href: '#' },
      { label: 'Contact', href: '#' },
    ],
  },
  {
    title: 'Resources',
    links: [
      { label: 'Documentation', href: '#' },
      { label: 'API Reference', href: '#' },
      { label: 'Status', href: '#' },
      { label: 'Security', href: '#' },
    ],
  },
  {
    title: 'Legal',
    links: [
      { label: 'Privacy Policy', href: '#' },
      { label: 'Terms of Service', href: '#' },
      { label: 'DPA', href: '#' },
      { label: 'SLA', href: '#' },
    ],
  },
];

export default function LandingFooter() {
  return (
    <>
      <style>{`
        @media (max-width: 768px) {
          .landing-footer-grid { grid-template-columns: repeat(2, 1fr) !important; }
        }
        @media (max-width: 480px) {
          .landing-footer-grid { grid-template-columns: 1fr !important; }
        }
      `}</style>

      <footer
        style={{
          backgroundColor: 'var(--aws-nav-bg)',
          padding: '64px 24px 40px',
          display: 'flex',
          justifyContent: 'center',
        }}
      >
        <div style={{ width: '100%', maxWidth: '1280px' }}>
          {/* Columns */}
          <div
            className="landing-footer-grid"
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(4, 1fr)',
              gap: '32px',
              marginBottom: '48px',
            }}
          >
            {/* Brand column */}
            <div>
              <Link
                href="/"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  textDecoration: 'none',
                  marginBottom: '16px',
                }}
              >
                <div
                  style={{
                    width: '32px',
                    height: '32px',
                    backgroundColor: 'rgba(255,255,255,0.08)',
                    borderRadius: '6px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <Shield style={{ width: '18px', height: '18px', color: 'var(--accent)' }} />
                </div>
                <span
                  style={{
                    fontSize: '16px',
                    fontWeight: 700,
                    color: 'var(--text-inverse)',
                  }}
                >
                  CloudVisor
                </span>
              </Link>
              <p
                style={{
                  fontSize: '12px',
                  color: 'var(--aws-nav-text-dim)',
                  lineHeight: 1.6,
                  margin: 0,
                }}
              >
                Unified cloud security from code to runtime. Protecting infrastructure
                across AWS, Azure, GCP, and OCI.
              </p>
              {/* Social links */}
              <div style={{ display: 'flex', gap: '12px', marginTop: '20px' }}>
                {['GitHub', 'Twitter', 'LinkedIn'].map((platform) => (
                  <a
                    key={platform}
                    href="#"
                    aria-label={platform}
                    style={{
                      width: '32px',
                      height: '32px',
                      borderRadius: '6px',
                      backgroundColor: 'rgba(255,255,255,0.06)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: 'var(--aws-nav-text-dim)',
                      fontSize: '11px',
                      fontWeight: 600,
                      textDecoration: 'none',
                      transition: 'background-color 0.15s',
                    }}
                  >
                    {platform[0]}
                  </a>
                ))}
              </div>
            </div>

            {/* Link columns */}
            {FOOTER_COLUMNS.map((col) => (
              <div key={col.title}>
                <h4
                  style={{
                    fontSize: '13px',
                    fontWeight: 700,
                    color: 'var(--text-inverse)',
                    margin: '0 0 16px 0',
                  }}
                >
                  {col.title}
                </h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {col.links.map((link) => (
                    <a
                      key={link.label}
                      href={link.href}
                      style={{
                        fontSize: '13px',
                        color: 'var(--aws-nav-text-dim)',
                        textDecoration: 'none',
                        transition: 'color 0.15s',
                      }}
                      onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--text-inverse)'; }}
                      onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--aws-nav-text-dim)'; }}
                    >
                      {link.label}
                    </a>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {/* Bottom bar */}
          <div
            style={{
              borderTop: '1px solid var(--aws-nav-border)',
              paddingTop: '24px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '12px',
            }}
          >
            <span style={{ fontSize: '12px', color: 'var(--aws-nav-text-dim)' }}>
              &copy; {new Date().getFullYear()} CloudVisor. All rights reserved.
            </span>
            <span style={{ fontSize: '12px', color: 'var(--aws-nav-text-dim)' }}>
              Built for security engineers, by security engineers.
            </span>
          </div>
        </div>
      </footer>
    </>
  );
}
