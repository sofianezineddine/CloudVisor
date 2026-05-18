/**
 * Keep API Client
 *
 * Axios instance configured for the Keep AIOps service at /v1/keep prefix.
 * All AIOps page components use this client to communicate with the Keep backend
 * through the CloudVisor API gateway.
 *
 * Features:
 * - Base URL: /v1/keep (proxied through API gateway at :8005)
 * - Authentication: Bearer JWT auto-attached from localStorage
 * - Correlation: X-Correlation-ID header (UUID v4) generated per request
 * - Error handling: 401 triggers silent token refresh; redirects to /login on failure
 *
 * Requirements: 12.1, 12.2, 12.3, 12.4, 12.5
 */

import axios, {
  type AxiosError,
  type InternalAxiosRequestConfig,
} from 'axios';

// ─── Configuration ────────────────────────────────────────────────────────────

const API_GATEWAY_URL =
  process.env.NEXT_PUBLIC_API_GATEWAY_URL || 'http://localhost:8005';

const AUTH_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8002';

// ─── Token helpers ────────────────────────────────────────────────────────────

function getAccessToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('access_token');
}

function getRefreshToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('refresh_token');
}

function setTokens(accessToken: string, refreshToken: string): void {
  if (!accessToken || !refreshToken) return;
  localStorage.setItem('access_token', accessToken);
  localStorage.setItem('refresh_token', refreshToken);
}

function clearSession(): void {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('cloudvisor-user');
}

// ─── Silent refresh logic ─────────────────────────────────────────────────────

/** Track whether a refresh is already in-flight to avoid concurrent refreshes. */
let refreshPromise: Promise<string | null> | null = null;

/**
 * Attempt a silent token refresh using the stored refresh token.
 * Returns the new access token on success, or null on failure.
 * Deduplicates concurrent refresh attempts.
 */
async function silentRefresh(): Promise<string | null> {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    const refreshToken = getRefreshToken();
    if (!refreshToken) return null;

    try {
      const res = await fetch(`${AUTH_BASE_URL}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!res.ok) return null;

      const data = await res.json();
      if (data.access_token && data.refresh_token) {
        setTokens(data.access_token, data.refresh_token);
        return data.access_token as string;
      }
      return null;
    } catch {
      return null;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

/** Clear tokens and redirect to login when session is unrecoverable. */
function forceLogout(): void {
  clearSession();
  if (typeof window !== 'undefined') {
    window.location.href = '/login?error=session_expired';
  }
}

// ─── Axios instance ───────────────────────────────────────────────────────────

export const keepApi = axios.create({
  baseURL: `${API_GATEWAY_URL}/v1/keep`,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30_000,
});

// ─── Request interceptor: attach JWT + X-Correlation-ID ───────────────────────

keepApi.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (typeof window !== 'undefined') {
    // Attach JWT Bearer token
    const token = getAccessToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    // Generate a unique correlation ID per request for distributed tracing
    config.headers['X-Correlation-ID'] = crypto.randomUUID();
  }
  return config;
});

// ─── Response interceptor: 401 → refresh → retry or redirect ─────────────────

keepApi.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    // Only handle 401 responses, and only retry once
    if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
      originalRequest._retry = true;

      // Attempt silent token refresh
      const newToken = await silentRefresh();

      if (newToken) {
        // Retry the original request with the new token
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return keepApi(originalRequest);
      }

      // Refresh failed — session is dead, force logout
      forceLogout();
    }

    return Promise.reject(error);
  },
);
