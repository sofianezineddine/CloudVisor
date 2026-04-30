'use client';

import * as React from 'react';
import { AppLayout } from '@/components/layout';
import { ProtectedRoute } from '@/components/protected-route';
import { Button } from '@/components/ui/button';
import { StatusBadge } from '@/components/ui/status-badge';
import { cn } from '@/lib/utils';
import { useAuth } from '@/hooks/use-auth';
import {
  User,
  Building2,
  CreditCard,
  Key,
  History,
  Edit3,
  Save,
  Download,
  Plus,
  Copy,
  Trash2,
  CheckCircle2,
  AlertCircle,
  Clock,
  Mail,
  Shield,
  Cloud,
  Lock,
} from 'lucide-react';
import { toast } from 'sonner';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8002';

// ─── Mock Data (replace with real API calls later) ───────────────────────────
const mockBilling = {
  currentPlan: 'Growth',
  price: '$49.00/mo',
  nextBilling: 'May 1, 2026',
  paymentMethod: 'Visa ending in 4242',
  status: 'active',
};

const mockPaymentHistory = [
  { id: 1, date: 'Apr 1, 2026', amount: '$49.00', status: 'paid', invoice: 'INV-2026-041' },
  { id: 2, date: 'Mar 1, 2026', amount: '$49.00', status: 'paid', invoice: 'INV-2026-031' },
  { id: 3, date: 'Feb 1, 2026', amount: '$49.00', status: 'paid', invoice: 'INV-2026-021' },
  { id: 4, date: 'Jan 1, 2026', amount: '$49.00', status: 'paid', invoice: 'INV-2026-011' },
];

const mockActivity = [
  { id: 1, action: 'Password changed', time: '2 hours ago', ip: '192.168.1.45', status: 'success' },
  { id: 2, action: 'New API key generated', time: '1 day ago', ip: '192.168.1.45', status: 'success' },
  { id: 3, action: 'Failed login attempt', time: '3 days ago', ip: '203.0.113.12', status: 'failed' },
  { id: 4, action: 'Organization plan upgraded', time: '1 week ago', ip: '192.168.1.45', status: 'success' },
  { id: 5, action: 'MFA enabled', time: '2 weeks ago', ip: '192.168.1.45', status: 'success' },
];

const mockApiKeys = [
  { id: 1, name: 'Production App', key: 'cv_live_8f3k...9x2m', created: 'Jan 20, 2026', lastUsed: '2 hours ago', active: true },
  { id: 2, name: 'CI/CD Pipeline', key: 'cv_live_7h2j...4k9p', created: 'Feb 14, 2026', lastUsed: '1 day ago', active: true },
  { id: 3, name: 'Local Testing', key: 'cv_live_3m9k...1x7n', created: 'Mar 5, 2026', lastUsed: 'Never', active: false },
];

// ─── Tabs Configuration ──────────────────────────────────────────────────────
const tabs = [
  { id: 'profile', label: 'Profile', icon: User },
  { id: 'billing', label: 'Billing & Payments', icon: CreditCard },
  { id: 'api-keys', label: 'API Keys', icon: Key },
  { id: 'activity', label: 'Activity Log', icon: History },
] as const;

type TabId = (typeof tabs)[number]['id'];

export default function ProfilePage() {
  const { user, refreshUser } = useAuth();
  const [activeTab, setActiveTab] = React.useState<TabId>('profile');
  const [isEditing, setIsEditing] = React.useState(false);
  const [formData, setFormData] = React.useState({
    firstName: '',
    lastName: '',
  });
  const [passwordData, setPasswordData] = React.useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  });
  const [loading, setLoading] = React.useState(false);
  const [saving, setSaving] = React.useState(false);

  React.useEffect(() => {
    document.title = 'Profile - CloudVisor';
  }, []);

  // Initialize form data from auth context user
  React.useEffect(() => {
    if (user) {
      setFormData({
        firstName: user.first_name || '',
        lastName: user.last_name || '',
      });
    }
  }, [user]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_BASE_URL}/auth/me`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          first_name: formData.firstName,
          last_name: formData.lastName,
        }),
      });

      if (!response.ok) throw new Error('Failed to update profile');

      await refreshUser();
      setIsEditing(false);
      toast.success('Profile updated successfully');
    } catch (err) {
      toast.error('Failed to update profile');
    } finally {
      setSaving(false);
    }
  };

  const handleChangePassword = async () => {
    if (passwordData.newPassword !== passwordData.confirmPassword) {
      toast.error('New passwords do not match');
      return;
    }
    if (passwordData.newPassword.length < 8) {
      toast.error('Password must be at least 8 characters');
      return;
    }
    if (!passwordData.currentPassword) {
      toast.error('Current password is required');
      return;
    }

    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_BASE_URL}/auth/password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          current_password: passwordData.currentPassword,
          new_password: passwordData.newPassword,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to change password');
      }

      toast.success('Password changed successfully');
      setPasswordData({ currentPassword: '', newPassword: '', confirmPassword: '' });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to change password');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard');
  };

  const profile = {
    firstName: formData.firstName || user?.first_name || '',
    lastName: formData.lastName || user?.last_name || '',
    email: user?.email || '',
    role: user?.role || 'Viewer',
    organization: user?.organization_name || '',
    orgId: user?.organization_id || '',
    joinedAt: (user as any)?.created_at ? new Date((user as any).created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : 'Unknown',
    mfaEnabled: (user as any)?.mfa_enabled || false,
  };

  return (
    <ProtectedRoute>
      <AppLayout>
        {/* Page Header */}
        <div className="mb-6">
          <h1 className="text-h1" style={{ color: 'var(--text-primary)' }}>Profile & Settings</h1>
          <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
            Manage your account, billing, and security preferences
          </p>
        </div>

        {/* Tabs Navigation */}
        <div className="mb-6 flex gap-2 overflow-x-auto border-b pb-1" style={{ borderColor: 'var(--border-default)' }}>
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  'flex items-center gap-2 rounded-t-lg px-4 py-2.5 text-sm font-medium transition-colors',
                )}
                style={
                  activeTab === tab.id
                    ? { backgroundColor: 'var(--bg-surface)', color: 'var(--accent)', borderBottom: `2px solid var(--accent)` }
                    : { color: 'var(--text-secondary)' }
                }
                onMouseEnter={e => {
                  if (activeTab !== tab.id) (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)');
                }}
                onMouseLeave={e => {
                  if (activeTab !== tab.id) (e.currentTarget.style.backgroundColor = 'transparent');
                }}
              >
                <Icon className="h-4 w-4" />
                <span className="hidden sm:inline">{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Tab Content */}
        <div className="space-y-6">
          {/* ─── Profile Tab ────────────────────────────────────────────────── */}
          {activeTab === 'profile' && (
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
              {/* Personal Info */}
              <div className="lg:col-span-2 cv-container p-6">
                <div className="mb-6 flex items-center justify-between">
                  <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Personal Information</h3>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => (isEditing ? handleSave() : setIsEditing(true))}
                    className="gap-1.5 text-xs"
                    disabled={saving}
                  >
                    {isEditing ? <Save className="h-3.5 w-3.5" /> : <Edit3 className="h-3.5 w-3.5" />}
                    {saving ? 'Saving...' : isEditing ? 'Save' : 'Edit'}
                  </Button>
                </div>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div>
                    <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>First Name</label>
                    <input
                      type="text"
                      value={formData.firstName}
                      onChange={(e) => setFormData({ ...formData, firstName: e.target.value })}
                      disabled={!isEditing}
                      className="w-full rounded-md border px-3 py-2 text-sm transition-colors focus:outline-none"
                      style={{
                        borderColor: 'var(--border-default)',
                        backgroundColor: 'var(--bg-base)',
                        color: 'var(--text-primary)',
                        opacity: isEditing ? 1 : 0.75,
                        cursor: isEditing ? 'text' : 'not-allowed',
                      }}
                    />
                  </div>
                  <div>
                    <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>Last Name</label>
                    <input
                      type="text"
                      value={formData.lastName}
                      onChange={(e) => setFormData({ ...formData, lastName: e.target.value })}
                      disabled={!isEditing}
                      className="w-full rounded-md border px-3 py-2 text-sm transition-colors focus:outline-none"
                      style={{
                        borderColor: 'var(--border-default)',
                        backgroundColor: 'var(--bg-base)',
                        color: 'var(--text-primary)',
                        opacity: isEditing ? 1 : 0.75,
                        cursor: isEditing ? 'text' : 'not-allowed',
                      }}
                    />
                  </div>
                  <div className="sm:col-span-2">
                    <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>Email Address</label>
                    <input
                      type="email"
                      value={profile.email}
                      disabled
                      className="w-full rounded-md border px-3 py-2 text-sm"
                      style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-base)', color: 'var(--text-primary)', opacity: 0.75, cursor: 'not-allowed' }}
                    />
                    <p className="mt-1 text-xs" style={{ color: 'var(--text-tertiary)' }}>Email cannot be changed. Contact support if you need to update it.</p>
                  </div>
                </div>

                {/* Password Change Section */}
                <div className="mt-6 border-t pt-6" style={{ borderColor: 'var(--border-faint)' }}>
                  <h4 className="mb-4 text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Security</h4>
                  
                  {user?.provider === 'local' ? (
                    <div>
                      <h5 className="mb-3 text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>Change Password</h5>
                      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                        <div>
                          <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>Current Password</label>
                          <input
                            type="password"
                            value={passwordData.currentPassword}
                            onChange={(e) => setPasswordData({ ...passwordData, currentPassword: e.target.value })}
                            className="w-full rounded-md border px-3 py-2 text-sm focus:outline-none"
                            style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-base)', color: 'var(--text-primary)' }}
                            placeholder="••••••••"
                          />
                        </div>
                        <div>
                          <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>New Password</label>
                          <input
                            type="password"
                            value={passwordData.newPassword}
                            onChange={(e) => setPasswordData({ ...passwordData, newPassword: e.target.value })}
                            className="w-full rounded-md border px-3 py-2 text-sm focus:outline-none"
                            style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-base)', color: 'var(--text-primary)' }}
                            placeholder="••••••••"
                          />
                        </div>
                        <div className="flex items-end">
                          <Button
                            onClick={handleChangePassword}
                            disabled={loading || !passwordData.currentPassword || !passwordData.newPassword}
                            className="gap-1.5 text-xs"
                          >
                            <Lock className="h-3.5 w-3.5" />
                            {loading ? 'Changing...' : 'Change Password'}
                          </Button>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="rounded-md border p-4" style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-elevated)' }}>
                      <div className="flex items-start gap-3">
                        <Shield className="h-5 w-5 mt-0.5" style={{ color: 'var(--accent)' }} />
                        <div>
                          <h5 className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                            Password managed by {user?.provider === 'google' ? 'Google' : user?.provider === 'github' ? 'GitHub' : 'Provider'}
                          </h5>
                          <p className="mt-1 text-xs" style={{ color: 'var(--text-secondary)' }}>
                            You signed up using {user?.provider === 'google' ? 'Google' : user?.provider === 'github' ? 'GitHub' : 'external'} authentication.
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Account Details */}
              <div className="cv-container p-6">
                <h3 className="mb-4 text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Account Details</h3>
                <div className="space-y-4">
                  {[
                    { icon: User, bg: 'var(--accent-dim)', color: 'var(--accent)', label: 'Role', value: profile.role },
                    { icon: Shield, bg: 'var(--success-dim)', color: 'var(--success)', label: 'MFA Status', value: profile.mfaEnabled ? 'Enabled' : 'Disabled', valueColor: 'var(--success)' },
                    { icon: Building2, bg: 'var(--bg-elevated)', color: 'var(--text-secondary)', label: 'Organization', value: profile.organization },
                    { icon: Clock, bg: 'var(--bg-elevated)', color: 'var(--text-secondary)', label: 'Member Since', value: profile.joinedAt },
                  ].map(({ icon: Icon, bg, color, label, value, valueColor }) => (
                    <div key={label} className="flex items-center gap-3">
                      <div className="flex h-8 w-8 items-center justify-center rounded-md" style={{ backgroundColor: bg }}>
                        <Icon className="h-4 w-4" style={{ color }} />
                      </div>
                      <div>
                        <div className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{label}</div>
                        <div className="text-sm font-medium" style={{ color: valueColor ?? 'var(--text-primary)' }}>{value}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ─── Billing & Payments Tab ─────────────────────────────────────── */}
          {activeTab === 'billing' && (
            <div className="space-y-6">
              {/* Current Subscription */}
              <div className="cv-container p-6">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Current Subscription</h3>
                    <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Manage your plan and payment method</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="rounded-full px-3 py-1 text-xs font-semibold" style={{ backgroundColor: 'var(--accent-dim)', color: 'var(--accent)' }}>
                      {mockBilling.currentPlan}
                    </span>
                    <span className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>{mockBilling.price}</span>
                  </div>
                </div>
                <div className="mt-4 grid grid-cols-1 gap-4 border-t pt-4 sm:grid-cols-3" style={{ borderColor: 'var(--border-faint)' }}>
                  <div>
                    <div className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Next Billing Date</div>
                    <div className="mt-1 text-sm" style={{ color: 'var(--text-primary)' }}>{mockBilling.nextBilling}</div>
                  </div>
                  <div>
                    <div className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Payment Method</div>
                    <div className="mt-1 flex items-center gap-2 text-sm" style={{ color: 'var(--text-primary)' }}>
                      <CreditCard className="h-3.5 w-3.5" style={{ color: 'var(--text-tertiary)' }} />
                      {mockBilling.paymentMethod}
                    </div>
                  </div>
                  <div className="flex items-end">
                    <Button variant="outline" size="sm" className="w-full sm:w-auto">Change Plan</Button>
                  </div>
                </div>
              </div>

              {/* Payment History */}
              <div className="cv-container overflow-hidden">
                <div className="border-b px-6 py-4" style={{ borderColor: 'var(--border-faint)' }}>
                  <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Payment History</h3>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b" style={{ borderColor: 'var(--border-faint)', backgroundColor: 'var(--bg-elevated)' }}>
                        {['Date', 'Amount', 'Status', 'Invoice', ''].map(h => (
                          <th key={h} className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y" style={{ borderColor: 'var(--border-faint)' }}>
                      {mockPaymentHistory.map((payment) => (
                        <tr
                          key={payment.id}
                          onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                          onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
                        >
                          <td className="px-6 py-4 text-sm" style={{ color: 'var(--text-primary)' }}>{payment.date}</td>
                          <td className="px-6 py-4 text-sm font-mono" style={{ color: 'var(--text-primary)' }}>{payment.amount}</td>
                          <td className="px-6 py-4">
                            <span className="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium" style={{ backgroundColor: 'var(--success-dim)', color: 'var(--success)' }}>
                              <CheckCircle2 className="h-3 w-3" />
                              Paid
                            </span>
                          </td>
                          <td className="px-6 py-4 text-sm font-mono" style={{ color: 'var(--text-tertiary)' }}>{payment.invoice}</td>
                          <td className="px-6 py-4 text-right">
                            <button style={{ color: 'var(--accent)' }}>
                              <Download className="h-4 w-4" />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* ─── API Keys Tab ───────────────────────────────────────────────── */}
          {activeTab === 'api-keys' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>API Keys</h3>
                  <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Manage keys used to authenticate API requests</p>
                </div>
                <Button size="sm" className="gap-1.5">
                  <Plus className="h-4 w-4" />
                  Generate Key
                </Button>
              </div>

              <div className="cv-container overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b" style={{ borderColor: 'var(--border-faint)', backgroundColor: 'var(--bg-elevated)' }}>
                        {['Name', 'Key', 'Created', 'Last Used', 'Status', 'Actions'].map(h => (
                          <th key={h} className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y" style={{ borderColor: 'var(--border-faint)' }}>
                      {mockApiKeys.map((apiKey) => (
                        <tr
                          key={apiKey.id}
                          onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                          onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
                        >
                          <td className="px-6 py-4 text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{apiKey.name}</td>
                          <td className="px-6 py-4">
                            <div className="flex items-center gap-2">
                              <code className="font-mono text-xs" style={{ color: 'var(--text-secondary)' }}>{apiKey.key}</code>
                              <button onClick={() => copyToClipboard(apiKey.key)} style={{ color: 'var(--text-tertiary)' }}>
                                <Copy className="h-3.5 w-3.5" />
                              </button>
                            </div>
                          </td>
                          <td className="px-6 py-4 text-sm" style={{ color: 'var(--text-tertiary)' }}>{apiKey.created}</td>
                          <td className="px-6 py-4 text-sm" style={{ color: 'var(--text-tertiary)' }}>{apiKey.lastUsed}</td>
                          <td className="px-6 py-4">
                            {apiKey.active ? (
                              <span className="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium" style={{ backgroundColor: 'var(--success-dim)', color: 'var(--success)' }}>
                                <CheckCircle2 className="h-3 w-3" />
                                Active
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium" style={{ backgroundColor: 'var(--info-dim)', color: 'var(--info)' }}>
                                <AlertCircle className="h-3 w-3" />
                                Revoked
                              </span>
                            )}
                          </td>
                          <td className="px-6 py-4 text-right">
                            <button style={{ color: 'var(--danger)' }}>
                              <Trash2 className="h-4 w-4" />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* ─── Activity Log Tab ───────────────────────────────────────────── */}
          {activeTab === 'activity' && (
            <div className="cv-container overflow-hidden">
              <div className="border-b px-6 py-4" style={{ borderColor: 'var(--border-faint)' }}>
                <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Recent Activity</h3>
                <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Track logins, security changes, and account actions</p>
              </div>
              <div className="divide-y" style={{ borderColor: 'var(--border-faint)' }}>
                {mockActivity.map((activity) => (
                  <div
                    key={activity.id}
                    className="flex items-center justify-between px-6 py-4 transition-colors"
                    onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                    onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
                  >
                    <div className="flex items-center gap-4">
                      <div
                        className="flex h-8 w-8 items-center justify-center rounded-full"
                        style={{ backgroundColor: activity.status === 'success' ? 'var(--success-dim)' : 'var(--critical-dim)' }}
                      >
                        {activity.status === 'success' ? (
                          <CheckCircle2 className="h-4 w-4" style={{ color: 'var(--success)' }} />
                        ) : (
                          <AlertCircle className="h-4 w-4" style={{ color: 'var(--critical)' }} />
                        )}
                      </div>
                      <div>
                        <div className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{activity.action}</div>
                        <div className="flex items-center gap-2 text-xs" style={{ color: 'var(--text-tertiary)' }}>
                          <span>{activity.time}</span>
                          <span>•</span>
                          <span>IP: {activity.ip}</span>
                        </div>
                      </div>
                    </div>
                    <span
                      className="rounded-full px-2 py-0.5 text-xs font-medium"
                      style={
                        activity.status === 'success'
                          ? { backgroundColor: 'var(--success-dim)', color: 'var(--success)' }
                          : { backgroundColor: 'var(--critical-dim)', color: 'var(--critical)' }
                      }
                    >
                      {activity.status === 'success' ? 'Success' : 'Failed'}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </AppLayout>
    </ProtectedRoute>
  );
}
