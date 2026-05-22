import type { Config } from 'tailwindcss';

const config: Config = {
  darkMode: ['selector', '[data-theme="dark"]'],
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
    './src/entities/**/*.{js,ts,jsx,tsx}',
    './src/features/**/*.{js,ts,jsx,tsx}',
    './src/widgets/**/*.{js,ts,jsx,tsx}',
    './src/shared/**/*.{js,ts,jsx,tsx}',
    './src/utils/**/*.{js,ts,jsx,tsx}',
    './src/keep/**/*.{js,ts,jsx,tsx}',
    './node_modules/@tremor/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        border: 'var(--border-default)',
        background: 'var(--bg-base)',
        foreground: 'var(--text-primary)',
        // Tremor light mode colors
        tremor: {
          brand: {
            faint: 'rgb(239 246 255)',
            muted: 'rgb(219 234 254)',
            subtle: 'rgb(96 165 250)',
            DEFAULT: '#0972d3',
            emphasis: '#0060b0',
            inverted: '#ffffff',
          },
          background: {
            muted: 'rgb(249 250 251)',
            subtle: 'rgb(243 244 246)',
            DEFAULT: '#ffffff',
            emphasis: 'rgb(55 65 81)',
          },
          border: {
            DEFAULT: 'rgb(229 231 235)',
          },
          ring: {
            DEFAULT: 'rgb(209 213 219)',
          },
          content: {
            subtle: 'rgb(156 163 175)',
            DEFAULT: 'rgb(107 114 128)',
            emphasis: 'rgb(55 65 81)',
            strong: 'rgb(17 24 39)',
            inverted: '#ffffff',
          },
        },
        // Tremor dark mode colors (referenced by dark: prefix in Tremor components)
        'dark-tremor': {
          brand: {
            faint: 'rgba(74, 144, 217, 0.05)',
            muted: 'rgba(74, 144, 217, 0.10)',
            subtle: 'rgba(74, 144, 217, 0.15)',
            DEFAULT: '#4a90d9',
            emphasis: '#5ba3f5',
            inverted: '#0d1117',
          },
          background: {
            muted: '#1c2433',
            subtle: '#131920',
            DEFAULT: '#0d1117',
            emphasis: '#d1d5db',
          },
          border: {
            DEFAULT: '#2e3140',
          },
          ring: {
            DEFAULT: '#2e3140',
          },
          content: {
            subtle: '#6b7280',
            DEFAULT: '#9ca3af',
            emphasis: '#e5e7eb',
            strong: '#f9fafb',
            inverted: '#0d1117',
          },
        },
        primary: {
          DEFAULT: 'var(--btn-primary-bg)',
          foreground: '#ffffff',
        },
        secondary: {
          DEFAULT: 'var(--bg-elevated)',
          foreground: 'var(--text-primary)',
        },
        destructive: {
          DEFAULT: 'var(--critical)',
          foreground: '#ffffff',
        },
        muted: {
          DEFAULT: 'var(--bg-elevated)',
          foreground: 'var(--text-secondary)',
        },
        accent: {
          DEFAULT: 'var(--accent)',
          foreground: '#ffffff',
        },
        popover: {
          DEFAULT: 'var(--bg-overlay)',
          foreground: 'var(--text-primary)',
        },
        card: {
          DEFAULT: 'var(--bg-surface)',
          foreground: 'var(--text-primary)',
        },
      },
      borderRadius: {
        lg: '4px',
        md: '2px',
        sm: '2px',
        'tremor-small': '0.375rem',
        'tremor-default': '0.5rem',
        'tremor-full': '9999px',
      },
      fontSize: {
        'tremor-label': ['0.75rem'],
        'tremor-default': ['0.875rem', { lineHeight: '1.25rem' }],
        'tremor-title': ['1.125rem', { lineHeight: '1.75rem' }],
        'tremor-metric': ['1.875rem', { lineHeight: '2.25rem' }],
      },
      boxShadow: {
        'tremor-input': '0 1px 2px 0 rgb(0 0 0 / 0.05)',
        'tremor-card': '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
        'tremor-dropdown': '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
        'dark-tremor-input': '0 1px 2px 0 rgb(0 0 0 / 0.2)',
        'dark-tremor-card': '0 1px 3px 0 rgb(0 0 0 / 0.3), 0 1px 2px -1px rgb(0 0 0 / 0.3)',
        'dark-tremor-dropdown': '0 4px 6px -1px rgb(0 0 0 / 0.3), 0 2px 4px -2px rgb(0 0 0 / 0.3)',
      },
      fontFamily: {
        sans: ['Open Sans', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
        mono: ['Courier New', 'Courier', 'monospace'],
      },
      keyframes: {
        'accordion-down': {
          from: { height: '0' },
          to: { height: 'var(--radix-accordion-content-height)' },
        },
        'accordion-up': {
          from: { height: 'var(--radix-accordion-content-height)' },
          to: { height: '0' },
        },
        'fade-in': {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        'skeleton-shimmer': {
          '0%': { backgroundPosition: '200% 0' },
          '100%': { backgroundPosition: '-200% 0' },
        },
      },
      animation: {
        'accordion-down': 'accordion-down 0.2s ease-out',
        'accordion-up': 'accordion-up 0.2s ease-out',
        'fade-in': 'fade-in 0.15s ease-out',
        'skeleton': 'skeleton-shimmer 1.5s ease-in-out infinite',
      },
    },
  },
  plugins: [require('tailwindcss-animate'), require('@headlessui/tailwindcss')],
};

export default config;
