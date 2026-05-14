'use client';
import { redirect } from 'next/navigation';

export default function CWPPReportsPage() {
  redirect('/cwpp?tab=reports');
}
