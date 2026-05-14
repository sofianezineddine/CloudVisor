'use client';

import * as React from 'react';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/hooks/use-auth';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  User,
  Building2,
  Clock,
  Shield,
  Edit3,
  Save,
  Lock,
  Monitor,
  Trash2,
  Loader2,
  Smartphone,
  CheckCircle2 as CheckCircle2Icon,
} from 'lucide-react';
import { toast } from 'sonner';
import { authAPI } from '@/lib/api/auth';

export default function ProfilePage() {
  const { user, refreshUser } = useAuth();
  const queryClient = useQueryClient();
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
      await authAPI.updateProfile({
        first_name: formData.firstName,
        last_name: formData.lastName,
      });
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
      await authAPI.changePassword({
        current_password: passwordData.currentPassword,
        new_password: passwordData.newPassword,
      });
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
    joinedAt: user?.created_at ? new Date(user.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : 'Unknown',
    mfaEnabled: user?.mfa_enabled ?? false,
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

                {/* MFA Enrollment */}
                <div className="mt-5 pt-4" style={{ borderTop: '1px solid var(--border-faint)' }}>
                  <h5 className="mb-3 text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>
                    Two-Factor Authentication (MFA)
                  </h5>
                  <MfaSection mfaEnabled={profile.mfaEnabled} />
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

      {/* Active Sessions */}
      <SessionsSection />
    </>
  );
}

// ─── MFA section ──────────────────────────────────────────────────────────────

function MfaSection({ mfaEnabled }: { mfaEnabled: boolean }) {
  const [enrolling, setEnrolling] = React.useState(false);
  const [qrCode, setQrCode] = React.useState<string | null>(null);
  const [secret, setSecret] = React.useState<string | null>(null);
  const [verifyCode, setVerifyCode] = React.useState('');
  const [backupCodes, setBackupCodes] = React.useState<string[] | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const startEnrollment = async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await authAPI.enrollMfa() as any;
      setQrCode(resp?.qr_code ?? null);
      setSecret(resp?.secret ?? null);
      setEnrolling(true);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const verifyEnrollment = async () => {
    if (!verifyCode || verifyCode.length !== 6) {
      setError('Enter the 6-digit code from your authenticator app');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const resp = await authAPI.verifyMfaEnrollment(verifyCode) as any;
      setBackupCodes(resp?.backup_codes ?? []);
      setEnrolling(false);
      toast.success('MFA enabled successfully');
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  if (mfaEnabled) {
    return (
      <div className="flex items-center gap-3 rounded-md border p-3"
        style={{ borderColor: 'var(--success)', backgroundColor: 'var(--success-bg)' }}>
        <CheckCircle2Icon className="h-5 w-5 flex-shrink-0" style={{ color: 'var(--success)' }} />
        <div>
          <p className="text-sm font-medium" style={{ color: 'var(--success)' }}>MFA is enabled</p>
          <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
            Your account is protected with TOTP two-factor authentication.
          </p>
        </div>
      </div>
    );
  }

  if (backupCodes) {
    return (
      <div className="rounded-md border p-4" style={{ borderColor: 'var(--success)', backgroundColor: 'var(--success-bg)' }}>
        <p className="text-sm font-semibold mb-2" style={{ color: 'var(--success)' }}>
          MFA enabled — save your backup codes
        </p>
        <p className="text-xs mb-3" style={{ color: 'var(--text-secondary)' }}>
          Store these codes securely. Each can be used once if you lose access to your authenticator.
        </p>
        <div className="grid grid-cols-2 gap-1">
          {backupCodes.map((code, i) => (
            <code key={i} className="rounded px-2 py-1 text-xs font-mono"
              style={{ backgroundColor: 'var(--bg-elevated)', color: 'var(--text-primary)' }}>
              {code}
            </code>
          ))}
        </div>
        <Button className="mt-3 gap-1.5 text-xs" size="sm" onClick={() => setBackupCodes(null)}>
          Done
        </Button>
      </div>
    );
  }

  if (enrolling && qrCode) {
    return (
      <div className="space-y-3">
        {error && (
          <div className="rounded border p-2 text-xs" style={{ borderColor: 'var(--critical)', color: 'var(--critical)', backgroundColor: 'var(--critical-dim)' }}>
            {error}
          </div>
        )}
        <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
          Scan this QR code with your authenticator app (Google Authenticator, Authy, 1Password):
        </p>
        <img src={qrCode} alt="MFA QR Code" className="rounded border"
          style={{ width: 160, height: 160, borderColor: 'var(--border-default)' }} />
        {secret && (
          <p className="text-xs font-mono" style={{ color: 'var(--text-tertiary)' }}>
            Manual key: {secret}
          </p>
        )}
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={verifyCode}
            onChange={e => setVerifyCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
            placeholder="6-digit code"
            maxLength={6}
            className="w-32 rounded-md border px-3 py-2 text-sm font-mono focus:outline-none"
            style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-base)', color: 'var(--text-primary)' }}
          />
          <Button onClick={verifyEnrollment} disabled={loading || verifyCode.length !== 6} className="gap-1.5 text-xs" size="sm">
            {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CheckCircle2Icon className="h-3.5 w-3.5" />}
            Verify
          </Button>
          <Button variant="outline" size="sm" onClick={() => { setEnrolling(false); setQrCode(null); setSecret(null); }}>
            Cancel
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-3">
      <div className="flex h-8 w-8 items-center justify-center rounded-md" style={{ backgroundColor: 'var(--warning-dim)' }}>
        <Smartphone className="h-4 w-4" style={{ color: 'var(--warning)' }} />
      </div>
      <div className="flex-1">
        <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>MFA not enabled</p>
        <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
          Add an extra layer of security with TOTP authentication.
        </p>
      </div>
      <Button onClick={startEnrollment} disabled={loading} variant="outline" size="sm" className="gap-1.5 text-xs">
        {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Smartphone className="h-3.5 w-3.5" />}
        Enable MFA
      </Button>
      {error && <p className="text-xs" style={{ color: 'var(--critical)' }}>{error}</p>}
    </div>
  );
}

// ─── Sessions section ─────────────────────────────────────────────────────────

function SessionsSection() {
  const queryClient = useQueryClient();

  const { data: sessionsData, isLoading } = useQuery({
    queryKey: ['auth-sessions'],
    queryFn: () => authAPI.getSessions(),
    select: (d: any) => d?.sessions ?? [],
  });

  const revokeMutation = useMutation({
    mutationFn: (sessionId: string) => authAPI.revokeSession(sessionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['auth-sessions'] });
      toast.success('Session revoked');
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const sessions = sessionsData ?? [];

  return (
    <div className="mt-6 cv-container p-6">
      <h3 className="mb-4 text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
        Active Sessions
      </h3>
      {isLoading ? (
        <div className="flex items-center justify-center py-6">
          <Loader2 className="h-5 w-5 animate-spin" style={{ color: 'var(--accent)' }} />
        </div>
      ) : sessions.length === 0 ? (
        <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>No active sessions found.</p>
      ) : (
        <div className="space-y-3">
          {sessions.map((session: any) => (
            <div key={session.id}
              className="flex items-center justify-between rounded-md border p-3"
              style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-elevated)' }}>
              <div className="flex items-center gap-3">
                <Monitor className="h-4 w-4" style={{ color: 'var(--text-secondary)' }} />
                <div>
                  <div className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                    {session.device_info || 'Unknown device'}
                  </div>
                  <div className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                    {session.ip_address && `${session.ip_address} · `}
                    Last active {session.last_active_at
                      ? new Date(session.last_active_at).toLocaleString()
                      : 'unknown'}
                  </div>
                </div>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => revokeMutation.mutate(session.id)}
                disabled={revokeMutation.isPending}
              >
                {revokeMutation.isPending ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Trash2 className="h-3.5 w-3.5" />
                )}
              </Button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
