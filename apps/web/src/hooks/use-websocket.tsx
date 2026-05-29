'use client';

import * as React from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { findingKeys } from './use-findings';
import { dashboardKeys } from './use-dashboard';
import { useAuth } from './use-auth';

// ─── Types ────────────────────────────────────────────────────────────────────

export type WSStatus = 'connected' | 'reconnecting' | 'disconnected';

interface WSEvent {
  type: 'finding.created' | 'finding.updated' | 'finding.resolved' | 'ping' | 'connected';
  data?: Record<string, unknown>;
  org_id?: string;
  timestamp?: string;
}

interface UseWebSocketReturn {
  status: WSStatus;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const WS_BASE_URL =
  `ws://${process.env.NEXT_PUBLIC_PUSHER_HOST || 'localhost'}:${process.env.NEXT_PUBLIC_PUSHER_PORT || '6001'}`;

const PUSHER_KEY = process.env.NEXT_PUBLIC_PUSHER_KEY || 'cloudvisor-key';
const PUSHER_HOST = process.env.NEXT_PUBLIC_PUSHER_HOST || 'localhost';
const PUSHER_PORT = parseInt(process.env.NEXT_PUBLIC_PUSHER_PORT || '6001', 10);

// ─── Hook ─────────────────────────────────────────────────────────────────────

export function useWebSocket(): UseWebSocketReturn {
  const queryClient = useQueryClient();
  const { user, isLoading: authLoading } = useAuth();
  const [status, setStatus] = React.useState<WSStatus>('disconnected');
  const wsRef = React.useRef<WebSocket | null>(null);
  const reconnectTimerRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);
  const attemptRef = React.useRef(0);
  const mountedRef = React.useRef(true);

  const connect = React.useCallback(() => {
    if (!mountedRef.current) return;

    // Auth via HttpOnly cookies — no token needed in query param.
    // The WebSocket server reads the cv_access cookie for authentication.
    // If the user is not authenticated, don't attempt connection.
    const sessionCookie =
      typeof document !== 'undefined' && document.cookie.includes('cv_session=1');
    if (!sessionCookie && !authLoading) {
      setStatus('disconnected');
      return;
    }

    // Use Pusher/Soketi for WebSocket — matches the AIOps pattern
    // The server-side Pusher auth endpoint handles cookie-based authentication.
    // For direct events WebSocket, connect to the Soketi endpoint.
    const url = `${WS_BASE_URL}/app/?key=${PUSHER_KEY}`;

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!mountedRef.current) return;
        setStatus('connected');
        attemptRef.current = 0;
      };

      ws.onmessage = (event) => {
        if (!mountedRef.current) return;
        try {
          const msg: WSEvent = JSON.parse(event.data);

          if (msg.type === 'ping') {
            ws.send('pong');
            return;
          }

          if (msg.type === 'connected') return;

          // Invalidate relevant queries on finding events
          if (msg.type === 'finding.created' || msg.type === 'finding.updated' || msg.type === 'finding.resolved') {
            queryClient.invalidateQueries({ queryKey: findingKeys.all() });
            queryClient.invalidateQueries({ queryKey: dashboardKeys.stats() });
            queryClient.invalidateQueries({ queryKey: dashboardKeys.recentFindings() });

            // Show toast for new critical findings
            if (msg.type === 'finding.created' && msg.data?.severity === 'CRITICAL') {
              try {
                const { toast } = require('sonner');
                toast.error(`Critical finding: ${msg.data?.title ?? 'New critical finding detected'}`, {
                  duration: 6000,
                });
              } catch {
                // Sonner not available — skip toast
              }
            }
          }
        } catch {
          // Ignore parse errors
        }
      };

      ws.onclose = () => {
        if (!mountedRef.current) return;
        wsRef.current = null;
        setStatus('reconnecting');
        scheduleReconnect();
      };

      ws.onerror = () => {
        if (!mountedRef.current) return;
        ws.close();
      };
    } catch {
      setStatus('reconnecting');
      scheduleReconnect();
    }
  }, [queryClient, authLoading]);

  const scheduleReconnect = React.useCallback(() => {
    if (!mountedRef.current) return;
    if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
    const delay = Math.min(1000 * Math.pow(2, attemptRef.current), 30_000);
    attemptRef.current += 1;
    reconnectTimerRef.current = setTimeout(() => {
      if (mountedRef.current) connect();
    }, delay);
  }, [connect]);

  React.useEffect(() => {
    mountedRef.current = true;
    connect();

    return () => {
      mountedRef.current = false;
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);

  return { status };
}
