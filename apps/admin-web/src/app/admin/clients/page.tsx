'use client';

import React from 'react';
import { AdminLayout } from '@/components/admin-layout';
import { AdminProtectedRoute } from '@/components/admin-protected-route';
import { Users, Search, Plus } from 'lucide-react';

export default function AdminClientsPage() {
  return (
    <AdminProtectedRoute>
      <AdminLayout>
        <div className="mb-5 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>Client Management</h1>
            <p className="text-sm mt-0.5" style={{ color: 'var(--text-secondary)' }}>Manage all registered organizations</p>
          </div>
          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2" style={{ color: 'var(--text-tertiary)' }} />
              <input
                type="text"
                placeholder="Search clients..."
                className="pl-7 pr-3 text-sm focus:outline-none"
                style={{ height: '32px', border: '1px solid var(--border-default)', borderRadius: '2px', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)', width: '200px' }}
              />
            </div>
            <button className="btn-primary text-xs gap-1.5">
              <Plus className="h-3.5 w-3.5" />
              Add Client
            </button>
          </div>
        </div>

        <div className="admin-card p-12 text-center">
          <Users className="mx-auto mb-3 h-10 w-10" style={{ color: 'var(--text-tertiary)' }} />
          <p className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>No clients yet</p>
          <p className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>Client management table coming soon</p>
        </div>
      </AdminLayout>
    </AdminProtectedRoute>
  );
}
