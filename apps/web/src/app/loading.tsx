export default function Loading() {
  return (
    <div className="flex items-center justify-center min-h-screen" style={{ backgroundColor: 'var(--bg-base)' }}>
      <div className="flex flex-col items-center gap-4">
        <div className="relative w-16 h-16">
          <div className="absolute inset-0 border-4 rounded-full" style={{ borderColor: 'var(--border-default)' }}></div>
          <div className="absolute inset-0 border-4 rounded-full border-t-transparent animate-spin" style={{ borderColor: 'var(--accent)' }}></div>
        </div>
        <div className="text-sm" style={{ color: 'var(--text-secondary)' }}>Loading...</div>
      </div>
    </div>
  );
}
