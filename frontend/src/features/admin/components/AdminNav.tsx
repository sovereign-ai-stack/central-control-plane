"use client";

import * as React from "react";
import Link from "next/link";
import { ArrowLeft, ChevronRight, LogOut, Shield, Activity, ExternalLink } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { BrandLogoIcon } from "@/components/ui/brand-logo";
import { ALL_NAV_ITEMS, ALLOWED_OBSERVABILITY_ROLES, getLangfuseUrl, getLiteLlmUrl, type AdminSection } from "@/features/admin/types";
import { Zap } from "lucide-react";
import type { AuthUser, UserRole } from "@/lib/types";

interface AdminNavProps {
  activeSection: AdminSection;
  onSelectSection: (section: AdminSection) => void;
  currentUser: AuthUser | null;
  onCloseMobile?: () => void;
}

export function AdminNav({
  activeSection,
  onSelectSection,
  currentUser,
  onCloseMobile,
}: AdminNavProps) {
  const role = (currentUser?.role || "super_admin") as UserRole;
  const [langfuseUrl, setLangfuseUrl] = React.useState("http://localhost:3000");
  const [litellmUrl, setLitellmUrl] = React.useState("http://localhost:4000");

  React.useEffect(() => {
    setLangfuseUrl(getLangfuseUrl());
    setLitellmUrl(getLiteLlmUrl());
  }, []);

  const allowedNavItems = ALL_NAV_ITEMS.filter((item) =>
    item.allowedRoles.includes(role)
  );

  return (
    <aside className="w-64 shrink-0 bg-surface-raised border-s border-border/40 flex flex-col h-full select-none">
      {/* 1. BRAND HEADER */}
      <div className="p-4 border-b border-border/30 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <BrandLogoIcon className="size-8" />
          <div>
            <div className="text-sm font-bold text-on-surface">پنل مدیریت سازمانی</div>
            <div className="text-[10.5px] text-on-surface-variant font-mono">Control Plane v2.0</div>
          </div>
        </div>
      </div>

      {/* 2. NAVIGATION LINKS */}
      <div className="flex-1 overflow-y-auto p-3 space-y-1 scrollbar-thin">
        <div className="px-3 py-1.5 text-[10.5px] font-bold text-on-surface-variant/70 uppercase tracking-wider">
          بخش‌های مدیریتی
        </div>

        {allowedNavItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeSection === item.id;
          return (
            <button
              key={item.id}
              onClick={() => {
                onSelectSection(item.id);
                if (onCloseMobile) onCloseMobile();
              }}
              className={`w-full flex items-center justify-between p-2.5 rounded-xl text-xs font-medium transition-all ${
                isActive
                  ? "bg-brand-cyan/15 text-brand-cyan font-bold border border-brand-cyan/30 shadow-sm"
                  : "text-on-surface-variant hover:text-on-surface hover:bg-surface-elevated/50"
              }`}
            >
              <div className="flex items-center gap-2.5">
                <div
                  className={`size-6 rounded-lg flex items-center justify-center ${
                    isActive ? "bg-brand-cyan/20 text-brand-cyan" : "text-on-surface-variant"
                  }`}
                >
                  <Icon className="size-3.5" />
                </div>
                <div className="text-start">
                  <div>{item.label}</div>
                  <div className="text-[10px] text-on-surface-variant/70 font-normal leading-tight">
                    {item.detail}
                  </div>
                </div>
              </div>
              <ChevronRight
                className={`size-3.5 transition-transform ${
                  isActive ? "rotate-90 text-brand-cyan" : "text-on-surface-variant/40"
                }`}
              />
            </button>
          );
        })}

        {/* OBSERVABILITY & INFERENCE LINKS FOR AUTHORIZED ROLES */}
        {ALLOWED_OBSERVABILITY_ROLES.includes(role) && (
          <div className="pt-2 space-y-1.5">
            <div className="px-3 py-1.5 text-[10.5px] font-bold text-on-surface-variant/70 uppercase tracking-wider">
              نظارت و زیرساخت استنتاج
            </div>

            {/* LANGFUSE TRACING LINK */}
            <a
              href={langfuseUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="w-full flex items-center justify-between p-2.5 rounded-xl text-xs font-semibold text-brand-cyan hover:bg-brand-cyan/10 border border-brand-cyan/25 transition-all group/langfuse cursor-pointer"
            >
              <div className="flex items-center gap-2.5">
                <div className="size-6 rounded-lg bg-brand-cyan/15 flex items-center justify-center text-brand-cyan">
                  <Activity className="size-3.5 animate-pulse" />
                </div>
                <div className="text-start">
                  <div className="flex items-center gap-1.5 font-bold">
                    <span>ردیابی Langfuse</span>
                    <Badge variant="outline" className="text-[9px] px-1 py-0 h-4 border-brand-cyan/40 bg-brand-cyan/10 text-brand-cyan">
                      زنده
                    </Badge>
                  </div>
                  <div className="text-[10px] text-on-surface-variant/80 font-normal leading-tight">
                    مشاهده Traces و تله‌متری
                  </div>
                </div>
              </div>
              <ExternalLink className="size-3.5 text-brand-cyan/70 group-hover/langfuse:text-brand-cyan group-hover/langfuse:translate-x-[-2px] transition-all shrink-0" />
            </a>

            {/* LITELLM PROXY DASHBOARD LINK */}
            <a
              href={litellmUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="w-full flex items-center justify-between p-2.5 rounded-xl text-xs font-semibold text-purple-400 hover:bg-purple-500/10 border border-purple-500/25 transition-all group/litellm cursor-pointer"
            >
              <div className="flex items-center gap-2.5">
                <div className="size-6 rounded-lg bg-purple-500/15 flex items-center justify-center text-purple-400">
                  <Zap className="size-3.5" />
                </div>
                <div className="text-start">
                  <div className="flex items-center gap-1.5 font-bold">
                    <span>درگاه LiteLLM</span>
                    <Badge variant="outline" className="text-[9px] px-1 py-0 h-4 border-purple-500/40 bg-purple-500/10 text-purple-400">
                      لایه استنتاج
                    </Badge>
                  </div>
                  <div className="text-[10px] text-on-surface-variant/80 font-normal leading-tight">
                    مدیریت روتینگ، کلیدها و بودجه
                  </div>
                </div>
              </div>
              <ExternalLink className="size-3.5 text-purple-400/70 group-hover/litellm:text-purple-400 group-hover/litellm:translate-x-[-2px] transition-all shrink-0" />
            </a>
          </div>
        )}
      </div>

      {/* 3. USER PROFILE & RETURN TO CHAT */}
      <div className="p-3 border-t border-border/30 space-y-2">
        <Link href="/" className="w-full">
          <Button
            variant="outline"
            size="sm"
            className="w-full text-xs gap-1.5 border-border/40 hover:border-brand-cyan/40 hover:text-brand-cyan cursor-pointer"
          >
            <ArrowLeft className="size-3.5" />
            بازگشت به محیط چت
          </Button>
        </Link>
      </div>
    </aside>
  );
}
