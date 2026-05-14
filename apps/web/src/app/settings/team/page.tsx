'use client';

import * as React from 'react';
import { Button } from '@/components/ui/button';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  UserPlus, CheckCircle2, AlertCircle, MoreHorizontal, Shield, User, Eye,
  Loader2, Trash2, AlertTriangle, ChevronDown,
} from 'lucide-react';
import { toast } from 'sonner';
import { authAPI } from '@/lib/api/auth';
import { useAuth } from '@/hooks/use-auth';

const VALID_ROLES = ['owner', 'admin', 'security_engineer', 'devops', 'viewer', 'auditor'] as const;
type Role = typeof VALID_ROLES[number];

const getRoleIcon = (role: string) => {
  switch (role) {
    case 'owner':
    case 'admin': return Shield;
    case 'viewer':
    case 'auditor': return Eye;
    default: return User;
  }
};

const getRoleColor = (role: string) => {
  switch (role) {
    case 'owner': return { bg: 'var(--accent-dim)', color: 'var(--accent)' };
    case 'admin': return { bg: 'var(--success-dim)', color: 'var(--success)' };
    case 'security_engineer': return { bg: 'rgba(168,85,247,0.12)', color: '#a855f7' };
    case 'devops': return { bg: 'var(--warning-dim)', color: 'var(--warning)' };
    case 'auditor': return { bg: 'var(--info-dim)', color: 'var(--info)' };
    default: return { bg: 'var(--bg-elevated)', color: 'var(--text-secondary)' };
  }
};

interface Member {
  id: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  role: string;
  provider: string;
  mfa_enabled: boolean;
  last_login_at: string | null;
  created_at: string | null;
}

export default function TeamPage() {
  const { user: currentUser } = useAuth();
  const queryClient = useQueryClient();
  const [showInvite, setShowInvite] = React.useState(false);
  const [inviteEmail, setInviteEmail] = React.useState('');
  const [inviteRole, setInviteRole] = React.useState<Role>('viewer');
  const [inviteFirstName, setInviteFirstName] = React.useState('');
  const [inviteLastName, setInviteLastName] = React.useState('');

  React.useEffect(() => {
    document.title = 'Team - Settings - CloudVisor';
  }, []);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['team-members'],
    queryFn: () => authAPI.getMembers(),
    select: (d) => (d?.members ?? []) as Member[],
  });

  const inviteMutation = useMutation({
    mutationFn: () =>
      authAPI.inviteMember({
        email: inviteEmail,
        role: inviteRole,
        first_name: inviteFirstName || undefined,
        last_name: inviteLastName || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['team-members'] });
      toast.success(`Invitation sent to ${inviteEmail}`);
      setShowInvite(false);
      setInviteEmail('');
      setInviteFirstName('');
      setInviteLastName('');
      setInviteRole('viewer');
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const removeMutation = useMutation({
    mutationFn: (memberId: string) => authAPI.removeMember(memberId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['team-members'] });
      toast.success('Member removed');
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const changeRoleMutation = useMutation({
    mutationFn: ({ memberId, role }: { memberId: string; role: string }) =>
      authAPI.updateMemberRole(memberId, role),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['team-members'] });
      toast.success('Role updated');
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const members = data ?? [];
  const currentUserRole = currentUser?.role ?? 'viewer';
  const canManage = ['owner', 'admin'].includes(currentUserRole);

  return (
    <>
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <h1 className="text-2xl font-semibold" style={{ color: 'var(--text-primary)' }}>Team</h1>
          {canManage && (
            <Button className="gap-2" onClick={() => setShowInvite(v => !v)}>
              <UserPlus className="h-4 w-4" />
              Invite Member
            </Button>
          )}
        </div>
        <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
          Manage your team members and their permissions
        </p>
      </div>

      {/* Invite form */}
      {showInvite && (
        <div className="mb-6 rounded-lg border p-5"
          style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)' }}>
          <h3 className="text-sm font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>
            Invite a new team member
          </h3>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <label className="mb-1 block text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
                Email *
              </label>
              <input
                type="email"
                value={inviteEmail}
                onChange={e => setInviteEmail(e.target.value)}
                placeholder="colleague@company.com"
                className="w-full rounded-md border px-3 py-2 text-sm focus:outline-none"
                style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-base)', color: 'var(--text-primary)' }}
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
                First name
              </label>
              <input
                type="text"
                value={inviteFirstName}
                onChange={e => setInviteFirstName(e.target.value)}
                placeholder="Jane"
                className="w-full rounded-md border px-3 py-2 text-sm focus:outline-none"
                style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-base)', color: 'var(--text-primary)' }}
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
                Last name
              </label>
              <input
                type="text"
                value={inviteLastName}
                onChange={e => setInviteLastName(e.target.value)}
                placeholder="Doe"
                className="w-full rounded-md border px-3 py-2 text-sm focus:outline-none"
                style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-base)', color: 'var(--text-primary)' }}
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
                Role *
              </label>
              <select
                value={inviteRole}
                onChange={e => setInviteRole(e.target.value as Role)}
                className="w-full rounded-md border px-3 py-2 text-sm focus:outline-none"
                style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-base)', color: 'var(--text-primary)' }}
              >
                {VALID_ROLES.filter(r => r !== 'owner' || currentUserRole === 'owner').map(r => (
                  <option key={r} value={r}>{r.replace('_', ' ')}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="mt-4 flex gap-2">
            <Button
              onClick={() => { if (inviteEmail.trim()) inviteMutation.mutate(); }}
              disabled={!inviteEmail.trim() || inviteMutation.isPending}
              className="gap-2"
            >
              {inviteMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <UserPlus className="h-4 w-4" />}
              Send Invite
            </Button>
            <Button variant="outline" onClick={() => setShowInvite(false)}>Cancel</Button>
          </div>
        </div>
      )}

      {/* Members table */}
      <div className="rounded-lg border overflow-hidden mb-6"
        style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)' }}>
        <div className="border-b px-6 py-4" style={{ borderColor: 'var(--border-faint)' }}>
          <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
            Team Members {!isLoading && `(${members.length})`}
          </h3>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin" style={{ color: 'var(--accent)' }} />
          </div>
        ) : isError ? (
          <div className="flex items-center gap-2 p-6 text-sm"
            style={{ color: 'var(--warning)' }}>
            <AlertTriangle className="h-4 w-4 flex-shrink-0" />
            Failed to load team members. Check your permissions.
          </div>
        ) : members.length === 0 ? (
          <div className="py-12 text-center">
            <User className="h-8 w-8 mx-auto mb-3" style={{ color: 'var(--text-tertiary)' }} />
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>No team members found</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b"
                  style={{ borderColor: 'var(--border-faint)', backgroundColor: 'var(--bg-elevated)' }}>
                  {['Member', 'Role', 'MFA', 'Last Login', ...(canManage ? ['Actions'] : [])].map(h => (
                    <th key={h} className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider"
                      style={{ color: 'var(--text-secondary)' }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y" style={{ borderColor: 'var(--border-faint)' }}>
                {members.map((member) => {
                  const roleColor = getRoleColor(member.role);
                  const RoleIcon = getRoleIcon(member.role);
                  const isCurrentUser = member.id === currentUser?.id;
                  const displayName = [member.first_name, member.last_name].filter(Boolean).join(' ') || member.email;

                  return (
                    <tr key={member.id}
                      onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                      onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="flex h-8 w-8 items-center justify-center rounded-full text-sm font-medium"
                            style={{ backgroundColor: 'var(--accent-dim)', color: 'var(--accent)' }}>
                            {displayName.slice(0, 2).toUpperCase()}
                          </div>
                          <div>
                            <div className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                              {displayName}
                              {isCurrentUser && (
                                <span className="ml-2 text-xs" style={{ color: 'var(--text-tertiary)' }}>(you)</span>
                              )}
                            </div>
                            <div className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{member.email}</div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        {canManage && !isCurrentUser ? (
                          <div className="relative inline-block">
                            <select
                              value={member.role}
                              onChange={e => changeRoleMutation.mutate({ memberId: member.id, role: e.target.value })}
                              disabled={changeRoleMutation.isPending}
                              className="appearance-none rounded-full pl-2 pr-6 py-0.5 text-xs font-medium cursor-pointer focus:outline-none"
                              style={{ backgroundColor: roleColor.bg, color: roleColor.color, border: 'none' }}
                            >
                              {VALID_ROLES.filter(r => r !== 'owner' || currentUserRole === 'owner').map(r => (
                                <option key={r} value={r}>{r.replace('_', ' ')}</option>
                              ))}
                            </select>
                            <ChevronDown className="pointer-events-none absolute right-1 top-1/2 -translate-y-1/2 h-3 w-3"
                              style={{ color: roleColor.color }} />
                          </div>
                        ) : (
                          <span className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium"
                            style={{ backgroundColor: roleColor.bg, color: roleColor.color }}>
                            <RoleIcon className="h-3 w-3" />
                            {member.role.replace('_', ' ')}
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        {member.mfa_enabled ? (
                          <CheckCircle2 className="h-4 w-4" style={{ color: 'var(--success)' }} />
                        ) : (
                          <AlertCircle className="h-4 w-4" style={{ color: 'var(--warning)' }} />
                        )}
                      </td>
                      <td className="px-6 py-4 text-sm" style={{ color: 'var(--text-tertiary)' }}>
                        {member.last_login_at
                          ? new Date(member.last_login_at).toLocaleDateString()
                          : 'Never'}
                      </td>
                      {canManage && (
                        <td className="px-6 py-4">
                          {!isCurrentUser && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => {
                                if (confirm(`Remove ${displayName} from the organization?`)) {
                                  removeMutation.mutate(member.id);
                                }
                              }}
                              disabled={removeMutation.isPending}
                              title="Remove member"
                            >
                              {removeMutation.isPending ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                              ) : (
                                <Trash2 className="h-4 w-4" />
                              )}
                            </Button>
                          )}
                        </td>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
