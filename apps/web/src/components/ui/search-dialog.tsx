'use client';

import * as React from 'react';
import { Search, X } from 'lucide-react';
import { SeverityBadge } from './severity-badge';

interface SearchDialogProps {
  open: boolean;
  onClose: () => void;
}

export function SearchDialog({ open, onClose }: SearchDialogProps) {
  const [query, setQuery] = React.useState('');

  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    if (open) {
      document.addEventListener('keydown', handleKeyDown);
      return () => document.removeEventListener('keydown', handleKeyDown);
    }
  }, [open, onClose]);

  if (!open) return null;

  const mockResults = [
    { type: 'Finding', title: 'S3 bucket publicly accessible', severity: 'critical', path: '/findings' },
    { type: 'Asset', title: 'prod-database-instance', severity: 'high', path: '/assets' },
    { type: 'Finding', title: 'Unencrypted EBS volume', severity: 'medium', path: '/findings' },
    { type: 'Asset', title: 'vpc-prod-us-east-1', severity: 'low', path: '/assets' },
  ].filter(item => 
    query === '' || 
    item.title.toLowerCase().includes(query.toLowerCase()) ||
    item.type.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[10vh] bg-black/50 backdrop-blur-sm">
      <div className="w-full max-w-2xl bg-[hsl(var(--bg-surface))] rounded-lg shadow-2xl border border-[hsl(var(--border-default))]">
        {/* Search Input */}
        <div className="flex items-center gap-3 p-4 border-b border-[hsl(var(--border-default))]">
          <Search className="h-5 w-5 text-[hsl(var(--text-tertiary))]" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search assets, findings, rules..."
            className="flex-1 bg-transparent border-none outline-none text-[hsl(var(--text-primary))] placeholder:text-[hsl(var(--text-tertiary))]"
            autoFocus
          />
          <button
            onClick={onClose}
            className="p-1 hover:bg-[hsl(var(--bg-elevated))] rounded"
          >
            <X className="h-4 w-4 text-[hsl(var(--text-tertiary))]" />
          </button>
        </div>

        {/* Results */}
        <div className="max-h-[60vh] overflow-y-auto p-2">
          {mockResults.length === 0 ? (
            <div className="p-8 text-center text-[hsl(var(--text-secondary))]">
              {query === '' ? 'Start typing to search...' : 'No results found'}
            </div>
          ) : (
            <div className="space-y-1">
              {mockResults.map((result, idx) => (
                <a
                  key={idx}
                  href={result.path}
                  className="flex items-center justify-between p-3 rounded-lg hover:bg-[hsl(var(--bg-elevated))] transition-colors"
                  onClick={onClose}
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs text-[hsl(var(--text-secondary))]">{result.type}</span>
                      <SeverityBadge severity={result.severity as any} size="sm" />
                    </div>
                    <div className="text-sm font-medium text-[hsl(var(--text-primary))]">
                      {result.title}
                    </div>
                  </div>
                </a>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-3 border-t border-[hsl(var(--border-default))] text-xs text-[hsl(var(--text-secondary))]">
          <div className="flex gap-4">
            <span>↑↓ Navigate</span>
            <span>↵ Select</span>
            <span>ESC Close</span>
          </div>
        </div>
      </div>
    </div>
  );
}
