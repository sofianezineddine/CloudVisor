'use client';
import { redirect } from 'next/navigation';

// Route /cspm/drift-detection → /cspm?tab=drift-detection
export default function CSPMDriftDetectionPage() {
  redirect('/cspm?tab=drift-detection');
}
