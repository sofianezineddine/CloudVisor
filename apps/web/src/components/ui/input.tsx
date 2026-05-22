import * as React from 'react';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={`flex h-9 w-full rounded-md border border-[var(--border-default)] bg-[var(--bg-surface)] px-3 py-1 text-sm text-[var(--text-primary)] shadow-sm transition-colors placeholder:text-[var(--text-tertiary)] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[#0972d3] disabled:cursor-not-allowed disabled:opacity-50 ${className || ''}`}
        ref={ref}
        {...props}
      />
    );
  }
);
Input.displayName = 'Input';

export { Input };
