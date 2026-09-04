import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'TrustRail — Checkout Agent',
  description: 'AI-powered conversational checkout for TrustRail electronics accessories.',
};

/* Inlined before React hydrates — prevents flash of wrong theme */
const themeScript = `
(function(){
  try {
    var t = localStorage.getItem('theme');
    if (t === 'light') { document.documentElement.classList.remove('dark'); }
    else { document.documentElement.classList.add('dark'); }
  } catch(e) { document.documentElement.classList.add('dark'); }
})();
`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className="font-sans h-screen overflow-hidden">
        {children}
      </body>
    </html>
  );
}
