"use client";

import * as React from "react";
import { Building2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";

interface CreateOrgDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  name: string;
  onNameChange: (val: string) => void;
  code: string;
  onCodeChange: (val: string) => void;
  tokenLimit: number;
  onTokenLimitChange: (val: number) => void;
  onSubmit: (e: React.FormEvent) => void;
}

export function CreateOrgDialog({
  open,
  onOpenChange,
  name,
  onNameChange,
  code,
  onCodeChange,
  tokenLimit,
  onTokenLimitChange,
  onSubmit,
}: CreateOrgDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md bg-surface-raised border-border/40 text-on-surface" dir="rtl">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <div className="flex size-9 items-center justify-center rounded-xl bg-brand-cyan/10 border border-brand-cyan/20 text-brand-cyan">
              <Building2 className="size-5" />
            </div>
            <div>
              <DialogTitle className="text-base font-bold text-on-surface">
                تعریف سازمان جدید
              </DialogTitle>
              <DialogDescription className="text-xs text-on-surface-variant">
                ایجاد یک شرکت یا ارگان مستقل در کلاستر سازمانی
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <form onSubmit={onSubmit} className="space-y-4 py-2">
          <FieldGroup className="space-y-3">
            <Field>
              <FieldLabel className="text-xs font-semibold">نام سازمان *</FieldLabel>
              <Input
                placeholder="مثلاً: هلدینگ فناوری پیشرو"
                value={name}
                onChange={(e) => onNameChange(e.target.value)}
                className="bg-surface-container/50 text-sm"
                required
              />
            </Field>

            <div className="grid grid-cols-2 gap-3">
              <Field>
                <FieldLabel className="text-xs font-semibold">شناسه کوتاه (Code)</FieldLabel>
                <Input
                  placeholder="HPC"
                  value={code}
                  onChange={(e) => onCodeChange(e.target.value)}
                  className="bg-surface-container/50 text-sm font-mono uppercase"
                />
              </Field>

              <Field>
                <FieldLabel className="text-xs font-semibold">سقف توکن ماهانه</FieldLabel>
                <Input
                  type="number"
                  value={tokenLimit}
                  onChange={(e) => onTokenLimitChange(Number(e.target.value))}
                  className="bg-surface-container/50 text-sm font-mono"
                  step={500000}
                />
              </Field>
            </div>
          </FieldGroup>

          <DialogFooter className="gap-2 sm:gap-0 pt-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => onOpenChange(false)}
              className="text-xs"
            >
              انصراف
            </Button>
            <Button
              type="submit"
              size="sm"
              className="bg-brand-cyan hover:bg-brand-cyan-strong text-slate-950 font-bold text-xs"
            >
              ثبت سازمان
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
