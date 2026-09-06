"use client";

import * as React from "react";
import { FolderTree, Plus, Users } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Team } from "@/lib/types";

interface TeamsSectionProps {
  teams: Team[];
  onOpenAddTeam: () => void;
  onOpenDetail: (team: Team) => void;
}

export function TeamsSection({
  teams,
  onOpenAddTeam,
  onOpenDetail,
}: TeamsSectionProps) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-on-surface">مدیریت تیم‌ها و واحدها</h2>
          <p className="text-xs text-on-surface-variant">
            تفکیک دپارتمان‌ها و تخصیص سقف منابع هوش مصنوعی به هر بخش
          </p>
        </div>
        <Button
          size="sm"
          onClick={onOpenAddTeam}
          className="bg-brand-cyan hover:bg-brand-cyan-strong text-slate-950 font-bold text-xs gap-1.5 cursor-pointer"
        >
          <Plus className="size-4" />
          تعریف تیم جدید
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {teams.length === 0 ? (
          <div className="col-span-full text-center py-12 bg-surface-raised border border-border/30 rounded-2xl">
            <FolderTree className="size-10 text-on-surface-variant/40 mx-auto mb-2" />
            <div className="text-sm font-semibold text-on-surface">هیچ تیمی یافت نشد</div>
            <div className="text-xs text-on-surface-variant mt-1">
              جهت شروع، اولین تیم را در سازمان خود تعریف کنید.
            </div>
          </div>
        ) : (
          teams.map((team) => {
            const usedPct = Math.min(
              100,
              Math.round(((team.usedTokens || 0) / Math.max(1, team.tokenLimit || 1)) * 100)
            );
            return (
              <Card
                key={team.id}
                onClick={() => onOpenDetail(team)}
                className="bg-surface-raised border-border/40 hover:border-brand-cyan/50 transition-all cursor-pointer group"
              >
                <CardHeader className="pb-3 flex flex-row items-start justify-between space-y-0">
                  <div className="space-y-1">
                    <CardTitle className="text-sm font-bold text-on-surface group-hover:text-brand-cyan transition-colors">
                      {team.name}
                    </CardTitle>
                    <div className="text-[11px] text-on-surface-variant font-mono">
                      سازمان: {team.organizationName || team.organizationId}
                    </div>
                  </div>
                  <Badge variant="outline" className="border-border/40 text-[10.5px]">
                    {team.memberCount || 0} عضو
                  </Badge>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="space-y-1 bg-surface-container/30 border border-border/20 rounded-xl p-2.5">
                    <div className="flex justify-between text-[11px]">
                      <span className="text-on-surface-variant">مصرف سهمیه:</span>
                      <span className="font-mono font-bold text-on-surface">
                        {(team.usedTokens || 0).toLocaleString()} / {(team.tokenLimit || 0).toLocaleString()}
                      </span>
                    </div>
                    <div className="h-1.5 w-full rounded-full bg-surface-container overflow-hidden">
                      <div
                        className="h-full bg-warning transition-all"
                        style={{ width: `${usedPct}%` }}
                      />
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-1 text-[11px] text-on-surface-variant">
                    <span className="font-mono">
                      {team.rpmLimit || 100} RPM | {(team.tpmLimit || 100000).toLocaleString()} TPM
                    </span>
                    <Button variant="ghost" size="sm" className="h-7 text-xs text-brand-cyan">
                      مدیریت تیم
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
