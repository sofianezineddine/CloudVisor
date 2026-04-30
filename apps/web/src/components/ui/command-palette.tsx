'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import {
  Search, Home, AlertTriangle, Shield, FileText, Settings,
  ChevronRight, Clock, TrendingUp,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// ─── Types ────────────────────────────────────────────────────────────────────

interface CommandItem {
  id: string;
  label: string;
  description?: string;
  icon?: React.ReactNode;
  action: () => void;
  keywords?: string[];
  group: string;
}

export interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

// ─── CommandPalette Component ─────────────────────────────────────────────────

export function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const router = useRouter();
  const [query, setQuery] = React.useState('');
  const [selectedIndex, setSelectedIndex] = React.useState(0);
  const inputRef = React.useRef<HTMLInputElement>(null);

  // Define all available commands
  const allCommands: CommandItem[] = React.useMemo(() => [
    // Pages
    {
      id: 'goto-dashboard',
      label: 'Go to Dashboard',
      description: 'Security overview',
      icon: <Home className="h-4 w-4" />,
      action: () => { router.push('/console'); onClose(); },
      keywords: ['home', 'overview'],
      group: 'Pages',
    },
    {
      id: 'goto-findings',
      label: 'Go to Findings',
      description: 'View all security findings',
      icon: <AlertTriangle className="h-4 w-4" />,
      action: () => { router.push('/findings'); onClose(); },
      keywords: ['issues', 'vulnerabilities', 'alerts'],
      group: 'Pages',
    },
    {
      id: 'goto-findings-critical',
      label: 'Open Findings — Critical',
      description: 'View critical severity findings',
      icon: <AlertTriangle className="h-4 w-4 text-[hsl(var(--critical))]" />,
      action: () => { router.push('/findings?severity=CRITICAL'); onClose(); },
      keywords: ['critical', 'urgent', 'high priority'],
      group: 'Pages',
    },
    {
      id: 'goto-assets',
      label: 'Go to Assets',
      description: 'Cloud resource inventory',
      icon: <Shield className="h-4 w-4" />,
      action: () => { router.push('/assets'); onClose(); },
      keywords: ['resources', 'inventory', 'cloud'],
      group: 'Pages',
    },
    {
      id: 'goto-compliance',
      label: 'Go to Compliance',
      description: 'Compliance frameworks',
      icon: <FileText className="h-4 w-4" />,
      action: () => { router.push('/compliance'); onClose(); },
      keywords: ['frameworks', 'soc2', 'cis', 'audit'],
      group: 'Pages',
    },
    {
      id: 'goto-settings',
      label: 'Go to Settings',
      description: 'Cloud accounts & configuration',
      icon: <Settings className="h-4 w-4" />,
      action: () => { router.push('/settings'); onClose(); },
      keywords: ['config', 'accounts', 'connectors'],
      group: 'Pages',
    },
    {
      id: 'goto-cspm',
      label: 'Go to CSPM',
      description: 'Cloud Security Posture Management',
      icon: <Shield className="h-4 w-4" />,
      action: () => { router.push('/cspm'); onClose(); },
      keywords: ['posture', 'misconfig'],
      group: 'Modules',
    },
    {
      id: 'goto-cdr',
      label: 'Go to CDR',
      description: 'Cloud Detection & Response',
      icon: <TrendingUp className="h-4 w-4" />,
      action: () => { router.push('/cdr'); onClose(); },
      keywords: ['detection', 'incidents', 'threats'],
      group: 'Modules',
    },
    // Actions
    {
      id: 'action-refresh',
      label: 'Refresh current page',
      description: 'Reload data',
      icon: <Clock className="h-4 w-4" />,
      action: () => { window.location.reload(); },
      keywords: ['reload', 'update'],
      group: 'Actions',
    },
  ], [router, onClose]);

  // Filter commands based on query
  const filteredCommands = React.useMemo(() => {
    if (!query.trim()) return allCommands;
    const q = query.toLowerCase();
    return allCommands.filter(cmd =>
      cmd.label.toLowerCase().includes(q) ||
      cmd.description?.toLowerCase().includes(q) ||
      cmd.keywords?.some(k => k.includes(q))
    );
  }, [query, allCommands]);

  // Group filtered commands
  const groupedCommands = React.useMemo(() => {
    const groups: Record<string, CommandItem[]> = {};
    filteredCommands.forEach(cmd => {
      if (!groups[cmd.group]) groups[cmd.group] = [];
      groups[cmd.group].push(cmd);
    });
    return groups;
  }, [filteredCommands]);

  // Reset selection when filtered commands change
  React.useEffect(() => {
    setSelectedIndex(0);
  }, [filteredCommands]);

  // Keyboard navigation
  React.useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex(i => Math.min(i + 1, filteredCommands.length - 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex(i => Math.max(i - 1, 0));
      } else if (e.key === 'Enter') {
        e.preventDefault();
        const cmd = filteredCommands[selectedIndex];
        if (cmd) cmd.action();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose, filteredCommands, selectedIndex]);

  // Focus input when opened
  React.useEffect(() => {
    if (isOpen) {
      inputRef.current?.focus();
      setQuery('');
      setSelectedIndex(0);
    }
  }, [isOpen]);

  // Prevent body scroll
  React.useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Command Palette */}
      <div className="fixed left-1/2 top-[20vh] z-50 w-full max-w-2xl -translate-x-1/2 px-4">
        <div className="overflow-hidden rounded-xl border border-[hsl(var(--border-strong))] bg-[hsl(var(--bg-surface))] shadow-2xl">
          {/* Search Input */}
          <div className="flex items-center border-b border-[hsl(var(--border-default))] px-4">
            <Search className="h-5 w-5 text-[hsl(var(--text-tertiary))]" />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search findings, assets, rules..."
              className="flex-1 bg-transparent px-4 py-4 text-sm text-[hsl(var(--text-primary))] placeholder-[hsl(var(--text-tertiary))] focus:outline-none"
            />
            <kbd className="hidden sm:inline-block rounded border border-[hsl(var(--border-default))] bg-[hsl(var(--bg-elevated))] px-2 py-1 text-xs text-[hsl(var(--text-tertiary))]">
              ESC
            </kbd>
          </div>

          {/* Results */}
          <div className="max-h-[60vh] overflow-y-auto p-2">
            {filteredCommands.length === 0 ? (
              <div className="py-12 text-center">
                <p className="text-sm text-[hsl(var(--text-tertiary))]">
                  No results found for &quot;{query}&quot;
                </p>
              </div>
            ) : (
              Object.entries(groupedCommands).map(([group, commands]) => (
                <div key={group} className="mb-3 last:mb-0">
                  <div className="mb-1 px-3 py-1 text-xs font-medium uppercase tracking-wider text-[hsl(var(--text-tertiary))]">
                    {group}
                  </div>
                  {commands.map((cmd, idx) => {
                    const globalIndex = filteredCommands.indexOf(cmd);
                    const isSelected = globalIndex === selectedIndex;
                    return (
                      <button
                        key={cmd.id}
                        onClick={cmd.action}
                        onMouseEnter={() => setSelectedIndex(globalIndex)}
                        className={cn(
                          'flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-left transition-colors',
                          isSelected
                            ? 'bg-[hsl(var(--accent))] text-white'
                            : 'text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--bg-elevated))]'
                        )}
                      >
                        <div className={cn(
                          'flex-shrink-0',
                          isSelected ? 'text-white' : 'text-[hsl(var(--text-tertiary))]'
                        )}>
                          {cmd.icon}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className={cn(
                            'text-sm font-medium truncate',
                            isSelected ? 'text-white' : 'text-[hsl(var(--text-primary))]'
                          )}>
                            {cmd.label}
                          </div>
                          {cmd.description && (
                            <div className={cn(
                              'text-xs truncate',
                              isSelected ? 'text-white/70' : 'text-[hsl(var(--text-tertiary))]'
                            )}>
                              {cmd.description}
                            </div>
                          )}
                        </div>
                        <ChevronRight className={cn(
                          'h-4 w-4 flex-shrink-0',
                          isSelected ? 'text-white/70' : 'text-[hsl(var(--text-tertiary))]'
                        )} />
                      </button>
                    );
                  })}
                </div>
              ))
            )}
          </div>

          {/* Footer hint */}
          <div className="border-t border-[hsl(var(--border-default))] px-4 py-2 text-xs text-[hsl(var(--text-tertiary))]">
            <span className="hidden sm:inline">
              Navigate with <kbd className="rounded bg-[hsl(var(--bg-elevated))] px-1.5 py-0.5">↑</kbd>{' '}
              <kbd className="rounded bg-[hsl(var(--bg-elevated))] px-1.5 py-0.5">↓</kbd> · Select with{' '}
              <kbd className="rounded bg-[hsl(var(--bg-elevated))] px-1.5 py-0.5">↵</kbd>
            </span>
          </div>
        </div>
      </div>
    </>
  );
}

