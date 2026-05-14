'use client';
import { redirect } from 'next/navigation';

export default function DSPMAssetsPage() {
  redirect('/dspm?tab=assets');
}
