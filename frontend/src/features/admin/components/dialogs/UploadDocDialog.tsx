"use client";

import * as React from "react";
import { FileText, Loader2, Sparkles, Upload, AlignLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { CustomSelect } from "@/components/ui/custom-select";
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
import { cn } from "@/lib/utils";
import type { Organization, Team } from "@/lib/types";

interface UploadDocDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  docMode?: "file" | "text";
  onDocModeChange?: (mode: "file" | "text") => void;
  file: File | null;
  onFileChange: (file: File | null) => void;
  textTitle?: string;
  onTextTitleChange?: (val: string) => void;
  textContent?: string;
  onTextContentChange?: (val: string) => void;
  orgId: string;
  onOrgIdChange: (val: string) => void;
  teamId: string;
  onTeamIdChange: (val: string) => void;
  uploading: boolean;
  stageText: string;
  organizations: Organization[];
  teams: Team[];
  currentUserOrgId?: string | null;
  currentUserTeamId?: string | null;
  currentUserRole?: string;
  onSubmit: (e: React.FormEvent) => void;
}

export function UploadDocDialog({
  open,
  onOpenChange,
  docMode = "file",
  onDocModeChange,
  file,
  onFileChange,
  textTitle = "",
  onTextTitleChange,
  textContent = "",
  onTextContentChange,
  orgId,
  onOrgIdChange,
  teamId,
  onTeamIdChange,
  uploading,
  stageText,
  organizations,
  teams,
  currentUserOrgId,
  currentUserRole = "user",
  onSubmit,
}: UploadDocDialogProps) {
  const isSuperAdmin = currentUserRole === "super_admin";
  const availableTeams = orgId ? teams.filter((t) => t.organizationId === orgId) : [];

  const handleOrgChange = (newOrgId: string) => {
    onOrgIdChange(newOrgId);
    if (!newOrgId) {
      onTeamIdChange("global");
    } else {
      const orgTeams = teams.filter((t) => t.organizationId === newOrgId);
      const isCurrentTeamValid = orgTeams.some((t) => t.id === teamId);
      if (!isCurrentTeamValid) {
        onTeamIdChange("global");
      }
    }
  };

  const getFileBadge = (filename: string) => {
    const ext = filename.split(".").pop()?.toLowerCase();
    if (ext === "pdf") return "PDF";
    if (ext === "docx" || ext === "doc") return "Word";
    if (ext === "txt" || ext === "md") return "متن";
    return "سند";
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg bg-surface-raised border-border/40 text-on-surface" dir="rtl">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <div className="flex size-9 items-center justify-center rounded-xl bg-brand-cyan/10 border border-brand-cyan/20 text-brand-cyan">
              <Upload className="size-5" />
            </div>
            <div>
              <DialogTitle className="text-base font-bold text-on-surface">افزودن سند به پایگاه دانش (RAG)</DialogTitle>
              <DialogDescription className="text-xs text-on-surface-variant">
                پشتیبانی از فایل‌های Word (.docx)، PDF، متنی (.txt) یا کپی و درج مستقیم متن
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        {/* Ingestion Mode Toggle Tabs */}
        <div className="grid grid-cols-2 p-1 bg-surface-container/50 rounded-xl border border-border/30 gap-1 mt-1">
          <button
            type="button"
            onClick={() => onDocModeChange?.("file")}
            className={cn(
              "flex items-center justify-center gap-2 py-2 text-xs font-semibold rounded-lg transition-all cursor-pointer",
              docMode === "file"
                ? "bg-brand-cyan text-slate-950 font-bold shadow-sm"
                : "text-on-surface-variant hover:text-on-surface hover:bg-surface-raised/50"
            )}
          >
            <FileText className="size-3.5" />
            <span>بارگذاری فایل (PDF / Word / متن)</span>
          </button>
          <button
            type="button"
            onClick={() => onDocModeChange?.("text")}
            className={cn(
              "flex items-center justify-center gap-2 py-2 text-xs font-semibold rounded-lg transition-all cursor-pointer",
              docMode === "text"
                ? "bg-brand-cyan text-slate-950 font-bold shadow-sm"
                : "text-on-surface-variant hover:text-on-surface hover:bg-surface-raised/50"
            )}
          >
            <AlignLeft className="size-3.5" />
            <span>درج مستقیم متن</span>
          </button>
        </div>

        <form onSubmit={onSubmit} className="space-y-4 py-1">
          <FieldGroup className="space-y-3">
            {docMode === "file" ? (
              <div className="flex flex-col items-center justify-center border-2 border-dashed border-border/60 hover:border-brand-cyan/60 rounded-2xl p-5 bg-surface-container/20 transition-all text-center">
                <input
                  type="file"
                  id="doc-file-upload"
                  accept=".pdf,.docx,.doc,.txt,.md,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/msword,text/plain,text/markdown"
                  className="hidden"
                  disabled={uploading}
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      onFileChange(e.target.files[0]);
                    }
                  }}
                />
                <label htmlFor="doc-file-upload" className="cursor-pointer flex flex-col items-center gap-2 w-full">
                  <div className="flex size-12 items-center justify-center rounded-2xl bg-brand-cyan/10 border border-brand-cyan/20 text-brand-cyan">
                    <FileText className="size-6" />
                  </div>
                  {file ? (
                    <div className="space-y-1">
                      <div className="flex items-center justify-center gap-1.5">
                        <span className="text-xs font-bold text-brand-cyan line-clamp-1">{file.name}</span>
                        <span className="bg-brand-cyan/20 text-brand-cyan text-[10px] font-mono px-1.5 py-0.5 rounded">
                          {getFileBadge(file.name)}
                        </span>
                      </div>
                      <div className="text-[11px] text-on-surface-variant font-mono">
                        حجم: {Math.round(file.size / 1024)} KB
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-1">
                      <div className="text-xs font-semibold text-on-surface">کلیک جهت انتخاب فایل PDF، Word (.docx) یا متنی (.txt)</div>
                      <div className="text-[11px] text-on-surface-variant">حداکثر حجم فایل ۲۵۰ مگابایت</div>
                    </div>
                  )}
                </label>
              </div>
            ) : (
              <div className="space-y-3">
                <Field>
                  <FieldLabel className="text-xs font-semibold">عنوان یا نام سند</FieldLabel>
                  <Input
                    value={textTitle}
                    onChange={(e) => onTextTitleChange?.(e.target.value)}
                    placeholder="مثال: خلاصه جزوه الگوریتم‌های بازگشتی..."
                    disabled={uploading}
                    className="bg-surface-container/50 text-xs"
                    required
                  />
                </Field>

                <Field>
                  <FieldLabel className="text-xs font-semibold">متن کامل سند (جهت قطعه‌بندی برداری)</FieldLabel>
                  <textarea
                    value={textContent}
                    onChange={(e) => onTextContentChange?.(e.target.value)}
                    placeholder="متن کامل یا کپی‌شده از فایل، کتاب یا جزوه را در اینجا الصاق (Paste) کنید..."
                    disabled={uploading}
                    rows={6}
                    className="w-full rounded-xl border border-border/40 bg-surface-container/50 p-3 text-xs text-on-surface placeholder:text-on-surface-variant/50 focus:outline-none focus:ring-1 focus:ring-brand-cyan transition-all resize-y min-h-[120px]"
                    required
                  />
                  <div className="flex justify-between items-center text-[10.5px] text-on-surface-variant px-1">
                    <span>تعداد کاراکترها: {textContent.length.toLocaleString("fa-IR")}</span>
                    <span>تخمین صفحات: {Math.max(1, Math.ceil(textContent.length / 2000)).toLocaleString("fa-IR")}</span>
                  </div>
                </Field>
              </div>
            )}

            {isSuperAdmin && (
              <Field>
                <FieldLabel className="text-xs font-semibold">تخصیص به سازمان</FieldLabel>
                <CustomSelect
                  value={orgId}
                  onChange={handleOrgChange}
                  options={[
                    { value: "", label: "سازمان عمومی / کل سامانه" },
                    ...organizations.map((o) => ({ value: o.id, label: `${o.name} (${o.code || o.id})` })),
                  ]}
                  className="w-full bg-surface-container/50 text-xs"
                />
              </Field>
            )}

            <Field>
              <FieldLabel className="text-xs font-semibold">واحد / تیم دسترسی‌دارنده</FieldLabel>
              <CustomSelect
                value={teamId}
                onChange={onTeamIdChange}
                disabled={!orgId}
                options={[
                  { value: "global", label: "پایگاه دانش سراسری (تمام تیم‌ها)" },
                  ...availableTeams.map((t) => ({ value: t.id, label: `تیم ${t.name}` })),
                ]}
                className="w-full bg-surface-container/50 text-xs disabled:opacity-70"
              />
              {!orgId && (
                <p className="text-[11px] text-brand-cyan/80 mt-1">
                  در حالت سازمان عمومی، سند به عنوان منبع دانش عمومی برای کل سامانه (تمام سازمان‌ها و تیم‌ها) ایندکس خواهد شد.
                </p>
              )}
            </Field>

            {uploading && (
              <div className="space-y-2 p-3 rounded-xl bg-brand-cyan/5 border border-brand-cyan/20 text-center animate-pulse">
                <div className="flex items-center justify-center gap-2 text-xs font-semibold text-brand-cyan">
                  <Loader2 className="size-4 animate-spin" />
                  <span>در حال پردازش و استخراج برداری...</span>
                </div>
                <div className="text-[11px] text-on-surface-variant">{stageText}</div>
              </div>
            )}
          </FieldGroup>

          <DialogFooter className="gap-2 sm:gap-0 pt-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={uploading}
              onClick={() => onOpenChange(false)}
              className="text-xs"
            >
              انصراف
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={uploading || (docMode === "file" ? !file : (!textTitle.trim() || !textContent.trim()))}
              className="bg-brand-cyan hover:bg-brand-cyan-strong text-slate-950 font-bold text-xs gap-1.5 cursor-pointer"
            >
              {uploading ? (
                <>
                  <Loader2 className="size-3.5 animate-spin" />
                  در حال ثبت...
                </>
              ) : (
                <>
                  <Sparkles className="size-3.5" />
                  پردازش و ثبت در RAG
                </>
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
