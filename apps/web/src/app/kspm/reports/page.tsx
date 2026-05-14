'use client';
import { redirect } from 'next/navigation';

export default function KSPMReportsPage() {
  redirect('/kspm?tab=reports');
}
