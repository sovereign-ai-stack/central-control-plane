"use client";

import * as React from "react";
import { Edit2, FileText, FolderTree, Info, Save, Trash2, Users } from "lucide-react";
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
import type { AdminUserQuota, RagDocument, Team } from "@/lib/types";

interface TeamDetailDialogProps {
  team: Team | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  tab: "overview" | "users" | "docs" | "edit";
  onTabChange: (tab: "overview" | "users" | "docs" | "edit") => void;
  members: AdminUserQuota[];
  documents: RagDocument[];
  editName: string;
  onEditNameChange: (val: string) => void;
  editTokenLimit: number;
  onEditTokenLimitChange: (val: number) => void;
  editRpm: number;
  onEditRpmChange: (val: number) => void;
  editTpm: number;
  onEditTpmChange: (val: number) => void;
  onSave: (e: React.FormEvent) => void;
  onDelete: (teamId: string) => void;
}

export function TeamDetailDialog({
  team,
  open,
  onOpenChange,
  tab,
  onTabChange,
  members,
  documents,
  editName,
  onEditNameChange,
  editTokenLimit,
  onEditTokenLimitChange,
  editRpm,
  onEditRpmChange,
  editTpm,
  onEditTpmChange,
  onSave,
  onDelete,
}: TeamDetailDialogProps) {
  if (!team) return null;

  const teamMembers = members.filter((u) => u.teamId === team.id);
  const teamDocs = documents.filter((d) => d.teamId === team.id);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-xl bg-surface-raised border-border/40 text-on-surface" dir="rtl">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="flex size-9 items-center justify-center rounded-xl bg-brand-cyan/10 border border-brand-cyan/20 text-brand-cyan">
                <FolderTree className="size-5" />
              </div>
              <div>
                <DialogTitle className="text-base font-bold text-on-surface">{team.name}</DialogTitle>
                <DialogDescription className="text-xs text-on-surface-variant font-mono">
                  شناسه تیم: {team.id} | سازمان: {team.organizationName || team.organizationId}
                </DialogDescription>
              </div>
            </div>
            <Badge variant="outline" className="border-brand-cyan/30 text-brand-cyan text-xs">
              واحد سازمانی
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
              وضعیت و سهمیه
            </button>
            <button
              onClick={() => onTabChange("users")}
              className={`px-3 py-1.5 text-xs font-semibold border-b-2 transition-all cursor-pointer ${
                tab === "users"
                  ? "border-brand-cyan text-brand-cyan"
                  : "border-transparent text-on-surface-variant hover:text-on-surface"
              }`}
            >
              <Users className="size-3.5 inline-block me-1" />
              اعضای تیم ({teamMembers.length})
            </button>
            <button
              onClick={() => onTabChange("docs")}
              className={`px-3 py-1.5 text-xs font-semibold border-b-2 transition-all cursor-pointer ${
                tab === "docs"
                  ? "border-brand-cyan text-brand-cyan"
                  : "border-transparent text-on-surface-variant hover:text-on-surface"
              }`}
            >
              <FileText className="size-3.5 inline-block me-1" />
              اسناد RAG ({teamDocs.length})
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
              تنظیمات
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
                    {(team.tokenLimit || 0).toLocaleString()}
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-surface-container/40 border-border/30">
                <CardContent className="p-3">
                  <div className="text-[11px] text-on-surface-variant font-medium">توکن مصرف‌شده</div>
                  <div className="text-base font-bold text-brand-cyan font-mono mt-1">
                    {(team.usedTokens || 0).toLocaleString()}
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-surface-container/40 border-border/30">
                <CardContent className="p-3">
                  <div className="text-[11px] text-on-surface-variant font-medium">محدودیت نرخ (Rate Limit)</div>
                  <div className="text-xs font-bold text-on-surface font-mono mt-1">
                    {team.rpmLimit || 100} RPM / {(team.tpmLimit || 100000).toLocaleString()} TPM
                  </div>
                </CardContent>
              </Card>
            </div>

            <div className="space-y-1.5 bg-surface-container/30 border border-border/30 rounded-xl p-3">
              <div className="flex justify-between text-xs">
                <span className="text-on-surface-variant">درصد مصرف سهمیه توکن تیم:</span>
                <span className="font-mono font-bold text-on-surface">
                  {Math.round(((team.usedTokens || 0) / Math.max(1, team.tokenLimit || 1)) * 100)}%
                </span>
              </div>
              <div className="h-2 w-full rounded-full bg-surface-container overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-brand-cyan to-[#43B88C] transition-all"
                  style={{
                    width: `${Math.min(
                      100,
                      Math.round(((team.usedTokens || 0) / Math.max(1, team.tokenLimit || 1)) * 100)
                    )}%`,
                  }}
                />
              </div>
            </div>
          </div>
        )}

        {tab === "users" && (
          <div className="space-y-2 py-3 max-h-64 overflow-y-auto">
            {teamMembers.length === 0 ? (
              <div className="text-center py-6 text-xs text-on-surface-variant">
                هیچ کاربری به این تیم تخصیص داده نشده است.
              </div>
            ) : (
              teamMembers.map((member) => (
                <div
                  key={member.id}
                  className="flex items-center justify-between p-3 rounded-xl bg-surface-container/40 border border-border/30"
                >
                  <div className="flex items-center gap-2.5">
                    <div className="flex size-7 items-center justify-center rounded-lg bg-surface-raised border border-border/30 text-xs font-bold font-mono">
                      {member.name.charAt(0)}
                    </div>
                    <div>
                      <div className="text-xs font-bold text-on-surface">{member.name}</div>
                      <div className="text-[10.5px] text-on-surface-variant font-mono">{member.email}</div>
                    </div>
                  </div>
                  <Badge variant="outline" className="border-border/40 text-[10.5px]">
                    {member.role === "team_admin" ? "مدیر تیم" : "کاربر عادی"}
                  </Badge>
                </div>
              ))
            )}
          </div>
        )}

        {tab === "docs" && (
          <div className="space-y-2 py-3 max-h-64 overflow-y-auto">
            {teamDocs.length === 0 ? (
              <div className="text-center py-6 text-xs text-on-surface-variant">
                هیچ سند اختصاصی برای این تیم آپلود نشده است.
              </div>
            ) : (
              teamDocs.map((doc) => (
                <div
                  key={doc.id}
                  className="flex items-center justify-between p-3 rounded-xl bg-surface-container/40 border border-border/30"
                >
                  <div className="flex items-center gap-2.5">
                    <FileText className="size-4 text-warning" />
                    <div>
                      <div className="text-xs font-bold text-on-surface">{doc.name}</div>
                      <div className="text-[10.5px] text-on-surface-variant font-mono">
                        {doc.pageCount} صفحه | {Math.round((doc.size || 0) / 1024)} KB
                      </div>
                    </div>
                  </div>
                  <Badge variant="outline" className="border-border/40 text-[10.5px]">
                    {doc.status}
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
                <FieldLabel className="text-xs font-semibold">نام تیم</FieldLabel>
                <Input
                  value={editName}
                  onChange={(e) => onEditNameChange(e.target.value)}
                  className="bg-surface-container/50 text-sm"
                  required
                />
              </Field>

              <div className="grid grid-cols-3 gap-2.5">
                <Field>
                  <FieldLabel className="text-xs font-semibold">سقف توکن</FieldLabel>
                  <Input
                    type="number"
                    value={editTokenLimit}
                    onChange={(e) => onEditTokenLimitChange(Number(e.target.value))}
                    className="bg-surface-container/50 text-xs font-mono"
                    step={100000}
                  />
                </Field>
                <Field>
                  <FieldLabel className="text-xs font-semibold">RPM Limit</FieldLabel>
                  <Input
                    type="number"
                    value={editRpm}
                    onChange={(e) => onEditRpmChange(Number(e.target.value))}
                    className="bg-surface-container/50 text-xs font-mono"
                  />
                </Field>
                <Field>
                  <FieldLabel className="text-xs font-semibold">TPM Limit</FieldLabel>
                  <Input
                    type="number"
                    value={editTpm}
                    onChange={(e) => onEditTpmChange(Number(e.target.value))}
                    className="bg-surface-container/50 text-xs font-mono"
                  />
                </Field>
              </div>
            </FieldGroup>

            <DialogFooter className="gap-2 sm:gap-0 pt-3">
              <Button
                type="button"
                variant="destructive"
                size="sm"
                onClick={() => onDelete(team.id)}
                className="text-xs gap-1 me-auto"
              >
                <Trash2 className="size-3.5" />
                حذف تیم
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
