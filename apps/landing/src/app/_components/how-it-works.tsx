'use client';

import { Plug, Search, AlertTriangle, ListFilter, Wrench } from 'lucide-react';

const STEPS = [
  {
    number: 1,
    icon: Plug,
    title: 'Connect',
    description: 'Link your cloud accounts in under 5 minutes. Read-only access — no agents required.',
  },
  {
    number: 2,
    icon: Search,
    title: 'Scan',
    description: 'Full inventory of every resource across AWS, Azure, GCP, and OCI in minutes.',
  },
  {
    number: 3,
    icon: AlertTriangle,
    title: 'Detect',
    description: '500+ rules evaluate every resource. AI reduces noise so you see what matters.',
  },
  {
    number: 4,
    icon: ListFilter,
    title: 'Prioritize',
    description: 'Risk scores combine exploit probability, internet exposure, and data sensitivity.',
  },
  {
    number: 5,
    icon: Wrench,
    title: 'Remediate',
    description: 'Step-by-step fixes with auto-generated PRs. Track resolution from open to closed.',
  },
];

export default function HowItWorks() {
  return (
    <>
      <style>{`
        @media (max-width: 768px) {
          .landing-flow-row { flex-direction: column !important; align-items: flex-start !important; }
          .landing-flow-connector { display: none !important; }
          .landing-flow-step { flex-direction: row !important; gap: 16px !important; text-align: left !important; padding: 8px 0 !important; }
        }
      `}</style>

      <section
        id="how-it-works"
        style={{
          backgroundColor: 'var(--bg-base)',
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
              How It Works
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
              Get from zero to full cloud visibility in five simple steps.
            </p>
          </div>

          <div
            className="landing-flow-row"
            style={{
              display: 'flex',
              alignItems: 'flex-start',
              justifyContent: 'center',
              gap: '0',
            }}
          >
            {STEPS.map((step, idx) => {
              const Icon = step.icon;
              return (
                <div
                  key={step.number}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0',
                  }}
                >
                  {/* Step card */}
                  <div
                    className="landing-flow-step"
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      textAlign: 'center',
                      width: '160px',
                      gap: '12px',
                    }}
                  >
                    {/* Number circle */}
                    <div
                      style={{
                        width: '48px',
                        height: '48px',
                        borderRadius: '50%',
                        backgroundColor: 'var(--accent)',
                        color: 'var(--text-inverse)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '18px',
                        fontWeight: 700,
                        flexShrink: 0,
                      }}
                    >
                      <Icon size={20} strokeWidth={2} />
                    </div>
                    <div>
                      <div
                        style={{
                          fontSize: '14px',
                          fontWeight: 700,
                          color: 'var(--text-primary)',
                          marginBottom: '4px',
                        }}
                      >
                        {step.title}
                      </div>
                      <div
                        style={{
                          fontSize: '12px',
                          color: 'var(--text-secondary)',
                          lineHeight: 1.5,
                        }}
                      >
                        {step.description}
                      </div>
                    </div>
                  </div>

                  {/* Connector line */}
                  {idx < STEPS.length - 1 && (
                    <div
                      className="landing-flow-connector"
                      style={{
                        width: '48px',
                        height: '2px',
                        backgroundColor: 'var(--border-strong)',
                        marginTop: '24px',
                        flexShrink: 0,
                      }}
                    />
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </section>
    </>
  );
}
