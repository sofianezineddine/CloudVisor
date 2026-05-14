'use client';
import { redirect } from 'next/navigation';

export default function DSPMReportsPage() {
  redirect('/dspm?tab=reports');
}
