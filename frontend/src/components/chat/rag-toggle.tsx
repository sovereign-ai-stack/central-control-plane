"use client";

import * as React from "react";
import { BookOpen } from "lucide-react";
import { cn } from "@/lib/utils";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import type { Language } from "@/lib/types";

export interface RagToggleProps {
  enabled: boolean;
  onToggle: (enabled: boolean) => void;
  disabled?: boolean;
  language?: Language;
  className?: string;
}

export function RagToggle({
  enabled,
  onToggle,
  disabled = false,
  language = "fa",
  className,
}: RagToggleProps) {
  const isFa = language === "fa";

  return (
    <TooltipProvider delayDuration={150}>
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            type="button"
            onClick={() => !disabled && onToggle(!enabled)}
            disabled={disabled}
            className={cn(
              "inline-flex items-center gap-1.5 h-8 px-2.5 rounded-xl text-[11px] sm:text-xs font-medium transition-all duration-300 select-none cursor-pointer outline-none focus:outline-none shrink-0",
              enabled
                ? "bg-brand-cyan/15 text-brand-cyan border border-brand-cyan/40 shadow-xs shadow-brand-cyan/20 hover:bg-brand-cyan/25 active:scale-95"
                : "bg-surface-raised/40 text-on-surface-variant/50 border border-border/30 hover:text-on-surface hover:bg-surface-raised/70 hover:border-border/60",
              disabled && "opacity-40 cursor-not-allowed",
              className
            )}
            aria-label={enabled ? "Disable Knowledge Base" : "Enable Knowledge Base"}
            aria-pressed={enabled}
          >
            <BookOpen
              className={cn(
                "size-3.5 shrink-0 transition-transform duration-300",
                enabled ? "text-brand-cyan scale-105" : "text-on-surface-variant/50"
              )}
            />

            <span className="decorative-font text-[11px] font-semibold">
              {isFa
                ? enabled
                  ? "پایگاه دانش"
                  : "پایگاه دانش (خاموش)"
                : enabled
                  ? "Knowledge Base"
                  : "Knowledge (Off)"}
            </span>

            {enabled ? (
              <span className="size-1.5 rounded-full bg-brand-mint shadow-xs shadow-brand-mint animate-pulse shrink-0" />
            ) : (
              <span className="size-1.5 rounded-full bg-on-surface-variant/30 shrink-0" />
            )}
          </button>
        </TooltipTrigger>
        <TooltipContent side="top" sideOffset={6} className="text-xs max-w-[240px] text-center" dir={isFa ? "rtl" : "ltr"}>
          {enabled
            ? isFa
              ? "جستجو در اسناد و پایگاه دانش سازمان فعال است (استخراج مدارک و ارجاعات موثق)"
              : "Knowledge base search is active (retrieving verified enterprise documents)"
            : isFa
              ? "کلیک کنید تا جستجو در اسناد فعال شود (اکنون در حالت هوش مصنوعی عمومی هستید)"
              : "Click to enable document search (currently in general AI mode)"}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
