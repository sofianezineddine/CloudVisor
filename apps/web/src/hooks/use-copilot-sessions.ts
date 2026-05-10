import { useCallback, useState } from 'react';
import { useCloudVisorQStore, ChatSession } from '@/stores/cloudvisor-q';

const COPILOT_BASE_URL = process.env.NEXT_PUBLIC_COPILOT_URL || 'http://localhost:8010';
// Gateway URL — used for session management endpoints proxied through the API gateway
const GW_BASE_URL = process.env.NEXT_PUBLIC_API_GATEWAY_URL || 'http://localhost:8005';

function getAuthHeaders(): Record<string, string> {
  const token =
    typeof window !== 'undefined'
      ? localStorage.getItem('access_token')
      : null;

  // Never fall back to a hardcoded dev token — fail loudly if unauthenticated
  if (!token) return {};

  const headers: Record<string, string> = { Authorization: `Bearer ${token}` };

  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    const orgId = payload?.organization_id ?? payload?.org_id;
    if (orgId) {
      headers['X-Org-ID'] = orgId;
    }
  } catch {
    // Silently fail if token parsing fails
  }

  return headers;
}

// Helper: try gateway first, fall back to direct copilot URL
async function copilotFetch(path: string, options: RequestInit = {}) {
  // Try gateway first (preferred — goes through rate limiting + auth)
  try {
    const gwResp = await fetch(`${GW_BASE_URL}${path}`, {
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      ...options,
    });
    if (gwResp.ok || gwResp.status === 204) {
      return gwResp.status === 204 ? null : gwResp.json();
    }
  } catch {
    // Gateway unavailable — fall through to direct
  }
  // Fallback: direct copilot service
  const resp = await fetch(`${COPILOT_BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    ...options,
  });
  if (!resp.ok) throw new Error(`${resp.status}: ${resp.statusText}`);
  return resp.status === 204 ? null : resp.json();
}

export function useCopilotSessions() {
  const currentSessionId = useCloudVisorQStore(s => s.currentSessionId);
  const setCurrentSessionId = useCloudVisorQStore(s => s.setCurrentSessionId);
  const sessions = useCloudVisorQStore(s => s.sessions);
  const setSessions = useCloudVisorQStore(s => s.setSessions);
  const addSession = useCloudVisorQStore(s => s.addSession);
  const removeSession = useCloudVisorQStore(s => s.removeSession);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadSessions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Sessions live directly on the copilot service at /v1/copilot/sessions
      // The gateway wraps responses as { data: { sessions: [...] }, meta: {} }
      // The direct copilot service returns { sessions: [...] } directly
      const data = await copilotFetch('/v1/copilot/sessions');

      // Unwrap all possible response shapes:
      // 1. Gateway envelope:  { data: { sessions: [...] } }
      // 2. Direct copilot:    { sessions: [...] }
      // 3. Flat array:        [...]
      let sessionsData: ChatSession[] = [];
      if (Array.isArray(data)) {
        sessionsData = data;
      } else if (Array.isArray(data?.data?.sessions)) {
        sessionsData = data.data.sessions;
      } else if (Array.isArray(data?.sessions)) {
        sessionsData = data.sessions;
      } else if (Array.isArray(data?.data)) {
        sessionsData = data.data;
      }
      setSessions(sessionsData);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load sessions';
      setError(message);
      setSessions([]);
    } finally {
      setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const createSession = useCallback(
    async (title: string, description?: string): Promise<ChatSession | null> => {
      try {
        setError(null);
        const session = await copilotFetch('/v1/copilot/sessions', {
          method: 'POST',
          body: JSON.stringify({ title, description }),
        });
        if (session) {
          addSession(session);
          setCurrentSessionId(session.id);
        }
        return session;
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to create session');
        return null;
      }
    },
    [addSession, setCurrentSessionId]
  );

  const getSession = useCallback(async (sessionId: string) => {
    try {
      setError(null);
      return await copilotFetch(`/v1/copilot/sessions/${sessionId}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load session');
      return null;
    }
  }, []);

  const updateSession = useCallback(
    async (sessionId: string, updates: { title?: string; description?: string; is_active?: boolean }): Promise<boolean> => {
      try {
        setError(null);
        await copilotFetch(`/v1/copilot/sessions/${sessionId}`, {
          method: 'PATCH',
          body: JSON.stringify(updates),
        });
        await loadSessions();
        return true;
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to update session');
        return false;
      }
    },
    [loadSessions]
  );

  const deleteSession = useCallback(
    async (sessionId: string): Promise<boolean> => {
      try {
        setError(null);
        await copilotFetch(`/v1/copilot/sessions/${sessionId}`, { method: 'DELETE' });
        removeSession(sessionId);
        if (currentSessionId === sessionId) setCurrentSessionId(null);
        return true;
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to delete session');
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
