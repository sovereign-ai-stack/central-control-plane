"use client";

import * as React from "react";
import { BookOpen, X, Sparkles, CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { SourceCard } from "./source-card";
import { useTranslation } from "@/lib/locale";
import type { Citation, ContextFact, Language } from "@/lib/types";

export interface SourceListProps extends React.ComponentProps<"div"> {
  citations: Citation[];
  contextFacts?: ContextFact[];
  language?: Language;
  highlightedMessageId?: string | null;
  onClose?: () => void;
  onSelectCitation?: (citation: Citation) => void;
}

export function SourceList({
  citations,
  contextFacts = [],
  language = "fa",
  highlightedMessageId,
  onClose,
  onSelectCitation,
  className,
  ...props
}: SourceListProps) {
  const t = useTranslation(language);

  return (
    <div
      data-slot="source-list"
      className={cn("flex h-full flex-col overflow-hidden select-none", className)}
      {...props}
    >
      {/* Header matching Reference HTML */}
      <div className="p-5 flex items-center justify-between border-b border-border/30">
        <h3 className="font-semibold text-[16px] text-on-surface decorative-font">
          {language === "fa" ? "منابع ارجاع داده شده" : t.sources.title}
        </h3>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className="text-on-surface-variant hover:text-on-surface p-1 rounded-lg hover:bg-surface-raised transition-colors cursor-pointer"
            aria-label="Close sources panel"
          >
            <X className="size-4" />
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {citations.length === 0 && contextFacts.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-6 text-center text-on-surface-variant">
            <BookOpen className="size-8 text-brand-cyan/40 mb-3" />
            <p className="text-xs leading-relaxed max-w-[220px]">
              {t.sources.empty}
            </p>
          </div>
        ) : (
          <>
            {/* Citations List */}
            {citations.map((citation, idx) => (
              <SourceCard
                key={`${citation.url}-${citation.messageId || ""}-${idx}`}
                citation={citation}
                index={idx}
                language={language}
                isHighlighted={Boolean(highlightedMessageId && citation.messageId === highlightedMessageId)}
                onSelect={() => onSelectCitation?.(citation)}
              />
            ))}

            {/* Project Context Facts */}
            {contextFacts.length > 0 && (
              <div className="pt-3 border-t border-border/30 space-y-2.5">
                <div className="flex items-center gap-2 text-xs font-bold text-on-surface decorative-font">
                  <Sparkles className="size-3.5 text-brand-mint" />
                  <span>{t.sources.contextTitle}</span>
                </div>
                <div className="space-y-2">
                  {contextFacts.map((fact, idx) => (
                    <div
                      key={idx}
                      className="rounded-xl border border-border/30 bg-surface-container-low/40 p-3 text-xs text-on-surface flex flex-col gap-1"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-[11px] text-brand-cyan">
                          {fact.key}
                        </span>
                        <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                          <CheckCircle2 className="size-2.5 text-brand-mint" />
                          {fact.status === "confirmed" ? t.sources.confirmed : t.sources.inferred}
                        </span>
                      </div>
                      <span className="font-semibold text-foreground">
                        {fact.value}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
