/**
 * Property-Based Test: Frontend Auth Guard (Property 4)
 *
 * Validates: Requirements 4.2, 4.5
 *
 * For any route matching `/aiops/*`, an unauthenticated user (no valid JWT)
 * SHALL be redirected to the CloudVisor login page and SHALL not see any
 * AIOps page content.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import * as fc from 'fast-check';
import { render, screen, waitFor } from '@testing-library/react';
import React from 'react';

// Mock next/navigation
const mockPush = vi.fn();
const mockPathname = vi.fn<() => string>().mockReturnValue('/aiops/alerts');

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
    replace: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
    prefetch: vi.fn(),
  }),
  usePathname: () => mockPathname(),
  useSearchParams: () => new URLSearchParams(),
}));

// Mock the useAuth hook
const mockUseAuth = vi.fn();
vi.mock('@/hooks/use-auth', () => ({
  useAuth: () => mockUseAuth(),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// Import ProtectedRoute after mocks are set up
import { ProtectedRoute } from '@/components/protected-route';

describe('Property 4: Frontend Auth Guard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  /**
   * Arbitrary for generating random AIOps sub-path segments.
   * Generates valid URL path segments (alphanumeric, hyphens, underscores).
   */
  const arbPathSegment = fc
    .array(
      fc.constantFrom(
        ...'abcdefghijklmnopqrstuvwxyz0123456789-_'.split(''),
      ),
      { minLength: 1, maxLength: 20 },
    )
    .map((chars) => chars.join(''));

  /**
   * Arbitrary for generating random /aiops/* paths.
   * Produces paths like "/aiops/alerts", "/aiops/incidents/abc-123", etc.
   */
  const arbAiopsPath = fc
    .array(arbPathSegment, { minLength: 1, maxLength: 3 })
    .map((segments) => '/aiops/' + segments.join('/'));

  it('should redirect unauthenticated users to /login from any /aiops/* route', async () => {
    await fc.assert(
      fc.asyncProperty(arbAiopsPath, async (aiopsPath) => {
        // Reset mocks for each iteration
        mockPush.mockClear();
        mockPathname.mockReturnValue(aiopsPath);

        // Simulate unauthenticated state (not loading, not authenticated)
        mockUseAuth.mockReturnValue({
          isAuthenticated: false,
          isLoading: false,
          user: null,
          login: vi.fn(),
          logout: vi.fn(),
          register: vi.fn(),
          refreshUser: vi.fn(),
        });

        const { unmount } = render(
          <ProtectedRoute>
            <div data-testid="protected-content">Secret AIOps Content</div>
          </ProtectedRoute>,
        );

        // Verify redirect to login with the current path as redirect param
        await waitFor(() => {
          expect(mockPush).toHaveBeenCalled();
        });

        const pushCall = mockPush.mock.calls[0][0] as string;
        expect(pushCall).toContain('/login');
        expect(pushCall).toContain(
          `redirect=${encodeURIComponent(aiopsPath)}`,
        );

        // Verify protected content is NOT rendered
        expect(screen.queryByTestId('protected-content')).toBeNull();

        unmount();
      }),
      { numRuns: 100 },
    );
  });

  it('should not render any AIOps page content when user is unauthenticated', async () => {
    await fc.assert(
      fc.asyncProperty(arbAiopsPath, async (aiopsPath) => {
        mockPush.mockClear();
        mockPathname.mockReturnValue(aiopsPath);

        // Simulate unauthenticated state
        mockUseAuth.mockReturnValue({
          isAuthenticated: false,
          isLoading: false,
          user: null,
          login: vi.fn(),
          logout: vi.fn(),
          register: vi.fn(),
          refreshUser: vi.fn(),
        });

        const { container, unmount } = render(
          <ProtectedRoute>
            <div data-testid="aiops-content">
              <h1>AIOps Dashboard</h1>
              <p>Sensitive alert data</p>
            </div>
          </ProtectedRoute>,
        );

        // The ProtectedRoute should render null (no children visible)
        expect(screen.queryByTestId('aiops-content')).toBeNull();
        expect(container.querySelector('h1')).toBeNull();
        expect(container.textContent).not.toContain('Sensitive alert data');

        unmount();
      }),
      { numRuns: 100 },
    );
  });

  it('should show loading state and not redirect while auth is loading', async () => {
    await fc.assert(
      fc.asyncProperty(arbAiopsPath, async (aiopsPath) => {
        mockPush.mockClear();
        mockPathname.mockReturnValue(aiopsPath);

        // Simulate loading state
        mockUseAuth.mockReturnValue({
          isAuthenticated: false,
          isLoading: true,
          user: null,
          login: vi.fn(),
          logout: vi.fn(),
          register: vi.fn(),
          refreshUser: vi.fn(),
        });

        const { unmount } = render(
          <ProtectedRoute>
            <div data-testid="protected-content">Secret Content</div>
          </ProtectedRoute>,
        );

        // Should NOT redirect while loading
        expect(mockPush).not.toHaveBeenCalled();

        // Should NOT show protected content while loading
        expect(screen.queryByTestId('protected-content')).toBeNull();

        unmount();
      }),
      { numRuns: 100 },
    );
  });
});
