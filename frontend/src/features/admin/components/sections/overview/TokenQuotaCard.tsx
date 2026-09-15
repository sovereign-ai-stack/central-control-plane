"use client";

import * as React from "react";
import { Activity, ArrowLeft, BarChart3 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { AdminSection } from "../../../types";

interface TokenQuotaCardProps {
  tokensUsed: number;
  tokenLimit: number;
  usedPercent: number;
  maxRps?: number;
  inferenceConcurrency?: number;
  messagesPerHour?: number;
  maxPdfPages?: number;
  onSelectSection?: (section: AdminSection) => void;
}

export function TokenQuotaCard({
  tokensUsed,
  tokenLimit,
  usedPercent,
  maxRps = 20,
  inferenceConcurrency = 32,
  messagesPerHour = 120,
  maxPdfPages = 25,
  onSelectSection,
}: TokenQuotaCardProps) {
  const badgeColorClass =
    usedPercent > 90
      ? "border-destructive/40 text-destructive bg-destructive/10"
      : usedPercent > 70
      ? "border-amber-500/40 text-amber-400 bg-amber-500/10"
      : "border-brand-cyan/40 text-brand-cyan bg-brand-cyan/10";

  const progressGradientClass =
    usedPercent > 90
      ? "bg-gradient-to-r from-amber-500 to-destructive"
      : usedPercent > 70
      ? "bg-gradient-to-r from-brand-cyan via-emerald-400 to-amber-500"
      : "bg-gradient-to-r from-brand-cyan to-emerald-400";

  return (
    <Card className="lg:col-span-2 bg-surface-raised border-border/40 flex flex-col h-full">
      <CardHeader className="pb-3 border-b border-border/30 shrink-0">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-bold text-on-surface flex items-center gap-2">
            <BarChart3 className="size-4 text-brand-cyan" />
            <span>سهمیه توکن و مدیریت بودجه کلاستر (3-Tier Token Quotas)</span>
          </CardTitle>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className={`text-xs font-mono font-bold ${badgeColorClass}`}>
              {usedPercent}% مصرف ماه جاری
            </Badge>
            {onSelectSection && (
              <Button
                size="sm"
                variant="ghost"
                onClick={() => onSelectSection("limits")}
                className="text-xs h-7 px-2 text-brand-cyan hover:bg-brand-cyan/10 cursor-pointer"
              >
                <span>تنظیم سقف</span>
                <ArrowLeft className="size-3 mr-1" />
              </Button>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4 pt-4 flex-1 flex flex-col justify-center">
        {/* Master Progress Bar */}
        <div className="space-y-3 bg-surface-container/30 border border-border/30 rounded-2xl p-4">
          <div className="flex justify-between text-xs">
            <span className="text-on-surface-variant flex items-center gap-1.5">
              <Activity className="size-3.5 text-brand-cyan" />
              <span>مجموع توکن مصرف‌شده در این دوره:</span>
            </span>
            <span className="font-mono font-bold text-on-surface text-sm">
              {tokensUsed.toLocaleString()} <span className="text-xs font-sans text-on-surface-variant">توکن</span>
            </span>
          </div>

          <div className="h-4 w-full rounded-full bg-surface-container overflow-hidden p-0.5 border border-border/20">
            <div
              className={`h-full rounded-full transition-all duration-700 ${progressGradientClass}`}
              style={{ width: `${Math.max(2, Math.min(100, usedPercent))}%` }}
            />
          </div>

          <div className="flex justify-between text-[11px] text-on-surface-variant font-mono pt-0.5">
            <span>۰ توکن</span>
            <span className="text-on-surface font-semibold">
              سقف کل مجاز ماهانه: {tokenLimit.toLocaleString()} توکن
            </span>
          </div>
        </div>

        {/* 3-Tier Multi-Level Explanation Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="bg-surface-container/20 border border-border/30 rounded-xl p-3 text-center flex flex-col justify-center hover:bg-surface-container/40 transition-colors">
            <div className="text-[10px] text-on-surface-variant mb-1 font-bold">سطح سازمان (Global)</div>
            <div className="font-mono text-sm font-black text-brand-cyan mb-1.5">{maxRps} RPS</div>
            <div className="text-[10px] text-on-surface-variant leading-relaxed">
              ترافیک کل سیستم کنترل و توزیع می‌شود (Global Rate Limiting).
            </div>
          </div>
          <div className="bg-surface-container/20 border border-border/30 rounded-xl p-3 text-center flex flex-col justify-center hover:bg-surface-container/40 transition-colors">
            <div className="text-[10px] text-on-surface-variant mb-1 font-bold">سطح تیم (Team)</div>
            <div className="font-mono text-sm font-black text-emerald-400 mb-1.5">{inferenceConcurrency} Conc.</div>
            <div className="text-[10px] text-on-surface-variant leading-relaxed">
              سقف پردازش‌های همزمان و سهمیه توکن اشتراکی تیم.
            </div>
          </div>
          <div className="bg-surface-container/20 border border-border/30 rounded-xl p-3 text-center flex flex-col justify-center hover:bg-surface-container/40 transition-colors">
            <div className="text-[10px] text-on-surface-variant mb-1 font-bold">سطح کاربر (User)</div>
            <div className="font-mono text-sm font-black text-purple-400 mb-1.5">{messagesPerHour} Msg/hr</div>
            <div className="text-[10px] text-on-surface-variant leading-relaxed">
              سقف پیام‌ها و محدودیت صفحات RAG (Max {maxPdfPages} pages).
            </div>
          </div>
        </div>

        {/* Operational Rate Limits */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 pt-1">
          <div className="p-2.5 rounded-xl bg-surface-container/30 border border-border/30 text-center">
            <div className="text-[10.5px] text-on-surface-variant">ماکزیمم RPS</div>
            <div className="text-sm font-bold text-on-surface font-mono mt-0.5">
              {maxRps} <span className="text-[10px] font-sans font-normal text-on-surface-variant">Req/s</span>
            </div>
          </div>
          <div className="p-2.5 rounded-xl bg-surface-container/30 border border-border/30 text-center">
            <div className="text-[10.5px] text-on-surface-variant">همزمانی استنتاج</div>
            <div className="text-sm font-bold text-on-surface font-mono mt-0.5">
              {inferenceConcurrency} <span className="text-[10px] font-sans font-normal text-on-surface-variant">Stream</span>
            </div>
          </div>
          <div className="p-2.5 rounded-xl bg-surface-container/30 border border-border/30 text-center">
            <div className="text-[10.5px] text-on-surface-variant">پیام در ساعت</div>
            <div className="text-sm font-bold text-on-surface font-mono mt-0.5">
              {messagesPerHour} <span className="text-[10px] font-sans font-normal text-on-surface-variant">Msg/h</span>
            </div>
          </div>
          <div className="p-2.5 rounded-xl bg-surface-container/30 border border-border/30 text-center">
            <div className="text-[10.5px] text-on-surface-variant">سقف صفحات PDF</div>
            <div className="text-sm font-bold text-on-surface font-mono mt-0.5">
              {maxPdfPages} <span className="text-[10px] font-sans font-normal text-on-surface-variant">Page</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
