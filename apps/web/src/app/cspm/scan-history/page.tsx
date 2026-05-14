'use client';
import { redirect } from 'next/navigation';

// Route /cspm/scan-history → /cspm?tab=scan-history
export default function CSPMScanHistoryPage() {
  redirect('/cspm?tab=scan-history');
}
