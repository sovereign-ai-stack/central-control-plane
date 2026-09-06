"use client";

import * as React from "react";
import { Activity, Gauge, Loader2 } from "lucide-react";
import { fetchUsageLimits } from "@/api/index";
import type { Language, UsageLimits } from "@/lib/types";

interface UsageTabProps {
  language: Language;
}

export function UsageTab({ language }: UsageTabProps) {
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

  const userUsed = limits?.totalTokensUsed || 0;
  const userLimit = limits?.totalTokenLimit || 500000;
  const userPct = Math.min(100, Math.round((userUsed / Math.max(1, userLimit)) * 100));

  const teamUsed = limits?.teamTokensUsed || 0;
  const teamLimit = limits?.teamTokenLimit || 2000000;
  const teamPct = Math.min(100, Math.round((teamUsed / Math.max(1, teamLimit)) * 100));

  const orgUsed = limits?.orgTokensUsed || 0;
  const orgLimit = limits?.orgTokenLimit || 10000000;
  const orgPct = Math.min(100, Math.round((orgUsed / Math.max(1, orgLimit)) * 100));

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
        <div className="p-3.5 rounded-2xl bg-surface-container/40 border border-border/30 space-y-1.5">
          <div className="flex justify-between text-xs">
            <span className="font-semibold text-on-surface">{isFa ? "۱. سهمیه حساب کاربری شما:" : "1. Personal Account Quota:"}</span>
            <span className="font-mono font-bold text-brand-cyan">
              {userUsed.toLocaleString()} / {userLimit.toLocaleString()} ({userPct}%)
            </span>
          </div>
          <div className="h-2 w-full rounded-full bg-surface-container overflow-hidden">
            <div className="h-full bg-brand-cyan transition-all duration-500" style={{ width: `${userPct}%` }} />
          </div>
        </div>

        {/* Team Quota */}
        <div className="p-3.5 rounded-2xl bg-surface-container/40 border border-border/30 space-y-1.5">
          <div className="flex justify-between text-xs">
            <span className="font-semibold text-on-surface">{isFa ? "۲. سهمیه کل تیم / دپارتمان:" : "2. Team / Department Quota:"}</span>
            <span className="font-mono font-bold text-warning">
              {teamUsed.toLocaleString()} / {teamLimit.toLocaleString()} ({teamPct}%)
            </span>
          </div>
          <div className="h-2 w-full rounded-full bg-surface-container overflow-hidden">
            <div className="h-full bg-warning transition-all duration-500" style={{ width: `${teamPct}%` }} />
          </div>
        </div>

        {/* Org Quota */}
        <div className="p-3.5 rounded-2xl bg-surface-container/40 border border-border/30 space-y-1.5">
          <div className="flex justify-between text-xs">
            <span className="font-semibold text-on-surface">{isFa ? "۳. سقف کل ماهانه سازمان:" : "3. Organization Total Quota:"}</span>
            <span className="font-mono font-bold text-info">
              {orgUsed.toLocaleString()} / {orgLimit.toLocaleString()} ({orgPct}%)
            </span>
          </div>
          <div className="h-2 w-full rounded-full bg-surface-container overflow-hidden">
            <div className="h-full bg-info transition-all duration-500" style={{ width: `${orgPct}%` }} />
          </div>
        </div>
      </div>
    </div>
  );
}
