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

const API_GATEWAY_URL =
  process.env.NEXT_PUBLIC_API_GATEWAY_URL || 'http://localhost:8005';

// ─── Axios instance ───────────────────────────────────────────────────────────

export const keepApi = axios.create({
  baseURL: `${API_GATEWAY_URL}/v1/keep`,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30_000,
  withCredentials: true, // Send HttpOnly cookies automatically
});

// ─── Request interceptor: attach CSRF token + X-Correlation-ID ────────────────

keepApi.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (typeof window !== 'undefined') {
    // Generate a unique correlation ID per request for distributed tracing
    config.headers['X-Correlation-ID'] = crypto.randomUUID();

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
