'use client';

import { Brain, ShieldCheck, ClipboardCheck } from 'lucide-react';

const CAPABILITIES = [
  {
    icon: Brain,
    title: 'AI-Powered Threat Detection',
    description:
      'Machine learning models trained on millions of cloud events detect anomalies in real time. Behavioral baselines for every identity and workload surface threats other tools miss.',
    color: '#0073bb',
  },
  {
    icon: ShieldCheck,
    title: 'Zero-Trust Architecture',
    description:
      'Every API call, every identity action, every network path is verified. Our graph engine maps all possible attack paths so you eliminate them before attackers find them.',
    color: '#1a6b3c',
  },
  {
    icon: ClipboardCheck,
    title: 'Automated Compliance',
    description:
      'Map findings to 12+ compliance frameworks automatically. Generate SOC 2, PCI-DSS, HIPAA, and ISO 27001 evidence reports with one click — no manual evidence collection.',
    color: '#d45b07',
  },
];

export default function Capabilities() {
  return (
    <>
      <style>{`
        @media (max-width: 768px) {
          .landing-cap-row { flex-direction: column !important; }
          .landing-cap-card { max-width: 100% !important; }
        }
      `}</style>

      <section
        id="capabilities"
        style={{
          backgroundColor: 'var(--bg-surface)',
          borderTop: '1px solid var(--border-default)',
          padding: '80px 24px',
          display: 'flex',
          justifyContent: 'center',
        }}
      >
        <div style={{ width: '100%', maxWidth: '1280px' }}>
          <div style={{ textAlign: 'center', marginBottom: '56px' }}>
            <h2
              style={{
                fontSize: '28px',
                fontWeight: 800,
                color: 'var(--text-primary)',
                margin: '0 0 12px 0',
                letterSpacing: '-0.3px',
              }}
            >
              Built for Modern Security Teams
            </h2>
            <p
              style={{
                fontSize: '15px',
                color: 'var(--text-secondary)',
                margin: 0,
                maxWidth: '560px',
                marginLeft: 'auto',
                marginRight: 'auto',
                lineHeight: 1.6,
              }}
            >
              Three pillars that power every module in our platform.
            </p>
          </div>

          <div
            className="landing-cap-row"
            style={{
              display: 'flex',
              justifyContent: 'center',
              gap: '32px',
            }}
          >
            {CAPABILITIES.map((cap) => {
              const Icon = cap.icon;
              return (
                <div
                  key={cap.title}
                  className="landing-cap-card"
                  style={{
                    flex: 1,
                    maxWidth: '360px',
                    textAlign: 'center',
                    padding: '40px 28px',
                  }}
                >
                  {/* Icon circle */}
                  <div
                    style={{
                      width: '80px',
                      height: '80px',
                      borderRadius: '50%',
                      backgroundColor: `${cap.color}10`,
                      border: `2px solid ${cap.color}30`,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      margin: '0 auto 24px',
                    }}
                  >
                    <Icon size={32} style={{ color: cap.color }} strokeWidth={1.5} />
                  </div>

                  <h3
                    style={{
                      fontSize: '18px',
                      fontWeight: 700,
                      color: 'var(--text-primary)',
                      margin: '0 0 12px 0',
                    }}
                  >
                    {cap.title}
                  </h3>
                  <p
                    style={{
                      fontSize: '14px',
                      color: 'var(--text-secondary)',
                      margin: 0,
                      lineHeight: 1.6,
                    }}
                  >
                    {cap.description}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      </section>
    </>
  );
}
