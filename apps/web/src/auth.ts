/**
 * Auth shim for Keep UI integration.
 * Keep UI imports { auth } from "@/auth" for server-side session access.
 * In CloudVisor, we provide a compatible interface that returns the
 * CloudVisor user session.
 */

export async function auth() {
  // In CloudVisor, server-side auth is handled by the API gateway.
  // Return a minimal session object for Keep UI compatibility.
  return {
    user: {
      id: 'cloudvisor-user',
      name: 'CloudVisor User',
      email: 'user@cloudvisor.io',
      accessToken: '',
      tenantId: 'default',
      role: 'admin',
    },
    accessToken: '',
    tenantId: 'default',
    userRole: 'admin',
  };
}

export async function signIn(...args: any[]) {
  return;
}

export async function signOut(...args: any[]) {
  return;
}
