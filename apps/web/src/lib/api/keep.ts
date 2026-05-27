/**
 * Keep API Client
 *
 * Axios instance configured for the Keep AIOps service at /v1/keep prefix.
 * Uses HttpOnly cookies for authentication (set by auth service).
 *
 * Features:
 * - Base URL: /v1/keep (proxied through API gateway at :8005)
 * - Authentication: HttpOnly cookies (sent automatically via withCredentials)
 * - CSRF: X-CSRF-Token header on state-changing requests
 * - Correlation: X-Correlation-ID header (UUID v4) generated per request
 */

import axios, { type InternalAxiosRequestConfig } from 'axios';
import { getCsrfToken } from '@/lib/csrf';

// ─── Configuration ────────────────────────────────────────────────────────────
// All API calls go through nginx same-origin proxy (/v1/keep -> api-gateway)
// This ensures HttpOnly cookies are sent automatically (same port 80 origin)

// ─── Axios instance ───────────────────────────────────────────────────────────

export const keepApi = axios.create({
  baseURL: '/v1/keep',
  headers: { 'Content-Type': 'application/json' },
  timeout: 30_000,
  withCredentials: true, // Send HttpOnly cookies through nginx proxy
});

// ─── Request interceptor: attach CSRF token + X-Correlation-ID ────────────────

keepApi.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (typeof window !== 'undefined') {
    // Generate a unique correlation ID per request for distributed tracing
    config.headers['X-Correlation-ID'] = crypto.randomUUID();

    // Auth via HttpOnly cookies (sent automatically by withCredentials: true)
    // No localStorage token storage — tokens are never accessible to JS (C-01 fix)

    // Attach CSRF token for state-changing requests
    const method = (config.method || '').toLowerCase();
    if (['post', 'put', 'patch', 'delete'].includes(method)) {
      const csrf = getCsrfToken();
      if (csrf) {
        config.headers['X-CSRF-Token'] = csrf;
      }
    }
  }
  return config;
});

// ─── Response interceptor: handle errors gracefully ───────────────────────────

keepApi.interceptors.response.use(
  (response) => response,
  async (error) => {
    // On 401, the session cookie has expired.
    // Don't clear anything — let the AuthProvider detect the missing cv_session cookie
    // and handle the redirect to login naturally.
    return Promise.reject(error);
  },
);
