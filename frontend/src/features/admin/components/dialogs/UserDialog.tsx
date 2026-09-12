"use client";

import * as React from "react";
import { LockKeyhole, Shield, UserCheck, UserPlus, Users, UserX } from "lucide-react";
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
import type { Organization, Team, UserRole } from "@/lib/types";

interface UserDialogProps {
  mode: "create" | "edit";
  open: boolean;
  onOpenChange: (open: boolean) => void;
  name: string;
  onNameChange: (val: string) => void;
  email: string;
  onEmailChange?: (val: string) => void;
  password: string;
  onPasswordChange: (val: string) => void;
  role: UserRole;
  onRoleChange: (val: UserRole) => void;
  orgId: string;
  onOrgIdChange: (val: string) => void;
  teamId: string;
  onTeamIdChange: (val: string) => void;
  tokenLimit: number;
  onTokenLimitChange: (val: number) => void;
  isActive?: boolean;
  onIsActiveChange?: (val: boolean) => void;
  organizations: Organization[];
  teams: Team[];
  currentUserRole?: UserRole;
  onSubmit: (e: React.FormEvent) => void;
}

export function UserDialog({
  mode,
  open,
  onOpenChange,
  name,
  onNameChange,
  email,
  onEmailChange,
  password,
  onPasswordChange,
  role,
  onRoleChange,
  orgId,
  onOrgIdChange,
  teamId,
  onTeamIdChange,
  tokenLimit,
  onTokenLimitChange,
  isActive,
  onIsActiveChange,
  organizations,
  teams,
  currentUserRole = "user",
  onSubmit,
}: UserDialogProps) {
  const isSuperAdmin = currentUserRole === "super_admin";
  const isOrgAdmin = currentUserRole === "org_admin";

  const availableTeams = orgId ? teams.filter((t) => t.organizationId === orgId) : [];

  const handleOrgChange = (newOrgId: string) => {
    onOrgIdChange(newOrgId);
    if (!newOrgId) {
      onTeamIdChange("");
    } else {
      const orgTeams = teams.filter((t) => t.organizationId === newOrgId);
      const isCurrentTeamValid = orgTeams.some((t) => t.id === teamId);
      if (!isCurrentTeamValid) {
        onTeamIdChange("");
      }
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md bg-surface-raised border-border/40 text-on-surface" dir="rtl">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <div className="flex size-9 items-center justify-center rounded-xl bg-brand-cyan/10 border border-brand-cyan/20 text-brand-cyan">
              {mode === "create" ? <UserPlus className="size-5" /> : <Users className="size-5" />}
            </div>
            <div>
              <DialogTitle className="text-base font-bold text-on-surface">
                {mode === "create" ? "تعریف کاربر جدید" : "ویرایش مشخصات کاربر"}
              </DialogTitle>
              <DialogDescription className="text-xs text-on-surface-variant">
                {mode === "create"
                  ? "صدور دسترسی جدید و تنظیم سهمیه توکن اختصاصی"
                  : "تغییر نقش، کلمه عبور، سهمیه یا وضعیت فعالیت کاربر"}
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <form onSubmit={onSubmit} className="space-y-4 py-2">
          <FieldGroup className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <Field>
                <FieldLabel className="text-xs font-semibold">نام و نام خانوادگی *</FieldLabel>
                <Input
                  placeholder="مهدی جعفری"
                  value={name}
                  onChange={(e) => onNameChange(e.target.value)}
                  className="bg-surface-container/50 text-sm"
                  required
                />
              </Field>

              <Field>
                <FieldLabel className="text-xs font-semibold">ایمیل سازمانی *</FieldLabel>
                <Input
                  type="email"
                  placeholder="user@organization.local"
                  value={email}
                  onChange={(e) => onEmailChange?.(e.target.value)}
                  disabled={mode === "edit"}
                  className="bg-surface-container/50 text-sm font-mono"
                  required
                />
              </Field>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <Field>
                <FieldLabel className="text-xs font-semibold">
                  {mode === "create" ? "کلمه عبور *" : "گذرواژه جدید (اختیاری)"}
                </FieldLabel>
                <Input
                  type="password"
                  placeholder={mode === "create" ? "••••••••" : "تغییر گذرواژه..."}
                  value={password}
                  onChange={(e) => onPasswordChange(e.target.value)}
                  className="bg-surface-container/50 text-sm font-mono"
                  required={mode === "create"}
                />
              </Field>

              <Field>
                <FieldLabel className="text-xs font-semibold">نقش کاربری *</FieldLabel>
                <CustomSelect
                  value={role}
                  onChange={(val) => onRoleChange(val as UserRole)}
                  options={[
                    ...(isSuperAdmin ? [{ value: "super_admin", label: "مدیر کل سیستم (Super Admin)" }] : []),
                    ...(isSuperAdmin || isOrgAdmin ? [{ value: "org_admin", label: "مدیر سازمان (Org Admin)" }] : []),
                    { value: "team_admin", label: "مدیر تیم (Team Admin)" },
                    { value: "user", label: "کاربر عادی (User)" },
                  ]}
                  className="w-full bg-surface-container/50 text-xs"
                />
              </Field>
            </div>

            {isSuperAdmin && (
              <Field>
                <FieldLabel className="text-xs font-semibold">سازمان مربوطه</FieldLabel>
                <CustomSelect
                  value={orgId}
                  onChange={handleOrgChange}
                  options={[
                    { value: "", label: "سازمان عمومی / بدون سازمان" },
                    ...organizations.map((o) => ({ value: o.id, label: `${o.name} (${o.code || o.id})` })),
                  ]}
                  className="w-full bg-surface-container/50 text-xs"
                />
              </Field>
            )}

            <div className="grid grid-cols-2 gap-3">
              <Field>
                <FieldLabel className="text-xs font-semibold">تیم / دپارتمان</FieldLabel>
                <CustomSelect
                  value={teamId}
                  onChange={onTeamIdChange}
                  disabled={!orgId}
                  options={[
                    { value: "", label: "بدون تیم / دسترسی عمومی" },
                    ...availableTeams.map((t) => ({ value: t.id, label: t.name })),
                  ]}
                  className="w-full bg-surface-container/50 text-xs disabled:opacity-70"
                />
              </Field>

              <Field>
                <FieldLabel className="text-xs font-semibold">سقف توکن ماهانه</FieldLabel>
                <Input
                  type="number"
                  value={tokenLimit}
                  onChange={(e) => onTokenLimitChange(Number(e.target.value))}
                  className="bg-surface-container/50 text-sm font-mono"
                  step={50000}
                />
              </Field>
            </div>

            {mode === "edit" && onIsActiveChange && (
              <div className="flex items-center justify-between p-3 rounded-xl bg-surface-container/30 border border-border/30">
                <div className="flex items-center gap-2">
                  {isActive ? (
                    <UserCheck className="size-4 text-brand-cyan" />
                  ) : (
                    <UserX className="size-4 text-destructive" />
                  )}
                  <span className="text-xs font-semibold text-on-surface">وضعیت حساب کاربری:</span>
                </div>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => onIsActiveChange(!isActive)}
                  className={`text-xs h-7 ${isActive ? "text-brand-cyan border-brand-cyan/30" : "text-destructive border-destructive/30"}`}
                >
                  {isActive ? "حساب فعال است" : "حساب غیرفعال است"}
                </Button>
              </div>
            )}
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
              {mode === "create" ? "ایجاد کاربر" : "ذخیره تغییرات"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
