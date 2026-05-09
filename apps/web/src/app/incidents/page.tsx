'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { Loader2 } from 'lucide-react';

export default function IncidentsRedirect() {
  const router = useRouter();

  React.useEffect(() => {
    router.replace('/cspm?tab=incidents');
  }, [router]);

  return (
    <div className="flex h-screen w-screen items-center justify-center bg-[var(--bg-base)]">
      <div className="text-center">
        <Loader2 className="mx-auto h-8 w-8 animate-spin text-[var(--accent)]" />
        <p className="mt-4 text-sm text-[var(--text-secondary)]">Redirecting to CSPM Incidents...</p>
      </div>
    </div>
  );
}
