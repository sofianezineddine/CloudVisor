'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Users, CreditCard, Cloud, TrendingUp, AlertTriangle, Activity, LogOut, LayoutDashboard, Shield, ChevronRight } from 'lucide-react';
import { authAPI } from '@/lib/api/auth';

interface AdminUser {
  id: string;
  email: string;
  name: string;
  role: string;
  last_login_at: string | null;
}

const mockClients = [
  { id: 1, name: 'Acme Corp', plan: 'Enterprise', users: 45, accounts: 12, mrr: 2500, status: 'active' },
  { id: 2, name: 'TechStart Inc', plan: 'Growth', users: 18, accounts: 5, mrr: 800, status: 'active' },
  { id: 3, name: 'CloudCo', plan: 'Starter', users: 8, accounts: 3, mrr: 300, status: 'active' },
  { id: 4, name: 'DataSafe Ltd', plan: 'Enterprise', users: 67, accounts: 18, mrr: 3200, status: 'active' },
  { id: 5, name: 'SecureNet', plan: 'Growth', users: 22, accounts: 7, mrr: 1100, status: 'trial' },
];

export default function AdminDashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<AdminUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('admin_access_token');
    if (!token) {
      router.push('/admin/login');
      return;
    }

    authAPI.getAdminUser()
      .then((data: any) => {
        setUser(data);
        setLoading(false);
      })
      .catch(() => {
        localStorage.removeItem('admin_access_token');
        localStorage.removeItem('admin_refresh_token');
        router.push('/admin/login');
      });
  }, [router]);

  const handleLogout = async () => {
    try {
      await authAPI.adminLogout();
    } catch {
      // Ignore logout errors
    }
    localStorage.removeItem('admin_access_token');
    localStorage.removeItem('admin_refresh_token');
    router.push('/admin/login');
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--bg-base)]">
        <div className="text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-[var(--accent)] border-t-transparent" />
          <p className="mt-4 text-sm text-[var(--text-secondary)]">Loading admin dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--bg-base)]">
      {/* Sidebar */}
      <aside className="fixed left-0 top-0 z-40 flex h-screen w-[240px] flex-col border-r border-[var(--border-default)] bg-[var(--bg-sidebar)]">
        <div className="flex h-14 items-center gap-2 border-b border-[rgba(255,255,255,0.08)] px-4">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-[var(--accent)]">
            <Shield className="h-4 w-4 text-white" />
          </div>
          <span className="text-sm font-semibold text-white">CloudVisor Admin</span>
        </div>

        <nav className="flex-1 px-2 py-4">
          <ul className="space-y-1">
            {[
              { label: 'Overview', href: '/admin/dashboard', icon: LayoutDashboard },
              { label: 'Clients', href: '/admin/clients', icon: Users },
              { label: 'Billing', href: '/admin/billing', icon: CreditCard },
              { label: 'Analytics', href: '/admin/analytics', icon: Activity },
            ].map((item) => (
              <li key={item.href}>
                <Link href={item.href} className="flex items-center gap-3 rounded-[var(--radius-button)] bg-[var(--admin-sidebar-active)] px-3 py-2 text-sm text-white">
                  <item.icon className="h-4 w-4 flex-shrink-0" strokeWidth={1.5} />
                  <span>{item.label}</span>
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        <div className="border-t border-[rgba(255,255,255,0.08)] px-2 py-4">
          <button onClick={handleLogout} className="flex w-full items-center gap-3 rounded-[var(--radius-button)] px-3 py-2 text-sm text-[var(--text-on-sidebar)] transition-colors hover:bg-[var(--bg-sidebar-hover)] hover:text-white">
            <LogOut className="h-4 w-4 flex-shrink-0" strokeWidth={1.5} />
            <span>Sign out</span>
          </button>
          <Link href="/" className="mt-2 flex w-full items-center gap-3 rounded-[var(--radius-button)] px-3 py-2 text-sm text-[var(--text-on-sidebar)] transition-colors hover:bg-[var(--bg-sidebar-hover)] hover:text-white">
            <ChevronRight className="h-4 w-4 flex-shrink-0" strokeWidth={1.5} />
            <span>Tenant Dashboard →</span>
          </Link>
        </div>
      </aside>

      {/* Main Content */}
      <div className="pl-[240px]">
        {/* Header */}
        <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-[var(--border-default)] bg-[var(--bg-surface)] px-6">
          <h2 className="text-sm font-medium text-[var(--text-secondary)]">Platform Administration</h2>
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-full bg-[var(--accent-dim)] flex items-center justify-center">
              <span className="text-xs font-semibold text-[var(--accent)]">{user?.name?.[0]?.toUpperCase() || 'A'}</span>
            </div>
            <div className="hidden sm:block">
              <div className="text-sm font-medium text-[var(--text-primary)]">{user?.name}</div>
              <div className="text-xs text-[var(--text-tertiary)]">{user?.email}</div>
            </div>
          </div>
        </header>

        {/* Dashboard Content */}
        <main className="p-6">
          <div className="mb-6">
            <h1 className="text-xl font-semibold text-[var(--text-primary)]">Platform Overview</h1>
            <p className="text-sm text-[var(--text-secondary)]">Key metrics for the last 30 days</p>
          </div>

          {/* Metrics Grid */}
          <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[
              { title: 'Total Clients', value: '147', icon: Users, trend: '12', color: 'accent' },
              { title: 'Active Users', value: '2,384', icon: Users, trend: '8', color: 'accent' },
              { title: 'Cloud Accounts', value: '892', icon: Cloud, trend: '15', color: 'accent' },
              { title: 'Monthly Recurring Revenue', value: '$45,230', icon: CreditCard, trend: '18', color: 'success' },
              { title: 'Security Events (24h)', value: '23', icon: AlertTriangle, color: 'critical' },
              { title: 'Platform Uptime', value: '99.97%', icon: Activity, color: 'success' },
            ].map((metric, i) => (
              <div key={i} className="rounded-[var(--radius-container)] border border-[var(--border-default)] bg-[var(--bg-surface)] p-6">
                <div className="mb-4 flex items-center justify-between">
                  <div className="flex h-10 w-10 items-center justify-center rounded-[var(--radius-container)]" style={{ backgroundColor: `var(--${metric.color}-dim)` }}>
                    <metric.icon className="h-5 w-5" style={{ color: `var(--${metric.color})` }} />
                  </div>
                  {metric.trend && (
                    <div className="flex items-center gap-1 text-sm text-[var(--success)]">
                      <TrendingUp className="h-3 w-3" />
                      <span>+{metric.trend}%</span>
                    </div>
                  )}
                </div>
                <div className="mb-1 font-mono text-2xl font-bold text-[var(--text-primary)]">{metric.value}</div>
                <div className="text-sm text-[var(--text-secondary)]">{metric.title}</div>
              </div>
            ))}
          </div>

          {/* Clients Table */}
          <div className="rounded-[var(--radius-container)] border border-[var(--border-default)] bg-[var(--bg-surface)]">
            <div className="border-b border-[var(--border-default)] px-6 py-4">
              <h2 className="text-sm font-semibold text-[var(--text-primary)]">Recent Clients</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-[var(--border-faint)]">
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-[var(--text-secondary)]">Client</th>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-[var(--text-secondary)]">Plan</th>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-[var(--text-secondary)]">Users</th>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-[var(--text-secondary)]">Cloud Accounts</th>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-[var(--text-secondary)]">MRR</th>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-[var(--text-secondary)]">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border-faint)]">
                  {mockClients.map((client) => (
                    <tr key={client.id} className="transition-colors hover:bg-[var(--bg-elevated)]">
                      <td className="whitespace-nowrap px-6 py-4 text-sm font-medium text-[var(--text-primary)]">{client.name}</td>
                      <td className="whitespace-nowrap px-6 py-4 text-sm text-[var(--text-secondary)]">{client.plan}</td>
                      <td className="whitespace-nowrap px-6 py-4 text-sm text-[var(--text-secondary)]">{client.users}</td>
                      <td className="whitespace-nowrap px-6 py-4 text-sm text-[var(--text-secondary)]">{client.accounts}</td>
                      <td className="whitespace-nowrap px-6 py-4 text-sm font-mono text-[var(--text-primary)]">${client.mrr}</td>
                      <td className="whitespace-nowrap px-6 py-4 text-sm">
                        <span className={`rounded-full px-2 py-1 text-xs font-medium ${
                          client.status === 'active'
                            ? 'bg-[var(--success-dim)] text-[var(--success)]'
                            : 'bg-[var(--warning-dim)] text-[var(--warning)]'
                        }`}>
                          {client.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
