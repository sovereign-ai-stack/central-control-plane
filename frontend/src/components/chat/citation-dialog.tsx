"use client";

import * as React from "react";
import { BookOpen, Check, Copy, FileText, Sparkles, X, ShieldCheck } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { Citation, Language } from "@/lib/types";

export interface CitationDialogProps {
  citation: Citation | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  language?: Language;
}

export function CitationDialog({
  citation,
  open,
  onOpenChange,
  language = "fa",
}: CitationDialogProps) {
  const [copied, setCopied] = React.useState(false);

  if (!citation) return null;

  const isFa = language === "fa";
  const snippetText = citation.snippet || citation.excerpt || (isFa ? "متن قطعه استناد شده در دسترس است." : "Referenced snippet available.");

  const handleCopy = () => {
    navigator.clipboard.writeText(snippetText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl bg-[#14161E]/95 backdrop-blur-xl border-border/80 text-foreground rounded-3xl p-6 shadow-2xl">
        <DialogHeader className="space-y-3 pb-3 border-b border-border/40">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="size-10 rounded-2xl bg-brand-cyan/15 border border-brand-cyan/30 flex items-center justify-center text-brand-cyan">
                <FileText className="size-5" />
              </div>
              <div>
                <DialogTitle className="text-sm font-bold text-foreground line-clamp-1">
                  {citation.title || (isFa ? "سند سازمانی موثق" : "Enterprise Document")}
                </DialogTitle>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-[11px] text-muted-foreground font-mono">
                    {citation.section || (isFa ? "پایگاه دانش اسناد" : "Knowledge Base")}
                  </span>
                </div>
              </div>
            </div>

            <Badge className="text-[10px] bg-brand-mint/15 text-brand-mint border border-brand-mint/30 rounded-full flex items-center gap-1 font-bold">
              <ShieldCheck className="size-3" />
              <span>{isFa ? "تایید شده و موثق" : "Grounded & Verified"}</span>
            </Badge>
          </div>
        </DialogHeader>

        <div className="space-y-4 py-3">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-muted-foreground flex items-center gap-1.5">
                <Sparkles className="size-3.5 text-brand-cyan" />
                <span>{isFa ? "متن دقیق استخراج‌شده از سند (RAG Grounding Snippet):" : "Exact Extracted Document Snippet:"}</span>
              </span>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={handleCopy}
                className="h-7 px-2.5 text-xs text-brand-cyan hover:bg-brand-cyan/10 rounded-xl gap-1.5 cursor-pointer"
              >
                {copied ? <Check className="size-3 text-brand-mint" /> : <Copy className="size-3" />}
                <span>{copied ? (isFa ? "کپی شد" : "Copied") : (isFa ? "کپی متن" : "Copy")}</span>
              </Button>
            </div>

            <div
              dir="auto"
              className="bg-surface/70 border border-border/50 rounded-2xl p-4 text-xs md:text-[13px] leading-relaxed text-foreground/90 font-serif selection:bg-brand-cyan/30 shadow-inner max-h-[260px] overflow-y-auto"
            >
              <blockquote className="border-s-3 border-brand-cyan ps-3 my-0 italic">
                {snippetText}
              </blockquote>
            </div>
          </div>

          <div className="bg-brand-cyan/5 border border-brand-cyan/15 rounded-2xl p-3 flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <BookOpen className="size-4 text-brand-cyan" />
              <span className="text-muted-foreground text-[11px]">
                {isFa ? "این بخش مستقیماً از پایگاه دانش وکتوری استخراج شده و مبنای پاسخ مدل بوده است." : "This snippet was retrieved directly from vector storage as context for the answer."}
              </span>
            </div>
          </div>
        </div>

        <div className="flex justify-end pt-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => onOpenChange(false)}
            className="h-8 px-4 rounded-xl text-xs font-semibold hover:bg-surface"
          >
            {isFa ? "بستن پنجره" : "Close"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
