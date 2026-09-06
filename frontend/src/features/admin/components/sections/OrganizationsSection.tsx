"use client";

import * as React from "react";
import { Building2, Edit2, Plus, Users } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Organization } from "@/lib/types";

interface OrganizationsSectionProps {
  organizations: Organization[];
  onOpenAddOrg: () => void;
  onOpenDetail: (org: Organization) => void;
}

export function OrganizationsSection({
  organizations,
  onOpenAddOrg,
  onOpenDetail,
}: OrganizationsSectionProps) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-on-surface">مدیریت سازمان‌ها و شرکت‌ها</h2>
          <p className="text-xs text-on-surface-variant">
            تعریف سقف منابع، توکن و شرکت‌های استفاده‌کننده از کلاستر
          </p>
        </div>
        <Button
          size="sm"
          onClick={onOpenAddOrg}
          className="bg-brand-cyan hover:bg-brand-cyan-strong text-slate-950 font-bold text-xs gap-1.5 cursor-pointer"
        >
          <Plus className="size-4" />
          افزودن سازمان جدید
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {organizations.length === 0 ? (
          <div className="col-span-full text-center py-12 bg-surface-raised border border-border/30 rounded-2xl">
            <Building2 className="size-10 text-on-surface-variant/40 mx-auto mb-2" />
            <div className="text-sm font-semibold text-on-surface">هیچ سازمانی یافت نشد</div>
            <div className="text-xs text-on-surface-variant mt-1">
              جهت شروع، اولین سازمان را در سامانه تعریف نمایید.
            </div>
          </div>
        ) : (
          organizations.map((org) => {
            const usedPct = Math.min(
              100,
              Math.round(((org.usedTokens || 0) / Math.max(1, org.tokenLimit || 1)) * 100)
            );
            return (
              <Card
                key={org.id}
                onClick={() => onOpenDetail(org)}
                className="bg-surface-raised border-border/40 hover:border-brand-cyan/50 transition-all cursor-pointer group"
              >
                <CardHeader className="pb-3 flex flex-row items-start justify-between space-y-0">
                  <div className="space-y-1">
                    <CardTitle className="text-sm font-bold text-on-surface group-hover:text-brand-cyan transition-colors">
                      {org.name}
                    </CardTitle>
                    <div className="text-[11px] text-on-surface-variant font-mono">
                      کد: {org.code || org.name.substring(0, 3).toUpperCase()} | {org.id}
                    </div>
                  </div>
                  <Badge variant="outline" className="border-brand-cyan/30 text-brand-cyan text-[10.5px]">
                    {org.teamCount || 0} تیم
                  </Badge>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="space-y-1 bg-surface-container/30 border border-border/20 rounded-xl p-2.5">
                    <div className="flex justify-between text-[11px]">
                      <span className="text-on-surface-variant">مصرف ماهانه:</span>
                      <span className="font-mono font-bold text-on-surface">
                        {(org.usedTokens || 0).toLocaleString()} / {(org.tokenLimit || 0).toLocaleString()}
                      </span>
                    </div>
                    <div className="h-1.5 w-full rounded-full bg-surface-container overflow-hidden">
                      <div
                        className="h-full bg-brand-cyan transition-all"
                        style={{ width: `${usedPct}%` }}
                      />
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-1 text-[11px] text-on-surface-variant">
                    <span className="flex items-center gap-1">
                      <Users className="size-3.5" />
                      {org.userCount || 0} کاربر فعال
                    </span>
                    <Button variant="ghost" size="sm" className="h-7 text-xs text-brand-cyan gap-1">
                      <Edit2 className="size-3" />
                      مشاهده جزئیات
                    </Button>
                  </div>
                </CardContent>
              </Card>
            );
          })
        )}
      </div>
    </div>
  );
}
