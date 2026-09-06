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
        <div className="p-3 rounded-xl bg-surface-container/40 border border-border/30 space-y-1.5">
          <div className="flex items-center justify-between text-xs">
            <span className="text-on-surface font-semibold flex items-center gap-1.5">
              <ShieldCheck className="size-4 text-brand-cyan" />
              <span>Central AI Gateway</span>
            </span>
            <Badge className="bg-emerald-500/15 text-emerald-400 border-emerald-500/30 text-[10px]">
              آنلاین و پایدار
            </Badge>
          </div>
          <div className="text-[11px] text-on-surface-variant leading-normal">
            احراز هویت نشست‌ها، کنترل سهمیه و استریم SSE با تفکیک تگ تفکر.
          </div>
        </div>

        {/* Semantic Router */}
        <div className="p-3 rounded-xl bg-surface-container/40 border border-border/30 space-y-1.5">
          <div className="flex items-center justify-between text-xs">
            <span className="text-on-surface font-semibold flex items-center gap-1.5">
              <Zap className="size-4 text-purple-400" />
              <span>Semantic Router Engine</span>
            </span>
            <Badge className="bg-purple-500/15 text-purple-400 border-purple-500/30 text-[10px] font-mono">
              {routerLatency}
            </Badge>
          </div>
          <div className="text-[11px] text-on-surface-variant leading-normal">
            طبقه‌بندی آنی قصد کاربر، نرمال‌سازی متن فارسی و کاوش خودکار RAG.
          </div>
        </div>

        {/* Weaviate Vector DB */}
        <div className="p-3 rounded-xl bg-surface-container/40 border border-border/30 space-y-1.5">
          <div className="flex items-center justify-between text-xs">
            <span className="text-on-surface font-semibold flex items-center gap-1.5">
              <Activity className="size-4 text-info" />
              <span>Weaviate Vector DB</span>
            </span>
            <Badge className="bg-info/15 text-info border-info/30 text-[10px]">
              RAG آماده به کار
            </Badge>
          </div>
          <div className="text-[11px] text-on-surface-variant leading-normal">
            جستجوی برداری متون با تفکیک شارد اختصاصی هر سازمان و تیم.
          </div>
        </div>

        {/* LiteLLM Proxy */}
        <div className="p-3 rounded-xl bg-surface-container/40 border border-border/30 space-y-1.5">
          <div className="flex items-center justify-between text-xs">
            <span className="text-on-surface font-semibold flex items-center gap-1.5">
              <Workflow className="size-4 text-emerald-400" />
              <span>LiteLLM Proxy & Balancer</span>
            </span>
            <Badge className="bg-emerald-500/15 text-emerald-400 border-emerald-500/30 text-[10px]">
              همگام‌سازی داینامیک
            </Badge>
          </div>
          <div className="text-[11px] text-on-surface-variant leading-normal">
            توزیع ترافیک روی ورکرها و استریم مستقیم توکن‌های استنتاجی.
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
