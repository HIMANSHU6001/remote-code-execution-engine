import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/context/AuthContext";

const poppins = {
  variable: "--font-poppins",
};

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
      className={`${poppins.variable} ${jetbrainsMono.variable} h-full antialiased dark`}
    >
      <body className="h-screen w-full overflow-hidden bg-[#0a0a0a] text-slate-200 font-sans">
        <AuthProvider>
          {children}
        </AuthProvider>
        <Toaster 
          position="bottom-right"
          toastOptions={{
            style: {
              background: '#18181b',
              color: '#fff',
              border: '1px solid #27272a',
            },
          }}
        />
      </body>
    </html>
  );
}
