import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Toaster } from "sonner";
import { AuthGuard } from "@/components/auth-guard";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "PRDforge",
  description: "Product Requirements Document management tool",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  // Inline script to prevent flash — reads localStorage before paint
  const themeScript = `
    (function() {
      var t = localStorage.getItem('prdforge-theme');
      if (t === 'light') return;
      document.documentElement.classList.add('dark');
    })();
  `;

  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className={`${inter.variable} font-sans antialiased`}>
        <AuthGuard>{children}</AuthGuard>
        <Toaster richColors position="bottom-right" />
      </body>
    </html>
  );
}
