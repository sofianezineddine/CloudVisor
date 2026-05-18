'use client';
export default function NotFound() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="text-center">
        <h1 className="text-2xl font-bold" style={{ color: 'var(--color-text-primary)' }}>404</h1>
        <p style={{ color: 'var(--color-text-secondary)' }}>Page not found</p>
      </div>
    </div>
  );
}
