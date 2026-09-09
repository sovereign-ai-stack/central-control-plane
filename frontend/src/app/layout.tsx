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
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              if (typeof window !== "undefined") {
                if (!window.crypto) { window.crypto = {}; }
                if (typeof window.crypto.randomUUID !== "function") {
                  window.crypto.randomUUID = function() {
                    if (typeof window.crypto.getRandomValues === "function") {
                      return ("" + 1e7 + -1e3 + -4e3 + -8e3 + -1e11).replace(/[018]/g, function(c) {
                        return (c ^ window.crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16);
                      });
                    }
                    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function(c) {
                      var r = Math.random() * 16 | 0, v = c === "x" ? r : (r & 0x3 | 0x8);
                      return v.toString(16);
                    });
                  };
                }
              }
            `,
          }}
        />
      </head>
      <body className="bg-canvas text-foreground antialiased h-[100dvh] w-full overflow-hidden select-none touch-manipulation selection:bg-brand-cyan/20 selection:text-brand-cyan">
        {children}
        <Toaster richColors position="bottom-left" dir="rtl" />
      </body>
    </html>
  );
}
