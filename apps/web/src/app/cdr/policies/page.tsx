'use client';
import { redirect } from 'next/navigation';

export default function CDRPoliciesPage() {
  redirect('/cdr?tab=policies');
}
