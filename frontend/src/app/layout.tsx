import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/context/AuthContext";
import { ThemeProvider } from "@/context/ThemeContext";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-poppins", // Reusing the variable name to minimize css changes
});

const jetbrainsMono = {
  variable: "--font-mono",
};

export const metadata: Metadata = {
  title: "CodeSpace",
  description: "Remote code execution workspace.",
};

import { Toaster } from "react-hot-toast";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${jetbrainsMono.variable} h-full antialiased dark`}
      suppressHydrationWarning
    >
      <body className="h-screen w-full overflow-hidden text-text-primary font-sans">
        <ThemeProvider>
          <AuthProvider>
            {children}
          </AuthProvider>
          <Toaster
            position="bottom-right"
            toastOptions={{
              style: {
                background: 'var(--toast-bg)',
                color: 'var(--toast-color)',
                border: '1px solid var(--toast-border)',
              },
            }}
          />
        </ThemeProvider>
      </body>
    </html>
  );
}
