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
    id: 'posture',
    label: 'Security & Posture',
    color: '#0073bb',
    bg: '#f0f8ff',
    iconText: 'SP',
    services: [
      { name: 'CSPM', href: '/cspm', desc: 'Unified security hub: Findings, Assets, Compliance, and Risk' },
      { name: 'CWPP', href: '/cwpp', desc: 'Workload and runtime protection for VMs and containers' },
      { name: 'KSPM', href: '/kspm', desc: 'Kubernetes and container security posture' },
    ],
  },
  {
    id: 'identity',
    label: 'Identity & Access',
    color: '#6b2fa0',
    bg: '#f8f0ff',
    iconText: 'IA',
    services: [
      { name: 'Identity (CIEM)', href: '/ciem', desc: 'Identity entitlements and access analysis' },
    ],
  },
  {
    id: 'data',
    label: 'Data Security',
    color: '#1a6b3c',
    bg: '#f2f8f5',
    iconText: 'DS',
    services: [
      { name: 'Data (DSPM)', href: '/dspm', desc: 'Data security posture and discovery' },
    ],
  },
  {
    id: 'devsecops',
    label: 'DevSecOps',
    color: '#8d6605',
    bg: '#fefaec',
    iconText: 'DO',
    services: [
      { name: 'CI/CD Security', href: '/cicd', desc: 'Pipeline security and shift-left' },
    ],
  },
  {
    id: 'detection',
    label: 'Detection & Response',
    color: '#d13212',
    bg: '#fdf3f1',
    iconText: 'DR',
    services: [
      { name: 'Detection (CDR)', href: '/cdr', desc: 'Cloud threat detection and response' },
    ],
  },
  {
    id: 'intelligence',
    label: 'Intelligence',
    color: '#0073bb',
    bg: '#f0f8ff',
    iconText: 'AI',
    services: [
      { name: 'AIOps',      href: '/aiops',   desc: 'ML-powered noise reduction' },
      { name: 'AI Copilot', href: '/copilot', desc: 'GenAI security assistant' },
    ],
  },
  {
    id: 'admin',
    label: 'Administration',
    color: '#687078',
    bg: '#f8f8f8',
    iconText: 'AD',
    services: [
      { name: 'Cloud Accounts', href: '/settings',               desc: 'Manage cloud environments' },
      { name: 'Notifications',  href: '/settings/notifications', desc: 'Configure alert channels' },
      { name: 'Team',           href: '/settings/team',          desc: 'Team members and RBAC' },
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
    // Validate the structure
    if (!Array.isArray(parsed)) return DEFAULT_PINS;
    
    // Validate that all items are strings and exist in ALL_SERVICES
    const validPins = parsed.filter(pin => 
      typeof pin === 'string' && 
      ALL_SERVICES.some(service => service.href === pin)
    );
    
    return validPins.length > 0 ? validPins : DEFAULT_PINS;
  } catch (error) {
    console.warn('Failed to load pinned services from localStorage:', error);
    return DEFAULT_PINS;
  }
}

export function savePins(pins: string[]): void {
  if (typeof window === 'undefined') return;
  try {
    // Validate pins before saving
    const validPins = pins.filter(pin => 
      typeof pin === 'string' && 
      ALL_SERVICES.some(service => service.href === pin)
    );
    localStorage.setItem(STORAGE_KEY, JSON.stringify(validPins));
  } catch (error) {
    console.warn('Failed to save pinned services to localStorage:', error);
  }
}

export function togglePin(href: string, current: string[]): string[] {
  if (current.includes(href)) {
    return current.filter(h => h !== href);
  }
  return [...current, href];
}

// Periodic backup to ensure persistence
if (typeof window !== 'undefined') {
  // Save pins on page unload to prevent data loss
  window.addEventListener('beforeunload', () => {
    const currentPins = loadPins();
    if (currentPins.length > 0) {
      savePins(currentPins);
    }
  });
  
  // Periodic backup every 30 seconds
  setInterval(() => {
    const currentPins = loadPins();
    if (currentPins.length > 0 && JSON.stringify(currentPins) !== JSON.stringify(DEFAULT_PINS)) {
      savePins(currentPins);
    }
  }, 30000);
}
