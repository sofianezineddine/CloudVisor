'use client';
import { redirect } from 'next/navigation';

export default function KSPMOverviewPage() {
  redirect('/kspm?tab=overview');
}
