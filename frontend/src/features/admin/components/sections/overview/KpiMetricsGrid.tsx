"use client";

import * as React from "react";
import { Building2, Cpu, Database, FolderTree, ShieldCheck, Users } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import type { AdminSection } from "../../../types";

interface KpiMetricsGridProps {
  totalOrgs: number;
  totalTeams: number;
  totalUsers: number;
  activeNodesCount: number;
  totalVramGb: number;
  totalDocs: number;
  onSelectSection?: (section: AdminSection) => void;
}

export function KpiMetricsGrid({
  totalOrgs,
  totalTeams,
  totalUsers,
  activeNodesCount,
  totalVramGb,
  totalDocs,
  onSelectSection,
}: KpiMetricsGridProps) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5">
      {/* Organizations */}
      <Card
        onClick={() => onSelectSection?.("organizations")}
        className="bg-surface-raised border-border/40 hover:border-brand-cyan/40 hover:shadow-md transition-all cursor-pointer group"
      >
        <CardContent className="p-4 flex items-center justify-between">
          <div className="space-y-1">
            <div className="text-[11px] text-on-surface-variant font-medium">سازمان‌های مستقل</div>
            <div className="text-2xl font-black text-on-surface font-mono group-hover:text-brand-cyan transition-colors">
              {totalOrgs}
            </div>
            <div className="text-[10px] text-on-surface-variant flex items-center gap-1">
              <Building2 className="size-3 text-brand-cyan" />
              <span>شارد‌های ایزوله داده</span>
            </div>
          </div>
          <div className="flex size-10 items-center justify-center rounded-xl bg-brand-cyan/10 border border-brand-cyan/20 text-brand-cyan group-hover:scale-105 transition-transform">
            <Building2 className="size-5" />
          </div>
        </CardContent>
      </Card>

      {/* Teams */}
      <Card
        onClick={() => onSelectSection?.("teams")}
        className="bg-surface-raised border-border/40 hover:border-warning/40 hover:shadow-md transition-all cursor-pointer group"
      >
        <CardContent className="p-4 flex items-center justify-between">
          <div className="space-y-1">
            <div className="text-[11px] text-on-surface-variant font-medium">دپارتمان‌ها و تیم‌ها</div>
            <div className="text-2xl font-black text-on-surface font-mono group-hover:text-warning transition-colors">
              {totalTeams}
            </div>
            <div className="text-[10px] text-on-surface-variant flex items-center gap-1">
              <FolderTree className="size-3 text-warning" />
              <span>سهمیه توکن مستقل</span>
            </div>
          </div>
          <div className="flex size-10 items-center justify-center rounded-xl bg-warning/10 border border-warning/20 text-warning group-hover:scale-105 transition-transform">
            <FolderTree className="size-5" />
          </div>
        </CardContent>
      </Card>

      {/* Users */}
      <Card
        onClick={() => onSelectSection?.("users")}
        className="bg-surface-raised border-border/40 hover:border-info/40 hover:shadow-md transition-all cursor-pointer group"
      >
        <CardContent className="p-4 flex items-center justify-between">
          <div className="space-y-1">
            <div className="text-[11px] text-on-surface-variant font-medium">کاربران مجاز</div>
            <div className="text-2xl font-black text-on-surface font-mono group-hover:text-info transition-colors">
              {totalUsers}
            </div>
            <div className="text-[10px] text-on-surface-variant flex items-center gap-1">
              <ShieldCheck className="size-3 text-info" />
              <span>کنترل دسترسی RBAC</span>
            </div>
          </div>
          <div className="flex size-10 items-center justify-center rounded-xl bg-info/10 border border-info/20 text-info group-hover:scale-105 transition-transform">
            <Users className="size-5" />
          </div>
        </CardContent>
      </Card>

      {/* GPU Nodes */}
      <Card className="bg-surface-raised border-border/40 hover:border-emerald-500/40 hover:shadow-md transition-all group">
        <CardContent className="p-4 flex items-center justify-between">
          <div className="space-y-1">
            <div className="text-[11px] text-on-surface-variant font-medium">نودهای فعال GPU</div>
            <div className="text-2xl font-black text-emerald-400 font-mono flex items-center gap-1.5">
              <span>{activeNodesCount}</span>
              {activeNodesCount > 0 ? (
                <span className="size-2 rounded-full bg-emerald-400 animate-pulse" title="آنلاین"></span>
              ) : (
                <span className="size-2 rounded-full bg-on-surface-variant/40" title="آفلاین"></span>
              )}
            </div>
            <div className="text-[10px] text-on-surface-variant flex items-center gap-1">
              <Cpu className="size-3 text-emerald-400" />
              <span>{totalVramGb} GB مجموع VRAM</span>
            </div>
          </div>
          <div className="flex size-10 items-center justify-center rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 group-hover:scale-105 transition-transform">
            <Cpu className="size-5" />
          </div>
        </CardContent>
      </Card>

      {/* RAG Knowledge Docs */}
      <Card
        onClick={() => onSelectSection?.("knowledge")}
        className="bg-surface-raised border-border/40 hover:border-purple-500/40 hover:shadow-md transition-all cursor-pointer group"
      >
        <CardContent className="p-4 flex items-center justify-between">
          <div className="space-y-1">
            <div className="text-[11px] text-on-surface-variant font-medium">اسناد پایگاه دانش</div>
            <div className="text-2xl font-black text-on-surface font-mono group-hover:text-purple-400 transition-colors">
              {totalDocs}
            </div>
            <div className="text-[10px] text-on-surface-variant flex items-center gap-1">
              <Database className="size-3 text-purple-400" />
              <span>ایندکس برداری Weaviate</span>
            </div>
          </div>
          <div className="flex size-10 items-center justify-center rounded-xl bg-purple-500/10 border border-purple-500/20 text-purple-400 group-hover:scale-105 transition-transform">
            <Database className="size-5" />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
