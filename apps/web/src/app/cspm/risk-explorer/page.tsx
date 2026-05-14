'use client';
import { redirect } from 'next/navigation';

// Route /cspm/risk-explorer → /cspm?tab=risk-map
export default function CSPMRiskExplorerPage() {
  redirect('/cspm?tab=risk-map');
}
