"use client";

import * as React from "react";
import { FolderTree } from "lucide-react";
import { Button } from "@/components/ui/button";
import { CustomSelect } from "@/components/ui/custom-select";
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
import type { Organization } from "@/lib/types";

interface CreateTeamDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  name: string;
  onNameChange: (val: string) => void;
  orgId: string;
  onOrgIdChange: (val: string) => void;
  tokenLimit: number;
  onTokenLimitChange: (val: number) => void;
  rpm: number;
  onRpmChange: (val: number) => void;
  organizations: Organization[];
  onSubmit: (e: React.FormEvent) => void;
}

export function CreateTeamDialog({
  open,
  onOpenChange,
  name,
  onNameChange,
  orgId,
  onOrgIdChange,
  tokenLimit,
  onTokenLimitChange,
  rpm,
  onRpmChange,
  organizations,
  onSubmit,
}: CreateTeamDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md bg-surface-raised border-border/40 text-on-surface" dir="rtl">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <div className="flex size-9 items-center justify-center rounded-xl bg-brand-cyan/10 border border-brand-cyan/20 text-brand-cyan">
              <FolderTree className="size-5" />
            </div>
            <div>
              <DialogTitle className="text-base font-bold text-on-surface">تعریف تیم جدید</DialogTitle>
              <DialogDescription className="text-xs text-on-surface-variant">
                ایجاد دپارتمان یا واحد کاری مستقل با کوتای مشخص
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <form onSubmit={onSubmit} className="space-y-4 py-2">
          <FieldGroup className="space-y-3">
            <Field>
              <FieldLabel className="text-xs font-semibold">سازمان مربوطه *</FieldLabel>
              <CustomSelect
                value={orgId}
                onChange={onOrgIdChange}
                options={[
                  { value: "", label: "انتخاب سازمان..." },
                  ...organizations.map((o) => ({ value: o.id, label: `${o.name} (${o.code || o.id})` })),
                ]}
                className="w-full bg-surface-container/50 text-sm"
              />
            </Field>

            <Field>
              <FieldLabel className="text-xs font-semibold">نام تیم / واحد *</FieldLabel>
              <Input
                placeholder="مثلاً: واحد هوش مصنوعی و داده"
                value={name}
                onChange={(e) => onNameChange(e.target.value)}
                className="bg-surface-container/50 text-sm"
                required
              />
            </Field>

            <div className="grid grid-cols-2 gap-3">
              <Field>
                <FieldLabel className="text-xs font-semibold">سقف توکن ماهانه</FieldLabel>
                <Input
                  type="number"
                  value={tokenLimit}
                  onChange={(e) => onTokenLimitChange(Number(e.target.value))}
                  className="bg-surface-container/50 text-sm font-mono"
                  step={100000}
                />
              </Field>

              <Field>
                <FieldLabel className="text-xs font-semibold">محدودیت RPM (درخواست/دقیقه)</FieldLabel>
                <Input
                  type="number"
                  value={rpm}
                  onChange={(e) => onRpmChange(Number(e.target.value))}
                  className="bg-surface-container/50 text-sm font-mono"
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
              ثبت تیم
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
