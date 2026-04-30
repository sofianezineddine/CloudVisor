// Use the Next.js proxy to avoid CORS — requests go through /api/proxy/* → backend
// Falls back to direct URL if NEXT_PUBLIC_ADMIN_API_BASE_URL is set explicitly
const USE_PROXY = typeof window !== 'undefined';
const DIRECT_URL = process.env.NEXT_PUBLIC_ADMIN_API_BASE_URL || 'http://localhost:8002';
const ADMIN_API_BASE = USE_PROXY ? '/api/proxy' : DIRECT_URL;

export const adminAuthAPI = {
  login: async (data: { email: string; password: string }) => {
    const response = await fetch(`${ADMIN_API_BASE}/admin/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'Login failed');
    }

    return response.json();
  },

  refreshToken: async (refreshToken: string) => {
    const response = await fetch(`${ADMIN_API_BASE}/admin/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'Token refresh failed');
    }

    return response.json();
  },

  logout: async () => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('admin_access_token') : null;
    const response = await fetch(`${ADMIN_API_BASE}/admin/auth/logout`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token && { Authorization: `Bearer ${token}` }),
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'Logout failed');
    }

    return response.json();
  },

  getCurrentUser: async (token: string) => {
    const response = await fetch(`${ADMIN_API_BASE}/admin/auth/me`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'Failed to fetch admin profile');
    }

    return response.json();
  },
};
