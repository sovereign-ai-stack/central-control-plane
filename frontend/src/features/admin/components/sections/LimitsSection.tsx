"use client";

import * as React from "react";
import { Activity, ShieldCheck, SlidersHorizontal, Users } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchUsageLimits } from "@/api/index";
import type { AdminDashboard, UsageLimits } from "@/lib/types";

interface LimitsSectionProps {
  dashboard: AdminDashboard | null;
}

export function LimitsSection({ dashboard }: LimitsSectionProps) {
  const [limits, setLimits] = React.useState<UsageLimits | null>(null);

  React.useEffect(() => {
    let isMounted = true;
    fetchUsageLimits()
      .then((data) => {
        if (isMounted && data) {
          setLimits(data);
        }
      })
      .catch(() => {
        // Fallback gracefully to dashboard props
      });
    return () => {
      isMounted = false;
    };
  }, []);

  const userUsed = limits?.totalTokensUsed ?? limits?.userTokensUsed ?? 0;
  const userLimit = limits?.totalTokenLimit ?? limits?.userTokenLimit ?? (dashboard?.perAccountTokenLimit || 500000);
  const userPct = Math.min(100, Math.round((userUsed / Math.max(1, userLimit)) * 100));

  const teamUsed = limits?.teamTokensUsed ?? 0;
  const teamLimit = limits?.teamTokenLimit ?? 2000000;
  const teamPct = Math.min(100, Math.round((teamUsed / Math.max(1, teamLimit)) * 100));

  const orgUsed = limits?.orgTokensUsed ?? (dashboard?.tokensThisMonth || 0);
  const orgLimit = limits?.orgTokenLimit ?? (dashboard?.workspaceTokenLimit || 10000000);
  const orgPct = Math.min(100, Math.round((orgUsed / Math.max(1, orgLimit)) * 100));

  const limitsData = [
    { label: "حداکثر سقف RPS سامانه (Max Requests/sec)", value: `${limits?.maxRps || dashboard?.maxRps || 20} req/s` },
    { label: "پیش‌فرض RPS هر کلاینت (Default RPS)", value: `${limits?.defaultRps || dashboard?.defaultRps || 5} req/s` },
    { label: "سقف استریم‌های همزمان استنتاج (Concurrency)", value: `${limits?.inferenceConcurrency || dashboard?.inferenceConcurrency || 32} streams` },
    { label: "حداکثر طول کاراکتر ورودی پرسش (Max Input Chars)", value: `${limits?.maxInputChars || dashboard?.maxInputChars || 8000} chars` },
    { label: "حداکثر توکن خروجی مدل (Max Output Tokens)", value: `${limits?.maxOutputTokens || dashboard?.maxOutputTokens || 4096} tokens` },
    { label: "حداکثر تعداد صفحات سند PDF (Max PDF Pages)", value: `${limits?.maxPdfPages || dashboard?.maxPdfPages || 20} pages` },
    { label: "سهمیه پیش‌فرض توکن کاربر (Default User Token Limit)", value: `${(userLimit).toLocaleString()} tokens` },
    { label: "سقف توکن کل کلاستر سازمانی", value: `${(orgLimit).toLocaleString()} tokens` },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-base font-bold text-on-surface">سهمیه‌ها و محدودیت‌های نرخ (Rate Limiting & Quotas)</h2>
        <p className="text-xs text-on-surface-variant">
          پیکربندی سقف‌های مصرف، سهمیه ۳ لایه (کاربر/تیم/سازمان) و لایه‌های حفاظتی کلاستر
        </p>
      </div>

      {/* 1. HIERARCHICAL QUOTAS */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* User Quota */}
        <Card className="bg-surface-raised border-border/40">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-bold text-on-surface flex items-center justify-between">
              <span className="flex items-center gap-1.5">
                <Users className="size-3.5 text-brand-cyan" />
                سهمیه کاربری فعال
              </span>
              <span className="font-mono text-brand-cyan">{userPct}%</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex justify-between text-[11px] font-mono">
              <span className="text-on-surface-variant">مصرف شده:</span>
              <span className="text-on-surface font-bold">{userUsed.toLocaleString()}</span>
            </div>
            <div className="flex justify-between text-[11px] font-mono">
              <span className="text-on-surface-variant">سقف مجاز:</span>
              <span className="text-on-surface font-bold">{userLimit.toLocaleString()}</span>
            </div>
            <div className="h-1.5 w-full rounded-full bg-surface-container overflow-hidden">
              <div
                className={`h-full ${userPct > 90 ? "bg-destructive" : "bg-brand-cyan"}`}
                style={{ width: `${userPct}%` }}
              />
            </div>
          </CardContent>
        </Card>

        {/* Team Quota */}
        <Card className="bg-surface-raised border-border/40">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-bold text-on-surface flex items-center justify-between">
              <span className="flex items-center gap-1.5">
                <ShieldCheck className="size-3.5 text-warning" />
                سهمیه واحد / تیم
              </span>
              <span className="font-mono text-warning">{teamPct}%</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex justify-between text-[11px] font-mono">
              <span className="text-on-surface-variant">مصرف تیم:</span>
              <span className="text-on-surface font-bold">{teamUsed.toLocaleString()}</span>
            </div>
            <div className="flex justify-between text-[11px] font-mono">
              <span className="text-on-surface-variant">سقف تیم:</span>
              <span className="text-on-surface font-bold">{teamLimit.toLocaleString()}</span>
            </div>
            <div className="h-1.5 w-full rounded-full bg-surface-container overflow-hidden">
              <div
                className={`h-full ${teamPct > 90 ? "bg-destructive" : "bg-warning"}`}
                style={{ width: `${teamPct}%` }}
              />
            </div>
          </CardContent>
        </Card>

        {/* Organization Quota */}
        <Card className="bg-surface-raised border-border/40">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-bold text-on-surface flex items-center justify-between">
              <span className="flex items-center gap-1.5">
                <Activity className="size-3.5 text-emerald-400" />
                سهمیه سازمان / کلاستر
              </span>
              <span className="font-mono text-emerald-400">{orgPct}%</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex justify-between text-[11px] font-mono">
              <span className="text-on-surface-variant">مصرف کل:</span>
              <span className="text-on-surface font-bold">{orgUsed.toLocaleString()}</span>
            </div>
            <div className="flex justify-between text-[11px] font-mono">
              <span className="text-on-surface-variant">سقف سازمان:</span>
              <span className="text-on-surface font-bold">{orgLimit.toLocaleString()}</span>
            </div>
            <div className="h-1.5 w-full rounded-full bg-surface-container overflow-hidden">
              <div
                className={`h-full ${orgPct > 90 ? "bg-destructive" : "bg-emerald-400"}`}
                style={{ width: `${orgPct}%` }}
              />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 2. PARAMETERS TABLE */}
      <Card className="bg-surface-raised border-border/40">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-bold text-on-surface flex items-center gap-2">
            <SlidersHorizontal className="size-4 text-brand-cyan" />
            جدول پارامترهای فعال کنترل ترافیک و سهمیه
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="divide-y divide-border/20 text-xs">
            {limitsData.map((item, idx) => (
              <div key={idx} className="flex items-center justify-between py-3">
                <span className="text-on-surface">{item.label}</span>
                <span className="font-mono font-bold text-brand-cyan">{item.value}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
