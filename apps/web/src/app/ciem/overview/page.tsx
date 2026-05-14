'use client';
import { redirect } from 'next/navigation';

export default function CIEMOverviewPage() {
  redirect('/ciem?tab=overview');
}
