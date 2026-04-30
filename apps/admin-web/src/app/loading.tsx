export default function AdminLoading() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-[hsl(var(--bg-base))]">
      <div className="text-center">
        <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-[hsl(var(--accent))] border-t-transparent" />
        <p className="mt-4 text-sm text-[hsl(var(--text-secondary))]">Loading admin dashboard...</p>
      </div>
    </div>
  );
}
