"use client";

/**
 * CloudVisor shim for Keep's useHydratedSession hook.
 * Returns a mock session using CloudVisor's auth token from localStorage.
 * This replaces Keep's NextAuth-based session management.
 */
export function useHydratedSession() {
  const getToken = () => {
    if (typeof window === 'undefined') return '';
    return localStorage.getItem('access_token') || '';
  };

  const getUser = () => {
    if (typeof window === 'undefined') return null;
    try {
      const stored = localStorage.getItem('cloudvisor-user');
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  };

  const user = getUser();
  const token = getToken();

  // Return a session-like object compatible with Keep UI expectations
  const session = token ? {
    user: {
      id: user?.id || 'cloudvisor-user',
      name: user?.name || 'CloudVisor User',
      email: user?.email || 'user@cloudvisor.io',
      image: user?.image || null,
      accessToken: token,
      tenantId: user?.organization_id || 'default',
      role: user?.role || 'admin',
    },
    accessToken: token,
    tenantId: user?.organization_id || 'default',
    userRole: user?.role || 'admin',
  } : null;

  return {
    data: session,
    status: token ? 'authenticated' as const : 'unauthenticated' as const,
    update: async () => session,
  };
}
