'use client';

import dynamic from 'next/dynamic';

export const WorkflowYAMLEditor = dynamic(
  () => import('./editor.client').then((mod) => mod.MonacoYAMLEditor),
  { ssr: false }
);

export default WorkflowYAMLEditor;
export type { MonacoYAMLEditorProps } from './MonacoYAMLEditor.types';
