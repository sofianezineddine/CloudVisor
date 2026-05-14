'use client';
import { redirect } from 'next/navigation';

// Route /cspm/compliance → /cspm?tab=compliance
export default function CSPMCompliancePage() {
  redirect('/cspm?tab=compliance');
}
