"use client";

import * as React from "react";
import Link from "next/link";
import { BookOpen, ChevronRight, ShieldAlert, Sparkles, Upload, UserPlus } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { AdminSection } from "../../../types";

interface QuickActionsCardProps {
  onSelectSection?: (section: AdminSection) => void;
}

export function QuickActionsCard({ onSelectSection }: QuickActionsCardProps) {
  return (
    <Card className="bg-surface-raised border-border/40">
      <CardHeader className="pb-3 border-b border-border/30">
        <CardTitle className="text-sm font-bold text-on-surface flex items-center gap-2">
          <Sparkles className="size-4 text-brand-cyan" />
          <span>عملیات و دسترسی سریع (Quick Actions)</span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2.5 pt-4">
        {/* Knowledge Upload */}
        <button
          onClick={() => onSelectSection?.("knowledge")}
          className="w-full flex items-center justify-between p-3 rounded-xl bg-surface-container/40 hover:bg-surface-container-high border border-border/30 hover:border-brand-cyan/30 text-start transition-all cursor-pointer group"
        >
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-purple-500/10 text-purple-400 group-hover:scale-105 transition-transform">
              <Upload className="size-4" />
            </div>
            <div>
              <div className="text-xs font-bold text-on-surface group-hover:text-brand-cyan transition-colors">
                بارگذاری اسناد سازمانی (RAG)
              </div>
              <div className="text-[10.5px] text-on-surface-variant">افزودن PDF و متون به دیتابیس برداری</div>
            </div>
          </div>
          <ChevronRight className="size-4 text-on-surface-variant group-hover:text-brand-cyan group-hover:-translate-x-1 transition-all rotate-180" />
        </button>

        {/* User Management */}
        <button
          onClick={() => onSelectSection?.("users")}
          className="w-full flex items-center justify-between p-3 rounded-xl bg-surface-container/40 hover:bg-surface-container-high border border-border/30 hover:border-info/30 text-start transition-all cursor-pointer group"
        >
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-info/10 text-info group-hover:scale-105 transition-transform">
              <UserPlus className="size-4" />
            </div>
            <div>
              <div className="text-xs font-bold text-on-surface group-hover:text-info transition-colors">
                افزودن کاربر و انتساب نقش
              </div>
              <div className="text-[10.5px] text-on-surface-variant">تعریف حساب کاربری و انتساب به تیم</div>
            </div>
          </div>
          <ChevronRight className="size-4 text-on-surface-variant group-hover:text-info group-hover:-translate-x-1 transition-all rotate-180" />
        </button>

        {/* Quotas & Limits */}
        <button
          onClick={() => onSelectSection?.("limits")}
          className="w-full flex items-center justify-between p-3 rounded-xl bg-surface-container/40 hover:bg-surface-container-high border border-border/30 hover:border-warning/30 text-start transition-all cursor-pointer group"
        >
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-warning/10 text-warning group-hover:scale-105 transition-transform">
              <ShieldAlert className="size-4" />
            </div>
            <div>
              <div className="text-xs font-bold text-on-surface group-hover:text-warning transition-colors">
                تنظیم سهمیه‌ها و سقف توکن
              </div>
              <div className="text-[10.5px] text-on-surface-variant">ویرایش بودجه ماهانه تیم‌ها و کاربران</div>
            </div>
          </div>
          <ChevronRight className="size-4 text-on-surface-variant group-hover:text-warning group-hover:-translate-x-1 transition-all rotate-180" />
        </button>

        {/* Docs */}
        <Link href="/docs" className="block w-full">
          <div className="flex items-center justify-between p-3 rounded-xl bg-surface-container/40 hover:bg-surface-container-high border border-border/30 hover:border-brand-cyan/30 text-start transition-all cursor-pointer group">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-brand-cyan/10 text-brand-cyan group-hover:scale-105 transition-transform">
                <BookOpen className="size-4" />
              </div>
              <div>
                <div className="text-xs font-bold text-on-surface group-hover:text-brand-cyan transition-colors">
                  مستندات معماری و وب‌سرویس‌ها
                </div>
                <div className="text-[10.5px] text-on-surface-variant">راهنمای Gateway، Registry و Semantic</div>
              </div>
            </div>
            <ChevronRight className="size-4 text-on-surface-variant group-hover:text-brand-cyan group-hover:-translate-x-1 transition-all rotate-180" />
          </div>
        </Link>
      </CardContent>
    </Card>
  );
}
