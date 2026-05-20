'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { usePathname } from 'next/navigation';
import { useQueryClient } from '@tanstack/react-query';
import Pusher, { type Channel } from 'pusher-js';
import { useAuth } from './use-auth';

// ─── Types ────────────────────────────────────────────────────────────────────

export type AIOpsWSConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

export type AIOpsEventType =
  | 'alert:created'
  | 'alert:updated'
  | 'incident:created'
  | 'incident:updated'
  | 'workflow:execution';

export interface AIOpsEvent {
  type: AIOpsEventType;
  data: unknown;
  timestamp: number;
}

export interface AIOpsWSEventHandlers {
  onAlertCreated?: (data: unknown) => void;
  onAlertUpdated?: (data: unknown) => void;
  onIncidentCreated?: (data: unknown) => void;
  onIncidentUpdated?: (data: unknown) => void;
  onWorkflowExecution?: (data: unknown) => void;
}

interface UseAIOpsWebSocketOptions {
  /** Custom event handlers */
  handlers?: AIOpsWSEventHandlers;
  /** Whether the hook should connect (default: true). Connection is also gated by pathname. */
  enabled?: boolean;
}

interface UseAIOpsWebSocketReturn {
  /** Current connection status */
  status: AIOpsWSConnectionStatus;
  /** Most recently received events (last 50) */
  events: AIOpsEvent[];
}

// ─── Constants ────────────────────────────────────────────────────────────────

const PUSHER_KEY = process.env.NEXT_PUBLIC_PUSHER_KEY || 'cloudvisor-key';
const PUSHER_HOST = process.env.NEXT_PUBLIC_PUSHER_HOST || 'localhost';
const PUSHER_PORT = parseInt(process.env.NEXT_PUBLIC_PUSHER_PORT || '6001', 10);

const MAX_EVENTS_BUFFER = 50;
const MAX_RECONNECT_ATTEMPTS = 10;
const INITIAL_RECONNECT_DELAY_MS = 1000;
const MAX_RECONNECT_DELAY_MS = 30_000;

// ─── Helpers ──────────────────────────────────────────────────────────────────

/** Returns true when the current pathname is under /aiops/* */
function isAIOpsRoute(pathname: string | null): boolean {
  if (!pathname) return false;
  return pathname === '/aiops' || pathname.startsWith('/aiops/');
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

/**
 * Hook for subscribing to AIOps real-time WebSocket events via Pusher.js / Soketi.
 *
 * Connects when AIOps pages are active (pathname starts with /aiops).
 * Disconnects when user navigates away from /aiops/*.
 * Subscribes to `private-{tenant_id}` channel and listens for:
 *   - alert:created — New alert ingested
 *   - alert:updated — Alert status/severity changed
 *   - incident:created — New incident correlated
 *   - incident:updated — Incident merged/split/updated
 *   - workflow:execution — Workflow execution completed
 *
 * Invalidates React Query cache on events to keep UI in sync.
 *
 * @param options - Configuration options
 * @returns Connection status and buffered events
 *
 * Validates: Requirements 6.2, 6.3, 6.4
 */
export function useAIOpsWebSocket(
  options: UseAIOpsWebSocketOptions = {}
): UseAIOpsWebSocketReturn {
  const { handlers = {}, enabled = true } = options;
  const { user } = useAuth();
  const pathname = usePathname();
  const queryClient = useQueryClient();

  const [status, setStatus] = useState<AIOpsWSConnectionStatus>('disconnected');
  const [events, setEvents] = useState<AIOpsEvent[]>([]);

  const pusherRef = useRef<Pusher | null>(null);
  const channelRef = useRef<Channel | null>(null);
  const reconnectAttemptRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const handlersRef = useRef(handlers);

  // Keep handlers ref up to date without re-binding
  useEffect(() => {
    handlersRef.current = handlers;
  });

  // Derive tenant_id from authenticated user's organization_id
  const tenantId = user?.organization_id;

  // Determine if we should be connected based on pathname and enabled flag
  const shouldConnect = enabled && isAIOpsRoute(pathname) && !!tenantId;

  // ─── Buffer event helper ──────────────────────────────────────────────────

  const pushEvent = useCallback((type: AIOpsEventType, data: unknown) => {
    const event: AIOpsEvent = { type, data, timestamp: Date.now() };
    setEvents((prev) => [...prev.slice(-(MAX_EVENTS_BUFFER - 1)), event]);
  }, []);

  // ─── Invalidate queries on real-time events ─────────────────────────────────

  const invalidateAlerts = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['aiops', 'alerts'] });
    queryClient.invalidateQueries({ queryKey: ['aiops', 'dashboard'] });
  }, [queryClient]);

  const invalidateIncidents = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['aiops', 'incidents'] });
    queryClient.invalidateQueries({ queryKey: ['aiops', 'dashboard'] });
  }, [queryClient]);

  const invalidateWorkflows = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['aiops', 'workflows'] });
    queryClient.invalidateQueries({ queryKey: ['aiops', 'dashboard'] });
  }, [queryClient]);

  // ─── Connect / Disconnect lifecycle ─────────────────────────────────────────

  useEffect(() => {
    if (!shouldConnect || typeof window === 'undefined') {
      // Disconnect if we shouldn't be connected (e.g., navigated away from /aiops/*)
      if (pusherRef.current) {
        if (channelRef.current) {
          channelRef.current.unbind_all();
          pusherRef.current.unsubscribe(`private-${tenantId}`);
          channelRef.current = null;
        }
        pusherRef.current.disconnect();
        pusherRef.current = null;
      }
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      setStatus('disconnected');
      return;
    }

    // Create Pusher instance connected to Soketi
    const pusher = new Pusher(PUSHER_KEY, {
      wsHost: PUSHER_HOST,
      wsPort: PUSHER_PORT,
      wssPort: PUSHER_PORT,
      forceTLS: false,
      disableStats: true,
      enabledTransports: ['ws', 'wss'],
      cluster: 'mt1', // Required by Pusher.js but unused with Soketi
      authEndpoint: `${process.env.NEXT_PUBLIC_API_GATEWAY_URL || 'http://localhost:8005'}/v1/keep/pusher/auth`,
      auth: {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('access_token') || ''}`,
        },
      },
    });

    pusherRef.current = pusher;
    setStatus('connecting');

    // ─── Connection state handlers ────────────────────────────────────────────

    pusher.connection.bind('connected', () => {
      setStatus('connected');
      reconnectAttemptRef.current = 0;
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      // Reconcile missed updates on reconnect
      invalidateAlerts();
      invalidateIncidents();
      invalidateWorkflows();
    });

    pusher.connection.bind('disconnected', () => {
      setStatus('disconnected');
      scheduleReconnect();
    });

    pusher.connection.bind('error', (err: { data?: { code?: number } }) => {
      const code = err?.data?.code;
      if (code === 4001 || code === 4003 || code === 401 || code === 403) {
        // Auth failure — stop reconnecting, redirect to login
        setStatus('error');
        reconnectAttemptRef.current = MAX_RECONNECT_ATTEMPTS;
        if (reconnectTimerRef.current) {
          clearTimeout(reconnectTimerRef.current);
        }
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('cloudvisor-user');
        window.location.href = '/login?error=session_expired';
      } else {
        setStatus('error');
      }
    });

    // ─── Subscribe to private tenant channel ──────────────────────────────────

    const channelName = `private-${tenantId}`;
    const channel = pusher.subscribe(channelName);
    channelRef.current = channel;

    // Bind event listeners for all AIOps event types
    channel.bind('alert:created', (data: unknown) => {
      pushEvent('alert:created', data);
      invalidateAlerts();
      handlersRef.current.onAlertCreated?.(data);
    });

    channel.bind('alert:updated', (data: unknown) => {
      pushEvent('alert:updated', data);
      invalidateAlerts();
      handlersRef.current.onAlertUpdated?.(data);
    });

    channel.bind('incident:created', (data: unknown) => {
      pushEvent('incident:created', data);
      invalidateIncidents();
      handlersRef.current.onIncidentCreated?.(data);
    });

    channel.bind('incident:updated', (data: unknown) => {
      pushEvent('incident:updated', data);
      invalidateIncidents();
      handlersRef.current.onIncidentUpdated?.(data);
    });

    channel.bind('workflow:execution', (data: unknown) => {
      pushEvent('workflow:execution', data);
      invalidateWorkflows();
      handlersRef.current.onWorkflowExecution?.(data);
    });

    // ─── Reconnection with exponential backoff ────────────────────────────────

    function scheduleReconnect() {
      if (reconnectAttemptRef.current >= MAX_RECONNECT_ATTEMPTS) return;

      const delay = Math.min(
        INITIAL_RECONNECT_DELAY_MS * Math.pow(2, reconnectAttemptRef.current),
        MAX_RECONNECT_DELAY_MS
      );
      reconnectAttemptRef.current += 1;

      reconnectTimerRef.current = setTimeout(() => {
        pusher.connect();
      }, delay);
    }

    // ─── Cleanup on unmount or dependency change ──────────────────────────────

    return () => {
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      channel.unbind_all();
      pusher.unsubscribe(channelName);
      pusher.disconnect();
      pusherRef.current = null;
      channelRef.current = null;
      setStatus('disconnected');
    };
  }, [shouldConnect, tenantId, queryClient, invalidateAlerts, invalidateIncidents, invalidateWorkflows, pushEvent]);

  return { status, events };
}
