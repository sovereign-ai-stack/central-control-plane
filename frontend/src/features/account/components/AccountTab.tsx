"use client";

import * as React from "react";
import { Building2, FolderTree, LogOut, Shield, User } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { AuthUser, Language } from "@/lib/types";

interface AccountTabProps {
  user?: AuthUser;
  language: Language;
  onLogout?: () => void;
}

export function AccountTab({ user, language, onLogout }: AccountTabProps) {
  const isFa = language === "fa";

  const getRoleTitle = (role?: string) => {
    switch (role) {
      case "super_admin":
        return isFa ? "مدیر کل سیستم (Super Admin)" : "System Super Administrator";
      case "org_admin":
        return isFa ? "مدیر سازمان (Org Admin)" : "Organization Administrator";
      case "team_admin":
        return isFa ? "مدیر تیم (Team Admin)" : "Team Administrator";
      default:
        return isFa ? "کاربر عادی (User)" : "Standard User";
    }
  };

  return (
    <div className="space-y-5">
      <div>
        <h3 className="text-xs font-bold text-on-surface flex items-center gap-2">
          <User className="size-4 text-brand-cyan" />
          {isFa ? "اطلاعات هویت کاربری" : "User Identity & Account"}
        </h3>
        <p className="text-[11px] text-on-surface-variant mt-0.5">
          {isFa ? "مشخصات سازمانی و نشست کاربری فعال شما" : "Your active enterprise credentials and role."}
        </p>
      </div>

      <div className="p-4 rounded-2xl bg-surface-container/40 border border-border/30 space-y-4">
        <div className="flex items-center gap-3">
          <div className="flex size-12 items-center justify-center rounded-2xl bg-brand-cyan/10 border border-brand-cyan/30 text-lg font-bold font-mono text-brand-cyan">
            {user?.name?.charAt(0) || "U"}
          </div>
          <div>
            <div className="text-sm font-bold text-on-surface">{user?.name || (isFa ? "کاربر سامانه" : "User")}</div>
            <div className="text-xs text-on-surface-variant font-mono">{user?.email}</div>
          </div>
        </div>

        <div className="divide-y divide-border/20 text-xs pt-2">
          <div className="flex justify-between py-2">
            <span className="text-on-surface-variant flex items-center gap-1.5">
              <Shield className="size-3.5 text-brand-cyan" />
              {isFa ? "سطح دسترسی (Role):" : "Role:"}
            </span>
            <span className="font-semibold text-on-surface">{getRoleTitle(user?.role)}</span>
          </div>

          <div className="flex justify-between py-2">
            <span className="text-on-surface-variant flex items-center gap-1.5">
              <Building2 className="size-3.5 text-warning" />
              {isFa ? "سازمان متبوع:" : "Organization:"}
            </span>
            <span className="font-semibold text-on-surface">
              {user?.organizationName || user?.organizationId || (isFa ? "سراسری" : "Global")}
            </span>
          </div>

          <div className="flex justify-between py-2">
            <span className="text-on-surface-variant flex items-center gap-1.5">
              <FolderTree className="size-3.5 text-info" />
              {isFa ? "واحد سازمانی (تیم):" : "Team / Department:"}
            </span>
            <span className="font-semibold text-on-surface">
              {user?.teamName || user?.teamId || (isFa ? "دسترسی آزاد" : "Global")}
            </span>
          </div>
        </div>
      </div>

      {onLogout && (
        <div className="pt-2">
          <Button
            type="button"
            variant="destructive"
            onClick={onLogout}
            className="w-full text-xs font-bold gap-2 cursor-pointer"
          >
            <LogOut className="size-4" />
            {isFa ? "خروج از حساب کاربری" : "Sign Out of Account"}
          </Button>
        </div>
      )}
    </div>
  );
}
