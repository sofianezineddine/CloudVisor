'use client';
import { redirect } from 'next/navigation';

export default function CDRAssetsPage() {
  redirect('/cdr?tab=assets');
}
