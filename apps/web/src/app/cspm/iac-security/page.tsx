'use client';
import { redirect } from 'next/navigation';

// Route /cspm/iac-security → /cspm?tab=iac-security
export default function CSPMIaCSecurityPage() {
  redirect('/cspm?tab=iac-security');
}
