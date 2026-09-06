"use client";

import * as React from "react";
import { Check, Copy, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { useTranslation } from "@/lib/locale";
import { cn } from "@/lib/utils";
import type { Language } from "@/lib/types";

export interface ShareDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  url: string | null;
  language?: Language;
}

export function ShareDialog({ open, onOpenChange, url, language = "fa" }: ShareDialogProps) {
  const t = useTranslation(language);
  const isRtl = language === "fa";
  const [copied, setCopied] = React.useState(false);

  React.useEffect(() => {
    if (!open) setCopied(false);
  }, [open]);

  const copyLink = async () => {
    if (!url) return;
    await navigator.clipboard.writeText(url);
    setCopied(true);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        dir={isRtl ? "rtl" : "ltr"}
        className="border-border/40 bg-surface-raised text-foreground sm:max-w-lg shadow-2xl rounded-2xl"
      >
        <DialogHeader className={cn("space-y-1.5 w-full", isRtl ? "text-right" : "text-left")}>
          <DialogTitle className={cn("text-base sm:text-lg font-bold text-on-surface decorative-font w-full", isRtl ? "text-right" : "text-left")}>
            {t.actions.share}
          </DialogTitle>
          <DialogDescription className={cn("text-xs sm:text-[13px] text-on-surface-variant/80 leading-relaxed w-full", isRtl ? "text-right" : "text-left")}>
            {language === "fa"
              ? "هر کسی که این پیوند را داشته باشد می‌تواند یک نسخه فقط‌خواندنی از گفتگو را ببیند."
              : "Anyone with this link can view a read-only snapshot of this conversation."}
          </DialogDescription>
        </DialogHeader>

        {/* Share Link Input (Right in RTL) & Copy Button (Left in RTL) */}
        <div className="flex items-center gap-2 w-full pt-1" dir={isRtl ? "rtl" : "ltr"}>
          <Input
            value={url || ""}
            readOnly
            dir="ltr"
            aria-label={t.actions.share}
            tabIndex={-1}
            style={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace' }}
            className="flex-1 min-w-0 bg-surface/80 border border-border/40 text-xs text-slate-300 text-left px-3 h-9 rounded-xl focus-visible:ring-0 focus-visible:ring-offset-0 focus:outline-none focus:ring-0 select-text"
          />
          <Button
            type="button"
            onClick={copyLink}
            disabled={!url}
            className="shrink-0 gap-1.5 bg-brand-cyan text-[#121319] hover:bg-brand-cyan/90 font-medium text-xs h-9 px-3.5 rounded-xl shadow-sm active:scale-95 transition-all cursor-pointer"
          >
            {copied ? (
              <Check className="size-3.5 text-[#121319]" />
            ) : (
              <Copy className="size-3.5 text-[#121319]" />
            )}
            <span>{copied ? t.actions.copiedLink : t.actions.copyLink}</span>
          </Button>
        </div>

        {/* Modal Footer: Open Link on Right in RTL (with icon on left of text), Close on Left in RTL */}
        <DialogFooter className="flex flex-row items-center justify-between sm:justify-between pt-2 border-t border-border/20 mt-1">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            asChild
            disabled={!url}
            className="text-xs text-brand-cyan hover:text-brand-cyan hover:bg-brand-cyan/10 active:scale-95 transition-all cursor-pointer px-2.5 h-8 rounded-lg"
          >
            <a
              href={url || "#"}
              target="_blank"
              rel="noopener noreferrer"
              className={cn("flex items-center gap-1.5 font-medium", isRtl && "flex-row-reverse")}
            >
              <ExternalLink className="size-3.5 shrink-0" />
              <span>{language === "fa" ? "باز کردن پیوند" : "Open link"}</span>
            </a>
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => onOpenChange(false)}
            className="text-xs border-border/40 hover:bg-surface-raised active:scale-95 transition-all cursor-pointer px-4 h-8 rounded-lg"
          >
            {language === "fa" ? "بستن" : "Close"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
