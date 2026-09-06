"use client";

import * as React from "react";
import { Loader2, ArrowRight, CheckCircle2, AlertCircle, Activity } from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useTranslation } from "@/lib/locale";
import type { Workflow, ProgressStage, Language } from "@/lib/types";

export interface WorkflowProgressProps extends React.ComponentProps<"div"> {
  workflow?: Workflow | null;
  stage?: ProgressStage | string;
  label?: string;
  language?: Language;
  onNextActionClick?: (action: string) => void;
}

export function WorkflowProgress({
  workflow,
  stage,
  label,
  language = "fa",
  onNextActionClick,
  className,
  ...props
}: WorkflowProgressProps) {
  const t = useTranslation(language);

  const stageLabels: Record<string, string> = {
    understanding: language === "fa" ? "تحلیل درخواست کاربر..." : "Understanding query...",
    searching: language === "fa" ? "جستجوی پایگاه دانش Weaviate..." : "Searching knowledge base...",
    verifying: language === "fa" ? "بررسی شواهد..." : "Verifying evidence...",
    reasoning: language === "fa" ? "تولید پاسخ مستند..." : "Generating a grounded answer...",
    answering: language === "fa" ? "تکمیل پاسخ..." : "Finishing the answer...",
  };
  const defaultLabel = label || stageLabels[stage || "understanding"];

  return (
    <div
      data-slot="workflow-progress"
      role="status"
      aria-live="polite"
      className={cn(
        "w-full mb-4 bg-surface-container/20 rounded-2xl p-4 border border-border/20 relative overflow-hidden backdrop-blur-sm text-right rtl select-none",
        className
      )}
      {...props}
    >
      <div className="flex flex-col gap-2.5 relative z-10 text-right rtl">
        {/* Active Stage with Animated Spinner and Gradient Shimmer */}
        <div className="flex items-center gap-2 font-body-ui text-[14px]">
          <Loader2 className="size-4 animate-spin text-secondary shrink-0" />
          <span className="decorative-font animate-pulse-shimmer bg-clip-text text-transparent bg-gradient-to-r from-[#6EF0C2] to-[#31C8ED] font-semibold">
            {defaultLabel}
          </span>
        </div>

        {/* Workflow steps */}
        {workflow ? (
          <div className="space-y-2 pt-1">
            <div className="flex items-center justify-between gap-2 mr-6 text-on-surface-variant/80 text-[13px]">
              <span className="decorative-font font-medium">{workflow.goal}</span>
              {workflow.state === "resolved" ? (
                <Badge variant="outline" className="border-brand-mint/40 bg-brand-mint/10 text-brand-mint gap-1 text-[11px]">
                  <CheckCircle2 className="size-3" />
                  <span>{t.workflow.states.resolved}</span>
                </Badge>
              ) : workflow.state === "blocked" ? (
                <Badge variant="outline" className="border-warning/40 bg-warning/10 text-warning gap-1 text-[11px]">
                  <AlertCircle className="size-3" />
                  <span>{t.workflow.states.blocked}</span>
                </Badge>
              ) : (
                <Badge variant="outline" className="border-brand-cyan/40 bg-brand-cyan/10 text-brand-cyan gap-1 text-[11px]">
                  <Activity className="size-3" />
                  <span>{t.workflow.states[workflow.state] || workflow.state}</span>
                </Badge>
              )}
            </div>

            {workflow.nextAction && (
              <div className="flex items-center justify-between gap-2 mr-6 rounded-xl border border-brand-cyan/20 bg-brand-cyan/5 p-2.5 text-xs">
                <div className="flex flex-col gap-0.5">
                  <span className="text-[11px] font-semibold text-brand-cyan">{t.workflow.nextActionLabel}</span>
                  <span className="text-foreground">{workflow.nextAction}</span>
                </div>
                {onNextActionClick && (
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-7 text-xs border-brand-cyan/40 text-brand-cyan hover:bg-brand-cyan/10"
                    onClick={() => onNextActionClick(workflow.nextAction!)}
                  >
                    <span>{language === "fa" ? "اجرا" : "Run"}</span>
                    <ArrowRight className="size-3 rtl:rotate-180" />
                  </Button>
                )}
              </div>
            )}
          </div>
        ) : null}
      </div>
    </div>
  );
}
