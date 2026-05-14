'use client';
import { redirect } from 'next/navigation';

export default function KSPMFindingsPage() {
  redirect('/kspm?tab=findings');
}
