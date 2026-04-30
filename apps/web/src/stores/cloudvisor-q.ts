import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface HistoryEntry {
  id: string;
  query: string;
  intent: string;
  response_preview: string;
  response: string;
  model_used: string;
  processing_ms: number;
  data_sources: string[];
  created_at: string;
}

interface CloudVisorQState {
  isOpen: boolean;
  width: number;
  isMaximized: boolean;
  setIsOpen: (isOpen: boolean) => void;
  setWidth: (width: number) => void;
  setIsMaximized: (isMaximized: boolean) => void;
  toggleOpen: () => void;

  // History sidebar
  showHistory: boolean;
  setShowHistory: (v: boolean) => void;
  historyEntries: HistoryEntry[];
  setHistoryEntries: (entries: HistoryEntry[]) => void;
  selectedHistoryId: string | null;
  setSelectedHistoryId: (id: string | null) => void;
}

// Default width = 50% of viewport, computed at runtime
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
      setIsOpen: (isOpen) => set({ isOpen }),
      setWidth: (width) => set({ width }),
      setIsMaximized: (isMaximized) => set({ isMaximized }),
      toggleOpen: () => set((state) => {
        // When opening, always reset to 50% width
        if (!state.isOpen) {
          return { isOpen: true, width: getDefaultWidth() };
        }
        return { isOpen: false };
      }),

      // History sidebar
      showHistory: false,
      setShowHistory: (v) => set({ showHistory: v }),
      historyEntries: [],
      setHistoryEntries: (entries) => set({ historyEntries: entries }),
      selectedHistoryId: null,
      setSelectedHistoryId: (id) => set({ selectedHistoryId: id }),
    }),
    {
      name: 'cloudvisor-q-storage',
      partialize: () => ({
        // Don't persist width - always open at 50% of current viewport
      }),
      skipHydration: true, // Prevent SSR hydration issues
    }
  )
);
