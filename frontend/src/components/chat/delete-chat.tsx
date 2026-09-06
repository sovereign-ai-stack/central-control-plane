"use client";

import * as React from "react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { cn } from "@/lib/utils";
import { useTranslation } from "@/lib/locale";
import type { Language } from "@/lib/types";

export interface DeleteChatDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
  language?: Language;
}

export function DeleteChatDialog({
  open,
  onOpenChange,
  onConfirm,
  language = "fa",
}: DeleteChatDialogProps) {
  const t = useTranslation(language);
  const isRtl = language === "fa";

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent
        dir={isRtl ? "rtl" : "ltr"}
        className="border border-border bg-surface-raised text-foreground sm:max-w-md"
      >
        <AlertDialogHeader className={cn(isRtl ? "text-right sm:text-right" : "text-left sm:text-left")}>
          <AlertDialogTitle className="text-base font-bold text-foreground">
            {t.actions.confirmDeleteTitle}
          </AlertDialogTitle>
          <AlertDialogDescription className="text-xs text-muted-foreground leading-relaxed">
            {t.actions.confirmDeleteDesc}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter
          className={cn(
            "mt-4 flex flex-row gap-2 sm:space-x-0",
            isRtl ? "justify-start sm:justify-start" : "justify-end sm:justify-end"
          )}
        >
          {isRtl ? (
            <>
              <AlertDialogAction
                onClick={onConfirm}
                className="bg-destructive text-destructive-foreground hover:bg-destructive/90 font-bold"
              >
                {t.actions.confirm}
              </AlertDialogAction>
              <AlertDialogCancel className="border-border bg-surface text-foreground hover:bg-surface-active mt-0">
                {t.actions.cancel}
              </AlertDialogCancel>
            </>
          ) : (
            <>
              <AlertDialogCancel className="border-border bg-surface text-foreground hover:bg-surface-active mt-0">
                {t.actions.cancel}
              </AlertDialogCancel>
              <AlertDialogAction
                onClick={onConfirm}
                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              >
                {t.actions.confirm}
              </AlertDialogAction>
            </>
          )}
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
