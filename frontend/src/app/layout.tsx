import type { Metadata, Viewport } from "next";
import { yekanBakh, iranSansMono } from "./fonts";
import "./globals.css";
import { Toaster } from "@/components/ui/sonner";

export const metadata: Metadata = {
  title: "Sovereign AI - Enterprise Assistant & Cluster Control",
  description:
    "Grounded Persian & English AI assistant for enterprise cluster orchestration, semantic routing, and local GPU inference.",
  icons: {
    icon: "/brand-logo - no text.svg",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  viewportFit: "cover",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="fa"
      dir="rtl"
      className={`${yekanBakh.variable} ${iranSansMono.variable} dark`}
    >
      <body className="bg-canvas text-foreground antialiased h-[100dvh] w-full overflow-hidden select-none touch-manipulation selection:bg-brand-cyan/20 selection:text-brand-cyan">
        {children}
        <Toaster richColors position="bottom-left" dir="rtl" />
      </body>
    </html>
  );
}
