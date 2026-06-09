'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { X, Send, Plus, Maximize2, Minimize2, History, Trash2 } from 'lucide-react';
import { useCloudVisorQStore } from '@/stores/cloudvisor-q';
import { useScopeStore } from '@/stores/scope';
import { usePathname } from 'next/navigation';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useCopilotSessions } from '@/hooks/use-copilot-sessions';
import { useAuth } from '@/hooks/use-auth';

// ─── Types ────────────────────────────────────────────────────────────────────
interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  intent?: string;
  processing?: boolean;
}

interface CloudVisorQPanelProps {}

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
    title: 'How did my security posture change this month?',
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

// ─── Conversations Modal ──────────────────────────────────────────────────────
function ConversationsModal({
  onClose,
  onSelect,
}: {
  onClose: () => void;
  onSelect: (sessionId: string, title: string) => void;
}) {
  const { sessions, loading, deleteSession, loadSessions } = useCopilotSessions();
  
  // Load sessions when modal opens
  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffDays = Math.floor((now.getTime() - date.getTime()) / 86400000);
    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    if (diffDays < 7) return days[date.getDay()];
    return date.toLocaleDateString('en-US', { month: 'numeric', day: 'numeric' });
  };

  const handleDelete = async (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation();
    await deleteSession(sessionId);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}
      onClick={onClose}
    >
      <div
        className="rounded-lg shadow-2xl"
        style={{
          backgroundColor: 'var(--bg-surface)',
          border: '1px solid var(--border-default)',
          width: '480px',
          maxHeight: '70vh',
          display: 'flex',
          flexDirection: 'column',
        }}
        onClick={e => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div
          className="flex items-center justify-between px-6 py-4 border-b flex-shrink-0"
          style={{ borderColor: 'var(--border-default)' }}
        >
          <div>
            <h2 className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
              CloudVisor Q
            </h2>
            <p className="text-sm font-medium mt-0.5" style={{ color: 'var(--text-primary)' }}>
              Conversations {sessions && Array.isArray(sessions) && sessions.length > 0 && `(${sessions.length})`}
            </p>
          </div>
          <button
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center transition-colors"
            style={{ color: 'var(--text-secondary)', borderRadius: 'var(--radius-button)' }}
            onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
            onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Sessions List */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="px-6 py-8 text-center text-sm" style={{ color: 'var(--text-secondary)' }}>
              Loading conversations...
            </div>
          ) : !sessions || !Array.isArray(sessions) || sessions.length === 0 ? (
            <div className="px-6 py-8 text-center text-sm" style={{ color: 'var(--text-secondary)' }}>
              No conversations yet.
            </div>
          ) : (
            (Array.isArray(sessions) ? sessions : []).map(session => (
              <div
                key={session.id}
                className="flex items-center justify-between px-6 py-3 cursor-pointer group border-b"
                style={{ borderColor: 'var(--border-faint)' }}
                onClick={() => onSelect(session.id, session.title)}
                onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
              >
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium truncate" style={{ color: 'var(--text-link)' }}>
                    {session.title}
                  </div>
                  <div className="text-xs mt-0.5" style={{ color: 'var(--text-secondary)' }}>
                    {formatDate(session.updated_at || session.created_at)}
                  </div>
                </div>
                <button
                  onClick={e => handleDelete(e, session.id)}
                  className="flex h-7 w-7 items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0 ml-2"
                  style={{ color: 'var(--text-secondary)', borderRadius: 'var(--radius-button)' }}
                  onMouseEnter={e => {
                    e.currentTarget.style.backgroundColor = 'var(--danger-bg)';
                    e.currentTarget.style.color = 'var(--danger)';
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.backgroundColor = 'transparent';
                    e.currentTarget.style.color = 'var(--text-secondary)';
                  }}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Message Bubble ───────────────────────────────────────────────────────────
function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user';

  if (message.processing) {
    return (
      <div className="flex items-start gap-3 py-2">
        <div
          className="flex h-7 w-7 items-center justify-center rounded-full flex-shrink-0"
          style={{ backgroundColor: 'rgba(255,153,0,0.15)', border: '1px solid #ff9900' }}
        >
          <span className="text-xs font-bold" style={{ color: '#ff9900' }}>Q</span>
        </div>
        <div className="flex items-center gap-1.5 pt-1.5">
          {[0, 150, 300].map(delay => (
            <span
              key={delay}
              className="h-2 w-2 rounded-full animate-bounce"
              style={{ backgroundColor: 'var(--text-tertiary)', animationDelay: `${delay}ms` }}
            />
          ))}
        </div>
      </div>
    );
  }

  if (isUser) {
    return (
      <div className="flex justify-end py-2">
        <div
          className="max-w-[80%] px-4 py-2.5 rounded-2xl text-sm"
          style={{ backgroundColor: 'var(--btn-primary-bg)', color: '#fff' }}
        >
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-3 py-2">
      <div
        className="flex h-7 w-7 items-center justify-center rounded-full flex-shrink-0 mt-0.5"
        style={{ backgroundColor: 'rgba(255,153,0,0.15)', border: '1px solid #ff9900' }}
      >
        <span className="text-xs font-bold" style={{ color: '#ff9900' }}>Q</span>
      </div>
      <div className="flex-1 min-w-0">
        <div
          className="text-sm prose prose-sm max-w-none markdown-content"
          style={{ color: 'var(--text-primary)' }}
        >
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
        </div>
        {message.intent && (
          <span
            className="inline-block mt-1.5 text-xs px-2 py-0.5 rounded"
            style={{ backgroundColor: 'var(--accent-dim)', color: 'var(--accent)' }}
          >
            {message.intent}
          </span>
        )}
      </div>
    </div>
  );
}

// ─── CloudVisor Q Panel ───────────────────────────────────────────────────────
export function CloudVisorQPanel({}: CloudVisorQPanelProps) {
  const isOpen        = useCloudVisorQStore(s => s.isOpen);
  const width         = useCloudVisorQStore(s => s.width);
  const isMaximized   = useCloudVisorQStore(s => s.isMaximized);
  const setIsOpen     = useCloudVisorQStore(s => s.setIsOpen);
  const setWidth      = useCloudVisorQStore(s => s.setWidth);
  const setIsMaximized = useCloudVisorQStore(s => s.setIsMaximized);

  const pathname        = usePathname();
  const scopeMode       = useScopeStore(s => s.mode);
  const scopeProvider   = useScopeStore(s => s.provider);
  const scopeLabel      = useScopeStore(s => s.label);
  const scopeAccountIds = useScopeStore(s => s.accountIds);
  const scopeAccounts   = useScopeStore(s => s.accounts);

  const { user } = useAuth();

  const [messages, setMessages]             = useState<Message[]>([]);
  const [inputValue, setInputValue]         = useState('');
  const [isProcessing, setIsProcessing]     = useState(false);
  const [isResizing, setIsResizing]         = useState(false);
  const [loadingSession, setLoadingSession] = useState(false);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);

  // Refs that always reflect the latest state — avoids stale closures in handleSendMessage
  const messagesRef = useRef<Message[]>([]);
  const activeSessionIdRef = useRef<string | null>(null);
  useEffect(() => { messagesRef.current = messages; }, [messages]);
  useEffect(() => { activeSessionIdRef.current = activeSessionId; }, [activeSessionId]);

  const showConversations    = useCloudVisorQStore(s => s.showConversations);
  const setShowConversations = useCloudVisorQStore(s => s.setShowConversations);

  const { getSession, loadSessions } = useCopilotSessions();

  const panelRef  = useRef<HTMLDivElement>(null);
  const inputRef  = useRef<HTMLTextAreaElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); }, [messages]);
  useEffect(() => { if (isOpen) setTimeout(() => inputRef.current?.focus(), 100); }, [isOpen]);

  // Load sessions when panel opens
  useEffect(() => {
    if (isOpen) {
      loadSessions();
    }
  }, [isOpen, loadSessions]);

  useEffect(() => {
    const onResize = () => {
      if (!isOpen) return;
      const max = (window.innerWidth * MAX_WIDTH_PERCENTAGE) / 100;
      if (width > max) setWidth(max);
    };
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, [isOpen, width, setWidth]);

  useEffect(() => {
    if (!isResizing) return;
    const onMove = (e: MouseEvent) => {
      const max = (window.innerWidth * MAX_WIDTH_PERCENTAGE) / 100;
      const newW = Math.min(Math.max(e.clientX, getMinWidth()), max);
      setWidth(newW);
      setIsMaximized((newW / window.innerWidth) * 100 >= FULLSCREEN_THRESHOLD);
    };
    const onUp = () => setIsResizing(false);
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
    return () => { document.removeEventListener('mousemove', onMove); document.removeEventListener('mouseup', onUp); };
  }, [isResizing, setWidth, setIsMaximized]);

  const onClose = useCallback(() => { setIsMaximized(false); setIsOpen(false); }, [setIsOpen, setIsMaximized]);

  const toggleMaximize = useCallback(() => {
    if (isMaximized) { setWidth(getMinWidth()); setIsMaximized(false); }
    else setIsMaximized(true);
  }, [isMaximized, setWidth, setIsMaximized]);

  const handleNewConversation = useCallback(() => {
    setMessages([]);
    setInputValue('');
    setActiveSessionId(null);
    inputRef.current?.focus();
  }, []);

  // Load a previous session's messages when selected from history
  const handleSelectSession = useCallback(async (sessionId: string) => {
    setShowConversations(false);
    setLoadingSession(true);
    setMessages([]);
    setActiveSessionId(sessionId);

    try {
      const data = await getSession(sessionId);
      if (!data || !data.messages) return;

      // Convert backend messages to panel Message format
      const loaded: Message[] = [];
      for (const m of data.messages) {
        // Each backend message has query + response
        if (m.query) {
          loaded.push({
            id: `${m.id}-user`,
            role: 'user',
            content: m.query,
            timestamp: new Date(m.created_at),
          });
        }
        if (m.response) {
          loaded.push({
            id: `${m.id}-assistant`,
            role: 'assistant',
            content: m.response,
            timestamp: new Date(m.created_at),
            intent: m.intent,
          });
        }
      }
      setMessages(loaded);
    } catch (err) {
      console.error('Failed to load session:', err);
    } finally {
      setLoadingSession(false);
    }
  }, [getSession]);

  const handleSendMessage = useCallback(async () => {
    if (!inputValue.trim() || isProcessing) return;

    const userMsg: Message = { id: `msg-${Date.now()}`, role: 'user', content: inputValue.trim(), timestamp: new Date() };
    const procMsg: Message = { id: `msg-${Date.now()}-proc`, role: 'assistant', content: '', timestamp: new Date(), processing: true };

    setMessages(prev => [...prev, userMsg, procMsg]);
    setInputValue('');
    setIsProcessing(true);

    try {
      const GW_BASE = process.env.NEXT_PUBLIC_API_GATEWAY_URL || 'http://localhost:8080';

      // org_id comes from the authenticated user — gateway also derives it from the JWT cookie
      const orgId = user?.organization_id ?? null;
      if (!orgId) throw new Error('Unable to determine your organization. Please log in again.');

      const pageMap: Record<string, string> = {
        '/console': 'Home Console', '/aiops/dashboard': 'Dashboard', '/findings': 'Findings',
        '/assets': 'Assets', '/cspm': 'CSPM', '/cwpp': 'CWPP', '/ciem': 'CIEM',
        '/kspm': 'KSPM', '/dspm': 'DSPM', '/cdr': 'CDR', '/cicd': 'CI/CD',
        '/aiops': 'AIOps', '/compliance': 'Compliance', '/aiops/incidents': 'Incidents',
        '/risk-map': 'Risk Map', '/settings': 'Settings',
      };
      const currentPage = Object.entries(pageMap).find(([r]) => pathname === r || pathname.startsWith(r + '/'))?.[1] ?? pathname;

      const context = {
        current_page: currentPage, current_path: pathname,
        scope: {
          mode: scopeMode, provider: scopeProvider, label: scopeLabel, account_ids: scopeAccountIds,
          accounts: scopeAccounts.filter(a => scopeAccountIds.includes(a.account_id)).map(a => ({
            account_id: a.account_id, provider: a.provider, name: a.name ?? a.account_id,
            resource_count: a.resource_count ?? 0, critical_count: a.critical_count ?? 0, posture_score: a.posture_score ?? 0,
          })),
        },
        all_accounts: scopeAccounts.map(a => ({
          account_id: a.account_id, provider: a.provider, name: a.name ?? a.account_id,
          resource_count: a.resource_count ?? 0, critical_count: a.critical_count ?? 0, posture_score: a.posture_score ?? 0,
        })),
      };

      const history = messagesRef.current
        .filter(m => !m.processing)
        .map(m => ({ role: m.role, content: m.content }));

      const requestBody = JSON.stringify({
        query: userMsg.content,
        stream: false,
        ui_context: context,
        conversation_history: history,
        ...(activeSessionIdRef.current ? { session_id: activeSessionIdRef.current } : {}),
      });

      const authHeaders = {
        'Content-Type': 'application/json',
        'X-Org-ID': orgId,
      };

      // Send query through the API gateway — auth via HttpOnly cookies
      let res: Response | null = null;
      try {
        res = await fetch(`${GW_BASE}/v1/copilot/query`, {
          method: 'POST',
          headers: authHeaders,
          credentials: 'include', // Send HttpOnly auth cookies
          body: requestBody,
        });
        if (!res.ok) res = null; // fall through to direct
      } catch {
        res = null;
      }

      if (!res) {
        const API_BASE = process.env.NEXT_PUBLIC_COPILOT_URL || 'http://localhost:8010';
        res = await fetch(`${API_BASE}/v1/copilot/query`, {
          method: 'POST',
          headers: authHeaders,
          credentials: 'include',
          body: requestBody,
        });
      }

      if (!res.ok) { const err = await res.text().catch(() => ''); throw new Error(`CloudVisor Q returned ${res.status}: ${err}`); }

      const raw = await res.json();

      // Unwrap gateway envelope: { data: { answer, session_id, ... }, meta: {} }
      // or direct copilot response: { answer, session_id, ... }
      const data = raw?.data ?? raw;

      // Track the session_id returned by the backend (auto-created on first message)
      if (data.session_id && !activeSessionIdRef.current) {
        setActiveSessionId(data.session_id);
      }

      setMessages(prev => {
        const filtered = prev.filter(m => m.id !== procMsg.id);
        return [...filtered, {
          id: data.query_id || `msg-${Date.now()}-res`,
          role: 'assistant' as const,
          content: data.answer || 'I was unable to generate a response.',
          timestamp: new Date(),
          intent: data.intent,
        }];
      });
    } catch (err) {
      setMessages(prev => {
        const filtered = prev.filter(m => m.id !== procMsg.id);
        return [...filtered, {
          id: `msg-${Date.now()}-err`,
          role: 'assistant' as const,
          content: `Error: ${err instanceof Error ? err.message : 'Unknown error occurred'}.`,
          timestamp: new Date(),
        }];
      });
    } finally {
      setIsProcessing(false);
    }
  }, [inputValue, isProcessing, pathname, scopeMode, scopeProvider, scopeLabel, scopeAccountIds, scopeAccounts, user]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSendMessage(); }
  }, [handleSendMessage]);

  if (!isOpen) return null;

  const panelWidth = isMaximized ? '100vw' : `${width}px`;
  const hasMessages = messages.length > 0;

  // Shared icon button style
  const iconBtn = {
    base: { color: 'var(--text-secondary)', backgroundColor: 'transparent' } as React.CSSProperties,
    hover: { backgroundColor: 'var(--bg-elevated)' } as React.CSSProperties,
  };

  // Shared textarea + send button style
  const InputBox = ({ rows = 2, placeholder }: { rows?: number; placeholder: string }) => (
    <div
      className="relative rounded"
      style={{ border: '1px solid var(--border-strong)', backgroundColor: 'var(--bg-surface)' }}
    >
      <textarea
        ref={inputRef}
        value={inputValue}
        onChange={e => setInputValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        className="w-full px-4 pt-3 pb-8 resize-none focus:outline-none text-sm"
        style={{
          minHeight: rows === 3 ? '80px' : '60px',
          maxHeight: '160px',
          color: 'var(--text-primary)',
          backgroundColor: 'transparent',
          borderRadius: '4px',
        }}
        rows={rows}
        disabled={isProcessing}
      />
      <button
        onClick={handleSendMessage}
        disabled={!inputValue.trim() || isProcessing}
        className="absolute bottom-2 right-2 flex h-7 w-7 items-center justify-center transition-colors"
        style={{
          backgroundColor: inputValue.trim() && !isProcessing ? 'var(--btn-primary-bg)' : 'transparent',
          color: inputValue.trim() && !isProcessing ? '#fff' : 'var(--text-tertiary)',
          cursor: inputValue.trim() && !isProcessing ? 'pointer' : 'not-allowed',
          borderRadius: 'var(--radius-button)',
        }}
      >
        <Send className="h-3.5 w-3.5" />
      </button>
    </div>
  );

  return (
    <>
      {showConversations && (
        <ConversationsModal
          onClose={() => setShowConversations(false)}
          onSelect={handleSelectSession}
        />
      )}

      <div
        ref={panelRef}
        className="flex flex-col h-full relative"
        style={{
          width: panelWidth,
          backgroundColor: 'var(--bg-surface)',
          borderRight: '1px solid var(--border-default)',
          transition: isResizing ? 'none' : 'width 0.2s ease-out',
        }}
      >
        {/* ── Header ── */}
        <div
          className="flex items-center justify-between px-4 border-b flex-shrink-0"
          style={{ height: '36px', borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)' }}
        >
          <span className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
            CloudVisor Q
          </span>

          <div className="flex items-center gap-0.5">
            {[
              { icon: <Plus className="h-4 w-4" />, title: 'New conversation', onClick: handleNewConversation },
              { icon: <History className="h-4 w-4" />, title: 'Conversations', onClick: () => setShowConversations(true) },
              { icon: isMaximized ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />, title: isMaximized ? 'Restore' : 'Maximize', onClick: toggleMaximize },
              { icon: <X className="h-4 w-4" />, title: 'Close', onClick: onClose },
            ].map((btn, i) => (
              <button
                key={i}
                onClick={btn.onClick}
                title={btn.title}
                className="flex h-8 w-8 items-center justify-center rounded transition-colors"
                style={iconBtn.base}
                onMouseEnter={e => Object.assign(e.currentTarget.style, iconBtn.hover)}
                onMouseLeave={e => Object.assign(e.currentTarget.style, iconBtn.base)}
              >
                {btn.icon}
              </button>
            ))}
          </div>
        </div>

        {/* ── Body ── */}
        <div className="flex-1 overflow-y-auto" style={{ backgroundColor: 'var(--bg-surface)', overscrollBehavior: 'contain' }}>
          {loadingSession ? (
            <div className="flex flex-col items-center justify-center h-full gap-3">
              <div className="flex gap-1.5">
                {[0, 150, 300].map(d => (
                  <span key={d} className="h-2.5 w-2.5 rounded-full animate-bounce"
                    style={{ backgroundColor: 'var(--text-tertiary)', animationDelay: `${d}ms` }} />
                ))}
              </div>
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Loading conversation...</p>
            </div>
          ) : !hasMessages ? (
            /* Welcome screen */
            <div className="flex flex-col items-center px-6 pt-12 pb-6">
              {/* Q icon */}
              <div
                className="mb-4 flex h-14 w-14 items-center justify-center rounded-full"
                style={{ backgroundColor: 'rgba(255,153,0,0.15)', border: '2px solid #ff9900' }}
              >
                <span className="text-xl font-bold" style={{ color: '#ff9900' }}>Q</span>
              </div>

              <h1 className="text-xl font-semibold mb-8" style={{ color: 'var(--text-primary)' }}>
                How can I help you today?
              </h1>

              {/* Centered input */}
              <div className="w-full max-w-2xl mb-1">
                <div
                  className="relative rounded"
                  style={{ border: '1px solid var(--border-strong)', backgroundColor: 'var(--bg-surface)' }}
                >
                  <textarea
                    ref={inputRef}
                    value={inputValue}
                    onChange={e => setInputValue(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Describe what you want to do with your cloud security, e.g., 'List all critical findings'"
                    className="w-full px-4 pt-3 pb-8 resize-none focus:outline-none text-sm"
                    style={{
                      minHeight: '80px',
                      maxHeight: '160px',
                      color: 'var(--text-primary)',
                      backgroundColor: 'transparent',
                      borderRadius: '4px',
                    }}
                    rows={3}
                    disabled={isProcessing}
                  />
                  <button
                    onClick={handleSendMessage}
                    disabled={!inputValue.trim() || isProcessing}
                    className="absolute bottom-2 right-2 flex h-7 w-7 items-center justify-center transition-colors"
                    style={{
                      backgroundColor: inputValue.trim() && !isProcessing ? 'var(--btn-primary-bg)' : 'transparent',
                      color: inputValue.trim() && !isProcessing ? '#fff' : 'var(--text-tertiary)',
                      cursor: inputValue.trim() && !isProcessing ? 'pointer' : 'not-allowed',
                      borderRadius: 'var(--radius-button)',
                    }}
                  >
                    <Send className="h-3.5 w-3.5" />
                  </button>
                </div>
                <p className="text-xs mt-1" style={{ color: 'var(--text-tertiary)' }}>Max 10000 characters</p>
              </div>

              {/* 2-column example grid */}
              <div className="w-full max-w-2xl grid grid-cols-2 gap-3 mt-5">
                {EXAMPLE_QUERIES.map((ex, i) => (
                  <button
                    key={i}
                    onClick={() => { setInputValue(ex.title); inputRef.current?.focus(); }}
                    className="text-left p-4 rounded border transition-colors"
                    style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)' }}
                    onMouseEnter={e => {
                      e.currentTarget.style.borderColor = 'var(--accent)';
                      e.currentTarget.style.backgroundColor = 'var(--bg-elevated)';
                    }}
                    onMouseLeave={e => {
                      e.currentTarget.style.borderColor = 'var(--border-default)';
                      e.currentTarget.style.backgroundColor = 'var(--bg-surface)';
                    }}
                  >
                    <p className="text-sm font-medium mb-1" style={{ color: 'var(--text-primary)' }}>{ex.title}</p>
                    <p className="text-xs mb-2" style={{ color: 'var(--text-secondary)' }}>{ex.subtitle}</p>
                    <span
                      className="text-xs px-2 py-0.5 rounded"
                      style={{ backgroundColor: 'var(--accent-dim)', color: 'var(--accent)' }}
                    >
                      {ex.badge}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            /* Chat messages */
            <div className="px-6 py-4 space-y-1 max-w-3xl mx-auto w-full">
              {messages.map(msg => <MessageBubble key={msg.id} message={msg} />)}
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        {/* ── Follow-up input (only when chatting) ── */}
        {hasMessages && !loadingSession && (
          <div
            className="flex-shrink-0 border-t px-6 py-3"
            style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)' }}
          >
            <div className="max-w-3xl mx-auto">
                <div
                  className="relative rounded"
                  style={{ border: '1px solid var(--border-strong)', backgroundColor: 'var(--bg-surface)' }}
                >
                  <textarea
                    ref={inputRef}
                    value={inputValue}
                    onChange={e => setInputValue(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Ask a follow-up..."
                    className="w-full px-4 pt-3 pb-8 resize-none focus:outline-none text-sm"
                    style={{
                      minHeight: '60px',
                      maxHeight: '160px',
                      color: 'var(--text-primary)',
                      backgroundColor: 'transparent',
                      borderRadius: '4px',
                    }}
                    rows={2}
                    disabled={isProcessing}
                  />
                  <button
                    onClick={handleSendMessage}
                    disabled={!inputValue.trim() || isProcessing}
                    className="absolute bottom-2 right-2 flex h-7 w-7 items-center justify-center transition-colors"
                    style={{
                      backgroundColor: inputValue.trim() && !isProcessing ? 'var(--btn-primary-bg)' : 'transparent',
                      color: inputValue.trim() && !isProcessing ? '#fff' : 'var(--text-tertiary)',
                      cursor: inputValue.trim() && !isProcessing ? 'pointer' : 'not-allowed',
                      borderRadius: 'var(--radius-button)',
                    }}
                  >
                    <Send className="h-3.5 w-3.5" />
                  </button>
                </div>
            </div>
          </div>
        )}

        {/* ── Footer ── */}
        <div
          className="flex-shrink-0 px-6 py-2 border-t text-xs"
          style={{ borderColor: 'var(--border-default)', color: 'var(--text-tertiary)', backgroundColor: 'var(--bg-surface)' }}
        >
          <div className="flex items-center justify-between max-w-3xl mx-auto">
            <span>CloudVisor Q may retain chats to improve the service.</span>
            <a
              href="#"
              style={{ color: 'var(--text-link)', textDecoration: 'none' }}
              onMouseEnter={e => (e.currentTarget.style.textDecoration = 'underline')}
              onMouseLeave={e => (e.currentTarget.style.textDecoration = 'none')}
            >
              Feedback
            </a>
          </div>
        </div>

        {/* ── Resize handle ── */}
        {!isMaximized && (
          <div
            className="absolute top-0 right-0 bottom-0 w-1 cursor-ew-resize z-10"
            onMouseDown={e => { e.preventDefault(); setIsResizing(true); }}
            style={{ backgroundColor: isResizing ? 'var(--accent)' : 'transparent' }}
            onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--border-default)')}
            onMouseLeave={e => (e.currentTarget.style.backgroundColor = isResizing ? 'var(--accent)' : 'transparent')}
          />
        )}
      </div>
    </>
  );
}
