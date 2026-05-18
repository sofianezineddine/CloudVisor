/**
 * Unit Tests for Keep API Client Module
 *
 * Tests URL construction, JWT attachment, X-Correlation-ID generation,
 * and 401 handling (session refresh + redirect to login).
 *
 * Validates: Requirements 12.1, 12.2, 12.3, 12.4
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import axios from 'axios';
import MockAdapter from 'axios-mock-adapter';

// We need to mock localStorage and crypto before importing the module
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
    get length() {
      return Object.keys(store).length;
    },
    key: vi.fn((index: number) => Object.keys(store)[index] ?? null),
  };
})();

Object.defineProperty(globalThis, 'localStorage', { value: localStorageMock });

// Mock crypto.randomUUID
const mockUUID = '550e8400-e29b-41d4-a716-446655440000';
Object.defineProperty(globalThis, 'crypto', {
  value: { randomUUID: vi.fn(() => mockUUID) },
});

// Mock window.location
const locationMock = { href: '' };
Object.defineProperty(globalThis, 'window', {
  value: { location: locationMock },
  writable: true,
});

// Mock fetch for the silent refresh calls
const mockFetch = vi.fn();
globalThis.fetch = mockFetch;

// Now import the module under test
import { keepApi } from './keep';

describe('Keep API Client', () => {
  let mock: MockAdapter;

  beforeEach(() => {
    mock = new MockAdapter(keepApi);
    localStorageMock.clear();
    locationMock.href = '';
    mockFetch.mockReset();
    vi.clearAllMocks();
  });

  afterEach(() => {
    mock.restore();
  });

  describe('Base URL configuration', () => {
    it('should use /v1/keep as the base URL prefix', () => {
      expect(keepApi.defaults.baseURL).toContain('/v1/keep');
    });

    it('should target the API gateway URL', () => {
      // Default is http://localhost:8005/v1/keep
      expect(keepApi.defaults.baseURL).toBe('http://localhost:8005/v1/keep');
    });

    it('should set Content-Type to application/json', () => {
      expect(keepApi.defaults.headers['Content-Type']).toBe('application/json');
    });

    it('should set timeout to 30 seconds', () => {
      expect(keepApi.defaults.timeout).toBe(30_000);
    });
  });

  describe('Request interceptor - JWT attachment', () => {
    it('should attach JWT in Authorization header when token exists', async () => {
      localStorageMock.setItem('access_token', 'test-jwt-token');
      mock.onGet('/alerts').reply(200, { data: [] });

      const response = await keepApi.get('/alerts');

      expect(mock.history.get[0].headers?.Authorization).toBe(
        'Bearer test-jwt-token',
      );
    });

    it('should not attach Authorization header when no token exists', async () => {
      mock.onGet('/alerts').reply(200, { data: [] });

      await keepApi.get('/alerts');

      // Authorization should not be set (or undefined)
      const authHeader = mock.history.get[0].headers?.Authorization;
      expect(authHeader).toBeUndefined();
    });
  });

  describe('Request interceptor - X-Correlation-ID', () => {
    it('should include X-Correlation-ID header on every request', async () => {
      mock.onGet('/alerts').reply(200, { data: [] });

      await keepApi.get('/alerts');

      expect(mock.history.get[0].headers?.['X-Correlation-ID']).toBe(mockUUID);
    });

    it('should generate a UUID for X-Correlation-ID', async () => {
      mock.onGet('/incidents').reply(200, { data: [] });

      await keepApi.get('/incidents');

      expect(crypto.randomUUID).toHaveBeenCalled();
      expect(mock.history.get[0].headers?.['X-Correlation-ID']).toBe(mockUUID);
    });
  });

  describe('Response interceptor - 401 handling', () => {
    it('should attempt silent token refresh on 401 response', async () => {
      localStorageMock.setItem('access_token', 'expired-token');
      localStorageMock.setItem('refresh_token', 'valid-refresh-token');

      // First request returns 401
      mock.onGet('/alerts').replyOnce(401);
      // After refresh, retry succeeds
      mock.onGet('/alerts').replyOnce(200, { data: [] });

      // Mock the refresh endpoint
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          access_token: 'new-access-token',
          refresh_token: 'new-refresh-token',
        }),
      });

      const response = await keepApi.get('/alerts');

      expect(response.status).toBe(200);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/auth/refresh'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ refresh_token: 'valid-refresh-token' }),
        }),
      );
    });

    it('should update stored tokens after successful refresh', async () => {
      localStorageMock.setItem('access_token', 'expired-token');
      localStorageMock.setItem('refresh_token', 'valid-refresh-token');

      mock.onGet('/alerts').replyOnce(401);
      mock.onGet('/alerts').replyOnce(200, { data: [] });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          access_token: 'new-access-token',
          refresh_token: 'new-refresh-token',
        }),
      });

      await keepApi.get('/alerts');

      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'access_token',
        'new-access-token',
      );
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'refresh_token',
        'new-refresh-token',
      );
    });

    it('should redirect to /login when refresh fails', async () => {
      localStorageMock.setItem('access_token', 'expired-token');
      localStorageMock.setItem('refresh_token', 'invalid-refresh-token');

      mock.onGet('/alerts').replyOnce(401);

      // Refresh fails
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: 'Invalid refresh token' }),
      });

      await keepApi.get('/alerts').catch(() => {});

      expect(locationMock.href).toBe('/login?error=session_expired');
    });

    it('should clear all tokens when refresh fails', async () => {
      localStorageMock.setItem('access_token', 'expired-token');
      localStorageMock.setItem('refresh_token', 'invalid-refresh-token');
      localStorageMock.setItem('cloudvisor-user', '{}');

      mock.onGet('/alerts').replyOnce(401);

      mockFetch.mockResolvedValueOnce({ ok: false });

      await keepApi.get('/alerts').catch(() => {});

      expect(localStorageMock.removeItem).toHaveBeenCalledWith('access_token');
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('refresh_token');
      expect(localStorageMock.removeItem).toHaveBeenCalledWith(
        'cloudvisor-user',
      );
    });

    it('should redirect to /login when no refresh token is available', async () => {
      localStorageMock.setItem('access_token', 'expired-token');
      // No refresh token set

      mock.onGet('/alerts').replyOnce(401);

      await keepApi.get('/alerts').catch(() => {});

      expect(locationMock.href).toBe('/login?error=session_expired');
    });

    it('should not retry more than once on 401', async () => {
      localStorageMock.setItem('access_token', 'expired-token');
      localStorageMock.setItem('refresh_token', 'valid-refresh-token');

      // Both requests return 401
      mock.onGet('/alerts').reply(401);

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          access_token: 'still-expired-token',
          refresh_token: 'new-refresh-token',
        }),
      });

      const error = await keepApi.get('/alerts').catch((e) => e);

      // The request should ultimately fail (rejected)
      expect(error).toBeDefined();
      expect(error.response?.status).toBe(401);
    });
  });

  describe('Non-401 errors', () => {
    it('should pass through non-401 errors without refresh attempt', async () => {
      mock.onGet('/alerts').reply(500, { detail: 'Internal server error' });

      await expect(keepApi.get('/alerts')).rejects.toThrow();
      expect(mockFetch).not.toHaveBeenCalled();
    });

    it('should pass through 403 errors without refresh attempt', async () => {
      mock.onGet('/alerts').reply(403, { detail: 'Forbidden' });

      await expect(keepApi.get('/alerts')).rejects.toThrow();
      expect(mockFetch).not.toHaveBeenCalled();
    });
  });
});
