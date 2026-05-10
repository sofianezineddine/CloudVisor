'use client';

const TESTIMONIALS = [
  {
    quote:
      'CloudVisor cut our alert volume by 80% while catching things our previous CSPM missed entirely. The graph-based asset view alone is worth the price.',
    name: 'Sarah Klein',
    title: 'VP of Security Engineering',
    company: 'TechCorp',
    initials: 'SK',
    color: '#d45b07',
  },
  {
    quote:
      'We went from zero cloud visibility to full compliance reporting in two weeks. Our SOC 2 auditor was impressed — and so was our board.',
    name: 'Marcus Chen',
    title: 'CISO',
    company: 'FinScale',
    initials: 'MC',
    color: '#0073bb',
  },
  {
    quote:
      'The CI/CD integration gave our developers instant feedback without slowing pipelines. We caught 12 secrets before they ever hit a repo — priceless.',
    name: 'Amara Osei',
    title: 'Director of Platform Engineering',
    company: 'CloudScale',
    initials: 'AO',
    color: '#1a6b3c',
  },
];

export default function Testimonials() {
  return (
    <>
      <style>{`
        @media (max-width: 768px) {
          .landing-testimonial-grid { grid-template-columns: 1fr !important; }
        }
      `}</style>

      <section
        style={{
          backgroundColor: 'var(--bg-surface)',
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
                color: 'var(--text-primary)',
                margin: '0 0 12px 0',
                letterSpacing: '-0.3px',
              }}
            >
              Trusted by Security Leaders
            </h2>
            <p
              style={{
                fontSize: '15px',
                color: 'var(--text-secondary)',
                margin: 0,
                lineHeight: 1.6,
              }}
            >
              Don&apos;t take our word for it.
            </p>
          </div>

          <div
            className="landing-testimonial-grid"
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))',
              gap: '24px',
            }}
          >
            {TESTIMONIALS.map((t) => (
              <div
                key={t.name}
                style={{
                  backgroundColor: 'var(--bg-base)',
                  border: '1px solid var(--border-default)',
                  borderRadius: 'var(--radius-container)',
                  padding: '28px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '20px',
                }}
              >
                {/* Quote */}
                <p
                  style={{
                    fontSize: '14px',
                    lineHeight: 1.65,
                    color: 'var(--text-primary)',
                    margin: 0,
                    fontStyle: 'italic',
                  }}
                >
                  &ldquo;{t.quote}&rdquo;
                </p>

                {/* Author */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <div
                    style={{
                      width: '44px',
                      height: '44px',
                      borderRadius: '50%',
                      backgroundColor: `${t.color}18`,
                      border: `2px solid ${t.color}40`,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: '15px',
                      fontWeight: 700,
                      color: t.color,
                      flexShrink: 0,
                    }}
                  >
                    {t.initials}
                  </div>
                  <div>
                    <div
                      style={{
                        fontSize: '14px',
                        fontWeight: 700,
                        color: 'var(--text-primary)',
                      }}
                    >
                      {t.name}
                    </div>
                    <div
                      style={{
                        fontSize: '12px',
                        color: 'var(--text-secondary)',
                        marginTop: '2px',
                      }}
                    >
                      {t.title}, {t.company}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}
