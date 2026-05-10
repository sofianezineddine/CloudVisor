'use client';

import { TrendingDown, Zap, BarChart3, DollarSign } from 'lucide-react';

const STATS = [
  {
    icon: TrendingDown,
    value: '85%',
    label: 'Risk Reduction',
    description: 'Average decrease in critical findings within 90 days of deployment',
  },
  {
    icon: Zap,
    value: '30%',
    label: 'Faster Deployments',
    description: 'Security checks integrated into CI/CD eliminate manual review bottlenecks',
  },
  {
    icon: BarChart3,
    value: '10x',
    label: 'Faster Incident Resolution',
    description: 'AI-powered context and auto-generated fixes reduce MTTR dramatically',
  },
  {
    icon: DollarSign,
    value: '2x',
    label: 'Return on Investment',
    description: 'Average ROI within 6 months reported by enterprise customers',
  },
];

export default function StatsSection() {
  return (
    <>
      <style>{`
        @media (max-width: 768px) {
          .landing-stats-grid { grid-template-columns: 1fr !important; }
        }
      `}</style>

      <section
        style={{
          background: 'linear-gradient(135deg, #0b1e3f 0%, #162d50 100%)',
          padding: '80px 24px',
          display: 'flex',
          justifyContent: 'center',
        }}
      >
        <div style={{ width: '100%', maxWidth: '1280px' }}>
          <div style={{ textAlign: 'center', marginBottom: '48px' }}>
            <h2
              style={{
                fontSize: '28px',
                fontWeight: 800,
                color: 'var(--text-inverse)',
                margin: '0 0 12px 0',
                letterSpacing: '-0.3px',
              }}
            >
              Real Results from Real Teams
            </h2>
            <p
              style={{
                fontSize: '15px',
                color: 'rgba(255,255,255,0.65)',
                margin: 0,
                maxWidth: '560px',
                marginLeft: 'auto',
                marginRight: 'auto',
                lineHeight: 1.6,
              }}
            >
              Outcomes our customers measure every quarter.
            </p>
          </div>

          <div
            className="landing-stats-grid"
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
              gap: '24px',
            }}
          >
            {STATS.map((stat) => {
              const Icon = stat.icon;
              return (
                <div
                  key={stat.label}
                  style={{
                    backgroundColor: 'rgba(255,255,255,0.04)',
                    border: '1px solid rgba(255,255,255,0.08)',
                    borderRadius: '8px',
                    padding: '32px 28px',
                    textAlign: 'center',
                  }}
                >
                  <Icon
                    size={28}
                    style={{
                      color: 'var(--btn-primary-bg)',
                      marginBottom: '16px',
                      strokeWidth: 1.5,
                    }}
                  />
                  <div
                    style={{
                      fontSize: '36px',
                      fontWeight: 800,
                      color: 'var(--text-inverse)',
                      marginBottom: '8px',
                      letterSpacing: '-0.5px',
                      lineHeight: 1.1,
                    }}
                  >
                    {stat.value}
                  </div>
                  <div
                    style={{
                      fontSize: '15px',
                      fontWeight: 700,
                      color: 'rgba(255,255,255,0.85)',
                      marginBottom: '8px',
                    }}
                  >
                    {stat.label}
                  </div>
                  <div
                    style={{
                      fontSize: '13px',
                      color: 'rgba(255,255,255,0.5)',
                      lineHeight: 1.5,
                    }}
                  >
                    {stat.description}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>
    </>
  );
}
