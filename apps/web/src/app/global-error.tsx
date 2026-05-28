"use client";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  // Log full stack trace to console for debugging
  console.error("[GlobalError] Error:", error?.message);
  console.error("[GlobalError] Stack:", error?.stack);
  return (
    <html>
      <body style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', fontFamily: 'sans-serif' }}>
        <div style={{ textAlign: 'center', maxWidth: '800px', padding: '2rem' }}>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#dc2626' }}>Something went wrong</h1>
          <p style={{ color: '#666', marginTop: '0.5rem' }}>{error.message}</p>
          <pre style={{ 
            textAlign: 'left', 
            fontSize: '0.75rem', 
            background: '#f5f5f5', 
            padding: '1rem', 
            borderRadius: '8px', 
            marginTop: '1rem',
            whiteSpace: 'pre-wrap',
            maxHeight: '400px',
            overflow: 'auto',
            color: '#333'
          }}>
            {error.stack || '(no stack trace available)'}
          </pre>
          <button onClick={reset} style={{ marginTop: '1rem', padding: '0.5rem 1rem', cursor: 'pointer' }}>
            Try again
          </button>
        </div>
      </body>
    </html>
  );
}
