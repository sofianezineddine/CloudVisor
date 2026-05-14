'use client';
import { redirect } from 'next/navigation';

export default function CDRReportsPage() {
  redirect('/cdr?tab=reports');
}
