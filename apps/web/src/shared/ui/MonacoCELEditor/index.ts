'use client';

import dynamic from 'next/dynamic';

export const MonacoCelEditor = dynamic(
  () => import('./monaco-cel-editor').then((mod) => mod.MonacoCelEditor),
  { ssr: false }
);
