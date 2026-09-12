"use client";

import * as React from "react";
import { Activity, Building2, FolderTree, Gauge, Loader2, User } from "lucide-react";
import { fetchUsageLimits } from "@/api/index";
import type { AuthUser, Language, UsageLimits } from "@/lib/types";

interface UsageTabProps {
  language: Language;
  user?: AuthUser;
}

export function UsageTab({ language, user }: UsageTabProps) {
  const isFa = language === "fa";
  const [limits, setLimits] = React.useState<UsageLimits | null>(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    let active = true;
    fetchUsageLimits()
      .then((data) => {
        if (active) setLimits(data);
      })
      .catch(() => {})
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12 text-on-surface-variant">
        <Loader2 className="size-6 text-brand-cyan animate-spin me-2" />
        <span className="text-xs">{isFa ? "در حال دریافت آمار مصرف سهمیه..." : "Loading usage limits..."}</span>
      </div>
    );
  }

  const userUsed = limits?.totalTokensUsed ?? limits?.userTokensUsed ?? user?.usedTokens ?? 0;
  const userLimit = limits?.totalTokenLimit ?? limits?.userTokenLimit ?? user?.tokenLimit ?? 500000;
  const userPct = Math.min(100, Math.round((userUsed / Math.max(1, userLimit)) * 100));

  const teamUsed = limits?.teamTokensUsed ?? 0;
  const teamLimit = limits?.teamTokenLimit ?? 2000000;
  const teamPct = Math.min(100, Math.round((teamUsed / Math.max(1, teamLimit)) * 100));
  const teamName = limits?.teamName || user?.teamName || user?.teamId || (isFa ? "تیم سازمانی" : "Team");

  const orgUsed = limits?.orgTokensUsed ?? (limits?.clusterTokensUsed || 0);
  const orgLimit = limits?.orgTokenLimit ?? (limits?.clusterTokenLimit || 10000000);
  const orgPct = Math.min(100, Math.round((orgUsed / Math.max(1, orgLimit)) * 100));
  const orgName = limits?.orgName || user?.organizationName || user?.organizationId || (isFa ? "سازمان مرکزی" : "Organization");

  return (
    <div className="space-y-5">
      <div>
        <h3 className="text-xs font-bold text-on-surface flex items-center gap-2">
          <Gauge className="size-4 text-brand-cyan" />
          {isFa ? "سهمیه توکن و مصرف لایه‌ای" : "Token Quota & Usage Limits"}
        </h3>
        <p className="text-[11px] text-on-surface-variant mt-0.5">
          {isFa
            ? "نظارت بر مصرف سهمیه توکن در سه لایه: حساب کاربری، تیم مربوطه و کل سازمان"
            : "Monitor token consumption across user, team, and organization levels."}
        </p>
      </div>

      <div className="space-y-3">
        {/* User Quota */}
        <div className="p-3.5 rounded-2xl bg-surface-container/40 border border-brand-cyan/30 space-y-1.5 shadow-sm">
          <div className="flex justify-between items-center text-xs">
            <span className="font-semibold text-on-surface flex items-center gap-1.5">
              <User className="size-3.5 text-brand-cyan" />
              {isFa ? `۱. سهمیه حساب کاربری (${user?.name || "شما"}):` : `1. Personal Quota (${user?.name || "You"}):`}
            </span>
            <span className="font-mono font-bold text-brand-cyan">
              {userUsed.toLocaleString()} / {userLimit.toLocaleString()} ({userPct}%)
            </span>
          </div>
          <div className="h-2 w-full rounded-full bg-surface-container overflow-hidden">
            <div
              className={`h-full transition-all duration-500 ${userPct > 90 ? "bg-destructive" : "bg-brand-cyan"}`}
              style={{ width: `${userPct}%` }}
            />
          </div>
        </div>

        {/* Team Quota */}
        <div className="p-3.5 rounded-2xl bg-surface-container/40 border border-warning/30 space-y-1.5 shadow-sm">
          <div className="flex justify-between items-center text-xs">
            <span className="font-semibold text-on-surface flex items-center gap-1.5">
              <FolderTree className="size-3.5 text-warning" />
              {isFa ? `۲. سهمیه واحد سازمانی (${teamName}):` : `2. Team Quota (${teamName}):`}
            </span>
            <span className="font-mono font-bold text-warning">
              {teamUsed.toLocaleString()} / {teamLimit.toLocaleString()} ({teamPct}%)
            </span>
          </div>
          <div className="h-2 w-full rounded-full bg-surface-container overflow-hidden">
            <div
              className={`h-full transition-all duration-500 ${teamPct > 90 ? "bg-destructive" : "bg-warning"}`}
              style={{ width: `${teamPct}%` }}
            />
          </div>
        </div>

        {/* Org Quota */}
        <div className="p-3.5 rounded-2xl bg-surface-container/40 border border-info/30 space-y-1.5 shadow-sm">
          <div className="flex justify-between items-center text-xs">
            <span className="font-semibold text-on-surface flex items-center gap-1.5">
              <Building2 className="size-3.5 text-info" />
              {isFa ? `۳. سقف کل ماهانه سازمان (${orgName}):` : `3. Org Quota (${orgName}):`}
            </span>
            <span className="font-mono font-bold text-info">
              {orgUsed.toLocaleString()} / {orgLimit.toLocaleString()} ({orgPct}%)
            </span>
          </div>
          <div className="h-2 w-full rounded-full bg-surface-container overflow-hidden">
            <div
              className={`h-full transition-all duration-500 ${orgPct > 90 ? "bg-destructive" : "bg-info"}`}
              style={{ width: `${orgPct}%` }}
            />
          </div>
        </div>
      </div>

      <div className="p-3 rounded-2xl bg-surface-container/20 border border-border/20 text-[11px] text-on-surface-variant flex items-center gap-2">
        <Activity className="size-3.5 text-brand-mint shrink-0" />
        <span>
          {isFa
            ? "محاسبه توکن‌ها به صورت زنده و دقیق با پروکسی LiteLLM و هسته Sovereign سنکرون است."
            : "Token usage is synchronized in real-time with LiteLLM proxy and Sovereign Control Plane."}
        </span>
      </div>
    </div>
  );
}

