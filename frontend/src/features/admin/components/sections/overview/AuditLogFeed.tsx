"use client";

import * as React from "react";
import { Activity, CheckCircle2, Database, ShieldCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface AuditLogFeedProps {
  activeNodesCount: number;
  totalDocs: number;
}

export function AuditLogFeed({ activeNodesCount, totalDocs }: AuditLogFeedProps) {
  return (
    <Card className="lg:col-span-2 bg-surface-raised border-border/40">
      <CardHeader className="pb-3 border-b border-border/30">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-bold text-on-surface flex items-center gap-2">
            <Activity className="size-4 text-brand-cyan" />
            <span>گزارش زنده فعالیت‌های کلاستر (Cluster Audit & Telemetry)</span>
          </CardTitle>
          <Badge variant="outline" className="text-[10px] border-emerald-500/30 text-emerald-400 font-mono">
            Live Feed
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3 pt-4">
        <div className="space-y-2.5">
          {/* Node Sync Event */}
          <div className="flex items-start gap-3 p-2.5 rounded-xl bg-surface-container/30 border border-border/20">
            <div className="size-7 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center shrink-0 mt-0.5">
              <CheckCircle2 className="size-4" />
            </div>
            <div className="flex-1 text-xs">
              <div className="flex items-center justify-between">
                <span className="font-bold text-on-surface">همگام‌سازی خودکار نودهای پردازشی GPU</span>
                <span className="text-[10px] text-on-surface-variant font-mono">
                  {activeNodesCount > 0 ? `پایدار (${activeNodesCount} نود)` : "در انتظار اتصال نود (۰ نود)"}
                </span>
              </div>
              <p className="text-[11px] text-on-surface-variant mt-0.5">
                {activeNodesCount > 0
                  ? "ضربان قلب نودها تأیید شد و مسیرهای استنتاجی در پایگاه پروکسی به‌روزرسانی گردید."
                  : "هنوز ورکر یا نود پردازشی به رجیستری مرکزی متصل نشده است."}
              </p>
            </div>
          </div>

          {/* Weaviate Event */}
          <div className="flex items-start gap-3 p-2.5 rounded-xl bg-surface-container/30 border border-border/20">
            <div className="size-7 rounded-lg bg-purple-500/10 text-purple-400 flex items-center justify-center shrink-0 mt-0.5">
              <Database className="size-4" />
            </div>
            <div className="flex-1 text-xs">
              <div className="flex items-center justify-between">
                <span className="font-bold text-on-surface">آمادگی پایگاه برداری Weaviate</span>
                <span className="text-[10px] text-on-surface-variant font-mono">ایندکس فعال ({totalDocs} سند)</span>
              </div>
              <p className="text-[11px] text-on-surface-variant mt-0.5">
                شاردهای اسناد سازمانی ایزوله بوده و آماده اجرای کاوش‌های معنایی چندمستأجری با آستانه شباهت ۰.۴۰ هستند.
              </p>
            </div>
          </div>

          {/* Quota Enforcement Event */}
          <div className="flex items-start gap-3 p-2.5 rounded-xl bg-surface-container/30 border border-border/20">
            <div className="size-7 rounded-lg bg-brand-cyan/10 text-brand-cyan flex items-center justify-center shrink-0 mt-0.5">
              <ShieldCheck className="size-4" />
            </div>
            <div className="flex-1 text-xs">
              <div className="flex items-center justify-between">
                <span className="font-bold text-on-surface">کنترل سهمیه ۳ سطحی توکن</span>
                <span className="text-[10px] text-on-surface-variant font-mono">فعال و ایمن</span>
              </div>
              <p className="text-[11px] text-on-surface-variant mt-0.5">
                اعتبارسنجی همزمان سقف سازمان، دپارتمان و کاربر بر روی خط لوله درخواست‌های چت بدون تأخیر در جریان است.
              </p>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
