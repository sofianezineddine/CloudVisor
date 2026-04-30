import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  intent?: string;
  processing?: boolean;
  created_at?: string;
}

export interface ChatSession {
  session_id: string;
  title: string;
  message_count: number;
  last_message_at: string;
  first_message_at: string;
  last_intent: string | null;
}

// ─── Store ────────────────────────────────────────────────────────────────────

interface CloudVisorQState {
  // Panel open/size state
  isOpen: boolean;
  width: number;
  isMaximized: boolean;
  setIsOpen: (v: boolean) => void;
  setWidth: (v: number) => void;
  setIsMaximized: (v: boolean) => void;
  toggleOpen: () => void;

  // History sidebar visibility
  showHistory: boolean;
  setShowHistory: (v: boolean) => void;

  // Sessions list (for history sidebar)
  sessions: ChatSession[];
  setSessions: (sessions: ChatSession[]) => void;

  // Currently active session_id (null = new conversation)
  activeSessionId: string | null;
  setActiveSessionId: (id: string | null) => void;

  // Currently viewed session in history (read-only view)
  viewingSessionId: string | null;
  setViewingSessionId: (id: string | null) => void;
}

function getDefaultWidth(): number {
  if (typeof window === 'undefined') return 500;
  return Math.round(window.innerWidth * 0.5);
}

export const useCloudVisorQStore = create<CloudVisorQState>()(
  persist(
    (set) => ({
      isOpen: false,
      width: getDefaultWidth(),
      isMaximized: false,
      setIsOpen: (v) => set({ isOpen: v }),
      setWidth: (v) => set({ width: v }),
      setIsMaximized: (v) => set({ isMaximized: v }),
      toggleOpen: () =>
        set((s) =>
          s.isOpen
            ? { isOpen: false }
            : { isOpen: true, width: getDefaultWidth() }
        ),

      showHistory: false,
      setShowHistory: (v) => set({ showHistory: v }),

      sessions: [],
      setSessions: (sessions) => set({ sessions }),

      activeSessionId: null,
      setActiveSessionId: (id) => set({ activeSessionId: id }),

      viewingSessionId: null,
      setViewingSessionId: (id) => set({ viewingSessionId: id }),
    }),
    {
      name: 'cloudvisor-q-storage',
      partialize: () => ({}), // don't persist anything — always fresh
      skipHydration: true,
    }
  )
);

// ─── Backward-compat export (used by old code) ────────────────────────────────
export type HistoryEntry = ChatSession;
