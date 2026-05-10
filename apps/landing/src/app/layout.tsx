import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'CloudVisor — Unified Cloud Security Platform',
  description:
    'AI-powered cloud security from code to runtime. Protect everything you build and run across AWS, Azure, GCP, and OCI.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
