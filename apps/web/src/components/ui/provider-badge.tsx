import * as React from 'react';

interface ProviderBadgeProps {
  provider: 'aws' | 'azure' | 'gcp' | 'oci' | string;
  size?: 'sm' | 'md';
}

const PROVIDER_STYLES: Record<string, { color: string; bg: string; label: string }> = {
  aws:   { color: 'var(--aws)',   bg: 'var(--aws-bg)',   label: 'AWS' },
  azure: { color: 'var(--azure)', bg: 'var(--azure-bg)', label: 'Azure' },
  gcp:   { color: 'var(--gcp)',   bg: 'var(--gcp-bg)',   label: 'GCP' },
  oci:   { color: 'var(--oci)',   bg: 'var(--oci-bg)',   label: 'OCI' },
};

export default function ProviderBadge({ provider, size = 'md' }: ProviderBadgeProps) {
  const s = PROVIDER_STYLES[provider?.toLowerCase()] ?? {
    color: 'var(--text-secondary)',
    bg: 'var(--bg-elevated)',
    label: (provider || 'Unknown').toUpperCase(),
  };

  return (
    <span
      className="inline-flex items-center font-semibold"
      style={{
        borderRadius: '2px',
        color: s.color,
        backgroundColor: s.bg,
        border: `1px solid ${s.color}30`,
        padding: size === 'sm' ? '1px 5px' : '2px 6px',
        fontSize: size === 'sm' ? '11px' : '12px',
        fontFamily: 'var(--font-sans)',
        whiteSpace: 'nowrap',
      }}
    >
      {s.label}
    </span>
  );
}
