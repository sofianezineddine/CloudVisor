'use client';
import { redirect } from 'next/navigation';

export default function CWPPAssetsPage() {
  redirect('/cwpp?tab=assets');
}
