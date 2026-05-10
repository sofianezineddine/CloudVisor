'use client';

import Link from 'next/link';
import {
  Shield, Monitor, GitBranch, Key, Box, Database, Activity, Sparkles, ArrowRight,
} from 'lucide-react';

const SERVICES = [
  {
    id: 'cspm',
    name: 'Cloud Security Posture',
    description: 'Continuously audit cloud configurations against 500+ built-in rules. Catch misconfigurations before they become breaches.',
    icon: Shield,
    color: '#0073bb',
  },
  {
    id: 'cwpp',
    name: 'Workload Protection',
    description: 'Agentless vulnerability scanning for VMs, containers, and serverless. Prioritized by exploit probability, not just CVSS.',
    icon: Monitor,
    color: '#1a6b3c',
  },
  {
    id: 'ciem',
    name: 'Identity & Entitlements',
    description: 'Map every identity to every permission. Detect over-privileged roles, privilege escalation paths, and unused access.',
    icon: Key,
    color: '#d45b07',
  },
  {
    id: 'cdr',
    name: 'Detection & Response',
    description: 'Real-time threat detection with behavioral baselines. MITRE ATT&CK-mapped detections with automated playbooks.',
    icon: Activity,
    color: '#d13212',
  },
  {
    id: 'kspm',
    name: 'Kubernetes Security',
    description: 'Full CIS Kubernetes Benchmark coverage. Audit pods, RBAC, network policies and admission control.',
    icon: Box,
    color: '#8d6605',
  },
  {
    id: 'dspm',
    name: 'Data Security',
    description: 'Discover where sensitive data lives. Classify for PII, PCI, PHI. Map who can access what — automatically.',
    icon: Database,
    color: '#7c3aed',
  },
  {
    id: 'cicd',
    name: 'CI/CD Pipeline Security',
    description: 'Shift left with SAST, secrets detection, SCA, and IaC scanning. Free CLI works offline — no account required.',
    icon: GitBranch,
    color: '#FF9900',
  },
  {
    id: 'copilot',
    name: 'Security Copilot',
    description: 'Ask natural language questions about your security posture. Get plain-English explanations and auto-generated fixes.',
    icon: Sparkles,
    color: '#0073bb',
  },
];

export default function ServicesGrid() {
  return (
    <section
      id="services"
      style={{
        backgroundColor: 'var(--bg-base)',
        padding: '80px 24px',
        display: 'flex',
        justifyContent: 'center',
      }}
    >
      <div style={{ width: '100%', maxWidth: '1280px' }}>
        {/* Section header */}
        <div style={{ textAlign: 'center', marginBottom: '56px' }}>
          <h2
            style={{
              fontSize: '28px',
              fontWeight: 800,
              color: 'var(--text-primary)',
              margin: '0 0 12px 0',
              letterSpacing: '-0.3px',
            }}
          >
            One Platform, Complete Cloud Security
          </h2>
          <p
            style={{
              fontSize: '15px',
              color: 'var(--text-secondary)',
              margin: 0,
              maxWidth: '560px',
              marginLeft: 'auto',
              marginRight: 'auto',
              lineHeight: 1.6,
            }}
          >
            CloudVisor unifies eight critical security capabilities into a single platform,
            so your team works in one place — not eight.
          </p>
        </div>

        {/* Cards grid */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: '20px',
          }}
        >
          {SERVICES.map((service) => {
            const Icon = service.icon;
            return (
              <div
                key={service.id}
                style={{
                  backgroundColor: 'var(--bg-surface)',
                  border: '1px solid var(--border-default)',
                  borderRadius: 'var(--radius-container)',
                  padding: '28px 24px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '16px',
                  transition: 'border-color 0.15s, box-shadow 0.15s',
                  cursor: 'default',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = service.color;
                  e.currentTarget.style.boxShadow = '0 4px 16px rgba(0,28,36,0.10)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = 'var(--border-default)';
                  e.currentTarget.style.boxShadow = 'none';
                }}
              >
                {/* Icon */}
                <div
                  style={{
                    width: '44px',
                    height: '44px',
                    borderRadius: '10px',
                    backgroundColor: `${service.color}14`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                  }}
                >
                  <Icon size={22} style={{ color: service.color }} strokeWidth={1.5} />
                </div>

                {/* Text */}
                <div>
                  <h3
                    style={{
                      fontSize: '16px',
                      fontWeight: 700,
                      color: 'var(--text-primary)',
                      margin: '0 0 8px 0',
                    }}
                  >
                    {service.name}
                  </h3>
                  <p
                    style={{
                      fontSize: '13px',
                      color: 'var(--text-secondary)',
                      margin: 0,
                      lineHeight: 1.55,
                    }}
                  >
                    {service.description}
                  </p>
                </div>

                {/* Link */}
                <Link
                  href="/signup"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                    fontSize: '13px',
                    fontWeight: 600,
                    color: service.color,
                    textDecoration: 'none',
                    marginTop: 'auto',
                  }}
                >
                  Learn more
                  <ArrowRight size={13} />
                </Link>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
