'use client';
import { redirect } from 'next/navigation';

export default function CWPPOverviewPage() {
  redirect('/cwpp?tab=overview');
}
