"use client";

import * as React from "react";
import { ExternalLink, CheckCircle2, AlertTriangle, HelpCircle, Link as LinkIcon, BookOpen } from "lucide-react";
import { cn } from "@/lib/utils";
import { useTranslation } from "@/lib/locale";
import type { Citation, Language } from "@/lib/types";

export interface SourceCardProps extends React.ComponentProps<"div"> {
  citation: Citation;
  index?: number;
  language?: Language;
  isHighlighted?: boolean;
  onSelect?: () => void;
}

export function SourceCard({
  citation,
  language = "fa",
  isHighlighted = false,
  onSelect,
  className,
  ...props
}: SourceCardProps) {
  const t = useTranslation(language);
  const cardRef = React.useRef<HTMLDivElement | null>(null);

  React.useEffect(() => {
    if (isHighlighted && cardRef.current) {
      cardRef.current.scrollIntoView({
        behavior: "smooth",
        block: "nearest",
      });
    }
  }, [isHighlighted]);

  const getStatusBadge = () => {
    switch (citation.supportStatus) {
      case "supported":
        return (
          <div className="bg-[#59dcb0]/15 text-[#59dcb0] border border-[#59dcb0]/30 px-2 py-0.5 rounded-lg text-[10.5px] font-medium flex items-center gap-1">
            <CheckCircle2 className="size-3" />
            <span>{t.sources.officialBadge}</span>
          </div>
        );
      case "conflict":
        return (
          <div className="bg-destructive/15 text-destructive border border-destructive/30 px-2 py-0.5 rounded-lg text-[10.5px] font-medium flex items-center gap-1">
            <AlertTriangle className="size-3" />
            <span>{t.sources.conflictBadge}</span>
          </div>
        );
      case "insufficient":
        return (
          <div className="bg-warning/15 text-warning border border-warning/30 px-2 py-0.5 rounded-lg text-[10.5px] font-medium flex items-center gap-1">
            <HelpCircle className="size-3" />
            <span>{t.sources.insufficientBadge}</span>
          </div>
        );
      default:
        return (
          <div className="bg-surface-raised/80 text-on-surface-variant border border-border/40 px-2 py-0.5 rounded-lg text-[10.5px] font-medium flex items-center gap-1">
            <CheckCircle2 className="size-3 text-brand-mint" />
            <span>{t.sources.officialBadge}</span>
          </div>
        );
    }
  };

  return (
    <div
      ref={cardRef}
      data-slot="source-card"
      className={cn(
        "bg-surface-raised/40 hover:bg-surface-raised/80 rounded-2xl border border-border/40 overflow-hidden shadow-xs relative group p-4 space-y-3 transition-all duration-300 hover:border-brand-cyan/40 cursor-pointer backdrop-blur-xs",
        isHighlighted && "border-brand-cyan/70 ring-1 ring-brand-cyan/50 bg-brand-cyan/[0.08] shadow-md shadow-brand-cyan/15 scale-[1.01]",
        className
      )}
      onClick={onSelect}
      {...props}
    >
      {/* Associated Prompt Tag (if available) */}
      {citation.promptSnippet && (
        <div className="bg-surface-container/60 border border-border/40 rounded-xl px-2.5 py-1.5 text-[11px] text-brand-cyan font-medium flex items-center gap-1.5 text-right dir-rtl">
          <span className="opacity-60 text-[10px]">{language === "fa" ? "مربوط به:" : "Query:"}</span>
          <span className="font-semibold truncate">«{citation.promptSnippet}»</span>
        </div>
      )}

      {/* Header with Type & Status */}
      <div className="flex justify-between items-center gap-2">
        <div className="flex items-center gap-1.5 text-on-surface-variant/80 text-[11px] font-medium">
          <BookOpen className="size-3.5 text-brand-cyan shrink-0" />
          <span>{language === "fa" ? "پایگاه دانش سازمانی" : "Knowledge Base"}</span>
        </div>
        {getStatusBadge()}
      </div>

      {/* Document Title */}
      <h4 className="font-bold text-[13.5px] text-on-surface decorative-font leading-snug text-right dir-rtl group-hover:text-brand-cyan transition-colors">
        {citation.title}
      </h4>

      {/* Prominent Full-Width Document Location */}
      {citation.section && (
        <div className="bg-surface-container/60 border border-brand-cyan/20 rounded-xl px-3 py-2 flex items-center justify-between text-right dir-rtl">
          <span className="text-[11px] text-on-surface-variant/80 font-medium">
            {language === "fa" ? "موقعیت در سند:" : "Location:"}
          </span>
          <span className="text-[12px] font-bold text-brand-cyan">
            {citation.section}
          </span>
        </div>
      )}

      {/* Footer Click Prompt */}
      <div className="pt-2 border-t border-border/20 flex items-center justify-between text-[11.5px] font-semibold text-brand-cyan group-hover:text-[#80e5ff] transition-colors" dir="rtl">
        <span className="flex items-center gap-1.5">
          <BookOpen className="size-3.5" />
          <span>{language === "fa" ? "کلیک جهت مشاهده متن قطعه (Snippet)" : "Click to view extracted snippet"}</span>
        </span>
        <span className="text-[10px] bg-brand-cyan/15 border border-brand-cyan/25 px-2 py-0.5 rounded-lg">
          {language === "fa" ? "مشاهده" : "View"}
        </span>
      </div>
    </div>
  );
}
