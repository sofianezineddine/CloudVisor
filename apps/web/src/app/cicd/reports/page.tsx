'use client';
import { redirect } from 'next/navigation';

export default function CICDReportsPage() {
  redirect('/cicd?tab=reports');
}
