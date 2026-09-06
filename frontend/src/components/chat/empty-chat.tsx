"use client";

import * as React from "react";
import { Activity, BookOpen, Rocket, Wrench } from "lucide-react";
import { cn } from "@/lib/utils";
import { BrandLogoIcon } from "@/components/ui/brand-logo";
import { useTranslation } from "@/lib/locale";
import type { Language } from "@/lib/types";

export interface EmptyChatProps extends React.ComponentProps<"div"> {
  onSelectStarter: (prompt: string) => void;
  language?: Language;
  disabled?: boolean;
}

export function EmptyChat({
  onSelectStarter,
  language = "fa",
  disabled = false,
  className,
  ...props
}: EmptyChatProps) {
  const t = useTranslation(language);

  const starterItems = [
    {
      key: "findDocs",
      icon: BookOpen,
      color: "text-brand-cyan",
      bg: "bg-brand-cyan/10 border-brand-cyan/20",
      ...t.starters.findDocs,
    },
    {
      key: "diagnoseError",
      icon: Wrench,
      color: "text-warning",
      bg: "bg-warning/10 border-warning/20",
      ...t.starters.diagnoseError,
    },
    {
      key: "prepareDeploy",
      icon: Rocket,
      color: "text-brand-mint",
      bg: "bg-brand-mint/10 border-brand-mint/20",
      ...t.starters.prepareDeploy,
    },
    {
      key: "serviceStatus",
      icon: Activity,
      color: "text-brand-mint",
      bg: "bg-brand-mint/10 border-brand-mint/20",
      ...t.starters.serviceStatus,
    },
  ];

  return (
    <div
      data-slot="empty-chat"
      className={cn(
        "flex flex-1 flex-col items-center justify-center p-3 sm:p-6 md:p-8 max-w-3xl mx-auto w-full select-none overflow-y-auto pb-28 sm:pb-32",
        className
      )}
      {...props}
    >
      <div className="w-full flex flex-col items-center text-center my-auto">
        {/* Logo Media with Brand Gradient Aura */}
        <div className="mb-4 sm:mb-6 relative flex size-12 sm:size-16 items-center justify-center rounded-2xl sm:rounded-3xl bg-surface-container/60 border border-border/40 shadow-xl shadow-primary/10">
          <div className="size-8 sm:size-10 flex items-center justify-center">
            <BrandLogoIcon className="size-7 sm:size-9" />
          </div>
        </div>

        <div className="max-w-xl text-center mb-6 sm:mb-8 px-2">
          <h2 className="text-lg sm:text-2xl font-bold tracking-tight text-on-surface decorative-font">
            {t.emptyTitle}
          </h2>
        </div>

        <div
          data-testid="starter-actions"
          className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 w-full max-w-2xl px-1 sm:px-0"
        >
          {starterItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.key}
                type="button"
                onClick={() => onSelectStarter(item.prompt)}
                disabled={disabled}
                aria-busy={disabled}
                className="group flex flex-col items-start gap-1.5 sm:gap-2 rounded-xl sm:rounded-2xl border border-border/30 bg-surface-container/30 backdrop-blur-sm p-3 sm:p-4 text-start transition-all hover:border-[#6EF0C2]/40 hover:bg-surface-raised/60 hover:shadow-lg hover:shadow-black/20 active:scale-[0.98] cursor-pointer disabled:cursor-wait disabled:opacity-60 disabled:hover:border-border/30 disabled:hover:bg-surface-container/30 disabled:hover:shadow-none"
              >
                <div className="flex items-center gap-2 sm:gap-2.5">
                  <div className={cn("flex size-7 sm:size-8 items-center justify-center rounded-lg sm:rounded-xl border shrink-0", item.bg)}>
                    <Icon className={cn("size-3.5 sm:size-4", item.color)} />
                  </div>
                  <span className="text-[12px] sm:text-[13px] font-bold text-on-surface group-hover:text-brand-cyan transition-colors decorative-font line-clamp-1">
                    {item.title}
                  </span>
                </div>
                <p className="text-[10.5px] sm:text-[11px] text-on-surface-variant/70 leading-relaxed line-clamp-2 ps-9 sm:ps-10">
                  {item.desc}
                </p>
              </button>
            );
          })}
        </div>

        <div className="mt-5 sm:mt-8 flex items-center justify-center text-center px-2">
          <p className="text-[10px] sm:text-[11px] text-on-surface-variant/60 leading-normal max-w-md bg-surface-container-low/30 backdrop-blur-sm border border-border/20 rounded-xl px-3 sm:px-4 py-1.5 sm:py-2">
            {t.privacyNote}
          </p>
        </div>
      </div>
    </div>
  );
}
