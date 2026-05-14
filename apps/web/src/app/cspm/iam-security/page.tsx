'use client';
import { redirect } from 'next/navigation';

// Route /cspm/iam-security → /cspm?tab=iam-security
export default function CSPMIAMSecurityPage() {
  redirect('/cspm?tab=iam-security');
}
