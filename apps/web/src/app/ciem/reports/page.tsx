'use client';
import { redirect } from 'next/navigation';

export default function CIEMReportsPage() {
  redirect('/ciem?tab=reports');
}
