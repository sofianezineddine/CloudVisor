/**
 * Property-Based Test: API Client Request Construction (Property 8)
 *
 * Validates: Requirements 12.1, 12.2, 12.3
 *
 * For any API call made through the Keep API client module:
 * - The request SHALL target the `/v1/keep` URL prefix
 * - The request SHALL include the authenticated user's JWT in the Authorization: Bearer header
 * - The request SHALL include a non-empty X-Correlation-ID header (UUID format)
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import * as fc from 'fast-check';
import axios from 'axios';
import MockAdapter from 'axios-mock-adapter';
import { keepApi } from './keep';

// UUID v4 regex pattern
const UUID_V4_REGEX =
  /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

describe('Property 8: API Client Request Construction', () => {
  let mock: MockAdapter;

  beforeEach(() => {
    mock = new MockAdapter(keepApi);
    // Mock all requests to return 200
    mock.onAny().reply(200, {});

    // Mock crypto.randomUUID for consistent behavior in jsdom
    vi.stubGlobal('crypto', {
      randomUUID: () => {
        // Generate a valid UUID v4
        const hex = [...Array(32)]
          .map(() => Math.floor(Math.random() * 16).toString(16))
          .join('');
        return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-4${hex.slice(13, 16)}-${(8 + Math.floor(Math.random() * 4)).toString(16)}${hex.slice(17, 20)}-${hex.slice(20, 32)}`;
      },
    });
  });

  afterEach(() => {
    mock.restore();
    vi.unstubAllGlobals();
    localStorage.clear();
  });

  /**
   * Arbitrary for generating random API path segments.
   * Generates paths like "alerts", "incidents/123", "workflows/abc/executions"
   */
  const arbPathSegment = fc
    .array(
      fc.constantFrom(
        ...'abcdefghijklmnopqrstuvwxyz0123456789-_'.split(''),
      ),
      { minLength: 1, maxLength: 20 },
    )
    .map((chars) => chars.join(''));

  const arbApiPath = fc
    .array(arbPathSegment, { minLength: 1, maxLength: 4 })
    .map((segments) => '/' + segments.join('/'));

  /**
   * Arbitrary for generating JWT-like tokens (base64-encoded segments).
   */
  const arbJwtToken = fc
    .tuple(
      fc.base64String({ minLength: 10, maxLength: 50 }),
      fc.base64String({ minLength: 10, maxLength: 100 }),
      fc.base64String({ minLength: 10, maxLength: 50 }),
    )
    .map(([header, payload, sig]) => `${header}.${payload}.${sig}`);

  /**
   * Arbitrary for HTTP methods supported by the API client.
   */
  const arbMethod = fc.constantFrom(
    'get',
    'post',
    'put',
    'patch',
    'delete',
  ) as fc.Arbitrary<'get' | 'post' | 'put' | 'patch' | 'delete'>;

  it('should target /v1/keep URL prefix for all requests', async () => {
    await fc.assert(
      fc.asyncProperty(arbApiPath, arbMethod, async (path, method) => {
        mock.resetHistory();

        // Set a token so requests go through
        localStorage.setItem('access_token', 'test-token');

        try {
          if (method === 'get' || method === 'delete') {
            await keepApi[method](path);
          } else {
            await keepApi[method](path, { data: 'test' });
          }
        } catch {
          // Ignore errors — we only care about request construction
        }

        // Verify the request was made to a URL containing /v1/keep
        expect(mock.history[method].length).toBeGreaterThan(0);
        const request = mock.history[method][0];
        expect(request.baseURL).toContain('/v1/keep');
      }),
      { numRuns: 100 },
    );
  });

  it('should include Bearer JWT in Authorization header when token exists', async () => {
    await fc.assert(
      fc.asyncProperty(
        arbApiPath,
        arbMethod,
        arbJwtToken,
        async (path, method, token) => {
          mock.resetHistory();

          // Set the JWT token in localStorage
          localStorage.setItem('access_token', token);

          try {
            if (method === 'get' || method === 'delete') {
              await keepApi[method](path);
            } else {
              await keepApi[method](path, { data: 'test' });
            }
          } catch {
            // Ignore errors — we only care about request construction
          }

          // Verify Authorization header contains Bearer {token}
          expect(mock.history[method].length).toBeGreaterThan(0);
          const request = mock.history[method][0];
          expect(request.headers?.Authorization).toBe(`Bearer ${token}`);
        },
      ),
      { numRuns: 100 },
    );
  });

  it('should include non-empty X-Correlation-ID header in UUID format for every request', async () => {
    await fc.assert(
      fc.asyncProperty(arbApiPath, arbMethod, async (path, method) => {
        mock.resetHistory();

        localStorage.setItem('access_token', 'test-token');

        try {
          if (method === 'get' || method === 'delete') {
            await keepApi[method](path);
          } else {
            await keepApi[method](path, { data: 'test' });
          }
        } catch {
          // Ignore errors — we only care about request construction
        }

        // Verify X-Correlation-ID is present, non-empty, and in UUID format
        expect(mock.history[method].length).toBeGreaterThan(0);
        const request = mock.history[method][0];
        const correlationId = request.headers?.['X-Correlation-ID'];
        expect(correlationId).toBeDefined();
        expect(correlationId).not.toBe('');
        expect(correlationId).toMatch(UUID_V4_REGEX);
      }),
      { numRuns: 100 },
    );
  });

  it('should generate unique X-Correlation-ID for each request', async () => {
    localStorage.setItem('access_token', 'test-token');

    await fc.assert(
      fc.asyncProperty(
        arbApiPath,
        arbApiPath,
        async (path1, path2) => {
          mock.resetHistory();

          try {
            await keepApi.get(path1);
            await keepApi.get(path2);
          } catch {
            // Ignore errors
          }

          // Verify two requests have different correlation IDs
          if (mock.history.get.length >= 2) {
            const id1 = mock.history.get[0].headers?.['X-Correlation-ID'];
            const id2 = mock.history.get[1].headers?.['X-Correlation-ID'];
            expect(id1).not.toBe(id2);
          }
        },
      ),
      { numRuns: 100 },
    );
  });
});
