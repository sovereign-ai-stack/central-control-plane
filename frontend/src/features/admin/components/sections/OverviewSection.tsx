"use client";

import * as React from "react";
import Link from "next/link";
import { AlertCircle, BookOpen, Bot, RefreshCw } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { AdminDashboard, AuthUser, UserRole } from "@/lib/types";
import type { AdminSection } from "../../types";
import { AuditLogFeed } from "./overview/AuditLogFeed";
import { ClusterStatusCard } from "./overview/ClusterStatusCard";
import { KpiMetricsGrid } from "./overview/KpiMetricsGrid";
import { ModelFleetGrid } from "./overview/ModelFleetGrid";
import { QuickActionsCard } from "./overview/QuickActionsCard";
import { TokenQuotaCard } from "./overview/TokenQuotaCard";

interface OverviewSectionProps {
  dashboard: AdminDashboard | null;
  currentUser: AuthUser | null;
  organizations?: any[];
  teams?: any[];
  users?: any[];
  documents?: any[];
  models?: any[];
  onSelectSection?: (section: AdminSection) => void;
  onRefresh?: () => void;
}

export function OverviewSection({
  dashboard,
  currentUser,
  organizations = [],
  teams = [],
  users = [],
  documents = [],
  models = [],
  onSelectSection,
  onRefresh,
}: OverviewSectionProps) {
  const role = (currentUser?.role || "user") as UserRole;

  const totalUsers = dashboard?.totalUsers ?? users.length;
  const totalOrgs = dashboard?.totalOrganizations ?? Math.max(1, organizations.length);
  const totalTeams = dashboard?.totalTeams ?? Math.max(1, teams.length);
  const totalDocs = documents.length;
  const tokensUsed = dashboard?.tokensThisMonth ?? 0;
  const tokenLimit = dashboard?.workspaceTokenLimit ?? 20000000;
  const usedPercent = dashboard?.tokenUsagePercent ?? Math.min(100, Math.round((tokensUsed / Math.max(1, tokenLimit)) * 100));
  const activeNodes = dashboard?.activeNodes ?? [];

  // VRAM & Hardware summary
  const totalVramGb = activeNodes.reduce((acc, node: any) => {
    return acc + (node?.hardware?.total_vram_gb || 0);
  }, 0);

  // Error State: if dashboard completely failed to load
  if (!dashboard && !users.length && !organizations.length) {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-center rounded-2xl bg-surface-raised border border-border/40 space-y-4">
        <div className="size-12 rounded-2xl bg-destructive/10 text-destructive flex items-center justify-center">
          <AlertCircle className="size-6" />
        </div>
        <div className="space-y-1">
          <h3 className="text-sm font-bold text-on-surface">خطا در بارگذاری داده‌های داشبورد</h3>
          <p className="text-xs text-on-surface-variant max-w-sm">
            ارتباط با سرور مرکزی برقرار نشد یا پاسخی دریافت نگردید. لطفاً مجدداً تلاش فرمایید.
          </p>
        </div>
        {onRefresh && (
          <Button
            size="sm"
            onClick={onRefresh}
            variant="outline"
            className="text-xs gap-1.5 border-border/50 hover:border-brand-cyan/40 hover:text-brand-cyan cursor-pointer"
          >
            <RefreshCw className="size-3.5" />
            <span>تلاش مجدد</span>
          </Button>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-6 select-none" dir="rtl">
      {/* 1. GREETING & CLUSTER HEALTH BANNER */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-surface-raised via-surface-container/60 to-surface-raised border border-border/50 p-5 sm:p-6 shadow-sm">
        <div className="absolute top-0 start-0 h-full w-1.5 bg-gradient-to-b from-brand-cyan via-emerald-400 to-brand-mint" />
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2">
              <span className="text-base sm:text-lg font-black text-on-surface">
                داشبورد نظارت و مدیریت کلاستر Sovereign AI
              </span>
              <Badge className="bg-emerald-500/15 text-emerald-400 border-emerald-500/30 text-[10.5px] gap-1 px-2 py-0.5">
                <span className="size-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                <span>کلاستر عملیاتی</span>
              </Badge>
            </div>
            <p className="text-xs text-on-surface-variant leading-relaxed max-w-2xl">
              خوش آمدید، <span className="font-bold text-on-surface">{currentUser?.name || "مدیر محترم"}</span>.
              وضعیت ورکرها، سهمیه توکن‌های چندمستأجری، پایگاه برداری Weaviate و مدل‌های استنتاجی در لحظه پایش می‌شوند.
            </p>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <Link href="/docs">
              <Button size="sm" variant="outline" className="text-xs gap-1.5 border-border/50 hover:border-brand-cyan/40 hover:text-brand-cyan cursor-pointer">
                <BookOpen className="size-3.5" />
                <span>مستندات فنی</span>
              </Button>
            </Link>
            <Link href="/">
              <Button size="sm" className="bg-brand-cyan hover:bg-brand-cyan-strong text-slate-950 font-bold text-xs gap-1.5 cursor-pointer">
                <Bot className="size-3.5" />
                <span>ورود به چت</span>
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* 2. TOP METRICS KPI CARDS */}
      <KpiMetricsGrid
        totalOrgs={totalOrgs}
        totalTeams={totalTeams}
        totalUsers={totalUsers}
        activeNodesCount={activeNodes.length}
        totalVramGb={totalVramGb}
        totalDocs={totalDocs}
        onSelectSection={onSelectSection}
      />

      {/* 3. MULTI-LEVEL TOKEN QUOTA & CLUSTER STATUS */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <TokenQuotaCard
          tokensUsed={tokensUsed}
          tokenLimit={tokenLimit}
          usedPercent={usedPercent}
          maxRps={dashboard?.maxRps}
          inferenceConcurrency={dashboard?.inferenceConcurrency}
          messagesPerHour={dashboard?.messagesPerHour}
          maxPdfPages={dashboard?.maxPdfPages}
          onSelectSection={onSelectSection}
        />
        <ClusterStatusCard
          litellmStatus={dashboard?.litellm?.status}
          gatewayStatus="healthy"
          routerLatency="Sub-15ms"
          vectorDbStatus="ready"
        />
      </div>

      {/* 4. ACTIVE MODEL FLEET & ROLE DISTRIBUTION */}
      <ModelFleetGrid
        isSuperAdmin={role === "super_admin"}
        models={models}
        onSelectSection={onSelectSection}
      />

      {/* 5. QUICK ACTIONS & AUDIT TELEMETRY FEED */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <QuickActionsCard onSelectSection={onSelectSection} />
        <AuditLogFeed
          activeNodesCount={activeNodes.length}
          totalDocs={totalDocs}
        />
      </div>
    </div>
  );
}
