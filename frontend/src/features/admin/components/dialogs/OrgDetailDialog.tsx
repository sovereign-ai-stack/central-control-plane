"use client";

import * as React from "react";
import { Building2, Edit2, FolderTree, Info, Save, Trash2, Users } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import type { Organization, Team } from "@/lib/types";

interface OrgDetailDialogProps {
  org: Organization | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  tab: "overview" | "teams" | "edit";
  onTabChange: (tab: "overview" | "teams" | "edit") => void;
  teams: Team[];
  editName: string;
  onEditNameChange: (val: string) => void;
  editCode: string;
  onEditCodeChange: (val: string) => void;
  editTokenLimit: number;
  onEditTokenLimitChange: (val: number) => void;
  onSave: (e: React.FormEvent) => void;
  onDelete: (orgId: string) => void;
}

export function OrgDetailDialog({
  org,
  open,
  onOpenChange,
  tab,
  onTabChange,
  teams,
  editName,
  onEditNameChange,
  editCode,
  onEditCodeChange,
  editTokenLimit,
  onEditTokenLimitChange,
  onSave,
  onDelete,
}: OrgDetailDialogProps) {
  if (!org) return null;

  const orgTeams = teams.filter((t) => t.organizationId === org.id);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-xl bg-surface-raised border-border/40 text-on-surface" dir="rtl">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="flex size-9 items-center justify-center rounded-xl bg-brand-cyan/10 border border-brand-cyan/20 text-brand-cyan">
                <Building2 className="size-5" />
              </div>
              <div>
                <DialogTitle className="text-base font-bold text-on-surface">{org.name}</DialogTitle>
                <DialogDescription className="text-xs text-on-surface-variant font-mono">
                  شناسه: {org.id} {org.code ? `(${org.code})` : ""}
                </DialogDescription>
              </div>
            </div>
            <Badge variant="outline" className="border-brand-cyan/30 text-brand-cyan text-xs">
              سازمان مستقل
            </Badge>
          </div>

          <div className="flex items-center gap-1 border-b border-border/30 pt-3">
            <button
              onClick={() => onTabChange("overview")}
              className={`px-3 py-1.5 text-xs font-semibold border-b-2 transition-all cursor-pointer ${
                tab === "overview"
                  ? "border-brand-cyan text-brand-cyan"
                  : "border-transparent text-on-surface-variant hover:text-on-surface"
              }`}
            >
              <Info className="size-3.5 inline-block me-1" />
              اطلاعات و سهمیه
            </button>
            <button
              onClick={() => onTabChange("teams")}
              className={`px-3 py-1.5 text-xs font-semibold border-b-2 transition-all cursor-pointer ${
                tab === "teams"
                  ? "border-brand-cyan text-brand-cyan"
                  : "border-transparent text-on-surface-variant hover:text-on-surface"
              }`}
            >
              <FolderTree className="size-3.5 inline-block me-1" />
              تیم‌ها ({orgTeams.length})
            </button>
            <button
              onClick={() => onTabChange("edit")}
              className={`px-3 py-1.5 text-xs font-semibold border-b-2 transition-all cursor-pointer ${
                tab === "edit"
                  ? "border-brand-cyan text-brand-cyan"
                  : "border-transparent text-on-surface-variant hover:text-on-surface"
              }`}
            >
              <Edit2 className="size-3.5 inline-block me-1" />
              ویرایش مشخصات
            </button>
          </div>
        </DialogHeader>

        {tab === "overview" && (
          <div className="space-y-4 py-3">
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <Card className="bg-surface-container/40 border-border/30">
                <CardContent className="p-3">
                  <div className="text-[11px] text-on-surface-variant font-medium">سقف توکن ماهانه</div>
                  <div className="text-base font-bold text-on-surface font-mono mt-1">
                    {(org.tokenLimit || 0).toLocaleString()}
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-surface-container/40 border-border/30">
                <CardContent className="p-3">
                  <div className="text-[11px] text-on-surface-variant font-medium">مصرف واقعی تیم‌ها</div>
                  <div className="text-base font-bold text-brand-cyan font-mono mt-1">
                    {(org.usedTokens || 0).toLocaleString()}
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-surface-container/40 border-border/30">
                <CardContent className="p-3">
                  <div className="text-[11px] text-on-surface-variant font-medium">تعداد کل تیم‌ها</div>
                  <div className="text-base font-bold text-on-surface mt-1">{orgTeams.length} تیم</div>
                </CardContent>
              </Card>
            </div>

            <div className="space-y-1.5 bg-surface-container/30 border border-border/30 rounded-xl p-3">
              <div className="flex justify-between text-xs">
                <span className="text-on-surface-variant">درصد مصرف سهمیه توکن سازمان:</span>
                <span className="font-mono font-bold text-on-surface">
                  {Math.round(((org.usedTokens || 0) / Math.max(1, org.tokenLimit || 1)) * 100)}%
                </span>
              </div>
              <div className="h-2 w-full rounded-full bg-surface-container overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-brand-cyan to-[#43B88C] transition-all"
                  style={{
                    width: `${Math.min(
                      100,
                      Math.round(((org.usedTokens || 0) / Math.max(1, org.tokenLimit || 1)) * 100)
                    )}%`,
                  }}
                />
              </div>
            </div>
          </div>
        )}

        {tab === "teams" && (
          <div className="space-y-2 py-3 max-h-64 overflow-y-auto">
            {orgTeams.length === 0 ? (
              <div className="text-center py-6 text-xs text-on-surface-variant">
                هیچ تیمی برای این سازمان تعریف نشده است.
              </div>
            ) : (
              orgTeams.map((team) => (
                <div
                  key={team.id}
                  className="flex items-center justify-between p-3 rounded-xl bg-surface-container/40 border border-border/30"
                >
                  <div className="flex items-center gap-2.5">
                    <FolderTree className="size-4 text-brand-cyan" />
                    <div>
                      <div className="text-xs font-bold text-on-surface">{team.name}</div>
                      <div className="text-[10.5px] text-on-surface-variant font-mono">
                        سقف: {(team.tokenLimit || 0).toLocaleString()} توکن | اعضا: {team.memberCount || 0} نفر
                      </div>
                    </div>
                  </div>
                  <Badge variant="outline" className="border-border/40 text-[11px] font-mono">
                    {team.id}
                  </Badge>
                </div>
              ))
            )}
          </div>
        )}

        {tab === "edit" && (
          <form onSubmit={onSave} className="space-y-3 py-2">
            <FieldGroup className="space-y-3">
              <Field>
                <FieldLabel className="text-xs font-semibold">نام سازمان</FieldLabel>
                <Input
                  value={editName}
                  onChange={(e) => onEditNameChange(e.target.value)}
                  className="bg-surface-container/50 text-sm"
                  required
                />
              </Field>

              <div className="grid grid-cols-2 gap-3">
                <Field>
                  <FieldLabel className="text-xs font-semibold">شناسه کوتاه</FieldLabel>
                  <Input
                    value={editCode}
                    onChange={(e) => onEditCodeChange(e.target.value)}
                    className="bg-surface-container/50 text-sm font-mono uppercase"
                  />
                </Field>
                <Field>
                  <FieldLabel className="text-xs font-semibold">سقف توکن ماهانه</FieldLabel>
                  <Input
                    type="number"
                    value={editTokenLimit}
                    onChange={(e) => onEditTokenLimitChange(Number(e.target.value))}
                    className="bg-surface-container/50 text-sm font-mono"
                    step={500000}
                  />
                </Field>
              </div>
            </FieldGroup>

            <DialogFooter className="gap-2 sm:gap-0 pt-3">
              <Button
                type="button"
                variant="destructive"
                size="sm"
                onClick={() => onDelete(org.id)}
                className="text-xs gap-1 me-auto"
              >
                <Trash2 className="size-3.5" />
                حذف سازمان
              </Button>
              <Button
                type="submit"
                size="sm"
                className="bg-brand-cyan hover:bg-brand-cyan-strong text-slate-950 font-bold text-xs gap-1"
              >
                <Save className="size-3.5" />
                ذخیره تغییرات
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
