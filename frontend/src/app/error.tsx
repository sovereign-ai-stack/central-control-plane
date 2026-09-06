"use client";

import * as React from "react";
import { AlertCircle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  React.useEffect(() => {
    // Log client error safely without sensitive data
    console.error("UI Error Boundary caught error:", error.message);
  }, [error]);

  return (
    <div className="flex min-h-screen w-full flex-col items-center justify-center p-6 bg-canvas text-foreground">
      <div className="flex max-w-md flex-col items-center gap-4 text-center rounded-2xl border border-border bg-surface p-8 shadow-xl">
        <div className="flex size-12 items-center justify-center rounded-full bg-destructive/10 text-destructive">
          <AlertCircle className="size-6" />
        </div>
        <h2 className="text-lg font-bold text-foreground">مشکلی در بارگذاری صفحه رخ داد</h2>
        <p className="text-xs text-muted-foreground leading-relaxed">
          خطایی در پردازش اطلاعات رخ داده است. می‌توانید با کلیک بر روی دکمه زیر صفحه را بازیابی کنید.
        </p>
        <Button
          onClick={() => reset()}
          className="mt-2 gap-2 bg-brand-cyan text-canvas hover:bg-brand-cyan/90"
        >
          <RefreshCw className="size-4" />
          <span>تلاش مجدد (Retry)</span>
        </Button>
      </div>
    </div>
  );
}
