"use client";

import * as React from "react";
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  Cpu,
  Globe,
  HardDrive,
  Key,
  Layers,
  Play,
  Plus,
  Power,
  RefreshCw,
  Server,
  Sparkles,
  Trash2,
  Zap,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { AddModelDialog, type AddModelFormData } from "@/features/admin/components/dialogs/AddModelDialog";
import type { GpuNode, ManagedModel } from "@/lib/types";

interface ModelsSectionProps {
  initialModels?: ManagedModel[];
}

const ROLE_INFO: Record<string, { label: string; color: string; desc: string }> = {
  "general-model": {
    label: "عمومی (General)",
    color: "bg-brand-cyan/15 text-brand-cyan border-brand-cyan/30",
    desc: "پاسخ‌دهی آزاد و گفتگوی عمومی",
  },
  "coding-model": {
    label: "کدنویسی (Coding)",
    color: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
    desc: "برنامه‌نویسی و دیباگ الگوریتم‌ها",
  },
  "reasoning-model": {
    label: "استدلال (Reasoning)",
    color: "bg-purple-500/15 text-purple-400 border-purple-500/30",
    desc: "اثبات ریاضی و تفکر عمیق گام‌به‌گام",
  },
  "rag-model": {
    label: "پایگاه دانش (RAG)",
    color: "bg-amber-500/15 text-amber-400 border-amber-500/30",
    desc: "استخراج مستند از پایگاه دانش",
  },
};

const PROVIDER_ICONS: Record<string, string> = {
  openai: "🟢 OpenAI",
  anthropic: "🟣 Anthropic",
  deepseek: "🔵 DeepSeek",
  gemini: "🔷 Google Gemini",
  openrouter: "🌐 OpenRouter",
  custom_vllm: "⚡ vLLM / Local",
  local_node: "🖥️ GPU Node",
};

export function ModelsSection({ initialModels = [] }: ModelsSectionProps) {
  const [models, setModels] = React.useState<ManagedModel[]>(initialModels);
  const [nodes, setNodes] = React.useState<GpuNode[]>([]);
  const [loading, setLoading] = React.useState<boolean>(true);
  const [refreshing, setRefreshing] = React.useState<boolean>(false);
  const [isAddOpen, setIsAddOpen] = React.useState<boolean>(false);
  const [activeTab, setActiveTab] = React.useState<"models" | "nodes">("models");
  const [actionLoading, setActionLoading] = React.useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = React.useState<{ id: string; name: string } | null>(null);
  const [testResult, setTestResult] = React.useState<{
    modelName: string;
    loading: boolean;
    success?: boolean;
    latencyMs?: number;
    replySnippet?: string;
    error?: string;
  } | null>(null);

  const fetchModelsData = React.useCallback(async () => {
    try {
      setRefreshing(true);
      const res = await fetch("/api/admin/models");
      if (res.ok) {
        const data = await res.json();
        setModels(data.models || []);
        setNodes(data.activeNodes || []);
      }
    } catch (err) {
      console.error("Failed to fetch models:", err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  React.useEffect(() => {
    fetchModelsData();
  }, [fetchModelsData]);

  const handleTestModel = async (model: ManagedModel) => {
    try {
      setTestResult({ modelName: model.name, loading: true });
      const res = await fetch(`/api/admin/models/${model.id}/test`, {
        method: "POST",
      });
      const data = await res.json();
      if (res.ok && data.success) {
        setTestResult({
          modelName: model.name,
          loading: false,
          success: true,
          latencyMs: data.latencyMs,
          replySnippet: data.replySnippet,
        });
      } else {
        setTestResult({
          modelName: model.name,
          loading: false,
          success: false,
          latencyMs: data.latencyMs,
          error: data.error || data.detail || "خطا در برقراری ارتباط با مدل",
        });
      }
    } catch (err: any) {
      setTestResult({
        modelName: model.name,
        loading: false,
        success: false,
        error: err.message || "خطای ارتباط با سرور",
      });
    }
  };

  const handleToggleModel = async (model: ManagedModel) => {
    try {
      setActionLoading(model.id);
      const newStatus = !model.isEnabled;
      const res = await fetch(`/api/admin/models/${model.id}/toggle`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ isEnabled: newStatus }),
      });
      if (res.ok) {
        setModels((prev) =>
          prev.map((m) => (m.id === model.id ? { ...m, isEnabled: newStatus } : m))
        );
      }
    } catch (err) {
      console.error("Failed to toggle model:", err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleDeleteModel = async (modelId: string) => {
    try {
      setActionLoading(modelId);
      const res = await fetch(`/api/admin/models/${modelId}`, {
        method: "DELETE",
      });
      if (res.ok) {
        setModels((prev) => prev.filter((m) => m.id !== modelId));
      }
    } catch (err) {
      console.error("Failed to delete model:", err);
    } finally {
      setActionLoading(null);
      setDeleteTarget(null);
    }
  };

  const handleCreateModel = async (formData: AddModelFormData) => {
    const res = await fetch("/api/admin/models", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(formData),
    });
    if (res.ok) {
      await fetchModelsData();
    } else {
      const err = await res.json();
      alert(err.detail || "خطا در ثبت مدل");
    }
  };

  const enabledModelsCount = models.filter((m) => m.isEnabled).length;
  const cloudModelsCount = models.filter((m) => m.provider !== "custom_vllm" && m.provider !== "local_node").length;

  return (
    <div className="space-y-5 select-none" dir="rtl">
      {/* 1. HEADER & ACTION BAR */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-2 border-b border-border/30">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-bold text-on-surface">مدیریت مدل‌های زبانی و نودهای پردازشی</h2>
            <Badge variant="outline" className="text-[10px] px-1.5 py-0.5 border-brand-cyan/40 bg-brand-cyan/10 text-brand-cyan">
              مختص Super Admin
            </Badge>
          </div>
          <p className="text-xs text-on-surface-variant mt-0.5">
            پیکربندی داینامیک مدل‌های کلود با API Key، مدل‌های لوکال، اختصاص نقش‌ها و خاموش/روشن کردن نودها
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={fetchModelsData}
            disabled={refreshing}
            className="text-xs h-8 gap-1.5 border-border/40 hover:border-brand-cyan/40 text-on-surface-variant hover:text-on-surface cursor-pointer"
          >
            <RefreshCw className={`size-3.5 ${refreshing ? "animate-spin text-brand-cyan" : ""}`} />
            بروزرسانی وضعیت
          </Button>

          <Button
            size="sm"
            onClick={() => setIsAddOpen(true)}
            className="bg-brand-cyan hover:bg-brand-cyan-strong text-slate-950 font-bold text-xs h-8 gap-1.5 cursor-pointer shadow-sm"
          >
            <Plus className="size-3.5" />
            افزودن مدل جدید (کلود / لوکال)
          </Button>
        </div>
      </div>

      {/* 2. STATS KPI CARDS */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <Card className="bg-surface-raised border-border/40">
          <CardContent className="p-3.5 flex items-center justify-between">
            <div>
              <div className="text-[11px] text-on-surface-variant font-medium">مدل‌های فعال و آنلاین</div>
              <div className="text-xl font-bold text-on-surface mt-0.5 flex items-center gap-1.5">
                <span>{enabledModelsCount}</span>
                <span className="text-xs text-on-surface-variant/70 font-normal">/ {models.length} مدل کل</span>
              </div>
            </div>
            <div className="size-9 rounded-xl bg-emerald-500/15 border border-emerald-500/25 flex items-center justify-center text-emerald-400">
              <Zap className="size-4" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-surface-raised border-border/40">
          <CardContent className="p-3.5 flex items-center justify-between">
            <div>
              <div className="text-[11px] text-on-surface-variant font-medium">سرویس‌های کلود با API Key</div>
              <div className="text-xl font-bold text-brand-cyan mt-0.5">
                {cloudModelsCount} <span className="text-xs text-on-surface-variant/70 font-normal">ارائه‌دهنده</span>
              </div>
            </div>
            <div className="size-9 rounded-xl bg-brand-cyan/15 border border-brand-cyan/25 flex items-center justify-center text-brand-cyan">
              <Globe className="size-4" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-surface-raised border-border/40">
          <CardContent className="p-3.5 flex items-center justify-between">
            <div>
              <div className="text-[11px] text-on-surface-variant font-medium">نودهای سخت‌افزاری GPU</div>
              <div className="text-xl font-bold text-purple-400 mt-0.5">
                {nodes.length} <span className="text-xs text-on-surface-variant/70 font-normal">کارت گرافیک</span>
              </div>
            </div>
            <div className="size-9 rounded-xl bg-purple-500/15 border border-purple-500/25 flex items-center justify-center text-purple-400">
              <Cpu className="size-4" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 3. TABS NAVIGATION */}
      <div className="flex items-center gap-2 border-b border-border/30 pb-1">
        <button
          onClick={() => setActiveTab("models")}
          className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
            activeTab === "models"
              ? "bg-brand-cyan/15 text-brand-cyan border border-brand-cyan/30"
              : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container/40"
          }`}
        >
          <Sparkles className="size-3.5" />
          <span>مدل‌های پیکربندی‌شده و نقش‌های سیستم ({models.length})</span>
        </button>

        <button
          onClick={() => setActiveTab("nodes")}
          className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
            activeTab === "nodes"
              ? "bg-brand-cyan/15 text-brand-cyan border border-brand-cyan/30"
              : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container/40"
          }`}
        >
          <Server className="size-3.5" />
          <span>نودهای متصل سخت‌افزاری GPU ({nodes.length})</span>
        </button>
      </div>

      {/* 4. TAB CONTENT: MODELS LIST */}
      {activeTab === "models" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
          {loading ? (
            <div className="col-span-full text-center py-12 text-xs text-on-surface-variant">
              در حال بارگذاری اطلاعات مدل‌ها و مسیرهای استنتاج...
            </div>
          ) : models.length === 0 ? (
            <div className="col-span-full text-center py-12 bg-surface-raised border border-border/30 rounded-2xl">
              <Cpu className="size-10 text-on-surface-variant/40 mx-auto mb-2" />
              <div className="text-sm font-semibold text-on-surface">هیچ مدلی ثبت نشده است</div>
              <div className="text-xs text-on-surface-variant mt-1">
                جهت افزودن مدل‌های کلود (با API Key) یا لوکال دکمه «افزودن مدل جدید» را انتخاب کنید.
              </div>
            </div>
          ) : (
            models.map((model) => {
              const roleInfo = ROLE_INFO[model.assignedRole] || {
                label: model.assignedRole,
                color: "bg-surface-container text-on-surface border-border",
                desc: "",
              };
              const providerLabel = PROVIDER_ICONS[model.provider] || model.provider;
              const isBusy = actionLoading === model.id;

              return (
                <Card
                  key={model.id}
                  className={`border transition-all ${
                    model.isEnabled
                      ? "bg-surface-raised border-border/40 hover:border-brand-cyan/40"
                      : "bg-surface-raised/50 border-border/20 opacity-75"
                  }`}
                >
                  <CardHeader className="pb-2.5 flex flex-row items-start justify-between space-y-0">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <CardTitle className="text-sm font-bold text-on-surface">
                          {model.name}
                        </CardTitle>
                        <Badge variant="outline" className={`text-[10px] px-1.5 py-0.5 border ${roleInfo.color}`}>
                          {roleInfo.label}
                        </Badge>
                      </div>
                      <div className="text-[11px] text-on-surface-variant font-mono">
                        {providerLabel} • <span className="text-on-surface">{model.modelId}</span>
                      </div>
                    </div>

                    {/* TOGGLE SWITCH BUTTON */}
                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={isBusy}
                        onClick={() => handleToggleModel(model)}
                        className={`text-xs h-7 px-2.5 gap-1.5 font-bold transition-all cursor-pointer ${
                          model.isEnabled
                            ? "bg-emerald-500/15 border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/25"
                            : "bg-surface-container/60 border-border/40 text-on-surface-variant hover:text-on-surface"
                        }`}
                      >
                        <Power className={`size-3 ${model.isEnabled ? "text-emerald-400" : "text-on-surface-variant"}`} />
                        <span>{model.isEnabled ? "روشن و فعال" : "خاموش"}</span>
                      </Button>
                    </div>
                  </CardHeader>

                  <CardContent className="space-y-2.5 text-xs">
                    <div className="grid grid-cols-2 gap-2 pt-2 border-t border-border/20 text-[11px] font-mono">
                      <div className="flex items-center justify-between">
                        <span className="text-on-surface-variant">کلید دسترسی:</span>
                        <span className="text-on-surface flex items-center gap-1">
                          {model.hasKey ? (
                            <>
                              <Key className="size-3 text-emerald-400" />
                              <span>{model.apiKey || "ثبت‌شده"}</span>
                            </>
                          ) : (
                            <span className="text-on-surface-variant/70">سرور محلی</span>
                          )}
                        </span>
                      </div>

                      <div className="flex items-center justify-between">
                        <span className="text-on-surface-variant">پنجره کانتکست:</span>
                        <span className="text-brand-cyan">{model.contextWindow?.toLocaleString() || "32,768"}</span>
                      </div>
                    </div>

                    {model.apiBase && (
                      <div className="text-[10px] text-on-surface-variant/80 font-mono truncate bg-surface-container/40 px-2 py-1 rounded" dir="ltr">
                        API Base: {model.apiBase}
                      </div>
                    )}

                    <div className="flex items-center justify-between pt-2 border-t border-border/15">
                      <div className="text-[10px] text-on-surface-variant/70">
                        {roleInfo.desc}
                      </div>

                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={isBusy || (testResult?.loading && testResult?.modelName === model.name)}
                          onClick={() => handleTestModel(model)}
                          className="text-[11px] h-7 px-2.5 text-brand-cyan border-brand-cyan/30 hover:bg-brand-cyan/10 hover:border-brand-cyan/50 cursor-pointer gap-1.5 font-semibold"
                        >
                          <Play className={`size-3 ${testResult?.loading && testResult?.modelName === model.name ? "animate-spin" : "fill-brand-cyan"}`} />
                          <span>{testResult?.loading && testResult?.modelName === model.name ? "در حال ارسال تست..." : "تست اتصال و استنتاج"}</span>
                        </Button>

                        <Button
                          variant="ghost"
                          size="sm"
                          disabled={isBusy}
                          onClick={() => setDeleteTarget({ id: model.id, name: model.name })}
                          className="text-[11px] h-7 px-2 text-red-400/80 hover:text-red-400 hover:bg-red-500/10 cursor-pointer gap-1"
                        >
                          <Trash2 className="size-3" />
                          حذف
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })
          )}
        </div>
      )}

      {/* 5. TAB CONTENT: HARDWARE GPU NODES */}
      {activeTab === "nodes" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
          {nodes.length === 0 ? (
            <div className="col-span-full text-center py-12 bg-surface-raised border border-border/30 rounded-2xl">
              <Server className="size-10 text-on-surface-variant/40 mx-auto mb-2" />
              <div className="text-sm font-semibold text-on-surface">هیچ نود پردازشی مستقلی متصل نیست</div>
              <div className="text-xs text-on-surface-variant mt-1">
                جهت اتصال کارت گرافیک سازمان، اسکریپت <code className="font-mono bg-surface-container px-1.5 py-0.5 rounded text-brand-cyan">ai-node-agent/run.bat</code> را روی سرور GPU اجرا کنید.
              </div>
            </div>
          ) : (
            nodes.map((node) => {
              const gpus = node.hardware?.gpus || [];
              const gpuName = gpus[0]?.name || "NVIDIA GPU";
              const vramGb = node.hardware?.total_vram_gb || 24;
              const isHealthy = node.status === "healthy";

              return (
                <Card key={node.node_id} className="bg-surface-raised border-border/40 hover:border-purple-500/40 transition-all">
                  <CardHeader className="pb-2.5 flex flex-row items-start justify-between space-y-0">
                    <div className="space-y-1">
                      <CardTitle className="text-sm font-bold text-on-surface flex items-center gap-2">
                        <Cpu className="size-4 text-purple-400" />
                        <span>نود {node.node_id}</span>
                      </CardTitle>
                      <div className="text-[11px] text-on-surface-variant font-mono">
                        {node.api_base} • مدل: {node.model_name}
                      </div>
                    </div>

                    <Badge
                      className={`text-[10.5px] ${
                        isHealthy
                          ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/30"
                          : "bg-red-500/20 text-red-400 border-red-500/30"
                      }`}
                    >
                      {isHealthy ? "آنلاین و فعال" : "آفلاین"}
                    </Badge>
                  </CardHeader>

                  <CardContent className="space-y-2.5 text-xs">
                    <div className="grid grid-cols-2 gap-2 pt-2 border-t border-border/20 text-[11px] font-mono">
                      <div className="flex justify-between">
                        <span className="text-on-surface-variant">پردازنده گرافیکی:</span>
                        <span className="text-on-surface">{gpuName}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-on-surface-variant">حافظه VRAM:</span>
                        <span className="text-purple-400">{vramGb} GB</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5 flex-wrap pt-1">
                      <span className="text-[10.5px] text-on-surface-variant">نقش‌های پشتیبانی‌شده:</span>
                      {node.supported_roles?.map((role) => (
                        <Badge key={role} variant="outline" className="text-[9.5px] font-mono border-border/40 bg-surface-container">
                          {role}
                        </Badge>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              );
            })
          )}
        </div>
      )}

      {/* 6. ADD MODEL MODAL DIALOG */}
      <AddModelDialog
        open={isAddOpen}
        onOpenChange={setIsAddOpen}
        onSubmit={handleCreateModel}
      />

      {/* 7. CUSTOM DESTRUCTION CONFIRM DIALOG */}
      <ConfirmDialog
        open={Boolean(deleteTarget)}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title={`حذف مدل «${deleteTarget?.name || ""}»`}
        description="آیا از حذف این مدل از سامانه اطمینان دارید؟ در صورت حذف، این مدل از پروکسی استنتاج LiteLLM خارج خواهد شد."
        confirmText="بله، حذف مدل"
        cancelText="انصراف"
        variant="destructive"
        onConfirm={() => {
          if (deleteTarget) {
            handleDeleteModel(deleteTarget.id);
          }
        }}
      />

      {/* 8. TEST RESULT MODAL DIALOG */}
      <Dialog open={Boolean(testResult)} onOpenChange={(open) => !open && setTestResult(null)}>
        <DialogContent className="sm:max-w-md bg-surface-raised border border-border/40 text-on-surface" dir="rtl">
          <DialogHeader>
            <DialogTitle className="text-sm font-bold flex items-center gap-2">
              <Activity className="size-4 text-brand-cyan" />
              <span>نتیجه تست زنده استنتاج مدل</span>
            </DialogTitle>
            <DialogDescription className="text-xs text-on-surface-variant">
              بررسی دسترسی، صحت کلید و زمان تاخیر مدل «{testResult?.modelName}»
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 py-2 text-xs">
            {testResult?.loading ? (
              <div className="flex flex-col items-center justify-center py-6 space-y-2">
                <RefreshCw className="size-8 animate-spin text-brand-cyan" />
                <div className="text-xs text-on-surface-variant">در حال ارسال پرامپت تستی به LiteLLM و ارائه‌دهنده...</div>
              </div>
            ) : testResult?.success ? (
              <div className="space-y-2.5">
                <div className="flex items-center justify-between p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="size-4 shrink-0" />
                    <span className="font-bold">اتصال موفقیت‌آمیز بود (مدل آماده کار است)</span>
                  </div>
                  {testResult?.latencyMs !== undefined && (
                    <Badge variant="outline" className="bg-emerald-500/20 text-emerald-400 border-emerald-500/40 text-[10px] font-mono">
                      ⚡ {testResult.latencyMs} ms
                    </Badge>
                  )}
                </div>

                {testResult?.replySnippet && (
                  <div className="space-y-1">
                    <div className="text-[11px] text-on-surface-variant font-medium">پاسخ دریافتی از مدل:</div>
                    <div className="p-2.5 rounded-xl bg-surface-container/60 border border-border/30 text-on-surface font-sans text-xs leading-relaxed max-h-40 overflow-y-auto">
                      {testResult.replySnippet}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="space-y-2.5">
                <div className="flex items-center gap-2 p-2.5 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400">
                  <AlertCircle className="size-4 shrink-0" />
                  <span className="font-bold">خطا در برقراری ارتباط با مدل</span>
                </div>
                {testResult?.error && (
                  <div className="space-y-1">
                    <div className="text-[11px] text-on-surface-variant font-medium">جزئیات پیام خطا:</div>
                    <div className="p-2.5 rounded-xl bg-surface-container/60 border border-red-500/20 text-red-300 font-mono text-[11px] leading-relaxed max-h-40 overflow-y-auto" dir="ltr">
                      {testResult.error}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          <DialogFooter className="sm:justify-start">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setTestResult(null)}
              className="text-xs border-border/40 hover:bg-surface-container cursor-pointer"
            >
              بستن پنجره
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
