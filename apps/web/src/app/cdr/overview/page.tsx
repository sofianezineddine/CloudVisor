'use client';
import { redirect } from 'next/navigation';

export default function CDROverviewPage() {
  redirect('/cdr?tab=overview');
}
