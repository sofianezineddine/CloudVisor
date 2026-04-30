'use client';

import * as React from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { findingKeys } from './use-findings';
import { dashboardKeys } from './use-dashboard';

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
  (process.env.NEXT_PUBLIC_API_GATEWAY_URL || 'http://localhost:8005')
    .replace(/^http/, 'ws');

// ─── Hook ─────────────────────────────────────────────────────────────────────

export function useWebSocket(): UseWebSocketReturn {
  const queryClient = useQueryClient();
  const [status, setStatus] = React.useState<WSStatus>('disconnected');
  const wsRef = React.useRef<WebSocket | null>(null);
  const reconnectTimerRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);
  const attemptRef = React.useRef(0);
  const mountedRef = React.useRef(true);

  const connect = React.useCallback(() => {
    if (!mountedRef.current) return;

    // Get access token from localStorage
    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
    if (!token) {
      setStatus('disconnected');
      return;
    }

    const url = `${WS_BASE_URL}/ws/events?token=${encodeURIComponent(token)}`;

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
              // Use the Sonner toast if available
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
  }, [queryClient]);

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
        wsRef.current.onclose = null; // prevent reconnect on intentional close
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);

  return { status };
}
