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
        className="bg-surface-container/20 border-border/30 hover:bg-surface-container/40 hover:border-brand-cyan/40 hover:shadow-lg transition-all duration-300 cursor-pointer group"
      >
        <CardContent className="p-5 flex flex-col items-center text-center space-y-3">
          <div className="flex size-12 items-center justify-center rounded-2xl bg-brand-cyan/10 border border-brand-cyan/20 text-brand-cyan group-hover:scale-110 transition-transform duration-300">
            <Building2 className="size-6" />
          </div>
          <div>
            <div className="text-3xl font-black text-on-surface font-mono group-hover:text-brand-cyan transition-colors">
              {totalOrgs}
            </div>
            <div className="text-xs text-on-surface-variant font-bold mt-1">سازمان‌های مستقل</div>
            <div className="text-[10px] text-on-surface-variant/70 mt-0.5">شارد‌های ایزوله داده</div>
          </div>
        </CardContent>
      </Card>

      {/* Teams */}
      <Card
        onClick={() => onSelectSection?.("teams")}
        className="bg-surface-container/20 border-border/30 hover:bg-surface-container/40 hover:border-warning/40 hover:shadow-lg transition-all duration-300 cursor-pointer group"
      >
        <CardContent className="p-5 flex flex-col items-center text-center space-y-3">
          <div className="flex size-12 items-center justify-center rounded-2xl bg-warning/10 border border-warning/20 text-warning group-hover:scale-110 transition-transform duration-300">
            <FolderTree className="size-6" />
          </div>
          <div>
            <div className="text-3xl font-black text-on-surface font-mono group-hover:text-warning transition-colors">
              {totalTeams}
            </div>
            <div className="text-xs text-on-surface-variant font-bold mt-1">تیم‌های پردازشی</div>
            <div className="text-[10px] text-on-surface-variant/70 mt-0.5">سهمیه توکن مستقل</div>
          </div>
        </CardContent>
      </Card>

      {/* Users */}
      <Card
        onClick={() => onSelectSection?.("users")}
        className="bg-surface-container/20 border-border/30 hover:bg-surface-container/40 hover:border-info/40 hover:shadow-lg transition-all duration-300 cursor-pointer group"
      >
        <CardContent className="p-5 flex flex-col items-center text-center space-y-3">
          <div className="flex size-12 items-center justify-center rounded-2xl bg-info/10 border border-info/20 text-info group-hover:scale-110 transition-transform duration-300">
            <Users className="size-6" />
          </div>
          <div>
            <div className="text-3xl font-black text-on-surface font-mono group-hover:text-info transition-colors">
              {totalUsers}
            </div>
            <div className="text-xs text-on-surface-variant font-bold mt-1">کاربران مجاز</div>
            <div className="text-[10px] text-on-surface-variant/70 mt-0.5">کنترل دسترسی RBAC</div>
          </div>
        </CardContent>
      </Card>

      {/* GPU Nodes */}
      <Card className="bg-surface-container/20 border-border/30 hover:bg-surface-container/40 hover:border-emerald-500/40 hover:shadow-lg transition-all duration-300 group">
        <CardContent className="p-5 flex flex-col items-center text-center space-y-3">
          <div className="flex size-12 items-center justify-center rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 group-hover:scale-110 transition-transform duration-300 relative">
            <Cpu className="size-6" />
            {activeNodesCount > 0 ? (
              <span className="absolute -top-1 -right-1 size-3 rounded-full bg-emerald-400 border-2 border-surface animate-pulse" title="آنلاین"></span>
            ) : (
              <span className="absolute -top-1 -right-1 size-3 rounded-full bg-on-surface-variant/40 border-2 border-surface" title="آفلاین"></span>
            )}
          </div>
          <div>
            <div className="text-3xl font-black text-emerald-400 font-mono">
              {activeNodesCount}
            </div>
            <div className="text-xs text-on-surface-variant font-bold mt-1">نودهای فعال GPU</div>
            <div className="text-[10px] text-on-surface-variant/70 mt-0.5">{totalVramGb} GB مجموع VRAM</div>
          </div>
        </CardContent>
      </Card>

      {/* RAG Knowledge Docs */}
      <Card
        onClick={() => onSelectSection?.("knowledge")}
        className="bg-surface-container/20 border-border/30 hover:bg-surface-container/40 hover:border-purple-500/40 hover:shadow-lg transition-all duration-300 cursor-pointer group"
      >
        <CardContent className="p-5 flex flex-col items-center text-center space-y-3">
          <div className="flex size-12 items-center justify-center rounded-2xl bg-purple-500/10 border border-purple-500/20 text-purple-400 group-hover:scale-110 transition-transform duration-300">
            <Database className="size-6" />
          </div>
          <div>
            <div className="text-3xl font-black text-on-surface font-mono group-hover:text-purple-400 transition-colors">
              {totalDocs}
            </div>
            <div className="text-xs text-on-surface-variant font-bold mt-1">اسناد پایگاه دانش</div>
            <div className="text-[10px] text-on-surface-variant/70 mt-0.5">ایندکس برداری Weaviate</div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
