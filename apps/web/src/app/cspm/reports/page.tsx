'use client';
import { redirect } from 'next/navigation';

// Route /cspm/reports → /cspm?tab=reports
export default function CSPMReportsPage() {
  redirect('/cspm?tab=reports');
}
