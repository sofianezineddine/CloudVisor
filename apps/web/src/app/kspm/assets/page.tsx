'use client';
import { redirect } from 'next/navigation';

export default function KSPMAssetsPage() {
  redirect('/kspm?tab=assets');
}
