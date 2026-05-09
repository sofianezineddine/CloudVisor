'use client';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function RiskMapRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace('/cspm?tab=risk-map');
  }, [router]);
  return null;
}
