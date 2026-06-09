import { defineConfig } from 'vitest/config';
import path from 'path';

export default defineConfig({
  // Disable PostCSS/Tailwind processing entirely for tests — avoids
  // the 'object-hash' missing-module crash from tailwindcss plugin
  css: {
    postcss: {
      plugins: [],
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.{test,spec}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}'],
    css: false,
    coverage: {
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'src/test/',
        '**/*.d.ts',
        '**/*.config.{js,ts}',
        '**/.*',
      ],
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      // Stub Next.js internals that aren't available in jsdom/vitest
      'next/dynamic': path.resolve(__dirname, 'src/test/__mocks__/next-dynamic.ts'),
      'next/navigation': path.resolve(__dirname, 'src/test/__mocks__/next-navigation.ts'),
      'next/image': path.resolve(__dirname, 'src/test/__mocks__/next-image.ts'),
      'next/link': path.resolve(__dirname, 'src/test/__mocks__/next-link.ts'),
    },
  },
});
