'use client';
import { redirect } from 'next/navigation';

export default function DSPMOverviewPage() {
  redirect('/dspm?tab=overview');
}
