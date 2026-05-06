'use client';

import * as React from 'react';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/hooks/use-auth';
import {
  User,
  Building2,
  Clock,
  Shield,
  Edit3,
  Save,
  Lock,
} from 'lucide-react';
import { toast } from 'sonner';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8002';

export default function ProfilePage() {
  const { user, refreshUser } = useAuth();
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
    document.title = 'Profile - Settings - CloudVisor';
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
    <>
      {/* Page Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>Profile</h1>
        <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
          Manage your personal information and security settings
        </p>
      </div>

      {/* Content */}
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
    </>
  );
}
