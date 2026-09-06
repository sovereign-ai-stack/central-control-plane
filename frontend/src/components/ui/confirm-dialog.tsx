"use client";

import * as React from "react";
import { AlertTriangle, ShieldAlert, Trash2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

interface ConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  confirmText?: string;
  cancelText?: string;
  variant?: "destructive" | "warning" | "default";
  onConfirm: () => void;
  loading?: boolean;
}

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmText = "تأیید و حذف",
  cancelText = "انصراف",
  variant = "destructive",
  onConfirm,
  loading = false,
}: ConfirmDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md bg-[#181922] border-border/80 text-foreground rounded-3xl p-6 shadow-2xl backdrop-blur-xl">
        <DialogHeader className="space-y-3">
          <div className="flex items-center gap-3">
            <div className="size-11 rounded-2xl bg-destructive/15 border border-destructive/30 flex items-center justify-center shrink-0 shadow-sm shadow-destructive/20">
              <ShieldAlert className="size-6 text-destructive animate-pulse" />
            </div>
            <div>
              <DialogTitle className="text-base font-bold text-foreground text-start">
                {title}
              </DialogTitle>
              <DialogDescription className="text-xs text-muted-foreground mt-1 text-start leading-relaxed">
                {description}
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <DialogFooter className="pt-4 flex flex-row items-center justify-end gap-2.5">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => onOpenChange(false)}
            disabled={loading}
            className="rounded-xl border-border/70 hover:bg-surface text-xs font-semibold px-4 h-9"
          >
            {cancelText}
          </Button>
          <Button
            type="button"
            variant={variant === "destructive" ? "destructive" : "default"}
            size="sm"
            onClick={() => {
              onConfirm();
              onOpenChange(false);
            }}
            disabled={loading}
            className="rounded-xl bg-destructive hover:bg-destructive/90 text-white text-xs font-bold px-4 h-9 shadow-md shadow-destructive/20 gap-1.5"
          >
            <Trash2 className="size-3.5" />
            <span>{confirmText}</span>
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
