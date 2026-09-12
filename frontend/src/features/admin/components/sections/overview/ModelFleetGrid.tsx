"use client";

import * as React from "react";
import { ArrowLeft, Cpu, HardDrive, Network, Server, Sparkles, Zap } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { AdminSection } from "../../../types";

interface ModelFleetGridProps {
  isSuperAdmin: boolean;
  models?: any[];
  onSelectSection?: (section: AdminSection) => void;
}

export function ModelFleetGrid({
  isSuperAdmin,
  models = [],
  onSelectSection,
}: ModelFleetGridProps) {
  const getRoleBadge = (roleId?: string) => {
    switch (roleId) {
      case "reasoning-model":
        return { label: "reasoning-model", color: "bg-purple-500/20 text-purple-400 border-purple-500/30" };
      case "coding-model":
        return { label: "coding-model", color: "bg-brand-cyan/20 text-brand-cyan border-brand-cyan/30" };
      case "rag-model":
        return { label: "rag-model", color: "bg-amber-500/20 text-amber-400 border-amber-500/30" };
      default:
        return { label: roleId || "general-model", color: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30" };
    }
  };

  return (
    <Card className="bg-surface-raised border-border/40">
      <CardHeader className="pb-3 border-b border-border/30">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-bold text-on-surface flex items-center gap-2">
            <Cpu className="size-4 text-brand-cyan" />
            <span>ناوگان مدل‌های فعال و نودهای پردازشی (Active Model Fleet & GPUs)</span>
          </CardTitle>
          {onSelectSection && isSuperAdmin && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => onSelectSection("models")}
              className="text-xs h-7 px-2.5 border-border/40 text-brand-cyan hover:bg-brand-cyan/10 cursor-pointer"
            >
              <span>مدیریت مدل‌ها</span>
              <ArrowLeft className="size-3 mr-1" />
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent className="pt-4">
        {models && models.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
            {models.map((m: any, idx: number) => {
              const roleBadge = getRoleBadge(m.id || m.served_model_name || m.assignedRole);
              const modelTitle = m.name || m.model_name || m.id || `Model #${idx + 1}`;
              const gpuName = m.gpu || m.hardware?.gpus?.[0]?.name || "NVIDIA GPU";
              const nodeId = m.nodeId || m.node_id || `node-${idx + 1}`;
              const endpoint = m.ip && m.port ? `${m.ip}:${m.port}` : (m.api_base || "127.0.0.1:8000");

              return (
                <div
                  key={m.id || idx}
                  className="p-3.5 rounded-xl bg-surface-container/40 border border-border/40 hover:border-brand-cyan/40 transition-all space-y-2.5 shadow-sm"
                >
                  <div className="flex items-center justify-between">
                    <Badge className={`text-[10px] font-mono ${roleBadge.color}`}>
                      {roleBadge.label}
                    </Badge>
                    <div className="flex items-center gap-1.5">
                      <span className="size-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                      <span className="text-[10px] text-emerald-400 font-bold">فعال</span>
                    </div>
                  </div>

                  <div>
                    <div className="font-bold text-xs text-on-surface truncate" title={modelTitle}>
                      {modelTitle}
                    </div>
                    <div className="text-[11px] text-on-surface-variant flex items-center gap-1 mt-0.5 font-mono">
                      <Server className="size-3 text-brand-cyan shrink-0" />
                      <span className="truncate">{nodeId}</span>
                    </div>
                  </div>

                  <div className="pt-1.5 border-t border-border/20 space-y-1 text-[10.5px] text-on-surface-variant font-mono">
                    <div className="flex items-center justify-between">
                      <span className="flex items-center gap-1">
                        <HardDrive className="size-3 text-warning shrink-0" />
                        <span className="truncate max-w-[120px]" title={gpuName}>{gpuName}</span>
                      </span>
                      <span className="text-on-surface font-semibold">{m.latencyMs ? `${m.latencyMs}ms` : "Live"}</span>
                    </div>
                    <div className="flex items-center justify-between text-[10px] text-on-surface-variant/70">
                      <span className="flex items-center gap-1">
                        <Network className="size-3 text-brand-cyan shrink-0" />
                        <span className="truncate max-w-[140px]">{endpoint}</span>
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-8 text-center rounded-xl bg-surface-container/20 border border-dashed border-border/40 p-4 space-y-2">
            <Cpu className="size-8 text-brand-cyan/60 animate-pulse" />
            <div className="text-xs font-bold text-on-surface">گره پردازشی فعالی به رجیستری متصل نیست</div>
            <p className="text-[11px] text-on-surface-variant max-w-md">
              گره‌های هوش مصنوعی (AI Node Agent) با اجرای دستور <code className="px-1.5 py-0.5 rounded bg-surface-raised font-mono text-brand-cyan">run.bat</code> یا اسکریپت ایجنت به صورت خودکار به کلاستر متصل و در این بخش نمایش داده می‌شوند.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

