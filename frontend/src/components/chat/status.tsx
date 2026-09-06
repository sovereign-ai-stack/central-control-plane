"use client";

import * as React from "react";
import { AlertCircle, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { useTranslation } from "@/lib/locale";
import type { Language } from "@/lib/types";

export function MessageSkeleton({ className }: { className?: string }) {
  return (
    <div
      data-slot="message-skeleton"
      className={cn("flex w-full flex-col gap-3 py-2", className)}
    >
      <div className="flex items-center gap-3">
        <Skeleton className="size-8 rounded-full bg-surface-raised" />
        <Skeleton className="h-4 w-32 bg-surface-raised" />
      </div>
      <div className="ps-11 flex flex-col gap-2">
        <Skeleton className="h-4 w-3/4 bg-surface-raised" />
        <Skeleton className="h-4 w-full bg-surface-raised" />
        <Skeleton className="h-4 w-1/2 bg-surface-raised" />
      </div>
    </div>
  );
}

export interface ErrorAlertProps extends React.ComponentProps<typeof Alert> {
  title?: string;
  description: string;
  retryable?: boolean;
  onRetry?: () => void;
  language?: Language;
}

export function ErrorAlert({
  title,
  description,
  retryable = false,
  onRetry,
  language = "fa",
  className,
  ...props
}: ErrorAlertProps) {
  const t = useTranslation(language);

  return (
    <Alert
      variant="destructive"
      className={cn("my-3 border-destructive/30 bg-destructive/10 text-foreground", className)}
      {...props}
    >
      <AlertCircle className="size-4 text-destructive" />
      <div className="flex flex-1 flex-col gap-1">
        {title && <AlertTitle className="font-semibold text-destructive">{title}</AlertTitle>}
        <AlertDescription className="text-xs text-foreground-muted leading-relaxed">
          {description}
        </AlertDescription>
        {retryable && onRetry && (
          <div className="mt-2">
            <Button
              size="sm"
              variant="outline"
              onClick={onRetry}
              className="h-7 gap-1.5 border-destructive/40 text-xs text-destructive hover:bg-destructive/15"
            >
              <RefreshCw className="size-3" data-icon="inline-start" />
              <span>{t.actions.retry}</span>
            </Button>
          </div>
        )}
      </div>
    </Alert>
  );
}
