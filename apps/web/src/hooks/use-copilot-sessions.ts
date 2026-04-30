import { useCallback, useEffect, useState } from 'react';
import { useCloudVisorQStore, ChatSession } from '@/stores/cloudvisor-q';

const COPILOT_BASE_URL = process.env.NEXT_PUBLIC_COPILOT_URL || 'http://localhost:8010';

function getAuthHeaders(): Record<string, string> {
  const token =
    typeof window !== 'undefined'
      ? localStorage.getItem('access_token') ?? 'dev-token'
      : 'dev-token';

  const headers: Record<string, string> = { Authorization: `Bearer ${token}` };

  // Extract org ID from JWT token
  if (token && token !== 'dev-token') {
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      const orgId = payload?.organization_id ?? payload?.org_id;
      if (orgId) {
        headers['X-Org-ID'] = orgId;
      }
    } catch (e) {
      // Silently fail if token parsing fails
    }
  }

  return headers;
}

export function useCopilotSessions() {
  const {
    currentSessionId,
    setCurrentSessionId,
    sessions,
    setSessions,
    addSession,
    removeSession,
  } = useCloudVisorQStore();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadSessions = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const headers = getAuthHeaders();
      const url = `${COPILOT_BASE_URL}/v1/copilot/sessions`;
      
      console.log('Loading sessions from:', url);
      console.log('Headers:', headers);

      const response = await fetch(url, {
        headers,
      });

      console.log('Response status:', response.status);
      console.log('Response ok:', response.ok);

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Error response:', errorText);
        throw new Error(`Failed to load sessions: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      console.log('Sessions data:', data);
      setSessions(data.sessions || []);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load sessions';
      setError(message);
      console.error('Error loading sessions:', err);
    } finally {
      setLoading(false);
    }
  }, [setSessions]);

  // Load sessions on mount
  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  const createSession = useCallback(
    async (title: string, description?: string): Promise<ChatSession | null> => {
      try {
        setError(null);

        const response = await fetch(`${COPILOT_BASE_URL}/v1/copilot/sessions`, {
          method: 'POST',
          headers: {
            ...getAuthHeaders(),
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ title, description }),
        });

        if (!response.ok) {
          throw new Error(`Failed to create session: ${response.statusText}`);
        }

        const session = await response.json();
        addSession(session);
        setCurrentSessionId(session.id);
        return session;
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to create session';
        setError(message);
        console.error('Error creating session:', err);
        return null;
      }
    },
    [addSession, setCurrentSessionId]
  );

  const getSession = useCallback(
    async (sessionId: string) => {
      try {
        setError(null);

        const response = await fetch(
          `${COPILOT_BASE_URL}/v1/copilot/sessions/${sessionId}`,
          {
            headers: getAuthHeaders(),
          }
        );

        if (!response.ok) {
          throw new Error(`Failed to load session: ${response.statusText}`);
        }

        return await response.json();
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to load session';
        setError(message);
        console.error('Error loading session:', err);
        return null;
      }
    },
    []
  );

  const updateSession = useCallback(
    async (
      sessionId: string,
      updates: { title?: string; description?: string; is_active?: boolean }
    ): Promise<boolean> => {
      try {
        setError(null);

        const response = await fetch(
          `${COPILOT_BASE_URL}/v1/copilot/sessions/${sessionId}`,
          {
            method: 'PATCH',
            headers: {
              ...getAuthHeaders(),
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(updates),
          }
        );

        if (!response.ok) {
          throw new Error(`Failed to update session: ${response.statusText}`);
        }

        // Reload sessions to get updated data
        await loadSessions();
        return true;
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to update session';
        setError(message);
        console.error('Error updating session:', err);
        return false;
      }
    },
    [loadSessions]
  );

  const deleteSession = useCallback(
    async (sessionId: string): Promise<boolean> => {
      try {
        setError(null);

        const response = await fetch(
          `${COPILOT_BASE_URL}/v1/copilot/sessions/${sessionId}`,
          {
            method: 'DELETE',
            headers: getAuthHeaders(),
          }
        );

        if (!response.ok) {
          throw new Error(`Failed to delete session: ${response.statusText}`);
        }

        removeSession(sessionId);
        if (currentSessionId === sessionId) {
          setCurrentSessionId(null);
        }
        return true;
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to delete session';
        setError(message);
        console.error('Error deleting session:', err);
        return false;
      }
    },
    [currentSessionId, removeSession, setCurrentSessionId]
  );

  return {
    sessions,
    currentSessionId,
    setCurrentSessionId,
    loading,
    error,
    loadSessions,
    createSession,
    getSession,
    updateSession,
    deleteSession,
  };
}
