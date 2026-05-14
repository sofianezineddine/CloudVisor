'use client';
import { redirect } from 'next/navigation';

export default function CIEMPoliciesPage() {
  redirect('/ciem?tab=policies');
}
