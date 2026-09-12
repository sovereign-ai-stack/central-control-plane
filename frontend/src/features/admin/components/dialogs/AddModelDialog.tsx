"use client";

import * as React from "react";
import { Cpu, Eye, EyeOff, HelpCircle, Key, Sparkles, Server, Zap } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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

export interface AddModelFormData {
  name: string;
  provider: "openai" | "anthropic" | "deepseek" | "gemini" | "openrouter" | "custom_vllm" | string;
  modelId: string;
  assignedRole: "general-model" | "coding-model" | "reasoning-model" | "rag-model" | string;
  apiKey: string;
  apiBase: string;
  contextWindow: number;
}

interface AddModelDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (formData: AddModelFormData) => Promise<void>;
}

const PROVIDERS = [
  { id: "openai", name: "OpenAI و سازگار", logo: "🟢", desc: "OpenAI, DeepSeek, OpenRouter, Anthropic و APIهای سازگار" },
  { id: "gemini", name: "Google Gemini", logo: "🔷", desc: "مدل‌های گوگل جمینای با API Key" },
  { id: "custom_vllm", name: "vLLM / سرور لوکال", logo: "⚡", desc: "سرورهای محلی، Ollama و کارت‌های گرافیک کلاستر" },
];

const PRESETS: Record<string, Array<{ id: string; label: string; name: string; role: string; ctx: number; apiBase?: string }>> = {
  openai: [
    { id: "gpt-4o", label: "GPT-4o (OpenAI)", name: "OpenAI GPT-4o", role: "general-model", ctx: 128000, apiBase: "" },
    { id: "gpt-4o-mini", label: "GPT-4o Mini (OpenAI)", name: "GPT-4o Mini", role: "general-model", ctx: 128000, apiBase: "" },
    { id: "o1-preview", label: "o1 Preview (استدلال)", name: "OpenAI o1", role: "reasoning-model", ctx: 128000, apiBase: "" },
    { id: "deepseek/deepseek-reasoner", label: "DeepSeek R1 (استدلال)", name: "DeepSeek R1 Reasoner", role: "reasoning-model", ctx: 64000, apiBase: "https://api.deepseek.com" },
    { id: "deepseek/deepseek-chat", label: "DeepSeek V3 (عمومی)", name: "DeepSeek V3 Chat", role: "general-model", ctx: 64000, apiBase: "https://api.deepseek.com" },
    { id: "openrouter/anthropic/claude-3.5-sonnet", label: "Claude 3.5 Sonnet (OpenRouter)", name: "Claude 3.5 Sonnet", role: "coding-model", ctx: 200000, apiBase: "https://openrouter.ai/api/v1" },
  ],
  gemini: [
    { id: "gemini/gemini-2.5-flash", label: "Gemini 2.5 Flash (سریع)", name: "Google Gemini 2.5 Flash", role: "general-model", ctx: 1000000, apiBase: "" },
    { id: "gemini/gemini-1.5-pro", label: "Gemini 1.5 Pro (تحلیلی)", name: "Google Gemini 1.5 Pro", role: "reasoning-model", ctx: 1000000, apiBase: "" },
    { id: "gemini/gemma-2-27b-it", label: "Gemma 2 27B (متن‌باز)", name: "Google Gemma 2", role: "general-model", ctx: 128000, apiBase: "" },
  ],
  custom_vllm: [
    { id: "openai/Qwen/Qwen2.5-7B-Instruct-AWQ", label: "Qwen 2.5 7B Local", name: "Qwen 2.5 7B Local", role: "general-model", ctx: 32768, apiBase: "http://host.docker.internal:8000/v1" },
    { id: "openai/deepseek-ai/DeepSeek-R1-Distill-Qwen-14B", label: "DeepSeek R1 14B Local", name: "DeepSeek R1 14B Local", role: "reasoning-model", ctx: 32768, apiBase: "http://host.docker.internal:8000/v1" },
  ],
};

const ROLES = [
  { id: "general-model", name: "عمومی (General)", desc: "پاسخ‌دهی آزاد و گفتگوی روزمره", color: "text-brand-cyan border-brand-cyan/30 bg-brand-cyan/10" },
  { id: "coding-model", name: "کدنویسی (Coding)", desc: "تولید کد، الگوریتم و رفع خطاها", color: "text-emerald-400 border-emerald-500/30 bg-emerald-500/10" },
  { id: "reasoning-model", name: "استدلال (Reasoning)", desc: "اثبات ریاضی، منطق و تفکر گام‌به‌گام", color: "text-purple-400 border-purple-500/30 bg-purple-500/10" },
  { id: "rag-model", name: "پایگاه دانش (RAG)", desc: "استخراج پاسخ مستند از اسناد سازمانی", color: "text-amber-400 border-amber-500/30 bg-amber-500/10" },
];

export function AddModelDialog({ open, onOpenChange, onSubmit }: AddModelDialogProps) {
  const [provider, setProvider] = React.useState<string>("openai");
  const [name, setName] = React.useState<string>("OpenAI GPT-4o");
  const [modelId, setModelId] = React.useState<string>("gpt-4o");
  const [assignedRole, setAssignedRole] = React.useState<string>("general-model");
  const [apiKey, setApiKey] = React.useState<string>("");
  const [apiBase, setApiBase] = React.useState<string>("");
  const [contextWindow, setContextWindow] = React.useState<number>(128000);
  const [showKey, setShowKey] = React.useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = React.useState<boolean>(false);

  // Auto-fill defaults when provider changes
  const handleProviderSelect = (pId: string) => {
    setProvider(pId);
    const presets = PRESETS[pId] || [];
    if (presets.length > 0) {
      handlePresetSelect(presets[0]);
    }
  };

  const handlePresetSelect = (preset: { id: string; label: string; name: string; role: string; ctx: number; apiBase?: string }) => {
    setModelId(preset.id);
    setName(preset.name);
    setAssignedRole(preset.role);
    setContextWindow(preset.ctx);
    setApiBase(preset.apiBase ?? (provider === "custom_vllm" ? "http://host.docker.internal:8000/v1" : ""));
    if (provider === "custom_vllm" && !apiKey) {
      setApiKey("sk-vllm-dummy");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!modelId || !name) return;
    setIsSubmitting(true);
    try {
      await onSubmit({
        name,
        provider,
        modelId,
        assignedRole,
        apiKey,
        apiBase,
        contextWindow,
      });
      onOpenChange(false);
      // Reset
      setName("");
      setApiKey("");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-xl max-h-[90vh] overflow-y-auto bg-surface-raised border-border/40 text-on-surface select-none" dir="rtl">
        <DialogHeader>
          <div className="flex items-center gap-2.5">
            <div className="flex size-9 items-center justify-center rounded-xl bg-brand-cyan/15 border border-brand-cyan/30 text-brand-cyan">
              <Sparkles className="size-5" />
            </div>
            <div>
              <DialogTitle className="text-base font-bold text-on-surface">
                افزودن مدل زبانی جدید (کلود / لوکال)
              </DialogTitle>
              <DialogDescription className="text-xs text-on-surface-variant">
                اتصال مدل‌های هوش مصنوعی تجاری با API Key یا سرورهای کارت گرافیک سازمان
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 py-2">
          {/* 1. SELECT PROVIDER */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-on-surface flex items-center justify-between">
              <span>۱. انتخاب ارائه‌دهنده سرویس (Provider)</span>
              <span className="text-[10.5px] text-on-surface-variant font-normal">سرویس مورد نظر را انتخاب کنید</span>
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {PROVIDERS.map((p) => {
                const isSelected = provider === p.id;
                return (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => handleProviderSelect(p.id)}
                    className={`p-2.5 rounded-xl border text-start transition-all cursor-pointer flex flex-col justify-between ${
                      isSelected
                        ? "bg-brand-cyan/15 border-brand-cyan text-brand-cyan shadow-sm"
                        : "bg-surface-container/50 border-border/40 hover:border-border text-on-surface-variant hover:text-on-surface"
                    }`}
                  >
                    <div className="flex items-center gap-2 font-bold text-xs">
                      <span>{p.logo}</span>
                      <span>{p.name}</span>
                    </div>
                    <div className="text-[10px] text-on-surface-variant/70 mt-1 truncate">
                      {p.desc}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* 2. SELECT SYSTEM ROLE */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-on-surface flex items-center justify-between">
              <span>۲. نقش سیستم در پلتفرم (System Role)</span>
              <span className="text-[10.5px] text-on-surface-variant font-normal">این مدل برای چه درخواستی پاسخ دهد؟</span>
            </label>
            <div className="grid grid-cols-2 gap-2">
              {ROLES.map((r) => {
                const isSelected = assignedRole === r.id;
                return (
                  <button
                    key={r.id}
                    type="button"
                    onClick={() => setAssignedRole(r.id)}
                    className={`p-2.5 rounded-xl border text-start transition-all cursor-pointer ${
                      isSelected
                        ? `${r.color} font-bold shadow-sm`
                        : "bg-surface-container/40 border-border/30 text-on-surface-variant hover:text-on-surface"
                    }`}
                  >
                    <div className="text-xs">{r.name}</div>
                    <div className="text-[10px] text-on-surface-variant/70 font-normal leading-tight mt-0.5">
                      {r.desc}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* QUICK PRESET CHIPS */}
          {PRESETS[provider] && (
            <div className="space-y-1.5 p-2.5 rounded-xl bg-surface-container/40 border border-border/30">
              <div className="text-[11px] font-bold text-on-surface flex items-center gap-1.5">
                <Sparkles className="size-3.5 text-brand-cyan" />
                <span>مدل‌های پرکاربرد (کلیک برای انتخاب و تکمیل خودکار فرم):</span>
              </div>
              <div className="flex flex-wrap items-center gap-1.5 pt-1">
                {PRESETS[provider].map((preset) => {
                  const isSelected = modelId === preset.id;
                  return (
                    <button
                      key={preset.id}
                      type="button"
                      onClick={() => handlePresetSelect(preset)}
                      className={`text-[11px] px-2.5 py-1 rounded-lg border transition-all cursor-pointer flex items-center gap-1.5 ${
                        isSelected
                          ? "bg-brand-cyan text-slate-950 border-brand-cyan font-bold shadow-sm"
                          : "bg-surface-raised border-border/50 text-on-surface-variant hover:text-on-surface hover:border-brand-cyan/40"
                      }`}
                    >
                      <span>{preset.label}</span>
                      <code className="text-[9.5px] opacity-75 font-mono">({preset.id})</code>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          <FieldGroup className="space-y-3 pt-1">
            {/* 3. MODEL NAME & TECHNICAL ID */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <Field>
                <FieldLabel className="text-xs font-semibold">نام نمایشی مدل در پنل *</FieldLabel>
                <Input
                  placeholder="مثلاً: DeepSeek R1 Reasoner"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="bg-surface-container/50 text-sm"
                  required
                />
              </Field>

              <Field>
                <FieldLabel className="text-xs font-semibold flex items-center justify-between">
                  <span>شناسه فنی API مدل (Model ID) *</span>
                </FieldLabel>
                <Input
                  placeholder="deepseek-reasoner یا gpt-4o"
                  value={modelId}
                  onChange={(e) => setModelId(e.target.value)}
                  className="bg-surface-container/50 text-sm font-mono"
                  dir="ltr"
                  required
                />
                <span className="text-[10px] text-on-surface-variant/80 mt-0.5 block">
                  نام دقیق مدل در مستندات API ارائه‌دهنده (با کلیک روی دکمه‌های بالا خودکار پر می‌شود)
                </span>
              </Field>
            </div>

            {/* 4. API KEY */}
            <Field>
              <FieldLabel className="text-xs font-semibold flex items-center justify-between">
                <span className="flex items-center gap-1.5">
                  <Key className="size-3.5 text-brand-cyan" />
                  <span>کلید دسترسی (API Key)</span>
                </span>
                <span className="text-[10.5px] text-on-surface-variant font-normal">
                  {provider === "custom_vllm" ? "برای سرورهای محلی نیاز نیست" : "کلید محرمانه حساب کاربری شما در سرویس‌دهنده"}
                </span>
              </FieldLabel>
              <div className="relative">
                <Input
                  type={showKey ? "text" : "password"}
                  placeholder={provider === "openai" ? "sk-proj-..." : provider === "anthropic" ? "sk-ant-..." : "sk-..."}
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  className="bg-surface-container/50 text-sm font-mono pe-10"
                  dir="ltr"
                />
                <button
                  type="button"
                  onClick={() => setShowKey(!showKey)}
                  className="absolute start-auto end-2.5 top-1/2 -translate-y-1/2 text-on-surface-variant hover:text-on-surface p-1 cursor-pointer"
                  title={showKey ? "مخفی‌سازی کلید" : "نمایش کلید"}
                >
                  {showKey ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                </button>
              </div>
            </Field>

            {/* 5. OPTIONAL API BASE & CONTEXT WINDOW */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <Field>
                <FieldLabel className="text-xs font-semibold">آدرس پایه API (اختیاری / Base URL)</FieldLabel>
                <Input
                  placeholder="https://api.deepseek.com"
                  value={apiBase}
                  onChange={(e) => setApiBase(e.target.value)}
                  className="bg-surface-container/50 text-xs font-mono"
                  dir="ltr"
                />
              </Field>

              <Field>
                <FieldLabel className="text-xs font-semibold">پنجره کانتکست (Context Window)</FieldLabel>
                <Input
                  type="number"
                  value={contextWindow}
                  onChange={(e) => setContextWindow(Number(e.target.value))}
                  className="bg-surface-container/50 text-sm font-mono"
                  step={4096}
                />
              </Field>
            </div>
          </FieldGroup>

          <DialogFooter className="gap-2 sm:gap-0 pt-3 border-t border-border/20">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => onOpenChange(false)}
              className="text-xs cursor-pointer"
            >
              انصراف
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={isSubmitting || !name || !modelId}
              className="bg-brand-cyan hover:bg-brand-cyan-strong text-slate-950 font-bold text-xs cursor-pointer gap-1.5"
            >
              {isSubmitting ? (
                <>در حال ثبت در کلاستر...</>
              ) : (
                <>
                  <Zap className="size-3.5" />
                  افزودن و فعال‌سازی مدل
                </>
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
