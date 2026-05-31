// ─── CNAPP Service Registry ──────────────────────────────────────────────────
// Single source of truth for all services, their tabs, and sidebar structure.
// Used by: sidebar, routing, breadcrumbs, service switcher.

export interface ServiceTab {
  id: string;
  label: string;
  count?: number;
}

export interface ServiceSection {
  label: string | null;
  tabs: ServiceTab[];
}

export interface ServiceDefinition {
  id: string;
  label: string;
  path: string; // e.g. '/cspm'
  defaultTab: string; // e.g. 'overview'
  sections: ServiceSection[];
}

// ─── Service Definitions ─────────────────────────────────────────────────────

export const SERVICES: ServiceDefinition[] = [
  {
    id: 'cspm',
    label: 'CSPM',
    path: '/cspm',
    defaultTab: 'overview',
    sections: [
      { label: null, tabs: [{ id: 'overview', label: 'Overview' }] },
      { label: 'Findings & Response', tabs: [{ id: 'findings', label: 'Findings' }, { id: 'incidents', label: 'Incidents' }] },
      { label: 'Resource Inventory', tabs: [{ id: 'assets', label: 'Assets' }, { id: 'risk-map', label: 'Risk Explorer' }] },
      { label: 'Identity & Access', tabs: [{ id: 'iam-security', label: 'IAM Security' }] },
      { label: 'Threat Analysis', tabs: [{ id: 'attack-paths', label: 'Attack Paths' }, { id: 'drift-detection', label: 'Drift Detection' }] },
      { label: 'Shift Left', tabs: [{ id: 'iac-security', label: 'IaC Security' }] },
      { label: 'Governance & Reports', tabs: [{ id: 'compliance', label: 'Compliance' }, { id: 'policy-engine', label: 'Policy Engine' }, { id: 'policies', label: 'Policies' }, { id: 'reports', label: 'Reports' }] },
      { label: 'Operations', tabs: [{ id: 'scan-history', label: 'Scan History' }] },
    ],
  },
  {
    id: 'cwpp',
    label: 'CWPP',
    path: '/cwpp',
    defaultTab: 'overview',
    sections: [
      { label: null, tabs: [{ id: 'overview', label: 'Overview' }] },
      { label: 'Protection', tabs: [{ id: 'findings', label: 'Findings' }, { id: 'assets', label: 'Assets' }] },
      { label: 'Governance', tabs: [{ id: 'policies', label: 'Policies' }, { id: 'reports', label: 'Reports' }] },
    ],
  },
  {
    id: 'ciem',
    label: 'CIEM',
    path: '/ciem',
    defaultTab: 'overview',
    sections: [
      { label: null, tabs: [{ id: 'overview', label: 'Overview' }] },
      { label: 'Identity', tabs: [{ id: 'findings', label: 'Findings' }, { id: 'assets', label: 'Assets' }] },
      { label: 'Governance', tabs: [{ id: 'policies', label: 'Policies' }, { id: 'reports', label: 'Reports' }] },
    ],
  },
  {
    id: 'kspm',
    label: 'KSPM',
    path: '/kspm',
    defaultTab: 'overview',
    sections: [
      { label: null, tabs: [{ id: 'overview', label: 'Overview' }] },
      { label: 'Kubernetes', tabs: [{ id: 'findings', label: 'Findings' }, { id: 'assets', label: 'Assets' }] },
      { label: 'Governance', tabs: [{ id: 'policies', label: 'Policies' }, { id: 'reports', label: 'Reports' }] },
    ],
  },
  {
    id: 'dspm',
    label: 'DSPM',
    path: '/dspm',
    defaultTab: 'overview',
    sections: [
      { label: null, tabs: [{ id: 'overview', label: 'Overview' }] },
      { label: 'Data', tabs: [{ id: 'findings', label: 'Findings' }, { id: 'assets', label: 'Assets' }] },
      { label: 'Governance', tabs: [{ id: 'policies', label: 'Policies' }, { id: 'reports', label: 'Reports' }] },
    ],
  },
  {
    id: 'cicd',
    label: 'CI/CD Security',
    path: '/cicd',
    defaultTab: 'overview',
    sections: [
      { label: null, tabs: [{ id: 'overview', label: 'Overview' }] },
      { label: 'Pipeline', tabs: [{ id: 'findings', label: 'Findings' }, { id: 'assets', label: 'Assets' }] },
      { label: 'Governance', tabs: [{ id: 'policies', label: 'Policies' }, { id: 'reports', label: 'Reports' }] },
    ],
  },
  {
    id: 'cdr',
    label: 'CDR',
    path: '/cdr',
    defaultTab: 'overview',
    sections: [
      { label: null, tabs: [{ id: 'overview', label: 'Overview' }] },
      { label: 'Detection', tabs: [{ id: 'findings', label: 'Findings' }, { id: 'assets', label: 'Assets' }] },
      { label: 'Governance', tabs: [{ id: 'policies', label: 'Policies' }, { id: 'reports', label: 'Reports' }] },
    ],
  },
  {
    id: 'aiops',
    label: 'AIOps',
    path: '/aiops',
    defaultTab: 'alerts',
    sections: [
      { label: 'Alert Management', tabs: [
        { id: 'alerts', label: 'Alerts' },
        { id: 'incidents', label: 'Incidents' },
        { id: 'deduplication', label: 'Deduplication' },
      ]},
      { label: 'Intelligence', tabs: [
        { id: 'ai', label: 'AI Plugins' },
        { id: 'rules', label: 'Correlation Rules' },
      ]},
      { label: 'Enrichment', tabs: [
        { id: 'mapping', label: 'Mapping' },
        { id: 'extraction', label: 'Extraction' },
      ]},
      { label: 'Automation', tabs: [
        { id: 'workflows', label: 'Workflows' },
        { id: 'maintenance', label: 'Maintenance Windows' },
      ]},
      { label: 'Infrastructure', tabs: [
        { id: 'providers', label: 'Providers' },
        { id: 'topology', label: 'Topology' },
      ]},
      { label: 'Analytics', tabs: [
        { id: 'dashboard', label: 'Dashboard' },
      ]},
      { label: 'Settings', tabs: [
        { id: 'settings', label: 'Settings' },
      ]},
    ],
  },
  {
    id: 'copilot',
    label: 'CloudVisor Q',
    path: '/copilot',
    defaultTab: 'chat',
    sections: [
      { label: null, tabs: [{ id: 'chat', label: 'Chat' }] },
      { label: 'History', tabs: [{ id: 'conversations', label: 'Conversations' }, { id: 'saved', label: 'Saved Responses' }] },
    ],
  },
];

// ─── Lookup helpers ──────────────────────────────────────────────────────────

/** Get a service definition by its path prefix (e.g. '/cspm') */
export function getServiceByPath(pathname: string): ServiceDefinition | undefined {
  return SERVICES.find(s => pathname === s.path || pathname.startsWith(s.path + '/'));
}

/** Get a service definition by its id (e.g. 'cspm') */
export function getServiceById(id: string): ServiceDefinition | undefined {
  return SERVICES.find(s => s.id === id);
}

/** Get all tab IDs for a service (flat list) */
export function getServiceTabIds(serviceId: string): string[] {
  const service = getServiceById(serviceId);
  if (!service) return [];
  return service.sections.flatMap(s => s.tabs.map(t => t.id));
}

/** Get the active tab from a pathname like '/cspm/findings' → 'findings' */
export function getActiveTabFromPath(pathname: string): string | null {
  const service = getServiceByPath(pathname);
  if (!service) return null;
  const segment = pathname.replace(service.path, '').replace(/^\//, '');
  if (!segment) return service.defaultTab;
  return segment;
}
