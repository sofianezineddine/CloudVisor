'use client';

import * as React from 'react';
import { AppLayout } from '@/components/layout';
import { ProtectedRoute } from '@/components/protected-route';
import Link from 'next/link';
import { Pin, PinOff } from 'lucide-react';
import { SERVICE_CATEGORIES, loadPins, savePins, togglePin } from '@/lib/services-data';

export default function AllServicesPage() {
  const [pins, setPins] = React.useState<string[]>([]);

  // Load pins from localStorage on mount
  React.useEffect(() => {
    document.title = 'All Services - CloudVisor';
    setPins(loadPins());
  }, []);

  const handleTogglePin = (href: string) => {
    const next = togglePin(href, pins);
    setPins(next);
    savePins(next);
    // Notify header to re-read pins
    window.dispatchEvent(new Event('cloudvisor-pins-changed'));
  };

  return (
    <ProtectedRoute>
      <AppLayout
        breadcrumbs={[
          { text: 'Home Console', href: '/console' },
          { text: 'All services' },
        ]}
      >
        {/* Page title */}
        <h1 className="text-xl font-bold mb-1" style={{ color: 'var(--text-primary)' }}>
          All services
        </h1>
        <p className="text-sm mb-1" style={{ color: 'var(--text-secondary)' }}>
          Pin any service to the navigation bar using the{' '}
          <Pin className="inline h-3 w-3" style={{ color: '#0972d3' }} /> icon.
        </p>
        <p className="text-sm font-semibold mb-5" style={{ color: 'var(--text-secondary)' }}>
          Services by category
        </p>

        {/* 4-column grid */}
        <div className="grid grid-cols-1 gap-x-8 gap-y-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {SERVICE_CATEGORIES.map(cat => (
            <div key={cat.id}>
              {/* Category header */}
              <div className="flex items-center gap-2 mb-2">
                <div
                  className="flex h-6 w-6 items-center justify-center rounded flex-shrink-0 text-[10px] font-bold"
                  style={{
                    backgroundColor: cat.bg,
                    border: `1px solid ${cat.color}40`,
                    color: cat.color,
                  }}
                >
                  {cat.iconText}
                </div>
                <span className="text-sm font-bold" style={{ color: 'var(--text-primary)' }}>
                  {cat.label}
                </span>
              </div>

              {/* Service links */}
              <ul className="space-y-0.5 pl-8">
                {cat.services.map(svc => {
                  const isPinned = pins.includes(svc.href);
                  return (
                    <li key={svc.href} className="group flex items-center gap-1.5">
                      <Link
                        href={svc.href}
                        className="text-sm flex-1 block py-0.5"
                        style={{ color: '#0972d3', textDecoration: 'none' }}
                        onMouseEnter={e => (e.currentTarget.style.textDecoration = 'underline')}
                        onMouseLeave={e => (e.currentTarget.style.textDecoration = 'none')}
                        title={svc.desc}
                      >
                        {svc.name}
                      </Link>

                      {/* Pin / unpin button — visible on row hover */}
                      <button
                        onClick={() => handleTogglePin(svc.href)}
                        title={isPinned ? 'Remove from navigation bar' : 'Pin to navigation bar'}
                        className="flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
                        style={{
                          background: 'none',
                          border: 'none',
                          cursor: 'pointer',
                          padding: '2px',
                          color: isPinned ? '#ff9900' : 'var(--text-tertiary)',
                          display: 'flex',
                          alignItems: 'center',
                        }}
                        onMouseEnter={e => (e.currentTarget.style.color = isPinned ? '#eb5f07' : '#0972d3')}
                        onMouseLeave={e => (e.currentTarget.style.color = isPinned ? '#ff9900' : 'var(--text-tertiary)')}
                      >
                        {isPinned
                          ? <PinOff className="h-3 w-3" />
                          : <Pin className="h-3 w-3" />
                        }
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>
      </AppLayout>
    </ProtectedRoute>
  );
}
