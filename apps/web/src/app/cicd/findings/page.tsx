'use client';
import { redirect } from 'next/navigation';

export default function CICDFindingsPage() {
  redirect('/cicd?tab=findings');
}
