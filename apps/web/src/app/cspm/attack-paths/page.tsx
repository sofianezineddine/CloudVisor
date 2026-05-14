'use client';
import { redirect } from 'next/navigation';

// Route /cspm/attack-paths → /cspm?tab=attack-paths
export default function CSPMAttackPathsPage() {
  redirect('/cspm?tab=attack-paths');
}
