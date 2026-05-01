'use client';

import React, { useEffect } from 'react';
import { X, Trash2 } from 'lucide-react';
import { useCloudVisorQStore } from '@/stores/cloudvisor-q';
import { useCopilotSessions } from '@/hooks/use-copilot-sessions';

interface CloudVisorQHistoryProps {
  onSelectSession?: (sessionId: string) => void;
  onClose?: () => void;
}

export function CloudVisorQHistory({ onSelectSession, onClose }: CloudVisorQHistoryProps) {
  const currentSessionId = useCloudVisorQStore((state) => state.currentSessionId);
  const setCurrentSessionId = useCloudVisorQStore((state) => state.setCurrentSessionId);

  const {
    sessions,
    loading,
    error,
    deleteSession,
  } = useCopilotSessions();

  const handleSelectSession = (sessionId: string) => {
    setCurrentSessionId(sessionId);
    onSelectSession?.(sessionId);
  };

  const handleDeleteSession = async (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation();
    if (confirm('Are you sure you want to delete this session?')) {
      await deleteSession(sessionId);
    }
  };

  const formatDate = (dateStr: string): string => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  return (
    <div
      className="flex flex-col h-full"
      style={{
        backgroundColor: 'var(--bg-surface)',
        borderRight: '1px solid var(--border-default)',
      }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-3 py-2 border-b flex-shrink-0"
        style={{
          height: '44px',
          backgroundColor: 'var(--bg-surface)',
          borderColor: 'var(--border-default)',
        }}
      >
        <span className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
          Chat History
        </span>
        <button
          onClick={onClose}
          className="flex h-7 w-7 items-center justify-center rounded transition-colors"
          style={{ color: 'var(--text-secondary)' }}
          onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
          onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
          title="Close history"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* New Session Button */}
      <div className="px-3 py-2 border-b flex-shrink-0" style={{ borderColor: 'var(--border-default)' }}>
        {/* Removed New Chat button as per requirements */}
      </div>

      {/* Sessions List */}
      <div className="flex-1 overflow-y-auto">
        {error && (
          <div className="px-3 py-2 text-xs" style={{ color: 'var(--error)' }}>
            Error loading sessions: {error}
          </div>
        )}

        {loading && sessions.length === 0 ? (
          <div className="px-3 py-4 text-xs text-center" style={{ color: 'var(--text-tertiary)' }}>
            Loading sessions...
          </div>
        ) : sessions.length === 0 ? (
          <div className="px-3 py-4 text-xs text-center" style={{ color: 'var(--text-tertiary)' }}>
            No chat sessions yet. Create one to get started.
          </div>
        ) : (
          <div className="space-y-1 p-2">
            {sessions.map((session) => (
              <button
                key={session.id}
                onClick={() => handleSelectSession(session.id)}
                className="w-full text-left px-3 py-2 rounded transition-colors group"
                style={{
                  backgroundColor:
                    currentSessionId === session.id
                      ? 'var(--accent-dim)'
                      : 'transparent',
                  color:
                    currentSessionId === session.id
                      ? 'var(--accent)'
                      : 'var(--text-primary)',
                }}
                onMouseEnter={(e) => {
                  if (currentSessionId !== session.id) {
                    e.currentTarget.style.backgroundColor = 'var(--bg-elevated)';
                  }
                }}
                onMouseLeave={(e) => {
                  if (currentSessionId !== session.id) {
                    e.currentTarget.style.backgroundColor = 'transparent';
                  }
                }}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium truncate">
                      {session.title}
                    </div>
                    <div
                      className="text-xs mt-0.5 truncate"
                      style={{
                        color:
                          currentSessionId === session.id
                            ? 'var(--text-secondary)'
                            : 'var(--text-tertiary)',
                      }}
                    >
                      {session.message_count} messages • {formatDate(session.created_at)}
                    </div>
                  </div>
                  <button
                    onClick={(e) => handleDeleteSession(e, session.id)}
                    className="flex h-6 w-6 items-center justify-center rounded opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0"
                    style={{
                      color: 'var(--text-tertiary)',
                      backgroundColor: 'transparent',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.backgroundColor = 'var(--error-dim)';
                      e.currentTarget.style.color = 'var(--error)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.backgroundColor = 'transparent';
                      e.currentTarget.style.color = 'var(--text-tertiary)';
                    }}
                    title="Delete session"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
