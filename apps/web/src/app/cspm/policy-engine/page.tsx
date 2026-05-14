'use client';
import { redirect } from 'next/navigation';

// Route /cspm/policy-engine → /cspm?tab=policy-engine
export default function CSPMPolicyEnginePage() {
  redirect('/cspm?tab=policy-engine');
}
