"use client";

import * as React from "react";
import { Activity, Server, ShieldCheck, Workflow, Zap } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface ClusterStatusCardProps {
  litellmStatus?: string;
  gatewayStatus?: string;
  routerLatency?: string;
  vectorDbStatus?: string;
}

export function ClusterStatusCard({
  litellmStatus = "online",
  gatewayStatus = "healthy",
  routerLatency = "Sub-15ms",
  vectorDbStatus = "ready",
}: ClusterStatusCardProps) {
  return (
    <Card className="bg-surface-raised border-border/40">
      <CardHeader className="pb-3 border-b border-border/30">
        <CardTitle className="text-sm font-bold text-on-surface flex items-center gap-2">
          <Server className="size-4 text-emerald-400" />
          <span>وضعیت موتور و سرویس‌های کلاستر</span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 pt-4">
        {/* Gateway */}
        <div className="p-4 rounded-xl bg-surface-container/40 border border-border/30 flex flex-col items-center justify-center space-y-2 text-center transition-colors hover:bg-surface-container/60">
          <div className="flex items-center gap-2">
            <ShieldCheck className="size-5 text-brand-cyan" />
            <span className="text-on-surface font-bold text-sm">Central AI Gateway</span>
          </div>
          <Badge className="bg-emerald-500/15 text-emerald-400 border-emerald-500/30 text-[10px] px-2 py-0.5">
            آنلاین و پایدار
          </Badge>
          <div className="text-[11px] text-on-surface-variant leading-relaxed max-w-[250px]">
            احراز هویت نشست‌ها، کنترل سهمیه و استریم SSE با تفکیک تگ تفکر.
          </div>
        </div>

        {/* Semantic Router */}
        <div className="p-4 rounded-xl bg-surface-container/40 border border-border/30 flex flex-col items-center justify-center space-y-2 text-center transition-colors hover:bg-surface-container/60">
          <div className="flex items-center gap-2">
            <Zap className="size-5 text-purple-400" />
            <span className="text-on-surface font-bold text-sm">Semantic Router Engine</span>
          </div>
          <Badge className="bg-purple-500/15 text-purple-400 border-purple-500/30 text-[10px] font-mono px-2 py-0.5">
            {routerLatency}
          </Badge>
          <div className="text-[11px] text-on-surface-variant leading-relaxed max-w-[250px]">
            طبقه‌بندی آنی قصد کاربر، نرمال‌سازی متن فارسی و کاوش خودکار RAG.
          </div>
        </div>

        {/* Weaviate Vector DB */}
        <div className="p-4 rounded-xl bg-surface-container/40 border border-border/30 flex flex-col items-center justify-center space-y-2 text-center transition-colors hover:bg-surface-container/60">
          <div className="flex items-center gap-2">
            <Activity className="size-5 text-info" />
            <span className="text-on-surface font-bold text-sm">Weaviate Vector DB</span>
          </div>
          <Badge className="bg-info/15 text-info border-info/30 text-[10px] px-2 py-0.5">
            RAG آماده به کار
          </Badge>
          <div className="text-[11px] text-on-surface-variant leading-relaxed max-w-[250px]">
            جستجوی برداری متون با تفکیک شارد اختصاصی هر سازمان و تیم.
          </div>
        </div>

        {/* LiteLLM Proxy */}
        <div className="p-4 rounded-xl bg-surface-container/40 border border-border/30 flex flex-col items-center justify-center space-y-2 text-center transition-colors hover:bg-surface-container/60">
          <div className="flex items-center gap-2">
            <Workflow className="size-5 text-amber-400" />
            <span className="text-on-surface font-bold text-sm">LiteLLM Proxy Router</span>
          </div>
          <Badge className="bg-amber-500/15 text-amber-400 border-amber-500/30 text-[10px] px-2 py-0.5 uppercase">
            {litellmStatus}
          </Badge>
          <div className="text-[11px] text-on-surface-variant leading-relaxed max-w-[250px]">
            توزیع بار، Failover، یکپارچه‌سازی API و ثبت لاگ (Langfuse).
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
