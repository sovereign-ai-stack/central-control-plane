"use client";

import * as React from "react";
import { Check, Globe, Shield, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useTranslation } from "@/lib/locale";
import type { Language } from "@/lib/types";

interface GeneralTabProps {
  language: Language;
  onLanguageChange: (lang: Language) => void;
}

export function GeneralTab({ language, onLanguageChange }: GeneralTabProps) {
  const t = useTranslation(language);
  const isFa = language === "fa";

  return (
    <div className="space-y-6">
      {/* 1. Language Selection */}
      <div className="space-y-3">
        <div>
          <h3 className="text-xs font-bold text-on-surface flex items-center gap-2">
            <Globe className="size-4 text-brand-cyan" />
            {isFa ? "زبان رابط کاربری سامانه" : "Interface Language"}
          </h3>
          <p className="text-[11px] text-on-surface-variant mt-0.5">
            {isFa
              ? "جهت تغییر چیدمان (RTL/LTR) و متون، زبان مورد نظر را انتخاب کنید."
              : "Select your preferred language and reading direction."}
          </p>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <button
            type="button"
            onClick={() => onLanguageChange("fa")}
            className={`flex items-center justify-between p-3.5 rounded-2xl border transition-all cursor-pointer ${
              isFa
                ? "bg-brand-cyan/15 border-brand-cyan/40 text-on-surface shadow-sm"
                : "bg-surface-container/30 border-border/30 text-on-surface-variant hover:border-border/60 hover:text-on-surface"
            }`}
          >
            <div className="text-start">
              <div className="text-xs font-bold font-sans">فارسی (پیش‌فرض)</div>
              <div className="text-[10px] text-on-surface-variant">راست به چپ (RTL)</div>
            </div>
            {isFa && <Check className="size-4 text-brand-cyan" />}
          </button>

          <button
            type="button"
            onClick={() => onLanguageChange("en")}
            className={`flex items-center justify-between p-3.5 rounded-2xl border transition-all cursor-pointer ${
              !isFa
                ? "bg-brand-cyan/15 border-brand-cyan/40 text-on-surface shadow-sm"
                : "bg-surface-container/30 border-border/30 text-on-surface-variant hover:border-border/60 hover:text-on-surface"
            }`}
          >
            <div className="text-start">
              <div className="text-xs font-bold font-sans">English (US)</div>
              <div className="text-[10px] text-on-surface-variant">Left to Right (LTR)</div>
            </div>
            {!isFa && <Check className="size-4 text-brand-cyan" />}
          </button>
        </div>
      </div>

      {/* 2. Platform Information */}
      <div className="space-y-3 pt-4 border-t border-border/30">
        <div>
          <h3 className="text-xs font-bold text-on-surface flex items-center gap-2">
            <Shield className="size-4 text-[#A78BFA]" />
            {isFa ? "مشخصات نگارش و پلتفرم" : "Platform Specifications"}
          </h3>
        </div>

        <div className="bg-surface-container/30 border border-border/30 rounded-2xl p-4 space-y-2 text-xs">
          <div className="flex justify-between items-center">
            <span className="text-on-surface-variant">{isFa ? "هسته مرکزی هوش مصنوعی:" : "Core AI Control Plane:"}</span>
            <span className="font-mono font-bold text-on-surface">Sovereign Control Plane v2.0</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-on-surface-variant">{isFa ? "موتور استنتاج محلی:" : "Local Inference Engine:"}</span>
            <span className="font-mono text-brand-cyan font-bold">LiteLLM + vLLM CUDA 12</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-on-surface-variant">{isFa ? "پایگاه داده برداری (RAG):" : "Vector Database:"}</span>
            <span className="font-mono text-warning font-bold">Weaviate Knowledge Base</span>
          </div>
        </div>
      </div>
    </div>
  );
}
