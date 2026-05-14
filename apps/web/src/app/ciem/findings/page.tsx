'use client';
import { redirect } from 'next/navigation';

export default function CIEMFindingsPage() {
  redirect('/ciem?tab=findings');
}
