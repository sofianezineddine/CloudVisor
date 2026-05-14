'use client';
import { redirect } from 'next/navigation';

export default function CICDPoliciesPage() {
  redirect('/cicd?tab=policies');
}
