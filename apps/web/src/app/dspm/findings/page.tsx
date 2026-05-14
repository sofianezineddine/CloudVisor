'use client';
import { redirect } from 'next/navigation';

export default function DSPMFindingsPage() {
  redirect('/dspm?tab=findings');
}
