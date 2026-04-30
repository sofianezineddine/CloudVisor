'use client';

import { AppLayout } from '@/components/layout';
import { ProtectedRoute } from '@/components/protected-route';
import { Code, AlertTriangle, Key, Shield, FileCode, Download } from 'lucide-react';
import { Button } from '@/components/ui/button';

const scanResults = [
  { repo: 'my-app', branch: 'main', status: 'Pass', findings: 0, duration: '1m 23s', time: '5m ago' },
  { repo: 'payments-service', branch: 'feature/x', status: 'Blocked', findings: 2, duration: '2m 11s', time: '12m ago' },
  { repo: 'infra-terraform', branch: 'main', status: 'Warn', findings: 4, duration: '0m 45s', time: '8m ago' },
];

const alerts = [
  { type: 'AWS Access Key', file: 'config.env', repo: 'my-app', commit: 'a1b2c3d' },
  { type: 'Private Key', file: 'id_rsa', repo: 'infra-terraform', commit: 'e4f5g6h' },
];

export default function CICDPage() {
  React.useEffect(() => {
    document.title = 'CI/CD Security - CloudVisor';
  }, []);

  return (
    <ProtectedRoute>
      <AppLayout breadcrumbs={[{ text: 'Home', href: '/console' }, { text: 'CI/CD Security' }]}>
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-h1" style={{ color: 'var(--text-primary)' }}>CI/CD Pipeline Security</h1>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Shift-left security for your development pipeline</p>
          </div>
          <Button variant="outline" className="gap-2">
            <Download className="h-4 w-4" />
            Install CLI
          </Button>
        </div>

        {/* Scan Type Breakdown */}
        <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-4">
          {[
            { label: 'SAST Findings', value: 84, icon: Code, color: 'var(--medium)', bg: 'var(--medium-dim)' },
            { label: 'Secrets Found', value: 12, icon: Key, color: 'var(--critical)', bg: 'var(--critical-dim)' },
            { label: 'SCA Vulns', value: 247, icon: Shield, color: 'var(--high)', bg: 'var(--high-dim)' },
            { label: 'IaC Issues', value: 156, icon: FileCode, color: 'var(--accent)', bg: 'var(--accent-dim)' },
          ].map((metric) => (
            <div key={metric.label} className="cv-container p-5">
              <div
                className="mb-3 flex h-8 w-8 items-center justify-center rounded-md"
                style={{ backgroundColor: metric.bg }}
              >
                <metric.icon className="h-4 w-4" style={{ color: metric.color }} />
              </div>
              <div className="mb-1 font-mono text-2xl font-bold" style={{ color: metric.color }}>{metric.value}</div>
              <div className="text-sm" style={{ color: 'var(--text-secondary)' }}>{metric.label}</div>
            </div>
          ))}
        </div>

        {/* Recent Pipeline Scans */}
        <div className="mb-8 cv-container overflow-hidden">
          <div className="border-b px-6 py-3" style={{ borderColor: 'var(--border-faint)' }}>
            <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Recent pipeline scans</h3>
          </div>
          <table className="w-full">
            <thead>
              <tr className="border-b" style={{ borderColor: 'var(--border-faint)', backgroundColor: 'var(--bg-elevated)' }}>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>Repository</th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>Branch</th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>Findings</th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>Duration</th>
              </tr>
            </thead>
            <tbody className="divide-y" style={{ borderColor: 'var(--border-faint)' }}>
              {scanResults.map((scan) => (
                <tr
                  key={scan.repo}
                  onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                  onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
                >
                  <td className="px-6 py-3 text-sm" style={{ color: 'var(--text-primary)' }}>{scan.repo}</td>
                  <td className="px-6 py-3 text-sm" style={{ color: 'var(--text-tertiary)' }}>{scan.branch}</td>
                  <td className="px-6 py-3">
                    <span
                      className="rounded-full px-2 py-0.5 text-xs font-semibold"
                      style={
                        scan.status === 'Pass'
                          ? { backgroundColor: 'var(--success-dim)', color: 'var(--success)' }
                          : scan.status === 'Blocked'
                          ? { backgroundColor: 'var(--critical-dim)', color: 'var(--critical)' }
                          : { backgroundColor: 'var(--warning-dim)', color: 'var(--warning)' }
                      }
                    >
                      {scan.status}
                    </span>
                  </td>
                  <td className="px-6 py-3 text-sm" style={{ color: 'var(--text-secondary)' }}>{scan.findings}</td>
                  <td className="px-6 py-3 text-sm" style={{ color: 'var(--text-tertiary)' }}>{scan.duration}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Secrets Exposure */}
        <div className="cv-container p-6" style={{ borderColor: 'var(--warning-border)' }}>
          <div className="mb-4 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4" style={{ color: 'var(--warning)' }} />
            <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Secrets exposure alerts</h3>
          </div>
          <div className="space-y-3">
            {alerts.map((alert, i) => (
              <div
                key={i}
                className="flex items-center justify-between rounded-md border p-3"
                style={{ borderColor: 'var(--border-faint)' }}
              >
                <div>
                  <div className="text-sm" style={{ color: 'var(--text-primary)' }}>
                    {alert.type} in <code className="font-mono" style={{ color: 'var(--accent)' }}>{alert.file}</code>
                  </div>
                  <div className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{alert.repo} · {alert.commit}</div>
                </div>
                <Button variant="ghost" size="sm" className="text-xs">Revoke</Button>
              </div>
            ))}
          </div>
        </div>
      </AppLayout>
    </ProtectedRoute>
  );
}
