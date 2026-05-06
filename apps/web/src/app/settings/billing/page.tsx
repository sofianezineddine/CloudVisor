'use client';

import * as React from 'react';
import { Button } from '@/components/ui/button';
import { useQuery } from '@tanstack/react-query';
import { CreditCard, Loader2, AlertTriangle, TrendingUp, Package, Cloud, Users } from 'lucide-react';

// ─── Types ────────────────────────────────────────────────────────────────────

interface BillingInfo {
  plan_name: string;
  plan_tier: 'free' | 'starter' | 'professional' | 'enterprise';
  limits: {
    max_accounts: number;
    max_resources: number;
    max_users: number;
    data_retention_days: number;
  };
  usage: {
    current_accounts: number;
    current_resources: number;
    current_users: number;
  };
  billing_cycle_end?: string;
}

// ─── API helper ───────────────────────────────────────────────────────────────

async function fetchBilling(): Promise<BillingInfo> {
  const res = await fetch('/api/v1/billing', { credentials: 'include' });
  if (!res.ok) throw new Error('Failed to fetch billing info');
  return res.json();
}

// ─── Fallback data ────────────────────────────────────────────────────────────

const FALLBACK_BILLING: BillingInfo = {
  plan_name: 'Free',
  plan_tier: 'free',
  limits: {
    max_accounts: 2,
    max_resources: 500,
    max_users: 3,
    data_retention_days: 7,
  },
  usage: {
    current_accounts: 0,
    current_resources: 0,
    current_users: 1,
  },
};

// ─── Usage bar ────────────────────────────────────────────────────────────────

function UsageBar({ label, current, max, icon: Icon }: {
  label: string;
  current: number;
  max: number;
  icon: React.ElementType;
}) {
  const pct = max > 0 ? Math.min(Math.round((current / max) * 100), 100) : 0;
  const barColor = pct >= 90 ? 'var(--critical)' : pct >= 70 ? 'var(--warning)' : 'var(--success)';
  const textColor = pct >= 90 ? 'var(--critical)' : pct >= 70 ? 'var(--warning)' : 'var(--success)';

  return (
    <div className="rounded-lg border p-5" style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)' }}>
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Icon className="h-4 w-4" style={{ color: 'var(--text-secondary)' }} />
          <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{label}</span>
        </div>
        <span className="font-mono text-sm font-semibold" style={{ color: textColor }}>
          {current.toLocaleString()} / {max === -1 ? '∞' : max.toLocaleString()}
        </span>
      </div>
      {max > 0 && (
        <div className="h-2 w-full overflow-hidden rounded-full" style={{ backgroundColor: 'var(--bg-elevated)' }}>
          <div
            className="h-full rounded-full transition-all duration-700"
            style={{ width: `${pct}%`, backgroundColor: barColor }}
          />
        </div>
      )}
      {max === -1 && (
        <div className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Unlimited</div>
      )}
    </div>
  );
}

// ─── Plan tier badge ──────────────────────────────────────────────────────────

const TIER_STYLES: Record<string, { bg: string; color: string }> = {
  free: { bg: 'var(--bg-elevated)', color: 'var(--text-secondary)' },
  starter: { bg: 'var(--accent-dim)', color: 'var(--accent)' },
  professional: { bg: 'var(--success-dim)', color: 'var(--success)' },
  enterprise: { bg: 'rgba(168,85,247,0.12)', color: '#a855f7' },
};

// ─── Main page ────────────────────────────────────────────────────────────────

export default function BillingPage() {
  const { data: billing, isLoading, isError } = useQuery({
    queryKey: ['billing'],
    queryFn: fetchBilling,
    staleTime: 300_000,
    retry: false,
  });

  React.useEffect(() => {
    document.title = 'Billing - Settings - CloudVisor';
  }, []);

  const info = billing ?? FALLBACK_BILLING;
  const tierStyle = TIER_STYLES[info.plan_tier] ?? TIER_STYLES.free;

  return (
    <>
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <h1 className="text-2xl font-semibold" style={{ color: 'var(--text-primary)' }}>Billing</h1>
          <Button disabled className="gap-2 opacity-60 cursor-not-allowed">
            <TrendingUp className="h-4 w-4" />
            Upgrade Plan
          </Button>
        </div>
        <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
          Your current plan and usage
        </p>
      </div>

      <div className="space-y-6">

          {isLoading && (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin" style={{ color: 'var(--accent)' }} />
            </div>
          )}

          {isError && (
            <div className="flex items-center gap-2 rounded-lg border p-3 text-sm" style={{ borderColor: 'var(--warning)', backgroundColor: 'var(--warning-dim)', color: 'var(--text-primary)' }}>
              <AlertTriangle className="h-4 w-4 flex-shrink-0" style={{ color: 'var(--warning)' }} />
              Billing API not available — showing default plan information.
            </div>
          )}

          {/* Current plan */}
          <div className="rounded-lg border p-6" style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)' }}>
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-4">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl" style={{ backgroundColor: 'var(--accent-dim)' }}>
                  <CreditCard className="h-6 w-6" style={{ color: 'var(--accent)' }} />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-xl font-semibold" style={{ color: 'var(--text-primary)' }}>{info.plan_name}</h2>
                    <span
                      className="rounded-full px-2.5 py-0.5 text-xs font-semibold capitalize"
                      style={{ backgroundColor: tierStyle.bg, color: tierStyle.color }}
                    >
                      {info.plan_tier}
                    </span>
                  </div>
                  {info.billing_cycle_end && (
                    <p className="text-sm mt-0.5" style={{ color: 'var(--text-secondary)' }}>
                      Renews {new Date(info.billing_cycle_end).toLocaleDateString(undefined, { month: 'long', day: 'numeric', year: 'numeric' })}
                    </p>
                  )}
                </div>
              </div>
            </div>

            {/* Plan limits */}
            <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
              {[
                { label: 'Cloud Accounts', value: info.limits.max_accounts === -1 ? 'Unlimited' : info.limits.max_accounts },
                { label: 'Resources', value: info.limits.max_resources === -1 ? 'Unlimited' : info.limits.max_resources.toLocaleString() },
                { label: 'Team Members', value: info.limits.max_users === -1 ? 'Unlimited' : info.limits.max_users },
                { label: 'Data Retention', value: `${info.limits.data_retention_days}d` },
              ].map(item => (
                <div key={item.label} className="rounded-lg p-3 text-center" style={{ backgroundColor: 'var(--bg-elevated)' }}>
                  <div className="font-mono text-lg font-bold" style={{ color: 'var(--text-primary)' }}>{item.value}</div>
                  <div className="text-xs mt-0.5" style={{ color: 'var(--text-tertiary)' }}>{item.label}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Usage */}
          <div>
            <h3 className="text-sm font-semibold mb-3" style={{ color: 'var(--text-primary)' }}>Current Usage</h3>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <UsageBar label="Cloud Accounts" current={info.usage.current_accounts} max={info.limits.max_accounts} icon={Cloud} />
              <UsageBar label="Resources" current={info.usage.current_resources} max={info.limits.max_resources} icon={Package} />
              <UsageBar label="Team Members" current={info.usage.current_users} max={info.limits.max_users} icon={Users} />
            </div>
          </div>

          {/* Upgrade CTA */}
          {info.plan_tier === 'free' && (
            <div className="rounded-lg border p-6" style={{ borderColor: 'var(--accent)', backgroundColor: 'var(--accent-dim)' }}>
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Unlock more with a paid plan</h3>
                  <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
                    Get unlimited accounts, resources, and longer data retention.
                  </p>
                </div>
                <Button disabled className="gap-2 opacity-60 cursor-not-allowed flex-shrink-0">
                  <TrendingUp className="h-4 w-4" />
                  Upgrade
                </Button>
              </div>
            </div>
          )}
        </div>
    </>
  );
}
