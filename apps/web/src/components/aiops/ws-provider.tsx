'use client';

import React, { createContext, useContext, useEffect, useRef, useState } from 'react';
import Pusher, { Channel } from 'pusher-js';
import { useAuth } from '@/hooks/use-auth';

// ─── Types ────────────────────────────────────────────────────────────────────

export type AIOpsWSConnectionStatus =
  | 'connected'
  | 'connecting'
  | 'disconnected'
  | 'failed';

interface AIOpsWSContextValue {
  /** The Pusher instance (null if not initialized) */
  pusher: Pusher | null;
  /** The subscribed private channel (null if not connected) */
  channel: Channel | null;
  /** Current connection status */
  status: AIOpsWSConnectionStatus;
}

const AIOpsWSContext = createContext<AIOpsWSContextValue>({
  pusher: null,
  channel: null,
  status: 'disconnected',
});

// ─── Constants ────────────────────────────────────────────────────────────────

const PUSHER_HOST = process.env.NEXT_PUBLIC_PUSHER_HOST || process.env.NEXT_PUBLIC_SOKETI_HOST || 'localhost';
const PUSHER_PORT = Number(process.env.NEXT_PUBLIC_PUSHER_PORT || process.env.NEXT_PUBLIC_SOKETI_PORT || '6001');
const PUSHER_KEY = process.env.NEXT_PUBLIC_PUSHER_KEY || process.env.NEXT_PUBLIC_SOKETI_KEY || 'cloudvisor-key';
const PUSHER_CLUSTER = process.env.NEXT_PUBLIC_SOKETI_CLUSTER || 'mt1';

const API_GATEWAY_BASE_URL =
  process.env.NEXT_PUBLIC_API_GATEWAY_URL || 'http://localhost:8005';

// ─── Provider ─────────────────────────────────────────────────────────────────

export function AIOpsWSProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const [status, setStatus] = useState<AIOpsWSConnectionStatus>('disconnected');
  const pusherRef = useRef<Pusher | null>(null);
  const channelRef = useRef<Channel | null>(null);

  useEffect(() => {
    if (!user?.organization_id) {
      setStatus('disconnected');
      return;
    }

    const token = localStorage.getItem('access_token');
    if (!token) {
      setStatus('disconnected');
      return;
    }

    const channelName = `private-${user.organization_id}`;

    // Initialize Pusher with Soketi configuration
    const pusher = new Pusher(PUSHER_KEY, {
      wsHost: PUSHER_HOST,
      wsPort: PUSHER_PORT,
      wssPort: PUSHER_PORT,
      cluster: PUSHER_CLUSTER,
      forceTLS: false,
      enabledTransports: ['ws', 'wss'],
      authEndpoint: `${API_GATEWAY_BASE_URL}/v1/keep/pusher/auth`,
      auth: {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      },
    });

    pusherRef.current = pusher;
    setStatus('connecting');

    // Connection state bindings
    pusher.connection.bind('connected', () => {
      setStatus('connected');
    });

    pusher.connection.bind('connecting', () => {
      setStatus('connecting');
    });

    pusher.connection.bind('disconnected', () => {
      setStatus('disconnected');
    });

    pusher.connection.bind('failed', () => {
      setStatus('failed');
    });

    // Subscribe to the private channel
    const channel = pusher.subscribe(channelName);
    channelRef.current = channel;

    // Cleanup on unmount or when user changes
    return () => {
      channel.unbind_all();
      pusher.unsubscribe(channelName);
      pusher.disconnect();
      pusherRef.current = null;
      channelRef.current = null;
      setStatus('disconnected');
    };
  }, [user?.organization_id]);

  return (
    <AIOpsWSContext.Provider
      value={{
        pusher: pusherRef.current,
        channel: channelRef.current,
        status,
      }}
    >
      {children}
    </AIOpsWSContext.Provider>
  );
}

// ─── Context hook ─────────────────────────────────────────────────────────────

export function useAIOpsWSContext() {
  return useContext(AIOpsWSContext);
}
