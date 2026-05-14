'use client';
import { redirect } from 'next/navigation';

export default function CICDOverviewPage() {
  redirect('/cicd?tab=overview');
}
