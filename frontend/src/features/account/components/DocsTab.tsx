"use client";

import * as React from "react";
import { BookOpen, ExternalLink, FileText, HardDrive, Shield } from "lucide-react";
import type { Language } from "@/lib/types";

interface DocsTabProps {
  language: Language;
}

export function DocsTab({ language }: DocsTabProps) {
  const isFa = language === "fa";

  const docLinks = [
    {
      title: isFa ? "مستندات تعاملی واسط برنامه‌نویسی (بک‌اند و OpenAPI مرکزی)" : "Central Gateway OpenAPI & Architecture Docs",
      url: "/docs?section=gateway",
      desc: isFa ? "مشاهده تمام متدهای احراز هویت، چت استریم، سهمیه‌ها و پنل ادمین" : "Explore REST and SSE streaming endpoints for control plane",
    },
    {
      title: isFa ? "مستندات رجیستری و نودهای پردازشی GPU" : "GPU Node Registry & Auto-Discovery Docs",
      url: "/docs?section=registry",
      desc: isFa ? "وب‌سرویس ثبت خودکار نودها، بررسی سلامت NVML و حافظه VRAM" : "Heartbeat, VRAM monitoring and node health auto-discovery service",
    },
    {
      title: isFa ? "مستندات وب‌سرویس مسیریاب سمنتیک و RAG" : "Semantic Router & Vector RAG Docs",
      url: "/docs?section=semantic",
      desc: isFa ? "تحلیل نیت پرسش کاربر (کدنویسی/استدلال/اسناد) و اتصال به پایگاه دانش" : "Intent classification, Persian/English normalization and vector RAG",
    },
  ];

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-xs font-bold text-on-surface flex items-center gap-2">
          <BookOpen className="size-4 text-brand-cyan" />
          {isFa ? "مستندات فنی و راهنمای توسعه‌دهندگان" : "API & Developer Documentation"}
        </h3>
        <p className="text-[11px] text-on-surface-variant mt-0.5">
          {isFa ? "لینک‌های سریع به واسط‌های وب‌سرویس و مراجع سیستم" : "Quick access to Swagger documentation and SDK guides."}
        </p>
      </div>

      <div className="space-y-2.5">
        {docLinks.map((doc, idx) => (
          <a
            key={idx}
            href={doc.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-between p-3.5 rounded-2xl bg-surface-container/30 border border-border/30 hover:border-brand-cyan/40 transition-all group"
          >
            <div className="space-y-0.5">
              <div className="text-xs font-bold text-on-surface group-hover:text-brand-cyan transition-colors flex items-center gap-1.5">
                <FileText className="size-3.5 text-brand-cyan" />
                {doc.title}
              </div>
              <div className="text-[10.5px] text-on-surface-variant font-mono">{doc.desc}</div>
            </div>
            <ExternalLink className="size-4 text-on-surface-variant group-hover:text-brand-cyan shrink-0" />
          </a>
        ))}
      </div>
    </div>
  );
}
