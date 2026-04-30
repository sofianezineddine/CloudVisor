'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  X, Send, Plus, Maximize2, Minimize2,
  Sparkles, Clock, Copy, ThumbsUp, ThumbsDown, RefreshCw, AlertCircle,
} from 'lucide-react';
import { useCloudVisorQStore, HistoryEntry } from '@/stores/cloudvisor-q';
import { useScopeStore } from '@/stores/scope';
import { usePathname } from 'next/navigation';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { CloudVisorQHistory } from './cloudvisor-q-history';

// ─── History helpers ──────────────────────────────────────────────────────────
const COPILOT_BASE_PANEL = process.env.NEXT_PUBLIC_COPILOT_URL || 'http://localhost:8010';

function getPanelAuthHeaders(): Record<string, string> {
  const token =
    typeof window !== 'undefined'
      ? localStorage.getItem('access_token') ?? 'dev-token'
      : 'dev-token';
  return { Authorization: `Bearer ${token}` };
}

function formatPanelTimeAgo(dateStr: string): string {
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
}

const PANEL_INTENT_COLORS: Record<string, string> = {
  POSTURE: '#3b82f6',
  FINDINGS: '#ef4444',
  COMPLIANCE: '#8b5cf6',
  ASSETS: '#10b981',
  INCIDENTS: '#f59e0b',
  GENERAL: '#6b7280',
};

function panelIntentColor(intent: string): string {
  return PANEL_INTENT_COLORS[intent?.toUpperCase()] ?? '#6b7280';
}

// ─── Types ────────────────────────────────────────────────────────────────────
interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  intent?: string;
  citations?: Citation[];
  suggestedActions?: SuggestedAction[];
  processing?: boolean;
}

interface Citation {
  source: string;
  reference: string;
  claim: string;
}

interface SuggestedAction {
  label: string;
  action: 'navigate' | 'remediation' | 'query';
  target?: string;
  finding_id?: string;
  query?: string;
}

interface CloudVisorQPanelProps {
  // No props needed - uses global store
}

// ─── Constants ────────────────────────────────────────────────────────────────
const MIN_WIDTH_PERCENTAGE = 50;
const MAX_WIDTH_PERCENTAGE = 95;
const FULLSCREEN_THRESHOLD = 90;

function getMinWidth(): number {
  if (typeof window === 'undefined') return 420;
  return Math.round((window.innerWidth * MIN_WIDTH_PERCENTAGE) / 100);
}

const EXAMPLE_QUERIES = [
  {
    title: 'Which production resources have critical findings and are internet-exposed?',
    subtitle: 'Analyze security posture for high-risk production assets.',
    badge: 'Q&A',
  },
  {
    title: 'How did my security posture change this month? Explain why.',
    subtitle: 'Analyze posture score changes with root cause insights.',
    badge: 'Q&A',
  },
  {
    title: 'Do I have over-privileged IAM roles in production?',
    subtitle: 'Identify excessive permissions to reduce attack surface.',
    badge: 'Q&A',
  },
  {
    title: 'List all public S3 buckets with sensitive data',
    subtitle: 'Show publicly accessible storage resources containing PII/PHI.',
    badge: 'Table',
  },
];

// ─── Message Bubble Component ─────────────────────────────────────────────────
function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user';

  if (message.processing) {
    return (
      <div className="flex items-start gap-3">
        <div
          className="flex h-8 w-8 items-center justify-center rounded-full flex-shrink-0"
          style={{ backgroundColor: 'rgba(255,153,0,0.1)' }}
        >
          <Sparkles className="h-4 w-4" style={{ color: '#ff9900' }} />
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <div className="flex gap-1">
              <span className="h-2 w-2 rounded-full bg-current animate-pulse" style={{ color: 'var(--text-tertiary)', animationDelay: '0ms' }} />
              <span className="h-2 w-2 rounded-full bg-current animate-pulse" style={{ color: 'var(--text-tertiary)', animationDelay: '150ms' }} />
              <span className="h-2 w-2 rounded-full bg-current animate-pulse" style={{ color: 'var(--text-tertiary)', animationDelay: '300ms' }} />
            </div>
            <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
              Thinking...
            </span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`flex items-start gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      <div
        className="flex h-8 w-8 items-center justify-center rounded-full flex-shrink-0"
        style={{
          backgroundColor: isUser ? 'var(--accent-dim)' : 'rgba(255,153,0,0.1)',
        }}
      >
        {isUser ? (
          <span className="text-xs font-semibold" style={{ color: 'var(--accent)' }}>
            U
          </span>
        ) : (
          <Sparkles className="h-4 w-4" style={{ color: '#ff9900' }} />
        )}
      </div>

      <div className={`flex-1 ${isUser ? 'text-right' : ''}`}>
        <div
          className={`inline-block text-left px-4 py-2 rounded-lg ${isUser ? 'max-w-[85%]' : 'w-full'}`}
          style={{
            backgroundColor: isUser ? 'var(--bg-elevated)' : 'transparent',
          }}
        >
          <div 
            className="text-sm prose prose-sm dark:prose-invert max-w-none markdown-content" 
            style={{ color: 'var(--text-primary)' }}
          >
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </ReactMarkdown>
          </div>

          {!isUser && message.intent && (
            <div className="mt-2">
              <span
                className="text-xs px-2 py-0.5 rounded"
                style={{
                  backgroundColor: 'var(--accent-dim)',
                  color: 'var(--accent)',
                }}
              >
                {message.intent}
              </span>
            </div>
          )}
        </div>

        <div className="mt-1 text-xs" style={{ color: 'var(--text-tertiary)' }}>
          {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </div>
      </div>
    </div>
  );
}

// ─── CloudVisor Q Panel Component ─────────────────────────────────────────────
export function CloudVisorQPanel({}: CloudVisorQPanelProps) {
  const isOpen = useCloudVisorQStore((state) => state.isOpen);
  const width = useCloudVisorQStore((state) => state.width);
  const isMaximized = useCloudVisorQStore((state) => state.isMaximized);
  const setIsOpen = useCloudVisorQStore((state) => state.setIsOpen);
  const setWidth = useCloudVisorQStore((state) => state.setWidth);
  const setIsMaximized = useCloudVisorQStore((state) => state.setIsMaximized);
  const showHistory = useCloudVisorQStore((state) => state.showHistory);
  const setShowHistory = useCloudVisorQStore((state) => state.setShowHistory);

  const pathname = usePathname();
  const scopeMode = useScopeStore((s) => s.mode);
  const scopeProvider = useScopeStore((s) => s.provider);
  const scopeLabel = useScopeStore((s) => s.label);
  const scopeAccountIds = useScopeStore((s) => s.accountIds);
  const scopeAccounts = useScopeStore((s) => s.accounts);

  const [isResizing, setIsResizing] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);

  const panelRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);

  const onClose = useCallback(() => {
    setIsMaximized(false);
    setIsOpen(false);
  }, [setIsOpen, setIsMaximized]);

  useEffect(() => {
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight;
    }
  }, [messages]);

  useEffect(() => {
    if (isOpen && inputRef.current) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isOpen]);

  useEffect(() => {
    const handleResize = () => {
      if (!isOpen) return;
      const maxWidth = (window.innerWidth * MAX_WIDTH_PERCENTAGE) / 100;
      if (width > maxWidth) {
        setWidth(maxWidth);
      }
      const widthPercentage = (width / window.innerWidth) * 100;
      if (widthPercentage >= FULLSCREEN_THRESHOLD && !isMaximized) {
        setIsMaximized(true);
      } else if (widthPercentage < FULLSCREEN_THRESHOLD && isMaximized) {
        setIsMaximized(false);
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [isOpen, width, isMaximized, setWidth, setIsMaximized]);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
  }, []);

  useEffect(() => {
    if (!isResizing) return;

    const handleMouseMove = (e: MouseEvent) => {
      if (!panelRef.current) return;
      const maxWidth = (window.innerWidth * MAX_WIDTH_PERCENTAGE) / 100;
      const newWidth = Math.min(Math.max(e.clientX, getMinWidth()), maxWidth);
      setWidth(newWidth);
      const widthPercentage = (newWidth / window.innerWidth) * 100;
      if (widthPercentage >= FULLSCREEN_THRESHOLD && !isMaximized) {
        setIsMaximized(true);
      } else if (widthPercentage < FULLSCREEN_THRESHOLD && isMaximized) {
        setIsMaximized(false);
      }
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing, isMaximized, setWidth, setIsMaximized]);

  const toggleMaximize = useCallback(() => {
    if (isMaximized) {
      setWidth(getMinWidth());
      setIsMaximized(false);
    } else {
      setIsMaximized(true);
    }
  }, [isMaximized, setWidth, setIsMaximized]);

  const handleSendMessage = useCallback(async () => {
    if (!inputValue.trim() || isProcessing) return;

    const userMessage: Message = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: inputValue.trim(),
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsProcessing(true);

    const processingMessage: Message = {
      id: `msg-${Date.now()}-processing`,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      processing: true,
    };
    setMessages(prev => [...prev, processingMessage]);

    try {
      const API_BASE = process.env.NEXT_PUBLIC_COPILOT_URL || process.env.NEXT_PUBLIC_API_GATEWAY_URL || 'http://localhost:8010';
      const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;

      let orgId: string | null = null;
      if (token) {
        try {
          const payload = JSON.parse(atob(token.split('.')[1]));
          orgId = payload?.organization_id ?? payload?.org_id ?? null;
        } catch {}
      }
      if (!orgId) {
        try {
          const userRaw = typeof window !== 'undefined' ? localStorage.getItem('cloudvisor-user') : null;
          if (userRaw) {
            const userData = JSON.parse(userRaw);
            orgId = userData?.organization_id ?? null;
          }
        } catch {}
      }
      if (!orgId) {
        throw new Error('Unable to determine your organization. Please log in again.');
      }

      const pageMap: Record<string, string> = {
        '/console': 'Home Console',
        '/dashboard': 'Dashboard',
        '/findings': 'Findings',
        '/assets': 'Assets',
        '/cspm': 'Cloud Security Posture (CSPM)',
        '/cwpp': 'Workload Protection (CWPP)',
        '/ciem': 'Identity & Access (CIEM)',
        '/kspm': 'Kubernetes Security (KSPM)',
        '/dspm': 'Data Security (DSPM)',
        '/cdr': 'Detection & Response (CDR)',
        '/cicd': 'CI/CD Security',
        '/aiops': 'AIOps',
        '/compliance': 'Compliance',
        '/incidents': 'Incidents',
        '/risk-map': 'Risk Map',
        '/settings': 'Settings',
        '/profile': 'Profile',
        '/services': 'Services',
      };
      const currentPage = Object.entries(pageMap).find(([route]) =>
        pathname === route || pathname.startsWith(route + '/')
      )?.[1] ?? pathname;

      const scopedAccountDetails = scopeAccounts
        .filter(a => scopeAccountIds.includes(a.account_id))
        .map(a => ({
          account_id: a.account_id,
          provider: a.provider,
          name: a.name ?? a.account_id,
          resource_count: a.resource_count ?? 0,
          critical_count: a.critical_count ?? 0,
          posture_score: a.posture_score ?? 0,
        }));

      const context = {
        current_page: currentPage,
        current_path: pathname,
        scope: {
          mode: scopeMode,
          provider: scopeProvider,
          label: scopeLabel,
          account_ids: scopeAccountIds,
          accounts: scopedAccountDetails,
        },
        all_accounts: scopeAccounts.map(a => ({
          account_id: a.account_id,
          provider: a.provider,
          name: a.name ?? a.account_id,
          resource_count: a.resource_count ?? 0,
          critical_count: a.critical_count ?? 0,
          posture_score: a.posture_score ?? 0,
        })),
      };

      const conversationHistory = messages
        .filter(m => !m.processing)
        .map(m => ({
          role: m.role,
          content: m.content,
        }));

      const response = await fetch(`${API_BASE}/v1/copilot/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Org-ID': orgId,
          ...(token ? { Authorization: `Bearer ${token}` } : { Authorization: 'Bearer dev-token' }),
        },
        body: JSON.stringify({
          query: userMessage.content,
          stream: false,
          ui_context: context,
          conversation_history: conversationHistory,
        }),
      });

      if (!response.ok) {
        const errText = await response.text().catch(() => '');
        console.error(`API Error ${response.status}:`, errText);
        throw new Error(`CloudVisor Q returned ${response.status}: ${errText}`);
      }

      const data = await response.json();

      setMessages(prev => {
        const filtered = prev.filter(m => m.id !== processingMessage.id);
        const assistantMessage: Message = {
          id: data.query_id || `msg-${Date.now()}-response`,
          role: 'assistant',
          content: data.answer || 'I apologize, but I was unable to generate a response.',
          timestamp: new Date(),
          intent: data.intent,
          citations: data.citations,
          suggestedActions: data.suggested_actions,
        };
        return [...filtered, assistantMessage];
      });
    } catch (error) {
      console.error('Error querying CloudVisor Q:', error);
      setMessages(prev => {
        const filtered = prev.filter(m => m.id !== processingMessage.id);
        const errorMessage: Message = {
          id: `msg-${Date.now()}-error`,
          role: 'assistant',
          content: `Error: ${error instanceof Error ? error.message : 'Unknown error occurred'}. Please check the browser console for details.`,
          timestamp: new Date(),
        };
        return [...filtered, errorMessage];
      });
    } finally {
      setIsProcessing(false);
    }
  }, [inputValue, isProcessing, messages, pathname, scopeMode, scopeProvider, scopeLabel, scopeAccountIds, scopeAccounts]);

  const handleExampleClick = useCallback((query: string) => {
    setInputValue(query);
    inputRef.current?.focus();
  }, []);

  const handleNewConversation = useCallback(() => {
    setMessages([]);
    setInputValue('');
    inputRef.current?.focus();
  }, []);

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  }, [handleSendMessage]);

  if (!isOpen) return null;

  const panelWidth = isMaximized ? '100vw' : `${width}px`;

  return (
    <div
      ref={panelRef}
      className="flex h-full"
      style={{
        width: panelWidth,
        backgroundColor: 'var(--bg-surface)',
        borderRight: '1px solid var(--border-default)',
        transition: isResizing ? 'none' : 'width 0.2s ease-out',
      }}
    >
      {/* History Sidebar */}
      {showHistory && (
        <div
          className="flex-shrink-0"
          style={{
            width: '280px',
            borderRight: '1px solid var(--border-default)',
          }}
        >
          <CloudVisorQHistory
            onClose={() => setShowHistory(false)}
            onSelectSession={() => {
              // Session selected, can add logic here if needed
            }}
          />
        </div>
      )}

      {/* Main Chat Area */}
      <div className="flex flex-col h-full flex-1">
      {/* Header */}
      <div
        className="flex items-center justify-between px-3 py-2 border-b flex-shrink-0"
        style={{
          height: '44px',
          backgroundColor: 'var(--bg-surface)',
          borderColor: 'var(--border-default)',
        }}
      >
        <div className="flex items-center gap-2">
          <div
            className="flex h-6 w-6 items-center justify-center rounded-full flex-shrink-0"
            style={{ backgroundColor: '#ff9900', color: '#000' }}
          >
            <span className="text-xs font-bold">Q</span>
          </div>
          <span className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
            CloudVisor Q
          </span>
        </div>

        <div className="flex items-center gap-1">
          <button
            onClick={() => setShowHistory(!showHistory)}
            className="flex h-7 w-7 items-center justify-center rounded transition-colors"
            style={{
              color: showHistory ? 'var(--accent)' : 'var(--text-secondary)',
              backgroundColor: showHistory ? 'var(--accent-dim)' : 'transparent',
            }}
            onMouseEnter={e => { if (!showHistory) e.currentTarget.style.backgroundColor = 'var(--bg-elevated)'; }}
            onMouseLeave={e => { if (!showHistory) e.currentTarget.style.backgroundColor = 'transparent'; }}
            title="Toggle history"
          >
            <Clock className="h-4 w-4" />
          </button>

          <button
            onClick={handleNewConversation}
            className="flex h-7 w-7 items-center justify-center rounded transition-colors"
            style={{ color: 'var(--text-secondary)' }}
            onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
            onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
            title="New conversation"
          >
            <Plus className="h-4 w-4" />
          </button>

          <button
            onClick={toggleMaximize}
            className="flex h-7 w-7 items-center justify-center rounded transition-colors"
            style={{ color: 'var(--text-secondary)' }}
            onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
            onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
            title={isMaximized ? 'Restore' : 'Maximize'}
          >
            {isMaximized ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
          </button>

          <button
            onClick={onClose}
            className="flex h-7 w-7 items-center justify-center rounded transition-colors"
            style={{ color: 'var(--text-secondary)' }}
            onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
            onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
            title="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Messages Area */}
      <div ref={messagesContainerRef} className="flex-1 overflow-y-auto px-4 py-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full">
            <div className="w-full max-w-sm space-y-4">
              <div className="text-center">
                <div
                  className="inline-flex h-12 w-12 items-center justify-center rounded-full mb-3"
                  style={{ backgroundColor: 'rgba(255,153,0,0.1)' }}
                >
                  <Sparkles className="h-6 w-6" style={{ color: '#ff9900' }} />
                </div>
                <h2 className="text-lg font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>
                  How can I help you today?
                </h2>
                <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                  Ask me about your cloud security posture, findings, compliance, or threats.
                </p>
              </div>

              <div className="space-y-2">
                {EXAMPLE_QUERIES.map((example, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleExampleClick(example.title)}
                    className="w-full text-left p-3 rounded border transition-colors"
                    style={{
                      backgroundColor: 'var(--bg-surface)',
                      borderColor: 'var(--border-default)',
                    }}
                    onMouseEnter={e => {
                      e.currentTarget.style.backgroundColor = 'var(--bg-elevated)';
                      e.currentTarget.style.borderColor = 'var(--accent)';
                    }}
                    onMouseLeave={e => {
                      e.currentTarget.style.backgroundColor = 'var(--bg-surface)';
                      e.currentTarget.style.borderColor = 'var(--border-default)';
                    }}
                  >
                    <div className="text-sm font-medium mb-1" style={{ color: 'var(--text-primary)' }}>
                      {example.title}
                    </div>
                    <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                      {example.subtitle}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
          </div>
        )}
      </div>

      {/* Input Area */}
      <div
        className="border-t px-3 py-3 flex-shrink-0"
        style={{ borderColor: 'var(--border-default)' }}
      >
        <div className="flex items-end gap-2">
          <textarea
            ref={inputRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask CloudVisor Q..."
            className="flex-1 px-3 py-2 rounded border resize-none focus:outline-none focus:ring-2 focus:ring-offset-0"
            style={{
              backgroundColor: 'var(--bg-surface)',
              borderColor: 'var(--border-default)',
              color: 'var(--text-primary)',
              minHeight: '40px',
              maxHeight: '100px',
            }}
            rows={1}
            disabled={isProcessing}
          />
          <button
            onClick={handleSendMessage}
            disabled={!inputValue.trim() || isProcessing}
            className="flex h-10 w-10 items-center justify-center rounded transition-colors flex-shrink-0"
            style={{
              backgroundColor: inputValue.trim() && !isProcessing ? '#ff9900' : 'var(--bg-elevated)',
              color: inputValue.trim() && !isProcessing ? '#000' : 'var(--text-tertiary)',
              cursor: inputValue.trim() && !isProcessing ? 'pointer' : 'not-allowed',
            }}
            title="Send message"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Footer */}
      <div
        className="border-t px-3 py-2 flex-shrink-0 text-xs"
        style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-elevated)', color: 'var(--text-tertiary)' }}
      >
        <div className="flex items-center justify-between">
          <span>© 2026 CloudVisor</span>
          <a href="#" style={{ color: 'var(--text-link)', textDecoration: 'none' }}>
            Feedback
          </a>
        </div>
      </div>

      {/* Resize handle */}
      {!isMaximized && (
        <div
          className="absolute top-0 right-0 bottom-0 w-1 cursor-ew-resize hover:bg-accent transition-colors z-10"
          onMouseDown={handleMouseDown}
          style={{
            backgroundColor: isResizing ? 'var(--accent)' : 'transparent',
          }}
        />
      )}
      </div>
    </div>
  );
}
