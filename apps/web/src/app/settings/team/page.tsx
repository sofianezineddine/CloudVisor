'use client';

import * as React from 'react';
import { Button } from '@/components/ui/button';
import { UserPlus, CheckCircle2, AlertCircle, MoreHorizontal, Shield, User, Eye } from 'lucide-react';

const mockMembers = [
  { id: '1', name: 'John Doe', email: 'john@company.com', role: 'Owner', lastLogin: '10m ago', avatar: 'JD' },
  { id: '2', name: 'Jane Smith', email: 'jane@company.com', role: 'Admin', lastLogin: '2h ago', avatar: 'JS' },
  { id: '3', name: 'Bob Johnson', email: 'bob@company.com', role: 'Member', lastLogin: '1d ago', avatar: 'BJ' },
  { id: '4', name: 'Alice Williams', email: 'alice@company.com', role: 'Viewer', lastLogin: '3d ago', avatar: 'AW' },
];

const mockInvites = [
  { id: '1', email: 'newuser@company.com', role: 'Member', sentAt: '2024-01-18' },
];

const getRoleIcon = (role: string) => {
  switch (role) {
    case 'Owner': return Shield;
    case 'Admin': return Shield;
    case 'Member': return User;
    case 'Viewer': return Eye;
    default: return User;
  }
};

const getRoleColor = (role: string) => {
  switch (role) {
    case 'Owner': return { bg: 'var(--accent-dim)', color: 'var(--accent)' };
    case 'Admin': return { bg: 'var(--success-dim)', color: 'var(--success)' };
    case 'Member': return { bg: 'var(--bg-elevated)', color: 'var(--text-secondary)' };
    case 'Viewer': return { bg: 'var(--info-dim)', color: 'var(--info)' };
    default: return { bg: 'var(--bg-elevated)', color: 'var(--text-secondary)' };
  }
};

export default function TeamPage() {
  React.useEffect(() => {
    document.title = 'Team - Settings - CloudVisor';
  }, []);

  return (
    <>
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <h1 className="text-2xl font-semibold" style={{ color: 'var(--text-primary)' }}>Team</h1>
          <Button className="gap-2">
            <UserPlus className="h-4 w-4" />
            Invite Member
          </Button>
        </div>
        <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
          Manage your team members and their permissions
        </p>
      </div>

      {/* Team Members */}
      <div className="rounded-lg border overflow-hidden mb-6" style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)' }}>
        <div className="border-b px-6 py-4" style={{ borderColor: 'var(--border-faint)' }}>
          <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Team Members ({mockMembers.length})</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b" style={{ borderColor: 'var(--border-faint)', backgroundColor: 'var(--bg-elevated)' }}>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>Member</th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>Role</th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>MFA</th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>Last Login</th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y" style={{ borderColor: 'var(--border-faint)' }}>
              {mockMembers.map((member) => {
                const roleColor = getRoleColor(member.role);
                const RoleIcon = getRoleIcon(member.role);
                return (
                  <tr
                    key={member.id}
                    onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                    onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
                  >
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="flex h-8 w-8 items-center justify-center rounded-full text-sm font-medium" style={{ backgroundColor: 'var(--accent-dim)', color: 'var(--accent)' }}>
                          {member.avatar}
                        </div>
                        <div>
                          <div className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{member.name}</div>
                          <div className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{member.email}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium" style={{ backgroundColor: roleColor.bg, color: roleColor.color }}>
                        <RoleIcon className="h-3 w-3" />
                        {member.role}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <CheckCircle2 className="h-4 w-4" style={{ color: 'var(--success)' }} />
                    </td>
                    <td className="px-6 py-4 text-sm" style={{ color: 'var(--text-tertiary)' }}>
                      {member.lastLogin}
                    </td>
                    <td className="px-6 py-4">
                      <Button variant="outline" size="sm">
                        <MoreHorizontal className="h-4 w-4" />
                      </Button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pending Invites */}
      <div className="rounded-lg border overflow-hidden" style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)' }}>
        <div className="border-b px-6 py-4" style={{ borderColor: 'var(--border-faint)' }}>
          <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Pending Invites ({mockInvites.length})</h3>
        </div>
        <div className="p-6">
          {mockInvites.length > 0 ? (
            <div className="space-y-3">
              {mockInvites.map((invite) => {
                const roleColor = getRoleColor(invite.role);
                return (
                  <div key={invite.id} className="flex items-center justify-between p-4 rounded-lg border" style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-elevated)' }}>
                    <div className="flex items-center gap-3">
                      <div className="flex h-8 w-8 items-center justify-center rounded-full text-sm font-medium" style={{ backgroundColor: 'var(--info-dim)', color: 'var(--info)' }}>
                        @
                      </div>
                      <div>
                        <div className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{invite.email}</div>
                        <div className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                          Invited {new Date(invite.sentAt).toLocaleDateString()}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium" style={{ backgroundColor: roleColor.bg, color: roleColor.color }}>
                        {invite.role}
                      </span>
                      <div className="flex gap-2">
                        <Button variant="outline" size="sm">Resend</Button>
                        <Button variant="outline" size="sm">Cancel</Button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="text-center py-8">
              <UserPlus className="h-8 w-8 mx-auto mb-3" style={{ color: 'var(--text-tertiary)' }} />
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>No pending invites</p>
            </div>
          )}
        </div>
      </div>
    </>
  );
}