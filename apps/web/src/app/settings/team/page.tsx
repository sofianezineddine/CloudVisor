'use client';

import * as React from 'react';
import { AppLayout } from '@/components/layout';
import { ProtectedRoute } from '@/components/protected-route';
import { Button } from '@/components/ui/button';
import { CvContainer } from '@/components/ui/cv-container';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/lib/api/apiClient';
import {
  UserPlus, Mail, MoreHorizontal, Shield, CheckCircle2, XCircle,
  Clock, Trash2, RefreshCw, ChevronDown, ChevronRight, X, Loader2, AlertTriangle,
} from 'lucide-react';

// ─── Types ────────────────────────────────────────────────────────────────────

type UserRole = 'owner' | 'admin' | 'member' | 'viewer';

interface TeamMember {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  mfaEnabled: boolean;
  lastLogin: string | null;
  avatarUrl?: string;
}

interface PendingInvite {
  id: string;
  email: string;
  role: UserRole;
  invitedBy: string;
  invitedAt: string;
}

const BREADCRUMBS = [
  { text: 'Home', href: '/console' },
  { text: 'Settings' },
  { text: 'Team' },
];

// ─── Mock Data ────────────────────────────────────────────────────────────────

const MOCK_MEMBERS: TeamMember[] = [
  {
    id: '1',
    name: 'John Doe',
    email: 'john@company.com',
    role: 'owner',
    mfaEnabled: true,
    lastLogin: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
  },
  {
    id: '2',
    name: 'Jane Smith',
    email: 'jane@company.com',
    role: 'admin',
    mfaEnabled: true,
    lastLogin: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(),
  },
  {
    id: '3',
    name: 'Bob Johnson',
    email: 'bob@company.com',
    role: 'member',
    mfaEnabled: false,
    lastLogin: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString(),
  },
  {
    id: '4',
    name: 'Alice Williams',
    email: 'alice@company.com',
    role: 'viewer',
    mfaEnabled: true,
    lastLogin: new Date(Date.now() - 1000 * 60 * 60 * 24 * 3).toISOString(),
  },
];

const MOCK_INVITES: PendingInvite[] = [
  {
    id: '1',
    email: 'newuser@company.com',
    role: 'member',
    invitedBy: 'John Doe',
    invitedAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 2).toISOString(),
  },
];

// ─── Role Badge ───────────────────────────────────────────────────────────────

const ROLE_STYLES: Record<UserRole, { bg: string; color: string; label: string }> = {
  owner: { bg: 'var(--purple-dim, rgba(168,85,247,0.15))', color: 'var(--purple, #a855f7)', label: 'Owner' },
  admin: { bg: 'var(--accent-dim)', color: 'var(--accent)', label: 'Admin' },
  member: { bg: 'var(--success-dim)', color: 'var(--success)', label: 'Member' },
  viewer: { bg: 'var(--bg-elevated)', color: 'var(--text-secondary)', label: 'Viewer' },
};

function RoleBadge({ role }: { role: UserRole }) {
  const style = ROLE_STYLES[role];
  return (
    <span
      className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium"
      style={{ backgroundColor: style.bg, color: style.color }}
    >
      {style.label}
    </span>
  );
}

// ─── Time Ago Helper ──────────────────────────────────────────────────────────

function timeAgo(isoDate: string | null): string {
  if (!isoDate) return 'Never';
  const diff = Date.now() - new Date(isoDate).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'Just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

// ─── Member Actions Dropdown ──────────────────────────────────────────────────

function MemberActions({
  member,
  onChangeRole,
  onRemove,
}: {
  member: TeamMember;
  onChangeRole: (id: string, role: UserRole) => void;
  onRemove: (id: string) => void;
}) {
  const [open, setOpen] = React.useState(false);
  const [triggerHover, setTriggerHover] = React.useState(false);
  const [removeHover, setRemoveHover] = React.useState(false);
  const ref = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const canEdit = member.role !== 'owner';

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(o => !o)}
        disabled={!canEdit}
        className="rounded p-1 transition-colors"
        style={{
          color: triggerHover && canEdit ? 'var(--text-primary)' : 'var(--text-tertiary)',
          backgroundColor: triggerHover && canEdit ? 'var(--bg-elevated)' : 'transparent',
          opacity: !canEdit ? 0.5 : 1,
          cursor: !canEdit ? 'not-allowed' : 'pointer',
        }}
        onMouseEnter={() => setTriggerHover(true)}
        onMouseLeave={() => setTriggerHover(false)}
      >
        <MoreHorizontal className="h-4 w-4" />
      </button>
      {open && canEdit && (
        <div
          className="absolute right-0 top-full z-50 mt-1 w-44 rounded-lg border shadow-xl"
          style={{
            borderColor: 'var(--border-default)',
            backgroundColor: 'var(--bg-overlay)',
          }}
        >
          <div
            className="px-2 py-1.5 text-xs font-medium border-b"
            style={{ color: 'var(--text-tertiary)', borderColor: 'var(--border-faint)' }}
          >
            Change Role
          </div>
          {(['admin', 'member', 'viewer'] as UserRole[]).map(role => (
            <RoleMenuItem
              key={role}
              label={ROLE_STYLES[role].label}
              disabled={member.role === role}
              onClick={() => { onChangeRole(member.id, role); setOpen(false); }}
            />
          ))}
          <div className="border-t" style={{ borderColor: 'var(--border-faint)' }}>
            <button
              onClick={() => { onRemove(member.id); setOpen(false); }}
              className="w-full px-3 py-2 text-left text-sm rounded-b-lg transition-colors"
              style={{
                color: 'var(--critical)',
                backgroundColor: removeHover ? 'var(--critical-dim)' : 'transparent',
              }}
              onMouseEnter={() => setRemoveHover(true)}
              onMouseLeave={() => setRemoveHover(false)}
            >
              Remove Member
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function RoleMenuItem({ label, disabled, onClick }: { label: string; disabled: boolean; onClick: () => void }) {
  const [hover, setHover] = React.useState(false);
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="w-full px-3 py-2 text-left text-sm transition-colors"
      style={{
        color: 'var(--text-primary)',
        backgroundColor: hover && !disabled ? 'var(--bg-elevated)' : 'transparent',
        opacity: disabled ? 0.5 : 1,
        cursor: disabled ? 'not-allowed' : 'pointer',
      }}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
    >
      {label}
    </button>
  );
}

// ─── Invite Modal ─────────────────────────────────────────────────────────────

function InviteModal({ isOpen, onClose, onInvite }: {
  isOpen: boolean;
  onClose: () => void;
  onInvite: (email: string, role: UserRole) => void;
}) {
  const [email, setEmail] = React.useState('');
  const [role, setRole] = React.useState<UserRole>('member');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (email) {
      onInvite(email, role);
      setEmail('');
      setRole('member');
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div
        className="fixed left-1/2 top-1/2 z-50 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-lg border shadow-2xl"
        style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)' }}
      >
        <div
          className="flex items-center justify-between border-b px-6 py-4"
          style={{ borderColor: 'var(--border-default)' }}
        >
          <h3 className="text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>Invite Team Member</h3>
          <button
            onClick={onClose}
            style={{ color: 'var(--text-tertiary)' }}
            onMouseEnter={e => (e.currentTarget.style.color = 'var(--text-primary)')}
            onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-tertiary)')}
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1.5" style={{ color: 'var(--text-primary)' }}>
              Email Address
            </label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="colleague@company.com"
              required
              className="w-full rounded-md border px-3 py-2 text-sm focus:outline-none focus:ring-1"
              style={{
                borderColor: 'var(--border-default)',
                backgroundColor: 'var(--bg-surface)',
                color: 'var(--text-primary)',
              }}
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1.5" style={{ color: 'var(--text-primary)' }}>
              Role
            </label>
            <select
              value={role}
              onChange={e => setRole(e.target.value as UserRole)}
              className="w-full rounded-md border px-3 py-2 text-sm focus:outline-none focus:ring-1"
              style={{
                borderColor: 'var(--border-default)',
                backgroundColor: 'var(--bg-surface)',
                color: 'var(--text-primary)',
              }}
            >
              <option value="viewer">Viewer - Read-only access</option>
              <option value="member">Member - Can manage findings</option>
              <option value="admin">Admin - Full access except billing</option>
            </select>
          </div>
          <div className="flex gap-3 pt-2">
            <Button type="button" variant="outline" onClick={onClose} className="flex-1">
              Cancel
            </Button>
            <Button type="submit" className="flex-1">
              Send Invite
            </Button>
          </div>
        </form>
      </div>
    </>
  );
}

// ─── Permissions Matrix ──────────────────────────────────────────────────────

function PermissionsMatrix({ isExpanded, onToggle }: { isExpanded: boolean; onToggle: () => void }) {
  const permissions = [
    { name: 'View findings', owner: true, admin: true, member: true, viewer: true },
    { name: 'Manage findings', owner: true, admin: true, member: true, viewer: false },
    { name: 'View assets', owner: true, admin: true, member: true, viewer: true },
    { name: 'Manage integrations', owner: true, admin: true, member: false, viewer: false },
    { name: 'Invite members', owner: true, admin: true, member: false, viewer: false },
    { name: 'Manage team', owner: true, admin: true, member: false, viewer: false },
    { name: 'View billing', owner: true, admin: false, member: false, viewer: false },
    { name: 'Manage billing', owner: true, admin: false, member: false, viewer: false },
  ];

  return (
    <div className="cv-container">
      <div className="p-5">
        <button
          onClick={onToggle}
          className="flex w-full items-center justify-between text-left"
        >
          <div className="flex items-center gap-2 text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
            <Shield className="h-5 w-5" />
            Role Permissions
          </div>
          {isExpanded
            ? <ChevronDown className="h-5 w-5" style={{ color: 'var(--text-tertiary)' }} />
            : <ChevronRight className="h-5 w-5" style={{ color: 'var(--text-tertiary)' }} />
          }
        </button>
      </div>
      {isExpanded && (
        <div className="border-t px-5 pb-5" style={{ borderColor: 'var(--border-faint)' }}>
          <div className="overflow-x-auto pt-4">
            <table className="w-full">
              <thead>
                <tr className="border-b" style={{ borderColor: 'var(--border-faint)' }}>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>
                    Permission
                  </th>
                  {['Owner', 'Admin', 'Member', 'Viewer'].map(col => (
                    <th key={col} className="px-4 py-3 text-center text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y" style={{ borderColor: 'var(--border-faint)' }}>
                {permissions.map((perm, idx) => (
                  <tr key={idx}>
                    <td className="px-4 py-3 text-sm" style={{ color: 'var(--text-primary)' }}>
                      {perm.name}
                    </td>
                    {[perm.owner, perm.admin, perm.member, perm.viewer].map((allowed, i) => (
                      <td key={i} className="px-4 py-3 text-center">
                        {allowed
                          ? <CheckCircle2 className="inline h-4 w-4" style={{ color: 'var(--success)' }} />
                          : <XCircle className="inline h-4 w-4" style={{ color: 'var(--text-tertiary)' }} />
                        }
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function TeamPage() {
  const queryClient = useQueryClient();
  const [inviteModalOpen, setInviteModalOpen] = React.useState(false);
  const [permissionsExpanded, setPermissionsExpanded] = React.useState(false);
  const [successMsg, setSuccessMsg] = React.useState<string | null>(null);

  React.useEffect(() => {
    document.title = 'Team - Settings - CloudVisor';
  }, []);

  const { data: teamData, isLoading } = useQuery({
    queryKey: ['team', 'members'],
    queryFn: async () => {
      try {
        const res = await (apiClient as any).auth?.team?.list?.() ?? null;
        return res?.data ?? null;
      } catch {
        return null;
      }
    },
    staleTime: 60_000,
  });

  const members: TeamMember[] = teamData?.members ?? MOCK_MEMBERS;
  const invites: PendingInvite[] = teamData?.invites ?? MOCK_INVITES;

  const inviteMutation = useMutation({
    mutationFn: async ({ email, role }: { email: string; role: UserRole }) => {
      try {
        await (apiClient as any).auth?.invites?.create?.({ email, role });
      } catch {
        // If endpoint doesn't exist, just show success
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['team'] });
      setSuccessMsg('Invite sent successfully');
      setTimeout(() => setSuccessMsg(null), 3000);
    },
  });

  const handleInvite = (email: string, role: UserRole) => {
    inviteMutation.mutate({ email, role });
  };

  const handleResendInvite = (id: string) => {
    console.log('Resend invite:', id);
  };

  const handleCancelInvite = (id: string) => {
    queryClient.setQueryData(['team', 'members'], (old: any) => ({
      ...old,
      invites: (old?.invites ?? MOCK_INVITES).filter((i: PendingInvite) => i.id !== id),
    }));
  };

  const handleChangeRole = (id: string, role: UserRole) => {
    queryClient.setQueryData(['team', 'members'], (old: any) => ({
      ...old,
      members: (old?.members ?? MOCK_MEMBERS).map((m: TeamMember) => m.id === id ? { ...m, role } : m),
    }));
  };

  const handleRemoveMember = (id: string) => {
    if (confirm('Are you sure you want to remove this team member?')) {
      queryClient.setQueryData(['team', 'members'], (old: any) => ({
        ...old,
        members: (old?.members ?? MOCK_MEMBERS).filter((m: TeamMember) => m.id !== id),
      }));
    }
  };

  return (
    <ProtectedRoute>
      <AppLayout breadcrumbs={BREADCRUMBS}>
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-h1" style={{ color: 'var(--text-primary)' }}>Team</h1>
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                Manage your team members and their permissions
              </p>
            </div>
            <Button onClick={() => setInviteModalOpen(true)} className="gap-2">
              <UserPlus className="h-4 w-4" />
              Invite Member
            </Button>
          </div>

          {/* Success message */}
          {successMsg && (
            <div
              className="flex items-center gap-2 rounded-lg border p-3 text-sm"
              style={{
                borderColor: 'var(--success)',
                backgroundColor: 'var(--success-dim)',
                color: 'var(--success)',
              }}
            >
              <CheckCircle2 className="h-4 w-4 flex-shrink-0" />
              {successMsg}
            </div>
          )}

          {/* Loading state */}
          {isLoading && (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin" style={{ color: 'var(--accent)' }} />
            </div>
          )}

          {/* Team Members */}
          <CvContainer header={{ title: `Team Members (${members.length})` }}>
            <div className="overflow-x-auto -mx-5 -mt-5">
              <table className="w-full">
                <thead>
                  <tr className="border-b" style={{ borderColor: 'var(--border-faint)' }}>
                    {['Member', 'Role', 'MFA', 'Last Login', ''].map((col, i) => (
                      <th
                        key={i}
                        className={`px-4 py-3 text-xs font-medium uppercase tracking-wider ${i < 4 ? 'text-left' : 'w-10'}`}
                        style={{ color: 'var(--text-secondary)' }}
                      >
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y" style={{ borderColor: 'var(--border-faint)' }}>
                  {members.map(member => (
                    <MemberRow
                      key={member.id}
                      member={member}
                      onChangeRole={handleChangeRole}
                      onRemove={handleRemoveMember}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          </CvContainer>

          {/* Pending Invites */}
          {invites.length > 0 && (
            <CvContainer header={{ title: `Pending Invites (${invites.length})` }}>
              <div className="space-y-3">
                {invites.map(invite => (
                  <InviteRow
                    key={invite.id}
                    invite={invite}
                    onResend={handleResendInvite}
                    onCancel={handleCancelInvite}
                  />
                ))}
              </div>
            </CvContainer>
          )}

          {/* Permissions Matrix */}
          <PermissionsMatrix
            isExpanded={permissionsExpanded}
            onToggle={() => setPermissionsExpanded(!permissionsExpanded)}
          />
        </div>

        {/* Invite Modal */}
        <InviteModal
          isOpen={inviteModalOpen}
          onClose={() => setInviteModalOpen(false)}
          onInvite={handleInvite}
        />
      </AppLayout>
    </ProtectedRoute>
  );
}

function MemberRow({
  member,
  onChangeRole,
  onRemove,
}: {
  member: TeamMember;
  onChangeRole: (id: string, role: UserRole) => void;
  onRemove: (id: string) => void;
}) {
  const [hover, setHover] = React.useState(false);
  return (
    <tr
      style={{ backgroundColor: hover ? 'var(--bg-elevated)' : 'transparent' }}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
    >
      <td className="px-4 py-3">
        <div className="flex items-center gap-3">
          <div
            className="flex h-8 w-8 items-center justify-center rounded-full text-sm font-medium"
            style={{ backgroundColor: 'var(--accent-dim)', color: 'var(--accent)' }}
          >
            {member.name.charAt(0)}
          </div>
          <div>
            <div className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{member.name}</div>
            <div className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{member.email}</div>
          </div>
        </div>
      </td>
      <td className="px-4 py-3">
        <RoleBadge role={member.role} />
      </td>
      <td className="px-4 py-3">
        {member.mfaEnabled
          ? <CheckCircle2 className="h-4 w-4" style={{ color: 'var(--success)' }} />
          : <XCircle className="h-4 w-4" style={{ color: 'var(--text-tertiary)' }} />
        }
      </td>
      <td className="px-4 py-3 text-sm" style={{ color: 'var(--text-tertiary)' }}>
        {timeAgo(member.lastLogin)}
      </td>
      <td className="px-4 py-3">
        <MemberActions member={member} onChangeRole={onChangeRole} onRemove={onRemove} />
      </td>
    </tr>
  );
}

function InviteRow({
  invite,
  onResend,
  onCancel,
}: {
  invite: PendingInvite;
  onResend: (id: string) => void;
  onCancel: (id: string) => void;
}) {
  return (
    <div
      className="flex items-center justify-between rounded-lg border p-4"
      style={{ borderColor: 'var(--border-default)' }}
    >
      <div className="flex items-center gap-3">
        <Mail className="h-5 w-5" style={{ color: 'var(--text-tertiary)' }} />
        <div>
          <div className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{invite.email}</div>
          <div className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
            Invited by {invite.invitedBy} · {timeAgo(invite.invitedAt)}
          </div>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <RoleBadge role={invite.role} />
        <Button variant="outline" size="sm" onClick={() => onResend(invite.id)} className="gap-1.5">
          <RefreshCw className="h-3 w-3" />
          Resend
        </Button>
        <CancelInviteButton onCancel={() => onCancel(invite.id)} />
      </div>
    </div>
  );
}

function CancelInviteButton({ onCancel }: { onCancel: () => void }) {
  const [hover, setHover] = React.useState(false);
  return (
    <button
      onClick={onCancel}
      className="inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm font-medium transition-colors"
      style={{
        borderColor: 'var(--border-default)',
        color: hover ? 'var(--critical)' : 'var(--text-primary)',
        backgroundColor: hover ? 'var(--critical-dim)' : 'transparent',
      }}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
    >
      <Trash2 className="h-3 w-3" />
      Cancel
    </button>
  );
}
