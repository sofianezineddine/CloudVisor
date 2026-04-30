'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'default' | 'normal' | 'outline' | 'ghost' | 'link' | 'icon' | 'destructive';
  size?: 'sm' | 'md' | 'lg' | 'icon';
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'md', style, ...props }, ref) => {
    // Map legacy variant names
    const v = variant === 'default' ? 'primary' : variant === 'outline' ? 'normal' : variant;

    const baseStyle: React.CSSProperties = {
      borderRadius: 'var(--radius-button)',   /* AWS: 2px square corners */
      fontFamily: 'var(--font-sans)',
      fontWeight: 400,
      transition: 'background-color 0.1s, border-color 0.1s',
      ...style,
    };

    return (
      <button
        className={cn(
          'inline-flex items-center justify-center transition-colors',
          'focus-visible:outline-none focus-visible:ring-2',
          'disabled:pointer-events-none disabled:opacity-50',
          // Variants — AWS Console style
          v === 'primary' && 'bg-[var(--btn-primary-bg)] text-white border border-[var(--btn-primary-bg)] hover:bg-[var(--btn-primary-hover)] hover:border-[var(--btn-primary-hover)]',
          v === 'normal' && 'bg-[var(--btn-normal-bg)] text-[var(--btn-normal-text)] border border-[var(--btn-normal-border)] hover:bg-[var(--btn-normal-hover)]',
          v === 'ghost' && 'bg-transparent border-0 text-[var(--text-secondary)] hover:bg-[var(--bg-elevated)] hover:text-[var(--text-primary)]',
          v === 'link' && 'text-[var(--text-link)] underline-offset-4 hover:underline bg-transparent border-0 hover:text-[var(--text-link-hover)]',
          v === 'icon' && 'bg-transparent border-0 text-[var(--text-secondary)] hover:bg-[var(--bg-elevated)]',
          v === 'destructive' && 'bg-[var(--danger)] text-white border border-[var(--danger)] hover:opacity-90',
          // Sizes
          size === 'sm' && 'h-7 px-3 text-xs',
          size === 'md' && 'h-8 px-4 text-sm',
          size === 'lg' && 'h-9 px-5 text-sm',
          (size === 'icon' || v === 'icon') && 'h-8 w-8 p-0',
          className
        )}
        style={baseStyle}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = 'Button';

export { Button };
