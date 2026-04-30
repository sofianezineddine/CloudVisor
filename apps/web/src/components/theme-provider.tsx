'use client';

import * as React from 'react';
import { useUserSettings } from '@/stores/user-settings';

type Theme = 'light' | 'dark';

interface ThemeContextType {
  theme: Theme;
  toggleTheme: () => void;
}

const ThemeContext = React.createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const storeTheme = useUserSettings(s => s.theme);
  const setTheme = useUserSettings(s => s.setTheme);

  // Resolve 'browser' to actual light/dark
  const resolved: Theme = storeTheme === 'browser'
    ? (typeof window !== 'undefined' && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
    : storeTheme as Theme;

  // Apply on mount and whenever theme changes
  React.useEffect(() => {
    document.documentElement.setAttribute('data-theme', resolved);
    localStorage.setItem('theme', resolved);
  }, [resolved]);

  const toggleTheme = React.useCallback(() => {
    setTheme(resolved === 'dark' ? 'light' : 'dark');
  }, [resolved, setTheme]);

  return (
    <ThemeContext.Provider value={{ theme: resolved, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = React.useContext(ThemeContext);
  if (!context) throw new Error('useTheme must be used within ThemeProvider');
  return context;
}
