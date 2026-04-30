// ─── Shared CloudVisor service catalogue ─────────────────────────────────────
// Used by: services page, mega-menu, pinned-favorites bar

export interface ServiceItem {
  name: string;
  href: string;
  desc: string;
}

export interface ServiceCategory {
  id: string;
  label: string;
  color: string;
  bg: string;
  iconText: string;
  services: ServiceItem[];
}

export const SERVICE_CATEGORIES: ServiceCategory[] = [
  {
    id: 'cloud-security',
    label: 'Cloud Security',
    color: '#d13212',
    bg: '#fdf3f1',
    iconText: 'CS',
    services: [
      { name: 'Findings',      href: '/findings',   desc: 'Security findings across your cloud environment' },
      { name: 'Incidents',     href: '/incidents',  desc: 'Security incident management and response' },
      { name: 'Assets',        href: '/assets',     desc: 'Cloud resource inventory and discovery' },
      { name: 'Compliance',    href: '/compliance', desc: 'Compliance posture across frameworks' },
      { name: 'Risk Explorer', href: '/risk-map',   desc: 'Attack path analysis and risk visualization' },
    ],
  },
  {
    id: 'posture',
    label: 'Posture Management',
    color: '#0073bb',
    bg: '#f0f8ff',
    iconText: 'PM',
    services: [
      { name: 'CSPM', href: '/cspm', desc: 'Cloud Security Posture Management' },
      { name: 'CWPP', href: '/cwpp', desc: 'Cloud Workload Protection Platform' },
      { name: 'KSPM', href: '/kspm', desc: 'Kubernetes Security Posture Management' },
    ],
  },
  {
    id: 'identity',
    label: 'Identity & Access',
    color: '#6b2fa0',
    bg: '#f8f0ff',
    iconText: 'IA',
    services: [
      { name: 'Identity (CIEM)', href: '/ciem', desc: 'Cloud Infrastructure Entitlement Management' },
    ],
  },
  {
    id: 'data',
    label: 'Data Security',
    color: '#1a6b3c',
    bg: '#f2f8f5',
    iconText: 'DS',
    services: [
      { name: 'Data (DSPM)', href: '/dspm', desc: 'Data Security Posture Management' },
    ],
  },
  {
    id: 'devsecops',
    label: 'DevSecOps',
    color: '#8d6605',
    bg: '#fefaec',
    iconText: 'DO',
    services: [
      { name: 'CI/CD Security', href: '/cicd', desc: 'Shift-left security for development pipelines' },
    ],
  },
  {
    id: 'detection',
    label: 'Detection & Response',
    color: '#d13212',
    bg: '#fdf3f1',
    iconText: 'DR',
    services: [
      { name: 'Detection (CDR)', href: '/cdr', desc: 'Cloud Detection and Response' },
    ],
  },
  {
    id: 'intelligence',
    label: 'Intelligence',
    color: '#0073bb',
    bg: '#f0f8ff',
    iconText: 'AI',
    services: [
      { name: 'AIOps',      href: '/aiops',   desc: 'ML-powered noise reduction and risk prioritization' },
      { name: 'AI Copilot', href: '/copilot', desc: 'Natural language security queries powered by LLMs' },
    ],
  },
  {
    id: 'admin',
    label: 'Administration',
    color: '#687078',
    bg: '#f8f8f8',
    iconText: 'AD',
    services: [
      { name: 'Cloud Accounts', href: '/settings',               desc: 'Connect and manage cloud environments' },
      { name: 'Notifications',  href: '/settings/notifications', desc: 'Configure alert channels' },
      { name: 'Team',           href: '/settings/team',          desc: 'Manage team members and permissions' },
      { name: 'API Keys',       href: '/settings/api-keys',      desc: 'Programmatic access management' },
      { name: 'Billing',        href: '/settings/billing',       desc: 'Plan and usage management' },
    ],
  },
];

// Flat list of all services for quick lookup
export const ALL_SERVICES: ServiceItem[] = SERVICE_CATEGORIES.flatMap(c => c.services);

// ─── Pinned favourites helpers ────────────────────────────────────────────────
const STORAGE_KEY = 'cloudvisor-pinned-services';

/** Default pinned hrefs shown before the user customises anything */
export const DEFAULT_PINS: string[] = ['/findings', '/assets', '/cspm', '/compliance'];

export function loadPins(): string[] {
  if (typeof window === 'undefined') return DEFAULT_PINS;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_PINS;
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : DEFAULT_PINS;
  } catch {
    return DEFAULT_PINS;
  }
}

export function savePins(pins: string[]): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(pins));
}

export function togglePin(href: string, current: string[]): string[] {
  if (current.includes(href)) {
    return current.filter(h => h !== href);
  }
  return [...current, href];
}
