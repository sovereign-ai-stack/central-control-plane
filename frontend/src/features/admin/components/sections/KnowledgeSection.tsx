"use client";

import * as React from "react";
import { FileText, Plus, Trash2, Upload } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { RagDocument } from "@/lib/types";

interface KnowledgeSectionProps {
  documents: RagDocument[];
  onOpenAddDoc: () => void;
  onDeleteDoc: (docId: string) => void;
}

export function KnowledgeSection({
  documents,
  onOpenAddDoc,
  onDeleteDoc,
}: KnowledgeSectionProps) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-on-surface">پایگاه دانش و اسناد سازمانی (RAG)</h2>
          <p className="text-xs text-on-surface-variant">
            اسناد بارگذاری‌شده در پایگاه داده برداری Weaviate جهت پاسخ‌دهی مستند هوش مصنوعی
          </p>
        </div>
        <Button
          size="sm"
          onClick={onOpenAddDoc}
          className="bg-brand-cyan hover:bg-brand-cyan-strong text-slate-950 font-bold text-xs gap-1.5 cursor-pointer"
        >
          <Upload className="size-4" />
          آپلود سند جدید
        </Button>
      </div>

      <div className="bg-surface-raised border border-border/40 rounded-2xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-start text-xs">
            <thead className="bg-surface-container/50 border-b border-border/30 text-on-surface-variant font-semibold">
              <tr>
                <th className="p-3 text-start">عنوان سند</th>
                <th className="p-3 text-start">سازمان / واحد</th>
                <th className="p-3 text-start">حجم / صفحات</th>
                <th className="p-3 text-start">قطعات برداری (Chunks)</th>
                <th className="p-3 text-start">وضعیت ایندکس</th>
                <th className="p-3 text-end">عملیات</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/20">
              {documents.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center py-12 text-on-surface-variant">
                    <FileText className="size-8 mx-auto mb-2 opacity-40" />
                    هنوز سندی در پایگاه دانش ثبت نشده است.
                  </td>
                </tr>
              ) : (
                documents.map((doc) => (
                  <tr key={doc.id} className="hover:bg-surface-container/30 transition-colors">
                    <td className="p-3 font-semibold text-on-surface flex items-center gap-2">
                      <FileText className="size-4 text-warning shrink-0" />
                      <span className="truncate max-w-xs">{doc.name}</span>
                    </td>
                    <td className="p-3 text-on-surface-variant font-mono">
                      {doc.organizationName || doc.organizationId} / {doc.teamName || doc.teamId}
                    </td>
                    <td className="p-3 font-mono">
                      {doc.pageCount} صفحه ({Math.max(1, Math.round((doc.size || 0) / 1024))} KB)
                    </td>
                    <td className="p-3 font-mono text-brand-cyan">{doc.chunkCount} چانک</td>
                    <td className="p-3">
                      {doc.status === "processing" ? (
                        <Badge variant="outline" className="border-warning/50 bg-warning/10 text-warning text-[10.5px] animate-pulse flex items-center gap-1.5 w-fit">
                          <span className="size-1.5 rounded-full bg-warning animate-ping" />
                          در حال استخراج برداری...
                        </Badge>
                      ) : doc.status === "failed" ? (
                        <Badge variant="outline" className="border-destructive/50 bg-destructive/10 text-destructive text-[10.5px]">
                          خطا در پردازش
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="border-brand-cyan/40 bg-brand-cyan/10 text-brand-cyan text-[10.5px] flex items-center gap-1.5 w-fit">
                          <span className="size-1.5 rounded-full bg-brand-cyan" />
                          ایندکس‌شده
                        </Badge>
                      )}
                    </td>
                    <td className="p-3 text-end">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => onDeleteDoc(doc.id)}
                        className="size-7 text-on-surface-variant hover:text-destructive"
                        title="حذف سند"
                      >
                        <Trash2 className="size-3.5" />
                      </Button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
