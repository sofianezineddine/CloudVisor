'use client';

import * as React from 'react';
import { Sun, Moon } from 'lucide-react';
import { useTheme } from '@/components/theme-provider';
import { cn } from '@/lib/utils';

export function ThemeToggle({ className }: { className?: string }) {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      onClick={toggleTheme}
      aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
      className={cn(
        'flex h-8 w-8 items-center justify-center rounded-md transition-colors',
        'text-[hsl(var(--text-on-sidebar))] hover:bg-[hsl(var(--bg-sidebar-hover))] hover:text-white',
        className
      )}
    >
      {theme === 'dark' ? (
        <Sun className="h-4 w-4" strokeWidth={1.5} />
      ) : (
        <Moon className="h-4 w-4" strokeWidth={1.5} />
      )}
    </button>
  );
}
