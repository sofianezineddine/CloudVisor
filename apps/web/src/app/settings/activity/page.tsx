'use client';

import * as React from 'react';
import { CheckCircle2, AlertCircle } from 'lucide-react';

const mockActivity = [
  { id: 1, action: 'Password changed', time: '2 hours ago', ip: '192.168.1.45', status: 'success' },
  { id: 2, action: 'New API key generated', time: '1 day ago', ip: '192.168.1.45', status: 'success' },
  { id: 3, action: 'Failed login attempt', time: '3 days ago', ip: '203.0.113.12', status: 'failed' },
  { id: 4, action: 'Organization plan upgraded', time: '1 week ago', ip: '192.168.1.45', status: 'success' },
  { id: 5, action: 'MFA enabled', time: '2 weeks ago', ip: '192.168.1.45', status: 'success' },
];

export default function ActivityPage() {
  React.useEffect(() => {
    document.title = 'Activity Log - Settings - CloudVisor';
  }, []);

  return (
    <>
      {/* Page Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>Activity Log</h1>
        <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
          Track logins, security changes, and account actions
        </p>
      </div>

      {/* Activity List */}
      <div className="cv-container overflow-hidden">
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
    </>
  );
}
