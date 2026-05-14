'use client';
import { redirect } from 'next/navigation';

// Route /cspm/overview → /cspm?tab=overview
export default function CSPMOverviewPage() {
  redirect('/cspm?tab=overview');
}
