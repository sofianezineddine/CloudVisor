/**
 * User Settings Store — persists ALL user preferences to localStorage
 *
 * Covers:
 *  - theme (light | dark)
 *  - language
 *  - console widget order
 *  - console removed widgets
 *  - console widget heights
 *  - content density (comfortable | compact)
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type Theme = 'light' | 'dark' | 'browser';
export type Density = 'comfortable' | 'compact';

export const DEFAULT_WIDGET_ORDER = [
  'recently-visited',
  'cloudvisor-health',
  'cost-usage',
  'welcome',
  'solutions',
  'explore',
  'announcements',
];

export interface UserSettingsState {
  theme: Theme;
  language: string;
  density: Density;
  // Console widget layout
  widgetOrder: string[];
  removedWidgets: string[];
  widgetHeights: Record<string, number>;
}

export interface UserSettingsActions {
  setTheme: (theme: Theme) => void;
  setLanguage: (lang: string) => void;
  setDensity: (density: Density) => void;
  setWidgetOrder: (order: string[]) => void;
  removeWidget: (id: string) => void;
  restoreWidget: (id: string) => void;
  setWidgetHeight: (id: string, height: number) => void;
  resetLayout: () => void;
}

export const useUserSettings = create<UserSettingsState & UserSettingsActions>()(
  persist(
    (set, get) => ({
      // ── Defaults ──────────────────────────────────────────────────────────
      theme: 'light',
      language: 'browser',
      density: 'comfortable',
      widgetOrder: DEFAULT_WIDGET_ORDER,
      removedWidgets: [],
      widgetHeights: {},

      // ── Actions ───────────────────────────────────────────────────────────
      setTheme: (theme) => {
        set({ theme });
        // Apply immediately to DOM
        const resolved = theme === 'browser'
          ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
          : theme;
        document.documentElement.setAttribute('data-theme', resolved);
        // Keep legacy key in sync for ThemeProvider
        localStorage.setItem('theme', resolved);
      },

      setLanguage: (language) => set({ language }),

      setDensity: (density) => set({ density }),

      setWidgetOrder: (widgetOrder) => set({ widgetOrder }),

      removeWidget: (id) => {
        const { removedWidgets, widgetOrder } = get();
        set({
          removedWidgets: [...removedWidgets, id],
          widgetOrder: widgetOrder.filter(w => w !== id),
        });
      },

      restoreWidget: (id) => {
        const { removedWidgets, widgetOrder } = get();
        set({
          removedWidgets: removedWidgets.filter(w => w !== id),
          widgetOrder: DEFAULT_WIDGET_ORDER.filter(
            w => w === id || widgetOrder.includes(w)
          ),
        });
      },

      setWidgetHeight: (id, height) => {
        set(state => ({
          widgetHeights: { ...state.widgetHeights, [id]: height },
        }));
      },

      resetLayout: () => {
        set({
          widgetOrder: DEFAULT_WIDGET_ORDER,
          removedWidgets: [],
          widgetHeights: {},
        });
      },
    }),
    {
      name: 'cloudvisor-user-settings',
      // Only persist these keys
      partialize: (state) => ({
        theme: state.theme,
        language: state.language,
        density: state.density,
        widgetOrder: state.widgetOrder,
        removedWidgets: state.removedWidgets,
        widgetHeights: state.widgetHeights,
      }),
      // After rehydration, re-apply theme to DOM
      onRehydrateStorage: () => (state) => {
        if (!state) return;
        if (typeof window === 'undefined') return;
        const resolved = state.theme === 'browser'
          ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
          : state.theme;
        document.documentElement.setAttribute('data-theme', resolved);
      },
    }
  )
);
