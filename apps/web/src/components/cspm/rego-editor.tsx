'use client';

import * as React from 'react';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface RegoEditorProps {
  value: string;
  onChange: (value: string) => void;
  readOnly?: boolean;
  height?: string;
  error?: string;
}

// ─── Rego Keywords ────────────────────────────────────────────────────────────

const REGO_KEYWORDS = [
  'package', 'import', 'default', 'allow', 'deny',
  'input', 'data', 'not', 'with', 'as', 'some', 'every',
  'true', 'false', 'null', 'else', 'if',
];

const KEYWORD_REGEX = new RegExp(`\\b(${REGO_KEYWORDS.join('|')})\\b`, 'g');
const STRING_REGEX = /"[^"]*"/g;
const COMMENT_REGEX = /#.*/g;

// ─── Syntax Highlighting ──────────────────────────────────────────────────────

function highlightRego(code: string): string {
  // Escape HTML entities
  let html = code
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  // Apply highlighting in order: comments > strings > keywords
  // Use placeholder tokens to avoid double-replacement
  const tokens: string[] = [];

  // Comments
  html = html.replace(COMMENT_REGEX, (match) => {
    const idx = tokens.length;
    tokens.push(`<span style="color: var(--rego-comment, #6a9955)">${match}</span>`);
    return `\x00${idx}\x00`;
  });

  // Strings
  html = html.replace(STRING_REGEX, (match) => {
    const idx = tokens.length;
    tokens.push(`<span style="color: var(--rego-string, #ce9178)">${match}</span>`);
    return `\x00${idx}\x00`;
  });

  // Keywords
  html = html.replace(KEYWORD_REGEX, (match) => {
    const idx = tokens.length;
    tokens.push(`<span style="color: var(--rego-keyword, #569cd6); font-weight: 600">${match}</span>`);
    return `\x00${idx}\x00`;
  });

  // Restore tokens
  html = html.replace(/\x00(\d+)\x00/g, (_, idx) => tokens[Number(idx)]);

  return html;
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * RegoEditor — lightweight code editor with Rego syntax highlighting.
 *
 * Uses a textarea for input with a transparent overlay <pre> for highlighting.
 * Line numbers are rendered in a side gutter.
 * CSS variables: --rego-keyword, --rego-string, --rego-comment, --rego-operator
 */
export function RegoEditor({
  value,
  onChange,
  readOnly = false,
  height = '300px',
  error,
}: RegoEditorProps) {
  const textareaRef = React.useRef<HTMLTextAreaElement>(null);
  const preRef = React.useRef<HTMLPreElement>(null);

  const lines = value.split('\n');
  const lineCount = lines.length;

  // Sync scroll between textarea and overlay
  const handleScroll = React.useCallback(() => {
    if (textareaRef.current && preRef.current) {
      preRef.current.scrollTop = textareaRef.current.scrollTop;
      preRef.current.scrollLeft = textareaRef.current.scrollLeft;
    }
  }, []);

  const handleChange = React.useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      onChange(e.target.value);
    },
    [onChange]
  );

  // Handle tab key for indentation
  const handleKeyDown = React.useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Tab') {
        e.preventDefault();
        const textarea = e.currentTarget;
        const start = textarea.selectionStart;
        const end = textarea.selectionEnd;
        const newValue = value.substring(0, start) + '  ' + value.substring(end);
        onChange(newValue);
        // Restore cursor position
        requestAnimationFrame(() => {
          textarea.selectionStart = textarea.selectionEnd = start + 2;
        });
      }
    },
    [value, onChange]
  );

  const highlightedHtml = React.useMemo(() => highlightRego(value), [value]);

  return (
    <div className="w-full">
      <div
        className="relative flex rounded-lg border overflow-hidden"
        style={{
          height,
          borderColor: error ? 'var(--rego-error-border, hsl(var(--critical)))' : 'hsl(var(--border-default))',
          backgroundColor: 'var(--rego-bg, hsl(var(--bg-surface)))',
        }}
      >
        {/* Line numbers gutter */}
        <div
          className="flex-shrink-0 select-none overflow-hidden border-r px-3 py-3 text-right"
          style={{
            borderColor: 'hsl(var(--border-faint))',
            backgroundColor: 'var(--rego-gutter-bg, hsl(var(--bg-elevated)))',
            color: 'var(--rego-line-number, hsl(var(--text-tertiary)))',
            fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace',
            fontSize: '13px',
            lineHeight: '1.5',
            minWidth: '3rem',
          }}
        >
          {Array.from({ length: lineCount }, (_, i) => (
            <div key={i + 1}>{i + 1}</div>
          ))}
        </div>

        {/* Editor area */}
        <div className="relative flex-1 overflow-hidden">
          {/* Syntax highlight overlay */}
          <pre
            ref={preRef}
            className="pointer-events-none absolute inset-0 overflow-auto whitespace-pre-wrap break-words p-3"
            style={{
              fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace',
              fontSize: '13px',
              lineHeight: '1.5',
              color: 'hsl(var(--text-primary))',
              margin: 0,
            }}
            aria-hidden="true"
            dangerouslySetInnerHTML={{ __html: highlightedHtml + '\n' }}
          />

          {/* Textarea (transparent text, visible caret) */}
          <textarea
            ref={textareaRef}
            value={value}
            onChange={handleChange}
            onScroll={handleScroll}
            onKeyDown={handleKeyDown}
            readOnly={readOnly}
            spellCheck={false}
            autoCapitalize="off"
            autoComplete="off"
            autoCorrect="off"
            className="absolute inset-0 w-full h-full resize-none overflow-auto whitespace-pre-wrap break-words p-3 outline-none"
            style={{
              fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace',
              fontSize: '13px',
              lineHeight: '1.5',
              color: 'transparent',
              caretColor: 'hsl(var(--text-primary))',
              backgroundColor: 'transparent',
            }}
            aria-label="Rego policy editor"
          />
        </div>
      </div>

      {/* Error display */}
      {error && (
        <div
          className="mt-2 rounded px-3 py-2 text-sm"
          style={{
            color: 'hsl(var(--critical))',
            backgroundColor: 'hsl(var(--critical-dim))',
          }}
        >
          {error}
        </div>
      )}
    </div>
  );
}
