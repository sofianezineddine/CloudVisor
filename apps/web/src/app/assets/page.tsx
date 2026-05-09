'use client';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function AssetsRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace('/cspm?tab=assets');
  }, [router]);
  return null;
}
