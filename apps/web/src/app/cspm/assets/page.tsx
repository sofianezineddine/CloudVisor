'use client';
import { redirect } from 'next/navigation';

// Route /cspm/assets → /cspm?tab=assets
export default function CSPMAssetsPage() {
  redirect('/cspm?tab=assets');
}
