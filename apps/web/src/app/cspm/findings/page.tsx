'use client';
import { redirect } from 'next/navigation';

// Route /cspm/findings → /cspm?tab=findings
export default function CSPMFindingsPage() {
  redirect('/cspm?tab=findings');
}
