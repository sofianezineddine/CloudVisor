'use client';

import React from 'react';
import { AdminLayout } from '@/components/admin-layout';
import { AdminProtectedRoute } from '@/components/admin-protected-route';
import { Users, CreditCard, Cloud, TrendingUp, AlertTriangle, Activity, MoreVertical } from 'lucide-react';
import Link from 'next/link';

// ─── Mock data ────────────────────────────────────────────────────────────────
const mockMetrics = [
  { title: 'Total Clients', value: '147', icon: Users, color: 'var(--accent)', bg: 'var(--accent-dim)', trend: '+12%' },
  { title: 'Active Users', value: '2,384', icon: Users, color: 'var(--accent)', bg: 'var(--accent-dim)', trend: '+8%' },
  { title: 'Cloud Accounts', value: '892', icon: Cloud, color: 'var(--accent)', bg: 'var(--accent-dim)', trend: '+15%' },
  { title: 'Monthly Revenue', value: '$45,230', icon: CreditCard, color: 'var(--success)', bg: 'var(--success-dim)', trend: '+18%' },
  { title: 'Security Events (24h)', value: '23', icon: AlertTriangle, color: 'var(--critical)', bg: 'var(--critical-dim)' },
  { title: 'Platform Uptime', value: '99.97%', icon: Activity, color: 'var(--success)', bg: 'var(--success-dim)' },
];

const mockClients = [
  { id: 1, name: 'Acme Corp', plan: 'Enterprise', users: 45, accounts: 12, mrr: 2500, status: 'active' },
  { id: 2, name: 'TechStart Inc', plan: 'Growth', users: 18, accounts: 5, mrr: 800, status: 'active' },
  { id: 3, name: 'CloudCo', plan: 'Starter', users: 8, accounts: 3, mrr: 300, status: 'active' },
  { id: 4, name: 'DataSafe Ltd', plan: 'Enterprise', users: 67, accounts: 18, mrr: 3200, status: 'active' },
  { id: 5, name: 'SecureNet', plan: 'Growth', users: 22, accounts: 7, mrr: 1100, status: 'trial' },
];

// ─── Metric card ──────────────────────────────────────────────────────────────
function MetricCard({ title, value, icon: Icon, color, bg, trend }: any) {
  return (
    <div className="admin-card p-5">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex h-9 w-9 items-center justify-center rounded" style={{ backgroundColor: bg }}>
          <Icon className="h-4 w-4" style={{ color }} />
        </div>
        {trend && (
          <div className="flex items-center gap-1 text-xs" style={{ color: 'var(--success)' }}>
            <TrendingUp className="h-3 w-3" />
            <span>{trend}</span>
          </div>
        )}
      </div>
      <div className="mb-0.5 text-2xl font-bold" style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
        {value}
      </div>
      <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>{title}</div>
    </div>
  );
}

// ─── Status badge ─────────────────────────────────────────────────────────────
function StatusBadge({ status }: { status: string }) {
  const isActive = status === 'active';
  return (
    <span
      className="inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-semibold"
      style={{
        backgroundColor: isActive ? 'var(--success-dim)' : 'var(--warning-dim)',
        color: isActive ? 'var(--success)' : 'var(--warning)',
        border: `1px solid ${isActive ? 'rgba(26,107,60,0.25)' : 'rgba(141,102,5,0.25)'}`,
      }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: isActive ? 'var(--success)' : 'var(--warning)' }} />
      {status}
    </span>
  );
}

// ─── Plan badge ───────────────────────────────────────────────────────────────
function PlanBadge({ plan }: { plan: string }) {
  const colors: Record<string, { bg: string; color: string }> = {
    Enterprise: { bg: 'var(--accent-dim)', color: 'var(--accent)' },
    Growth: { bg: 'var(--success-dim)', color: 'var(--success)' },
    Starter: { bg: 'var(--bg-elevated)', color: 'var(--text-secondary)' },
  };
  const style = colors[plan] ?? colors.Starter;
  return (
    <span className="rounded px-2 py-0.5 text-xs font-medium" style={{ backgroundColor: style.bg, color: style.color }}>
      {plan}
    </span>
  );
}

// ─── Dashboard page ───────────────────────────────────────────────────────────
export default function AdminDashboardPage() {
  return (
    <AdminProtectedRoute>
      <AdminLayout>
        {/* Page header */}
        <div className="mb-5 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>Platform Overview</h1>
            <p className="text-sm mt-0.5" style={{ color: 'var(--text-secondary)' }}>Key metrics for the last 30 days</p>
          </div>
          <div className="flex items-center gap-2">
            <button className="btn-normal text-xs">Export</button>
            <button className="btn-primary text-xs">+ Add Client</button>
          </div>
        </div>

        {/* Metrics grid */}
        <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {mockMetrics.map(m => <MetricCard key={m.title} {...m} />)}
        </div>

        {/* Clients table */}
        <div className="admin-card overflow-hidden">
          <div className="flex items-center justify-between border-b px-5 py-3" style={{ borderColor: 'var(--border-faint)' }}>
            <h2 className="text-sm font-bold" style={{ color: 'var(--text-primary)' }}>Recent Clients</h2>
            <div className="flex items-center gap-2">
              <Link href="/admin/clients" className="text-xs transition-colors" style={{ color: 'var(--text-link)' }}
                onMouseEnter={e => (e.currentTarget.style.textDecoration = 'underline')}
                onMouseLeave={e => (e.currentTarget.style.textDecoration = 'none')}
              >View all</Link>
              <button className="flex h-6 w-6 items-center justify-center rounded transition-colors" style={{ color: 'var(--text-tertiary)' }}
                onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
              >
                <MoreVertical className="h-4 w-4" />
              </button>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b" style={{ borderColor: 'var(--border-faint)', backgroundColor: 'var(--bg-elevated)' }}>
                  {['Client', 'Plan', 'Users', 'Cloud Accounts', 'MRR', 'Status'].map(h => (
                    <th key={h} className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y" style={{ borderColor: 'var(--border-faint)' }}>
                {mockClients.map(client => (
                  <tr key={client.id} className="transition-colors"
                    onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                    onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
                  >
                    <td className="px-5 py-3 text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>{client.name}</td>
                    <td className="px-5 py-3"><PlanBadge plan={client.plan} /></td>
                    <td className="px-5 py-3 text-sm" style={{ color: 'var(--text-secondary)' }}>{client.users}</td>
                    <td className="px-5 py-3 text-sm" style={{ color: 'var(--text-secondary)' }}>{client.accounts}</td>
                    <td className="px-5 py-3 text-sm font-semibold" style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>${client.mrr.toLocaleString()}</td>
                    <td className="px-5 py-3"><StatusBadge status={client.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </AdminLayout>
    </AdminProtectedRoute>
  );
}
