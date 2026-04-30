import type { Config } from 'tailwindcss';

const config: Config = {
  darkMode: ['class'],
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    container: { center: true, padding: '2rem', screens: { '2xl': '1400px' } },
    extend: {
      colors: {
        border: {
          DEFAULT: 'hsl(var(--border-default))',
          faint: 'hsl(var(--border-faint))',
          strong: 'hsl(var(--border-strong))',
        },
        background: { DEFAULT: 'hsl(var(--bg-base))' },
        foreground: { DEFAULT: 'hsl(var(--text-primary))' },
        card: { DEFAULT: 'hsl(var(--bg-surface))', foreground: 'hsl(var(--text-primary))' },
        popover: { DEFAULT: 'hsl(var(--bg-overlay))', foreground: 'hsl(var(--text-primary))' },
        primary: { DEFAULT: 'hsl(var(--accent))', foreground: '#fff', hover: 'hsl(var(--accent-hover))' },
        muted: { DEFAULT: 'hsl(var(--bg-elevated))', foreground: 'hsl(var(--text-secondary))' },
        destructive: { DEFAULT: 'hsl(var(--critical))', foreground: '#fff' },
        success: { DEFAULT: 'hsl(var(--success))', foreground: '#fff' },
        warning: { DEFAULT: 'hsl(var(--warning))', foreground: '#fff' },
        ring: 'hsl(var(--accent))',
        sidebar: {
          DEFAULT: 'hsl(var(--admin-sidebar))',
          foreground: 'hsl(var(--text-on-sidebar))',
          active: 'hsl(var(--admin-sidebar-active))',
          hover: 'hsl(var(--admin-sidebar-hover))',
        },
        critical: 'hsl(var(--critical))',
        high: 'hsl(var(--high))',
        medium: 'hsl(var(--medium))',
        low: 'hsl(var(--low))',
        info: 'hsl(var(--info))',
      },
      borderRadius: { lg: '12px', md: '8px', sm: '6px' },
      keyframes: { 'fade-in': { from: { opacity: '0' }, to: { opacity: '1' } } },
      animation: { 'fade-in': 'fade-in 0.2s ease-out' },
    },
  },
  plugins: [require('tailwindcss-animate')],
};

export default config;
