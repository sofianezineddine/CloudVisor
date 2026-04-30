'use client';

import { useEffect, useState } from 'react';
import { usePathname } from 'next/navigation';

export function NavigationProgress() {
  const pathname = usePathname();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    const timeout = setTimeout(() => setLoading(false), 300);
    return () => clearTimeout(timeout);
  }, [pathname]);

  if (!loading) return null;

  return (
    <div className="fixed top-0 left-0 right-0 z-[100] h-1 bg-[hsl(var(--bg-base))]">
      <div 
        className="h-full bg-[hsl(var(--accent))] transition-all duration-300 ease-out"
        style={{
          width: '100%',
          animation: 'progress 0.3s ease-out'
        }}
      />
      <style jsx>{`
        @keyframes progress {
          from {
            width: 0%;
          }
          to {
            width: 100%;
          }
        }
      `}</style>
    </div>
  );
}
