'use client';
import { redirect } from 'next/navigation';

export default function CDRFindingsPage() {
  redirect('/cdr?tab=findings');
}
