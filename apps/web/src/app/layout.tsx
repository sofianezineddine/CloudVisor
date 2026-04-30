import type { Metadata } from 'next';
import { NavigationProgress } from '@/components/navigation-progress';
import { AuthProvider } from '@/hooks/use-auth';
import { Toaster } from '@/components/ui/toaster';
import { CommandPaletteProvider } from '@/components/ui/command-palette-provider';
import { QueryProvider } from '@/components/query-provider';
import { ThemeProvider } from '@/components/theme-provider';
import './globals.css';

export const metadata: Metadata = {
  title: 'CloudVisor - Cloud Security Platform',
  description: 'Unified cloud security from code to runtime',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      {/* Inline script runs before React hydration — prevents dark-mode flash */}
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
(function(){
  try {
    var s = localStorage.getItem('cloudvisor-user-settings');
    if (s) {
      var state = JSON.parse(s);
      var theme = state.state && state.state.theme ? state.state.theme : null;
      if (!theme) theme = localStorage.getItem('theme');
      
      // Handle 'browser' option by checking system preference
      if (theme === 'browser') {
        theme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
      }
      
      if (theme === 'dark') {
        document.documentElement.setAttribute('data-theme','dark');
      } else if (theme === 'light') {
        document.documentElement.setAttribute('data-theme','light');
      }
    } else {
      var legacyTheme = localStorage.getItem('theme');
      if (legacyTheme === 'dark') {
        document.documentElement.setAttribute('data-theme','dark');
      } else if (legacyTheme === 'light') {
        document.documentElement.setAttribute('data-theme','light');
      }
    }
  } catch(e){console.error('Theme init error:', e);}
})();
            `.trim(),
          }}
        />
      </head>
      <body className="antialiased">
        <QueryProvider>
          <ThemeProvider>
            <AuthProvider>
              <CommandPaletteProvider>
                <NavigationProgress />
                {children}
                <Toaster />
              </CommandPaletteProvider>
            </AuthProvider>
          </ThemeProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
