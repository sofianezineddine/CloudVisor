'use client';

import * as React from 'react';

// Generic string type — backward compatible
export type ModuleTab = string;

export interface TabDef {
  id: string;
  label: string;
  count?: number;
}

export interface ModuleTabBarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
  tabs?: TabDef[];
  // Legacy prop kept for backward compat
  module?: string;
}

const LEGACY_TABS: TabDef[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'findings', label: 'Findings' },
  { id: 'policies', label: 'Policies' },
  { id: 'reports', label: 'Reports' },
];

export function ModuleTabBar({ activeTab, onTabChange, tabs }: ModuleTabBarProps) {
  const resolvedTabs = tabs ?? LEGACY_TABS;
  return (
    <div
      className="mb-4 flex border-b overflow-x-auto"
      style={{ borderColor: 'var(--border-default)' }}
    >
      {resolvedTabs.map(tab => (
        <button
          key={tab.id}
          onClick={() => onTabChange(tab.id)}
          className="relative flex-shrink-0 px-4 py-2.5 text-sm transition-colors"
          style={{
            color: activeTab === tab.id ? 'var(--text-primary)' : 'var(--text-link)',
            fontWeight: activeTab === tab.id ? 700 : 400,
            borderBottom: activeTab === tab.id ? '2px solid var(--aws-orange)' : '2px solid transparent',
            marginBottom: '-1px',
            backgroundColor: 'transparent',
          }}
          onMouseEnter={e => {
            if (activeTab !== tab.id) (e.currentTarget.style.color = 'var(--text-link-hover)');
          }}
          onMouseLeave={e => {
            if (activeTab !== tab.id) (e.currentTarget.style.color = 'var(--text-link)');
          }}
        >
          {tab.label}
          {tab.count !== undefined && (
            <span
              className="ml-1.5 rounded-full px-1.5 py-0.5 text-xs font-normal"
              style={{
                backgroundColor: 'var(--bg-elevated)',
                color: 'var(--text-secondary)',
                fontSize: '11px',
              }}
            >
              {tab.count}
            </span>
          )}
        </button>
      ))}
    </div>
  );
}
