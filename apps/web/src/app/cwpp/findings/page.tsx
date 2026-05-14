'use client';
import { redirect } from 'next/navigation';

export default function CWPPFindingsPage() {
  redirect('/cwpp?tab=findings');
}
