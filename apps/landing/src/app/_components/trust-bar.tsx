'use client';

export default function TrustBar() {
  const logos = [
    { letter: 'T', label: 'TechCorp' },
    { letter: 'F', label: 'FinServ' },
    { letter: 'H', label: 'HealthPlus' },
    { letter: 'C', label: 'CloudScale' },
    { letter: 'D', label: 'DataVault' },
    { letter: 'S', label: 'SecureNet' },
  ];

  return (
    <section
      style={{
        backgroundColor: 'var(--bg-surface)',
        borderBottom: '1px solid var(--border-default)',
        padding: '32px 24px',
        display: 'flex',
        justifyContent: 'center',
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '1280px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '40px',
          flexWrap: 'wrap',
        }}
      >
        <span
          style={{
            fontSize: '13px',
            fontWeight: 600,
            color: 'var(--text-secondary)',
            whiteSpace: 'nowrap',
          }}
        >
          Trusted by 500+ security teams
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '32px', flexWrap: 'wrap' }}>
          {logos.map((logo) => (
            <div
              key={logo.letter}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                opacity: 0.55,
              }}
              title={logo.label}
            >
              <div
                style={{
                  width: '28px',
                  height: '28px',
                  borderRadius: '6px',
                  backgroundColor: 'var(--bg-elevated)',
                  border: '1px solid var(--border-faint)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '13px',
                  fontWeight: 700,
                  color: 'var(--text-tertiary)',
                }}
              >
                {logo.letter}
              </div>
              <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)' }}>
                {logo.label}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
