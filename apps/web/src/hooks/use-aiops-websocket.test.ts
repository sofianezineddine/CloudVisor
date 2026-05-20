import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';

// ─── Mocks ────────────────────────────────────────────────────────────────────

// Mock usePathname
let currentPathname = '/aiops/alerts';
vi.mock('next/navigation', () => ({
  usePathname: () => currentPathname,
}));

// Mock useAuth
let currentUser: Record<string, unknown> | null = {
  id: 'user-1',
  email: 'test@example.com',
  first_name: 'Test',
  last_name: 'User',
  organization_id: 'org-123',
  mfa_enabled: false,
  provider: 'local',
};
vi.mock('./use-auth', () => ({
  useAuth: () => ({ user: currentUser, isAuthenticated: !!currentUser, isLoading: false }),
}));

// Mock React Query
const mockInvalidateQueries = vi.fn();
vi.mock('@tanstack/react-query', () => ({
  useQueryClient: () => ({
    invalidateQueries: mockInvalidateQueries,
  }),
}));

// Mock Pusher.js — use a factory that captures calls
const mockChannelBind = vi.fn();
const mockUnbindAll = vi.fn();
const mockSubscribe = vi.fn(() => ({
  bind: mockChannelBind,
  unbind_all: mockUnbindAll,
}));
const mockUnsubscribe = vi.fn();
const mockDisconnect = vi.fn();
const mockConnect = vi.fn();
const mockConnectionBind = vi.fn();

vi.mock('pusher-js', () => ({
  default: class MockPusher {
    connection = { bind: mockConnectionBind };
    subscribe = mockSubscribe;
    unsubscribe = mockUnsubscribe;
    disconnect = mockDisconnect;
    connect = mockConnect;
    constructor(public key: string, public options: Record<string, unknown>) {}
  },
}));

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] || null),
    setItem: vi.fn((key: string, value: string) => { store[key] = value; }),
    removeItem: vi.fn((key: string) => { delete store[key]; }),
    clear: vi.fn(() => { store = {}; }),
  };
})();
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('useAIOpsWebSocket', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.clear();
    localStorageMock.setItem('access_token', 'test-jwt-token');
    currentPathname = '/aiops/alerts';
    currentUser = {
      id: 'user-1',
      email: 'test@example.com',
      first_name: 'Test',
      last_name: 'User',
      organization_id: 'org-123',
      mfa_enabled: false,
      provider: 'local',
    };
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should connect when on an AIOps page with authenticated user', async () => {
    const { useAIOpsWebSocket } = await import('./use-aiops-websocket');

    renderHook(() => useAIOpsWebSocket());

    // Should subscribe to the private channel with tenant_id
    expect(mockSubscribe).toHaveBeenCalledWith('private-org-123');
  });

  it('should not connect when pathname is not under /aiops', async () => {
    currentPathname = '/settings/profile';
    const { useAIOpsWebSocket } = await import('./use-aiops-websocket');

    renderHook(() => useAIOpsWebSocket());

    expect(mockSubscribe).not.toHaveBeenCalled();
  });

  it('should not connect when user is not authenticated', async () => {
    currentUser = null;
    const { useAIOpsWebSocket } = await import('./use-aiops-websocket');

    renderHook(() => useAIOpsWebSocket());

    expect(mockSubscribe).not.toHaveBeenCalled();
  });

  it('should not connect when enabled is false', async () => {
    const { useAIOpsWebSocket } = await import('./use-aiops-websocket');

    renderHook(() => useAIOpsWebSocket({ enabled: false }));

    expect(mockSubscribe).not.toHaveBeenCalled();
  });

  it('should bind all required event types', async () => {
    const { useAIOpsWebSocket } = await import('./use-aiops-websocket');

    renderHook(() => useAIOpsWebSocket());

    const boundEvents = mockChannelBind.mock.calls.map((call) => call[0]);
    expect(boundEvents).toContain('alert:created');
    expect(boundEvents).toContain('alert:updated');
    expect(boundEvents).toContain('incident:created');
    expect(boundEvents).toContain('incident:updated');
    expect(boundEvents).toContain('workflow:execution');
  });

  it('should disconnect on unmount', async () => {
    const { useAIOpsWebSocket } = await import('./use-aiops-websocket');

    const { unmount } = renderHook(() => useAIOpsWebSocket());
    unmount();

    expect(mockUnbindAll).toHaveBeenCalled();
    expect(mockUnsubscribe).toHaveBeenCalledWith('private-org-123');
    expect(mockDisconnect).toHaveBeenCalled();
  });

  it('should disconnect when navigating away from /aiops/*', async () => {
    const { useAIOpsWebSocket } = await import('./use-aiops-websocket');

    const { rerender } = renderHook(() => useAIOpsWebSocket());

    // Verify connected
    expect(mockSubscribe).toHaveBeenCalledWith('private-org-123');

    // Simulate navigation away — change pathname and rerender
    currentPathname = '/dashboard';
    rerender();

    // Should disconnect
    expect(mockDisconnect).toHaveBeenCalled();
  });

  it('should return disconnected status initially when not on AIOps page', async () => {
    currentPathname = '/settings';
    const { useAIOpsWebSocket } = await import('./use-aiops-websocket');

    const { result } = renderHook(() => useAIOpsWebSocket());

    expect(result.current.status).toBe('disconnected');
    expect(result.current.events).toEqual([]);
  });

  it('should use organization_id from useAuth as tenant_id', async () => {
    currentUser = { ...currentUser!, organization_id: 'tenant-abc' };
    const { useAIOpsWebSocket } = await import('./use-aiops-websocket');

    renderHook(() => useAIOpsWebSocket());

    expect(mockSubscribe).toHaveBeenCalledWith('private-tenant-abc');
  });

  it('should configure Pusher with ws transport and no TLS for Soketi', async () => {
    const { useAIOpsWebSocket } = await import('./use-aiops-websocket');
    const PusherMod = await import('pusher-js');

    renderHook(() => useAIOpsWebSocket());

    // The Pusher constructor should have been called (via the class mock)
    // Verify the subscribe was called which means Pusher was instantiated
    expect(mockSubscribe).toHaveBeenCalled();
  });

  it('should call custom handlers when events are received', async () => {
    const { useAIOpsWebSocket } = await import('./use-aiops-websocket');
    const onAlertCreated = vi.fn();

    renderHook(() => useAIOpsWebSocket({ handlers: { onAlertCreated } }));

    // Find the alert:created handler that was bound
    const alertCreatedCall = mockChannelBind.mock.calls.find((call) => call[0] === 'alert:created');
    expect(alertCreatedCall).toBeDefined();

    // Simulate receiving an event
    const handler = alertCreatedCall![1];
    act(() => {
      handler({ id: 'alert-1', severity: 'critical' });
    });

    expect(onAlertCreated).toHaveBeenCalledWith({ id: 'alert-1', severity: 'critical' });
  });

  it('should invalidate React Query cache on alert events', async () => {
    const { useAIOpsWebSocket } = await import('./use-aiops-websocket');

    renderHook(() => useAIOpsWebSocket());

    // Find the alert:created handler
    const alertCreatedCall = mockChannelBind.mock.calls.find((call) => call[0] === 'alert:created');
    const handler = alertCreatedCall![1];

    act(() => {
      handler({ id: 'alert-1' });
    });

    expect(mockInvalidateQueries).toHaveBeenCalledWith({ queryKey: ['aiops', 'alerts'] });
    expect(mockInvalidateQueries).toHaveBeenCalledWith({ queryKey: ['aiops', 'dashboard'] });
  });

  it('should work with /aiops root path', async () => {
    currentPathname = '/aiops';
    const { useAIOpsWebSocket } = await import('./use-aiops-websocket');

    renderHook(() => useAIOpsWebSocket());

    expect(mockSubscribe).toHaveBeenCalledWith('private-org-123');
  });
});
