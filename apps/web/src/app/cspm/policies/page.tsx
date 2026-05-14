'use client';
import { redirect } from 'next/navigation';

// Route /cspm/policies → /cspm?tab=policies
export default function CSPMPoliciesPage() {
  redirect('/cspm?tab=policies');
}
