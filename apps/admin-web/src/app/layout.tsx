import './globals.css';
import { AuthProvider } from '@/hooks/use-admin-auth';

export const metadata = {
  title: 'CloudVisor Admin',
  description: 'CloudVisor Platform Administration Dashboard',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body style={{ backgroundColor: 'var(--bg-base)', color: 'var(--text-primary)', fontFamily: 'var(--font-sans)', margin: 0 }}>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
