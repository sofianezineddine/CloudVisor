'use client';

// Global recently visited tracker that works independently of React hooks

export interface RecentlyVisitedItem {
  href: string;
  label: string;
  color?: string;
  visitedAt: number;
}

const STORAGE_KEY = 'cloudvisor_recently_visited';
const MAX_ITEMS = 8;

// Service definitions
const SERVICE_DEFINITIONS: Record<string, Omit<RecentlyVisitedItem, 'href' | 'visitedAt'>> = {
  '/findings': { label: 'Findings', color: 'var(--critical)' },
  '/assets': { label: 'Assets', color: 'var(--success)' },
  '/cspm': { label: 'CSPM', color: 'var(--accent)' },
  '/cwpp': { label: 'CWPP', color: 'var(--high)' },
  '/ciem': { label: 'Identity (CIEM)', color: '#6b2fa0' },
  '/kspm': { label: 'Kubernetes (KSPM)', color: '#326ce5' },
  '/dspm': { label: 'Data (DSPM)', color: 'var(--success)' },
  '/cdr': { label: 'Detection (CDR)', color: 'var(--critical)' },
  '/compliance': { label: 'Compliance', color: 'var(--info)' },
  '/aiops/incidents': { label: 'Incidents', color: 'var(--warning)' },
  '/settings': { label: 'Settings', color: 'var(--text-secondary)' },
  '/profile': { label: 'Profile', color: 'var(--text-secondary)' },
  '/risk-map': { label: 'Risk Map', color: 'var(--critical)' },
  '/cicd': { label: 'CI/CD Security', color: 'var(--warning)' },
  '/aiops': { label: 'AIOps', color: 'var(--accent)' },
};

// Global state
let currentItems: RecentlyVisitedItem[] = [];
let listeners: Array<(items: RecentlyVisitedItem[]) => void> = [];

// Load from localStorage with better error handling
function loadFromStorage(): RecentlyVisitedItem[] {
  if (typeof window === 'undefined') return [];
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return [];
    
    const parsed = JSON.parse(stored);
    // Validate the structure
    if (!Array.isArray(parsed)) return [];
    
    return parsed.filter(item => 
      item && 
      typeof item.href === 'string' && 
      typeof item.label === 'string' && 
      typeof item.visitedAt === 'number'
    );
  } catch (error) {
    console.warn('Failed to load recently visited items from localStorage:', error);
    return [];
  }
}

// Save to localStorage with better error handling
function saveToStorage(items: RecentlyVisitedItem[]): void {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  } catch (error) {
    console.warn('Failed to save recently visited items to localStorage:', error);
  }
}

// Notify all listeners
function notifyListeners(): void {
  listeners.forEach(listener => listener([...currentItems]));
}

// Initialize
function initialize(): void {
  if (typeof window === 'undefined') return;
  currentItems = loadFromStorage();
}

// Add a visit
export function trackVisit(pathname: string): void {
  if (typeof window === 'undefined') return;
  
  // Find matching service definition
  let serviceDefinition: Omit<RecentlyVisitedItem, 'href' | 'visitedAt'> | null = null;
  let baseRoute = pathname;
  
  // Try exact match first
  if (SERVICE_DEFINITIONS[pathname]) {
    serviceDefinition = SERVICE_DEFINITIONS[pathname];
  } else {
    // Try prefix match
    const matchingRoute = Object.keys(SERVICE_DEFINITIONS).find(route => 
      pathname.startsWith(route + '/') || pathname === route
    );
    if (matchingRoute) {
      serviceDefinition = SERVICE_DEFINITIONS[matchingRoute];
      baseRoute = matchingRoute;
    }
  }
  
  if (!serviceDefinition) {
    return;
  }
  
  const newItem: RecentlyVisitedItem = {
    href: baseRoute,
    ...serviceDefinition,
    visitedAt: Date.now(),
  };
  
  // Remove existing entry for this route
  currentItems = currentItems.filter(item => item.href !== baseRoute);
  
  // Add new entry at the beginning
  currentItems = [newItem, ...currentItems].slice(0, MAX_ITEMS);
  
  // Save and notify
  saveToStorage(currentItems);
  notifyListeners();
}

// Get current items
export function getRecentlyVisited(): RecentlyVisitedItem[] {
  return [...currentItems];
}

// Clear all items
export function clearRecentlyVisited(): void {
  currentItems = [];
  saveToStorage(currentItems);
  notifyListeners();
}

// Subscribe to changes
export function subscribeToChanges(listener: (items: RecentlyVisitedItem[]) => void): () => void {
  listeners.push(listener);
  
  // Ensure we have loaded from storage
  if (currentItems.length === 0 && typeof window !== 'undefined') {
    currentItems = loadFromStorage();
  }
  
  // Immediately call with current items
  listener([...currentItems]);
  
  // Return unsubscribe function
  return () => {
    listeners = listeners.filter(l => l !== listener);
  };
}

// Auto-track page changes
function setupAutoTracking(): void {
  if (typeof window === 'undefined') return;
  
  // Track initial page
  trackVisit(window.location.pathname);
  
  // Track navigation events
  const originalPushState = window.history.pushState;
  const originalReplaceState = window.history.replaceState;
  
  window.history.pushState = function(...args) {
    originalPushState.apply(window.history, args);
    setTimeout(() => {
      trackVisit(window.location.pathname);
    }, 0);
  };
  
  window.history.replaceState = function(...args) {
    originalReplaceState.apply(window.history, args);
    setTimeout(() => {
      trackVisit(window.location.pathname);
    }, 0);
  };
  
  window.addEventListener('popstate', () => {
    trackVisit(window.location.pathname);
  });
  
  // Also track on focus (when user returns to tab)
  window.addEventListener('focus', () => {
    trackVisit(window.location.pathname);
  });
}

// Initialize when this module loads
if (typeof window !== 'undefined') {
  // Load initial data
  initialize();
  
  // Setup auto-tracking
  setupAutoTracking();
  
  // Periodic backup to ensure data persistence
  setInterval(() => {
    if (currentItems.length > 0) {
      saveToStorage(currentItems);
    }
  }, 30000); // Save every 30 seconds if there are items
  
  // Save on page unload
  window.addEventListener('beforeunload', () => {
    saveToStorage(currentItems);
  });
}