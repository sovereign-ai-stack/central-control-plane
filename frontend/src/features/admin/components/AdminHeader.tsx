"use client";

import Link from "next/link";
import { BookOpen, Menu, RefreshCw, Shield, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { AuthUser } from "@/lib/types";

interface AdminHeaderProps {
  currentUser: AuthUser | null;
  refreshing?: boolean;
  onRefresh?: () => void;
  onOpenMobileNav: () => void;
}

export function AdminHeader({
  currentUser,
  refreshing,
  onRefresh,
  onOpenMobileNav,
}: AdminHeaderProps) {
  const getRoleBadge = (role?: string) => {
    switch (role) {
      case "super_admin":
        return <Badge className="bg-brand-cyan/20 text-brand-cyan border-brand-cyan/30 text-[10.5px]">مدیر ارشد (Super Admin)</Badge>;
      case "org_admin":
        return <Badge className="bg-warning/20 text-warning border-warning/30 text-[10.5px]">مدیر سازمان (Org Admin)</Badge>;
      case "team_admin":
        return <Badge className="bg-info/20 text-info border-info/30 text-[10.5px]">مدیر تیم (Team Admin)</Badge>;
      default:
        return <Badge variant="outline" className="border-border/40 text-[10.5px]">کاربر</Badge>;
    }
  };

  return (
    <header className="h-14 shrink-0 bg-surface-raised border-b border-border/40 flex items-center justify-between px-4 sm:px-6">
      <div className="flex items-center gap-2.5">
        <Button
          variant="ghost"
          size="icon"
          onClick={onOpenMobileNav}
          className="md:hidden size-8 text-on-surface"
        >
          <Menu className="size-5" />
        </Button>
        <div className="text-xs sm:text-sm font-bold text-on-surface flex items-center gap-2">
          <Shield className="size-4 text-brand-cyan hidden sm:inline-block" />
          <span>پلتفرم کنترل متمرکز هوش مصنوعی</span>
        </div>
        <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-surface-container/50 border border-border/30 text-[10.5px] text-on-surface-variant font-mono">
          <span className="size-2 rounded-full bg-emerald-400 animate-pulse"></span>
          <span>Cluster: 100% Operational</span>
        </div>
      </div>

      <div className="flex items-center gap-2">
        {onRefresh && (
          <Button
            size="sm"
            variant="ghost"
            onClick={onRefresh}
            disabled={refreshing}
            className="size-8 p-0 text-on-surface-variant hover:text-brand-cyan cursor-pointer"
            title="به‌روزرسانی داده‌ها"
          >
            <RefreshCw className={`size-3.5 ${refreshing ? "animate-spin text-brand-cyan" : ""}`} />
          </Button>
        )}

        <Link href="/docs">
          <Button
            size="sm"
            variant="outline"
            className="hidden sm:inline-flex text-xs h-8 gap-1.5 border-border/40 hover:border-brand-cyan/40 hover:text-brand-cyan cursor-pointer"
          >
            <BookOpen className="size-3.5" />
            <span>مستندات</span>
          </Button>
        </Link>

        {currentUser && (
          <div className="flex items-center gap-2 ps-2 border-s border-border/30">
            <div className="flex size-7 items-center justify-center rounded-lg bg-surface-container border border-border/40 text-xs font-bold font-mono text-brand-cyan">
              {currentUser.name.charAt(0)}
            </div>
            <div className="hidden sm:block text-start">
              <div className="text-xs font-bold text-on-surface leading-none">{currentUser.name}</div>
              <div className="text-[10px] text-on-surface-variant font-mono">{currentUser.email}</div>
            </div>
            {getRoleBadge(currentUser.role)}
          </div>
        )}
      </div>
    </header>
  );
}
