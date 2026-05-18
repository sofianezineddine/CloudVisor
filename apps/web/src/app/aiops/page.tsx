'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function AIOpsPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/aiops/alerts');
  }, [router]);

  return null;
}
