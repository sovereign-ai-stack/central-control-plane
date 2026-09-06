"use client";

import * as React from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  Bot,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  Code2,
  Copy,
  Cpu,
  Database,
  Eye,
  FileCode,
  FileText,
  Globe,
  HardDrive,
  HelpCircle,
  Info,
  Key,
  Layers,
  Lock,
  Network,
  Play,
  Radio,
  RefreshCw,
  Search,
  Server,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Terminal,
  Waypoints,
  Workflow,
  Zap,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function DocsPage() {
  return (
    <React.Suspense fallback={<div className="p-8 text-center text-xs text-on-surface-variant">در حال بارگذاری مستندات...</div>}>
      <DocsContent />
    </React.Suspense>
  );
}

function DocsContent() {
  const searchParams = useSearchParams();
  const initialSection = searchParams.get("section") || "gateway";
  const [activeSection, setActiveSection] = React.useState<string>(initialSection);

  React.useEffect(() => {
    const s = searchParams.get("section");
    if (s && ["gateway", "registry", "semantic"].includes(s)) {
      setActiveSection(s);
    }
  }, [searchParams]);

  return (
    <div className="h-[100dvh] w-full overflow-y-auto bg-canvas text-on-surface font-sans select-none scroll-smooth" dir="rtl">
      {/* Top Navbar */}
      <header className="sticky top-0 z-40 border-b border-border/40 bg-surface-raised/90 backdrop-blur-md px-4 sm:px-8 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href="/" className="flex items-center gap-2 text-brand-cyan hover:opacity-80 transition-opacity">
            <div className="flex size-8 items-center justify-center rounded-xl bg-brand-cyan/15 border border-brand-cyan/30 text-brand-cyan font-bold font-mono">
              S
            </div>
            <span className="text-sm font-bold text-on-surface">Sovereign AI Stack</span>
          </Link>
          <span className="text-border/60 text-xs">/</span>
          <span className="text-xs font-semibold text-on-surface-variant">مستندات جامع معماری و توسعه‌دهندگان</span>
        </div>

        <div className="flex items-center gap-2">
          <Link href="/">
            <Button size="sm" variant="outline" className="text-xs gap-1.5 border-border/40 cursor-pointer">
              <ArrowRight className="size-3.5" />
              <span>بازگشت به چت</span>
            </Button>
          </Link>
          <Link href="/admin">
            <Button size="sm" className="bg-brand-cyan hover:bg-brand-cyan-strong text-slate-950 font-bold text-xs gap-1.5 cursor-pointer">
              <Shield className="size-3.5" />
              <span>پنل مدیریت</span>
            </Button>
          </Link>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-8 py-8 grid grid-cols-1 md:grid-cols-4 gap-8">
        {/* Navigation Sidebar */}
        <aside className="md:col-span-1 space-y-2 md:sticky md:top-20 md:self-start">
          <div className="text-xs font-bold text-on-surface-variant px-2 mb-3">بخش‌های مستندات</div>
          <button
            onClick={() => setActiveSection("gateway")}
            className={`w-full flex items-center gap-2.5 px-3.5 py-2.5 rounded-xl text-xs font-bold transition-all text-right cursor-pointer ${
              activeSection === "gateway"
                ? "bg-brand-cyan/15 text-brand-cyan border border-brand-cyan/30 shadow-sm"
                : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container/40"
            }`}
          >
            <Server className="size-4 shrink-0" />
            <div className="truncate">۱. گیت‌وی مرکزی و API</div>
          </button>

          <button
            onClick={() => setActiveSection("registry")}
            className={`w-full flex items-center gap-2.5 px-3.5 py-2.5 rounded-xl text-xs font-bold transition-all text-right cursor-pointer ${
              activeSection === "registry"
                ? "bg-brand-cyan/15 text-brand-cyan border border-brand-cyan/30 shadow-sm"
                : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container/40"
            }`}
          >
            <Cpu className="size-4 shrink-0" />
            <div className="truncate">۲. رجیستری و نودهای GPU</div>
          </button>

          <button
            onClick={() => setActiveSection("semantic")}
            className={`w-full flex items-center gap-2.5 px-3.5 py-2.5 rounded-xl text-xs font-bold transition-all text-right cursor-pointer ${
              activeSection === "semantic"
                ? "bg-brand-cyan/15 text-brand-cyan border border-brand-cyan/30 shadow-sm"
                : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container/40"
            }`}
          >
            <Zap className="size-4 shrink-0" />
            <div className="truncate">۳. مسیریاب سمنتیک و RAG</div>
          </button>

          {/* Clean Active Services Status (WITHOUT port numbers) */}
          <div className="pt-6 border-t border-border/30 mt-6 px-2 space-y-2.5 text-[11px] text-on-surface-variant">
            <div className="font-semibold text-on-surface flex items-center gap-1.5">
              <Activity className="size-3.5 text-brand-cyan" />
              <span>وضعیت سرویس‌های فعال:</span>
            </div>
            <div className="flex items-center justify-between p-2 rounded-lg bg-surface-container/40 border border-border/20">
              <span className="font-medium text-on-surface">Central Gateway</span>
              <div className="flex items-center gap-1.5">
                <span className="size-2 rounded-full bg-emerald-400 animate-pulse"></span>
                <span className="text-emerald-400 font-bold text-[10px]">آنلاین</span>
              </div>
            </div>
            <div className="flex items-center justify-between p-2 rounded-lg bg-surface-container/40 border border-border/20">
              <span className="font-medium text-on-surface">Node Registry</span>
              <div className="flex items-center gap-1.5">
                <span className="size-2 rounded-full bg-emerald-400 animate-pulse"></span>
                <span className="text-emerald-400 font-bold text-[10px]">آنلاین</span>
              </div>
            </div>
            <div className="flex items-center justify-between p-2 rounded-lg bg-surface-container/40 border border-border/20">
              <span className="font-medium text-on-surface">LiteLLM Proxy</span>
              <div className="flex items-center gap-1.5">
                <span className="size-2 rounded-full bg-emerald-400 animate-pulse"></span>
                <span className="text-emerald-400 font-bold text-[10px]">آماده</span>
              </div>
            </div>
            <div className="flex items-center justify-between p-2 rounded-lg bg-surface-container/40 border border-border/20">
              <span className="font-medium text-on-surface">Weaviate DB</span>
              <div className="flex items-center gap-1.5">
                <span className="size-2 rounded-full bg-emerald-400 animate-pulse"></span>
                <span className="text-emerald-400 font-bold text-[10px]">متصل</span>
              </div>
            </div>
          </div>
        </aside>

        {/* Documentation Content Area */}
        <main className="md:col-span-3 space-y-8 select-text pb-24">
          {activeSection === "gateway" && <GatewayDocs />}
          {activeSection === "registry" && <RegistryDocs />}
          {activeSection === "semantic" && <SemanticDocs />}
        </main>
      </div>
    </div>
  );
}

/* ==============================================================================
   UI HELPER COMPONENTS (CodeBlock, CopyButton, StepTimeline, ParamTable)
============================================================================== */

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = React.useState(false);

  const handleCopy = () => {
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <button
      onClick={handleCopy}
      className="p-1.5 rounded-lg bg-surface-container hover:bg-surface-container-high border border-border/40 text-on-surface-variant hover:text-brand-cyan transition-colors text-[10px] flex items-center gap-1 cursor-pointer"
      title="کپی متن"
    >
      {copied ? <Check className="size-3 text-emerald-400" /> : <Copy className="size-3" />}
      <span>{copied ? "کپی شد" : "کپی"}</span>
    </button>
  );
}

function CodeSnippet({
  title,
  language = "json",
  code,
  badge,
  badgeColor = "cyan",
}: {
  title?: string;
  language?: string;
  code: string;
  badge?: string;
  badgeColor?: "cyan" | "emerald" | "amber" | "purple" | "blue";
}) {
  const badgeClasses = {
    cyan: "border-brand-cyan/40 bg-brand-cyan/10 text-brand-cyan",
    emerald: "border-emerald-500/40 bg-emerald-500/10 text-emerald-400",
    amber: "border-amber-500/40 bg-amber-500/10 text-amber-400",
    purple: "border-purple-500/40 bg-purple-500/10 text-purple-400",
    blue: "border-blue-500/40 bg-blue-500/10 text-blue-400",
  };

  return (
    <div className="rounded-xl border border-border/40 bg-surface-container-lowest overflow-hidden shadow-sm">
      {(title || badge) && (
        <div className="flex items-center justify-between px-3.5 py-2 border-b border-border/30 bg-surface-container/50">
          <div className="flex items-center gap-2">
            {badge && (
              <Badge variant="outline" className={`text-[10px] font-mono ${badgeClasses[badgeColor]}`}>
                {badge}
              </Badge>
            )}
            {title && <span className="text-xs font-semibold text-on-surface">{title}</span>}
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono text-on-surface-variant uppercase">{language}</span>
            <CopyButton text={code} />
          </div>
        </div>
      )}
      <div
        className="p-3.5 text-[11px] font-mono text-left overflow-x-auto text-emerald-400/90 leading-relaxed whitespace-pre selection:bg-brand-cyan/30"
        dir="ltr"
      >
        {code}
      </div>
    </div>
  );
}

function StepItem({
  number,
  icon: Icon,
  title,
  subtitle,
  badge,
  badgeColor = "cyan",
  children,
  isLast = false,
}: {
  number: number;
  icon: any;
  title: string;
  subtitle?: string;
  badge?: string;
  badgeColor?: "cyan" | "emerald" | "amber" | "purple" | "blue";
  children: React.ReactNode;
  isLast?: boolean;
}) {
  const colorMap = {
    cyan: "border-brand-cyan/40 bg-brand-cyan/10 text-brand-cyan",
    emerald: "border-emerald-500/40 bg-emerald-500/10 text-emerald-400",
    amber: "border-amber-500/40 bg-amber-500/10 text-amber-400",
    purple: "border-purple-500/40 bg-purple-500/10 text-purple-400",
    blue: "border-blue-500/40 bg-blue-500/10 text-blue-400",
  };

  return (
    <div className="relative flex gap-4">
      {/* Timeline Line */}
      {!isLast && (
        <div className="absolute top-10 right-4 -bottom-4 w-0.5 bg-gradient-to-b from-brand-cyan/40 via-border/50 to-transparent -translate-x-1/2" />
      )}

      {/* Number & Icon Pill */}
      <div className="relative z-10 flex size-8 shrink-0 items-center justify-center rounded-xl bg-surface-container border border-border/60 text-brand-cyan font-bold text-xs shadow-sm">
        <Icon className="size-4" />
      </div>

      {/* Content Card */}
      <div className="flex-1 pb-6 space-y-2">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-on-surface">{title}</span>
            {subtitle && <span className="text-[11px] text-on-surface-variant font-mono">({subtitle})</span>}
          </div>
          {badge && (
            <Badge variant="outline" className={`text-[10px] font-mono ${colorMap[badgeColor]}`}>
              {badge}
            </Badge>
          )}
        </div>
        <div className="text-xs text-on-surface-variant leading-relaxed space-y-1.5">{children}</div>
      </div>
    </div>
  );
}

/* ==============================================================================
   1. GATEWAY DOCUMENTATION
============================================================================== */
function GatewayDocs() {
  const chatRequestBodySample = `{
  "message": "راهنمای تنظیم سهمیه توکن سازمان چیست؟",
  "conversationId": "conv_8f3a9e1",
  "language": "fa",
  "use_rag": true
}`;

  const chatStreamEventSample = `event: progress
data: {"stage": "routing", "message": "تحلیل هدف پرسش..."}

event: tool
data: {"tool": "vector_rag", "status": "running"}

event: citation
data: {"title": "آیین‌نامه سهمیه توکن", "score": 0.89, "chunkId": "doc_456"}

event: thinking
data: {"chunk": "برای پاسخ، ابتدا سیاست سهمیه سه سطحی را تشریح می‌کنم..."}

event: delta
data: {"content": "سهمیه توکن در سه سطح سازمان، تیم و کاربر بررسی می‌شود."}

event: complete
data: {"message": {"id": "msg_99", "role": "assistant", "content": "..."}, "done": true}`;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-2">
          <Badge className="bg-brand-cyan/20 text-brand-cyan border-brand-cyan/30 text-[10.5px]">نسخه 2.0.0</Badge>
          <Badge variant="outline" className="border-border/40 text-[10.5px] font-mono">FastAPI / ASGI Core</Badge>
          <Badge variant="outline" className="border-brand-mint/40 text-brand-mint text-[10.5px]">Production Ready</Badge>
        </div>
        <h1 className="text-xl sm:text-2xl font-black text-on-surface">مستندات جامع گیت‌وی مرکزی (Central AI Gateway API)</h1>
        <p className="text-xs sm:text-sm text-on-surface-variant mt-1.5 leading-relaxed">
          هسته مرکزی پردازش درخواست‌ها، احراز هویت نشست‌ها، کنترل دسترسی ۴ لایه (RBAC)، استریم بلادرنگ چت (SSE)، اعتبارسنجی ۳ سطحی سهمیه توکن، جستجوی برداری چندمستأجری در Weaviate و پایش با Langfuse.
        </p>
      </div>

      {/* Overview & Core Purpose */}
      <Card className="bg-surface-raised border-border/40">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-bold text-on-surface flex items-center gap-2">
            <Layers className="size-4 text-brand-cyan" />
            ۱. نمای کلی و نقش گیت‌وی (Overview & Responsibilities)
          </CardTitle>
        </CardHeader>
        <CardContent className="text-xs text-on-surface-variant space-y-3 leading-relaxed">
          <p>
            گیت‌وی مرکزی (<code className="font-mono text-brand-cyan text-[11.5px]">central-control-plane</code>) نقطه ورود واحد تمام ترافیک کاربران و کلاینت‌ها به کلاستر هوش مصنوعی است. وظایف اصلی این لایه شامل موارد زیر است:
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1 text-on-surface">
            <div className="p-3 bg-surface-container/40 rounded-xl border border-border/30 space-y-1">
              <div className="font-bold text-brand-cyan text-[12px] flex items-center gap-1.5">
                <Shield className="size-3.5" />
                کنترل دسترسی و سهمیه توکن
              </div>
              <p className="text-[11px] text-on-surface-variant leading-normal">
                بررسی سهمیه‌های مصرفی ۳ لایه (کاربر، تیم و سازمان) به صورت بلادرنگ پیش از ارسال درخواست به مدل استنتاجی.
              </p>
            </div>
            <div className="p-3 bg-surface-container/40 rounded-xl border border-border/30 space-y-1">
              <div className="font-bold text-emerald-400 text-[12px] flex items-center gap-1.5">
                <Workflow className="size-3.5" />
                استریم پیوسته با تفکیک تگ تفکر
              </div>
              <p className="text-[11px] text-on-surface-variant leading-normal">
                ارکستراسیون SSE با تفکیک دقیق رویدادهای <code className="font-mono text-brand-cyan">thinking</code> و <code className="font-mono text-brand-cyan">delta</code> بدون نشت اطلاعات متنی.
              </p>
            </div>
            <div className="p-3 bg-surface-container/40 rounded-xl border border-border/30 space-y-1">
              <div className="font-bold text-amber-400 text-[12px] flex items-center gap-1.5">
                <Database className="size-3.5" />
                جستجوی برداری فدرال (RAG)
              </div>
              <p className="text-[11px] text-on-surface-variant leading-normal">
                ارتباط چندمستأجری امن با Weaviate و بازیابی اسناد منطبق بر شاردهای اختصاصی سازمان و تیم کاربر.
              </p>
            </div>
            <div className="p-3 bg-surface-container/40 rounded-xl border border-border/30 space-y-1">
              <div className="font-bold text-purple-400 text-[12px] flex items-center gap-1.5">
                <Activity className="size-3.5" />
                رهگیری و لاگینگ با Langfuse
              </div>
              <p className="text-[11px] text-on-surface-variant leading-normal">
                ثبت اسپن‌های مسیریابی، بازیابی برداری، مدت‌زمان استنتاج مدل و میزان توکن مصرفی برای ارزیابی عملکرد.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Visual Lifecycle Architecture (Replaced ASCII Art) */}
      <Card className="bg-surface-raised border-border/40">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-bold text-on-surface flex items-center gap-2">
            <Workflow className="size-4 text-brand-cyan" />
            ۲. معماری بصری و چرخه حیات یک درخواست (Request Lifecycle Architecture)
          </CardTitle>
        </CardHeader>
        <CardContent className="text-xs text-on-surface-variant space-y-6 leading-relaxed">
          <p>
            هنگامی که پیامی از کلاینت ارسال می‌شود، درخواست مرحله‌به‌مرحله از خط لوله زیر عبور می‌کند:
          </p>

          {/* Visual Step-by-Step Pipeline */}
          <div className="p-4 bg-surface-container-lowest/60 rounded-2xl border border-border/40 space-y-2">
            <StepItem
              number={1}
              icon={Key}
              title="احراز هویت و بررسی نشست (Session Authentication)"
              subtitle="resolve_user"
              badge="Bearer JWT / Cookie"
              badgeColor="blue"
            >
              <p>توکن ارسالی در هدر Authorization یا کوکی امن اعتبارسنجی شده و اطلاعات کاربر، نقش و تیم استخراج می‌شود.</p>
            </StepItem>

            <StepItem
              number={2}
              icon={ShieldAlert}
              title="اعتبارسنجی سهمیه ۳ سطحی (3-Tier Quota Check)"
              subtitle="Token Enforcement"
              badge="Quota Validator"
              badgeColor="amber"
            >
              <p>
                بررسی همزمان سقف توکن کاربر، تیم کاربر، و مجموع سهمیه تخصیص‌یافته به کل سازمان در برابر سقف کل ماهانه.
                در صورت تکمیل سهمیه، خطای <code className="font-mono text-amber-400">429 quota_exceeded</code> ارسال می‌شود.
              </p>
            </StepItem>

            <StepItem
              number={3}
              icon={Zap}
              title="مسیریابی هوشمند سمنتیک (Semantic Router Engine)"
              subtitle="Intent Classification"
              badge="Sub-15ms"
              badgeColor="cyan"
            >
              <p>
                تحلیل قصد کاربر در ۴ مسیر (<code className="font-mono text-amber-400">rag</code>, <code className="font-mono text-brand-cyan">coding</code>, <code className="font-mono text-purple-400">reasoning</code>, <code className="font-mono text-emerald-400">general</code>).
                رویداد <code className="font-mono text-brand-cyan">event: tool (router)</code> برای اعلام وضعیت به فرانت‌اند صادر می‌شود.
              </p>
            </StepItem>

            <StepItem
              number={4}
              icon={Database}
              title="کاوش برداری در Weaviate (Federated RAG Retrieval)"
              subtitle="Multi-Tenant Search"
              badge="Dense Vector Search"
              badgeColor="emerald"
            >
              <p>
                در صورت فعال بودن RAG، جستجو در شاردهای مجاز کاربر (سازمان، تیم و شارد عمومی) انجام شده و اسناد بالای ضریب شباهت ۰.۴۰ استخراج و رویداد <code className="font-mono text-brand-cyan">event: citation</code> ارسال می‌گردد.
              </p>
            </StepItem>

            <StepItem
              number={5}
              icon={Cpu}
              title="ساخت پرامپت و استریم از ورکر (Model Dispatch & Stream)"
              subtitle="LiteLLM Proxy Stream"
              badge="<think> Splitter"
              badgeColor="purple"
            >
              <p>
                ارسال درخواست به مدل مرتبط و اجرای پارسر بافر جهت تفکیک بلادرنگ خط فکری مدل (<code className="font-mono text-purple-400">event: thinking</code>) از متن پاسخ نهایی (<code className="font-mono text-emerald-400">event: delta</code>).
              </p>
            </StepItem>

            <StepItem
              number={6}
              icon={CheckCircle2}
              title="تکمیل پاسخ و ثبت اسپن (Finalize & Langfuse Trace)"
              subtitle="Trace Logging"
              badge="event: complete"
              badgeColor="cyan"
              isLast={true}
            >
              <p>ذخیره پاسخ نهایی در دیتابیس، ارسال رویداد پایان، و ثبت ردپای کامل مصرف توکن و زمان استنتاج در سامانه Langfuse.</p>
            </StepItem>
          </div>
        </CardContent>
      </Card>

      {/* Authentication & RBAC */}
      <Card className="bg-surface-raised border-border/40">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-bold text-on-surface flex items-center gap-2">
            <Key className="size-4 text-brand-cyan" />
            ۳. احراز هویت و کنترل دسترسی بر مبنای نقش (Authentication & RBAC)
          </CardTitle>
        </CardHeader>
        <CardContent className="text-xs text-on-surface-variant space-y-3 leading-relaxed">
          <p>
            احراز هویت از طریق ماژول <code className="font-mono text-brand-cyan">app.auth.dependencies.resolve_user</code> انجام می‌شود. توکن نشست می‌تواند در دو محل قرار گیرد:
          </p>
          <ul className="list-disc list-inside space-y-1 text-on-surface">
            <li>هدر استاندارد: <code className="font-mono text-brand-cyan text-[11px]">Authorization: Bearer &lt;session_token&gt;</code></li>
            <li>کوکی ایمن: <code className="font-mono text-brand-cyan text-[11px]">sovereign_session=&lt;session_token&gt;</code> یا هدر <code className="font-mono text-brand-cyan text-[11px]">x-session-token</code></li>
          </ul>

          <div className="pt-2">
            <div className="font-bold text-on-surface mb-2">سطوح دسترسی و سلسله‌مراتب نقش‌ها (RBAC Hierarchy):</div>
            <div className="overflow-x-auto">
              <table className="w-full text-right border-collapse border border-border/40 text-[11.5px]">
                <thead>
                  <tr className="bg-surface-container/60 text-on-surface">
                    <th className="p-2 border border-border/40 font-bold">نقش (Role)</th>
                    <th className="p-2 border border-border/40 font-bold">دامنه دسترسی (Scope)</th>
                    <th className="p-2 border border-border/40 font-bold">اختیارات و مجوزها</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/30 text-on-surface-variant">
                  <tr>
                    <td className="p-2 border border-border/40 font-mono font-bold text-brand-cyan">super_admin</td>
                    <td className="p-2 border border-border/40">سراسر سیستم (Global)</td>
                    <td className="p-2 border border-border/40">تعریف و حذف سازمان‌ها، مشاهده تمام نودها، ویرایش مدل‌های فعال، دسترسی فدرال به تمام اسناد.</td>
                  </tr>
                  <tr>
                    <td className="p-2 border border-border/40 font-mono font-bold text-emerald-400">org_admin</td>
                    <td className="p-2 border border-border/40">سازمان کاربر (Organization)</td>
                    <td className="p-2 border border-border/40">مدیریت تیم‌ها، ساخت کاربران سازمان، تنظیم سهمیه توکن تیم‌ها و آپلود اسناد عمومی سازمان.</td>
                  </tr>
                  <tr>
                    <td className="p-2 border border-border/40 font-mono font-bold text-amber-400">team_admin</td>
                    <td className="p-2 border border-border/40">تیم کاربر (Team)</td>
                    <td className="p-2 border border-border/40">مدیریت اعضای تیم، مشاهده مصرف توکن تیم و بارگذاری اسناد اختصاصی تیم در Weaviate.</td>
                  </tr>
                  <tr>
                    <td className="p-2 border border-border/40 font-mono font-bold text-purple-400">user</td>
                    <td className="p-2 border border-border/40">حساب کاربری اختصاصی</td>
                    <td className="p-2 border border-border/40">ارسال پیام چت، ساخت گفتگوها، انشعاب پیام‌ها و جستجو در اسناد مجاز تیم و سازمان خود.</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Complete API Reference with Structured CodeBlocks */}
      <Card className="bg-surface-raised border-border/40">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-bold text-on-surface flex items-center gap-2">
            <Terminal className="size-4 text-brand-cyan" />
            ۴. مستندات وب‌سرویس استریم چت (Chat API Specification)
          </CardTitle>
        </CardHeader>
        <CardContent className="text-xs text-on-surface-variant space-y-4 leading-relaxed">
          {/* Chat Stream API Spec */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Badge className="bg-emerald-500/20 text-emerald-400 border-emerald-500/30 font-mono font-bold">POST</Badge>
                <code className="font-mono font-bold text-on-surface text-[12px]">/api/chat</code>
              </div>
              <Badge variant="outline" className="text-[10px] font-mono border-border/40">Auth: Bearer Token</Badge>
            </div>
            <p className="text-[11px] text-on-surface-variant">
              ارسال پیام کاربر و دریافت پاسخ به صورت رویدادهای پیوسته سرور (Server-Sent Events).
            </p>

            {/* Request Body CodeSnippet */}
            <CodeSnippet
              title="نمونه بدنه درخواست (JSON Request Body)"
              language="json"
              badge="POST /api/chat"
              badgeColor="emerald"
              code={chatRequestBodySample}
            />

            {/* Request Parameters Description Table */}
            <div className="overflow-x-auto pt-1">
              <table className="w-full text-right border-collapse border border-border/40 text-[11px]">
                <thead>
                  <tr className="bg-surface-container/60 text-on-surface">
                    <th className="p-2 border border-border/40 font-bold">پارامتر</th>
                    <th className="p-2 border border-border/40 font-bold">نوع</th>
                    <th className="p-2 border border-border/40 font-bold">الزام</th>
                    <th className="p-2 border border-border/40 font-bold">توضیحات و عملکرد</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/30 text-on-surface-variant font-mono">
                  <tr>
                    <td className="p-2 border border-border/40 text-brand-cyan">message</td>
                    <td className="p-2 border border-border/40">string</td>
                    <td className="p-2 border border-border/40 text-emerald-400 font-sans">اجباری</td>
                    <td className="p-2 border border-border/40 font-sans">متن ورودی یا پرسش مطرح‌شده توسط کاربر.</td>
                  </tr>
                  <tr>
                    <td className="p-2 border border-border/40 text-brand-cyan">conversationId</td>
                    <td className="p-2 border border-border/40">string</td>
                    <td className="p-2 border border-border/40 text-amber-400 font-sans">اختیاری</td>
                    <td className="p-2 border border-border/40 font-sans">شناسه یکتای گفتگو جهت حفظ و ادامه‌دادن سابقه پیام‌ها.</td>
                  </tr>
                  <tr>
                    <td className="p-2 border border-border/40 text-brand-cyan">use_rag</td>
                    <td className="p-2 border border-border/40">boolean</td>
                    <td className="p-2 border border-border/40 text-amber-400 font-sans">اختیاری</td>
                    <td className="p-2 border border-border/40 font-sans">کلید صریح جستجو در پایگاه دانش سازمان و تیم (پیش‌فرض: true).</td>
                  </tr>
                  <tr>
                    <td className="p-2 border border-border/40 text-brand-cyan">language</td>
                    <td className="p-2 border border-border/40">string</td>
                    <td className="p-2 border border-border/40 text-amber-400 font-sans">اختیاری</td>
                    <td className="p-2 border border-border/40 font-sans">زبان پاسخ مدل (fa یا en - پیش‌فرض: fa).</td>
                  </tr>
                </tbody>
              </table>
            </div>

            {/* SSE Response Format */}
            <div className="pt-2">
              <CodeSnippet
                title="نمونه رویدادهای استریم پاسخ (SSE Stream Format)"
                language="http-sse"
                badge="Content-Type: text/event-stream"
                badgeColor="cyan"
                code={chatStreamEventSample}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Admin Management APIs */}
      <Card className="bg-surface-raised border-border/40">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-bold text-on-surface flex items-center gap-2">
            <ShieldCheck className="size-4 text-brand-cyan" />
            ۵. کاتالوگ وب‌سرویس‌های مدیریتی (Admin Management APIs)
          </CardTitle>
        </CardHeader>
        <CardContent className="text-xs text-on-surface-variant space-y-3 leading-relaxed">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-on-surface">
            <div className="p-3 bg-surface-container/30 rounded-xl border border-border/30 space-y-1">
              <div className="flex items-center gap-1.5 font-mono text-[11px] font-bold text-brand-cyan">
                <span className="text-emerald-400">GET/POST</span> /api/admin/organizations
              </div>
              <p className="text-[10.5px] text-on-surface-variant">مدیریت لیست سازمان‌ها و تعیین سقف ماهانه توکن کل سازمان.</p>
            </div>

            <div className="p-3 bg-surface-container/30 rounded-xl border border-border/30 space-y-1">
              <div className="flex items-center gap-1.5 font-mono text-[11px] font-bold text-brand-cyan">
                <span className="text-emerald-400">GET/POST</span> /api/admin/teams
              </div>
              <p className="text-[10.5px] text-on-surface-variant">ساخت دپارتمان‌های تابعه و تخصیص سهمیه توکن به هر تیم.</p>
            </div>

            <div className="p-3 bg-surface-container/30 rounded-xl border border-border/30 space-y-1">
              <div className="flex items-center gap-1.5 font-mono text-[11px] font-bold text-brand-cyan">
                <span className="text-emerald-400">GET/POST</span> /api/admin/users
              </div>
              <p className="text-[10.5px] text-on-surface-variant">مدیریت کاربران، انتساب نقش‌ها (RBAC) و فعال/غیرفعال کردن حساب.</p>
            </div>

            <div className="p-3 bg-surface-container/30 rounded-xl border border-border/30 space-y-1">
              <div className="flex items-center gap-1.5 font-mono text-[11px] font-bold text-brand-cyan">
                <span className="text-emerald-400">GET/POST</span> /api/admin/documents
              </div>
              <p className="text-[10.5px] text-on-surface-variant">آپلود و ایندکس برداری فایل‌های PDF/Word در دیتابیس Weaviate.</p>
            </div>

            <div className="p-3 bg-surface-container/30 rounded-xl border border-border/30 space-y-1">
              <div className="flex items-center gap-1.5 font-mono text-[11px] font-bold text-brand-cyan">
                <span className="text-emerald-400">GET/POST</span> /api/admin/models
              </div>
              <p className="text-[10.5px] text-on-surface-variant">مدیریت مدل‌های زبانی متصل و نگاشت نقش‌های سیستمی.</p>
            </div>

            <div className="p-3 bg-surface-container/30 rounded-xl border border-border/30 space-y-1">
              <div className="flex items-center gap-1.5 font-mono text-[11px] font-bold text-brand-cyan">
                <span className="text-blue-400">GET</span> /api/admin/dashboard
              </div>
              <p className="text-[10.5px] text-on-surface-variant">دریافت آمارهای کلان مصرف، توکن‌ها و اسناد ایندکس‌شده.</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Troubleshooting & Error Codes */}
      <Card className="bg-surface-raised border-border/40">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-bold text-on-surface flex items-center gap-2">
            <AlertTriangle className="size-4 text-amber-400" />
            ۶. راهنمای عیب‌یابی و کدهای خطا (Troubleshooting & Error Handling)
          </CardTitle>
        </CardHeader>
        <CardContent className="text-xs text-on-surface-variant space-y-3 leading-relaxed">
          <div className="space-y-2">
            <div className="p-3 bg-destructive/10 border border-destructive/30 rounded-xl space-y-1">
              <div className="font-bold text-destructive flex items-center gap-1.5 text-[11.5px]">
                <AlertCircle className="size-3.5" />
                خطای ۴۰۱ (Unauthorized / Session Expired)
              </div>
              <p className="text-[11px] text-on-surface-variant">
                <strong>علت:</strong> انقضای توکن نشست یا عدم ارسال هدر Authorization.
                <br />
                <strong>راهکار:</strong> خروج از حساب و ورود مجدد از طریق صفحه لاگین یا ارسال مجدد نشست به <code className="font-mono text-brand-cyan">/api/auth/login</code>.
              </p>
            </div>

            <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-xl space-y-1">
              <div className="font-bold text-amber-400 flex items-center gap-1.5 text-[11.5px]">
                <AlertTriangle className="size-3.5" />
                خطای ۴۲۹ (Quota Exceeded / سقف توکن تکمیل است)
              </div>
              <p className="text-[11px] text-on-surface-variant">
                <strong>علت:</strong> مصرف ماهانه توکن کاربر، تیم یا سازمان به سقف مجاز تعریف‌شده رسیده است.
                <br />
                <strong>راهکار:</strong> افزایش سقف توکن از طریق تب سازمان‌ها یا تیم‌ها در پنل ادمین توسط مدیر ارشد.
              </p>
            </div>

            <div className="p-3 bg-blue-500/10 border border-blue-500/30 rounded-xl space-y-1">
              <div className="font-bold text-blue-400 flex items-center gap-1.5 text-[11.5px]">
                <Info className="size-3.5" />
                خطای ۵۰۲ (LiteLLM Disconnected / Inference Engine Offline)
              </div>
              <p className="text-[11px] text-on-surface-variant">
                <strong>علت:</strong> عدم اتصال به کانتینر پروکسی یا فعال نبودن ورکر پردازشی محلی.
                <br />
                <strong>راهکار:</strong> بررسی وضعیت کانتینر <code className="font-mono text-brand-cyan">litellm-proxy</code> و اطمینان از صحت سلامت نودهای فعال در بخش رجیستری.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

/* ==============================================================================
   2. REGISTRY DOCUMENTATION
============================================================================== */
function RegistryDocs() {
  const nodeRegistrationSample = `{
  "node_id": "node_gpu_rtx4090_01",
  "api_base": "http://192.168.1.50:8000/v1",
  "model_name": "Qwen/Qwen2.5-7B-Instruct-AWQ",
  "served_model_name": "qwen-7b",
  "supported_roles": [
    "general-model",
    "coding-model"
  ],
  "hardware": {
    "gpus": [
      {
        "name": "NVIDIA GeForce RTX 4090",
        "total_vram_gb": 24.0,
        "free_vram_gb": 22.4,
        "driver_version": "550.54"
      }
    ],
    "total_vram_gb": 24.0,
    "tensor_parallel_size": 1,
    "tier_id": "tier_high_vram"
  }
}`;

  const heartbeatSample = `{
  "node_id": "node_gpu_rtx4090_01",
  "status": "online",
  "gpu_utilization_pct": 14.2,
  "vram_used_gb": 12.8
}`;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-2">
          <Badge className="bg-brand-cyan/20 text-brand-cyan border-brand-cyan/30 text-[10.5px]">نسخه 2.0.0</Badge>
          <Badge variant="outline" className="border-border/40 text-[10.5px] font-mono">Cluster Orchestrator</Badge>
          <Badge variant="outline" className="border-emerald-500/40 text-emerald-400 text-[10.5px]">Dynamic Cluster</Badge>
        </div>
        <h1 className="text-xl sm:text-2xl font-black text-on-surface">مستندات جامع رجیستری و نودهای پردازشی (Node Registry API)</h1>
        <p className="text-xs sm:text-sm text-on-surface-variant mt-1.5 leading-relaxed">
          کشف خودکار سخت‌افزار GPU، ثبت و لغو ثبت داینامیک ورکرها در پروکسی LiteLLM، مدیریت دوره‌ای ضربان قلب (Heartbeat) و تحمل خطا در هنگام قطع نودها.
        </p>
      </div>

      {/* Registry Overview */}
      <Card className="bg-surface-raised border-border/40">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-bold text-on-surface flex items-center gap-2">
            <Cpu className="size-4 text-brand-cyan" />
            ۱. نقش و هدف رجیستری مرکزی (Registry Overview & Responsibilities)
          </CardTitle>
        </CardHeader>
        <CardContent className="text-xs text-on-surface-variant space-y-3 leading-relaxed">
          <p>
            سرویس رجیستری مرکزی (<code className="font-mono text-brand-cyan text-[11.5px]">central-node-registry</code>) پل ارتباطی میان نودهای فیزیکی کارت گرافیک (<code className="font-mono text-brand-cyan">ai-node-agent</code>) و پروکسی LiteLLM است:
          </p>
          <ul className="list-disc list-inside space-y-1.5 text-on-surface">
            <li><strong>کشف و الحاق خودکار:</strong> به محض روشن شدن یک سیستم دارای GPU، عامل نود سخت‌افزار را خوانده و خود را در رجیستری ثبت می‌کند.</li>
            <li><strong>تزریق لحظه‌ای مسیرها به LiteLLM:</strong> رجیستری مدل و نقش‌های پشتیبانی‌شده توسط نود (مانند <code className="font-mono text-brand-cyan">general-model</code> و <code className="font-mono text-brand-cyan">coding-model</code>) را بلافاصله در LiteLLM ایجاد یا به‌روزرسانی می‌کند.</li>
            <li><strong>پایش ضربان قلب و پاکسازی نودهای مرده:</strong> اگر نودی بیش از ۶۰ ثانیه پینگ ارسال نکند، مسیرهای آن از LiteLLM پاک شده و وضعیت به <code className="font-mono text-destructive">offline</code> تغییر می‌یابد.</li>
          </ul>
        </CardContent>
      </Card>

      {/* Visual Lifecycle Architecture */}
      <Card className="bg-surface-raised border-border/40">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-bold text-on-surface flex items-center gap-2">
            <Workflow className="size-4 text-brand-cyan" />
            ۲. جریان بصری چرخه حیات نود GPU (Node Lifecycle Pipeline)
          </CardTitle>
        </CardHeader>
        <CardContent className="text-xs text-on-surface-variant space-y-6 leading-relaxed">
          <p>
            فرایند کشف سخت‌افزار، اتصال، پایش ضربان قلب و حذف خودکار نود به صورت گام‌به‌گام:
          </p>

          <div className="p-4 bg-surface-container-lowest/60 rounded-2xl border border-border/40 space-y-2">
            <StepItem
              number={1}
              icon={HardDrive}
              title="کشف مشخصات کارت گرافیک (Hardware Detection)"
              subtitle="hardware_detector.py"
              badge="NVML / CUDA Driver"
              badgeColor="cyan"
            >
              <p>عامل نود (<code className="font-mono text-brand-cyan">ai-node-agent</code>) مقدار VRAM، تعداد هسته‌های CUDA، مدل کارت گرافیک و توان پردازشی را استخراج می‌کند.</p>
            </StepItem>

            <StepItem
              number={2}
              icon={Server}
              title="ارسال درخواست ثبت‌نام نود (Node Registration)"
              subtitle="POST /nodes/register"
              badge="Registration Payload"
              badgeColor="emerald"
            >
              <p>مشخصات سخت‌افزاری، آدرس پایه موتور vLLM و نقش‌های پشتیبانی‌شده به رجیستری مرکزی ارسال می‌گردد.</p>
            </StepItem>

            <StepItem
              number={3}
              icon={Network}
              title="تزریق آنی مسیرها به LiteLLM (Dynamic Route Sync)"
              subtitle="POST /model/new"
              badge="Proxy Sync"
              badgeColor="blue"
            >
              <p>رجیستری بلافاصله با فراخوانی API مدیریت پروکسی، مدل و نام‌های مستعار (<code className="font-mono text-brand-cyan">role aliases</code>) را به جدول مسیریابی اضافه می‌کند.</p>
            </StepItem>

            <StepItem
              number={4}
              icon={Radio}
              title="پایش مداوم ضربان قلب (10s Heartbeat Loop)"
              subtitle="POST /nodes/heartbeat"
              badge="Every 10s"
              badgeColor="purple"
            >
              <p>عامل نود هر ۱۰ ثانیه یک بار وضعیت سلامت، میزان لود GPU و مصرف VRAM را برای تمدید لایسنس ارسال می‌کند.</p>
            </StepItem>

            <StepItem
              number={5}
              icon={ShieldAlert}
              title="تحمل خطا و پاکسازی خودکار نود قطع‌شده (Fault Tolerance)"
              subtitle="POST /model/delete"
              badge="Timeout > 60s"
              badgeColor="amber"
              isLast={true}
            >
              <p>اگر پینگی طی ۶۰ ثانیه دریافت نشود، نود به عنوان <code className="font-mono text-destructive">offline</code> علامت‌گذاری شده و مسیرهای آن فوراً از جدول پروکسی پاک می‌شود تا ترافیک خطا ندهد.</p>
            </StepItem>
          </div>
        </CardContent>
      </Card>

      {/* Data Model & Request Schemas */}
      <Card className="bg-surface-raised border-border/40">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-bold text-on-surface flex items-center gap-2">
            <FileCode className="size-4 text-brand-cyan" />
            ۳. مدل داده و ساختار بسته‌های ارسالی (Schemas & Payloads)
          </CardTitle>
        </CardHeader>
        <CardContent className="text-xs text-on-surface-variant space-y-4 leading-relaxed">
          {/* Registration Schema */}
          <div className="space-y-3">
            <CodeSnippet
              title="ساختار پلود ثبت‌نام نود (NodeRegistrationRequest)"
              language="json"
              badge="POST /nodes/register"
              badgeColor="emerald"
              code={nodeRegistrationSample}
            />

            <div className="overflow-x-auto pt-1">
              <table className="w-full text-right border-collapse border border-border/40 text-[11px]">
                <thead>
                  <tr className="bg-surface-container/60 text-on-surface">
                    <th className="p-2 border border-border/40 font-bold">فیلد</th>
                    <th className="p-2 border border-border/40 font-bold">نوع</th>
                    <th className="p-2 border border-border/40 font-bold">توضیحات و عملکرد</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/30 text-on-surface-variant font-mono">
                  <tr>
                    <td className="p-2 border border-border/40 text-brand-cyan">node_id</td>
                    <td className="p-2 border border-border/40">string</td>
                    <td className="p-2 border border-border/40 font-sans">شناسه یکتای سرور یا سیستم دارای پردازنده گرافیکی.</td>
                  </tr>
                  <tr>
                    <td className="p-2 border border-border/40 text-brand-cyan">api_base</td>
                    <td className="p-2 border border-border/40">string</td>
                    <td className="p-2 border border-border/40 font-sans">آدرس پایه استنتاج موتور محلی (vLLM یا Ollama).</td>
                  </tr>
                  <tr>
                    <td className="p-2 border border-border/40 text-brand-cyan">supported_roles</td>
                    <td className="p-2 border border-border/40">array[string]</td>
                    <td className="p-2 border border-border/40 font-sans">نقش‌های پشتیبانی‌شده نظیر coding-model، reasoning-model، general-model.</td>
                  </tr>
                  <tr>
                    <td className="p-2 border border-border/40 text-brand-cyan">hardware.total_vram_gb</td>
                    <td className="p-2 border border-border/40">float</td>
                    <td className="p-2 border border-border/40 font-sans">میزان کل حافظه اختصاصی کارت‌های گرافیک بر حسب گیگابایت.</td>
                  </tr>
                </tbody>
              </table>
            </div>

            {/* Heartbeat CodeSnippet */}
            <div className="pt-2">
              <CodeSnippet
                title="ساختار بسته ضربان قلب (Heartbeat Payload)"
                language="json"
                badge="POST /nodes/heartbeat"
                badgeColor="purple"
                code={heartbeatSample}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Registry API Catalog */}
      <Card className="bg-surface-raised border-border/40">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-bold text-on-surface flex items-center gap-2">
            <Terminal className="size-4 text-brand-cyan" />
            ۴. فهرست کامل وب‌سرویس‌های رجیستری (Endpoints Catalog)
          </CardTitle>
        </CardHeader>
        <CardContent className="text-xs text-on-surface-variant space-y-3 leading-relaxed">
          <div className="overflow-x-auto">
            <table className="w-full text-right border-collapse border border-border/40 text-[11.5px]">
              <thead>
                <tr className="bg-surface-container/60 text-on-surface">
                  <th className="p-2 border border-border/40 font-bold">متد و مسیر</th>
                  <th className="p-2 border border-border/40 font-bold">ورودی</th>
                  <th className="p-2 border border-border/40 font-bold">هدف و رفتار</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/30 text-on-surface-variant">
                <tr>
                  <td className="p-2 border border-border/40 font-mono text-emerald-400 font-bold">POST /nodes/register</td>
                  <td className="p-2 border border-border/40 font-mono">NodeRegistrationRequest</td>
                  <td className="p-2 border border-border/40 font-sans">ثبت نود پردازشی و تزریق خودکار aliasها در LiteLLM Proxy.</td>
                </tr>
                <tr>
                  <td className="p-2 border border-border/40 font-mono text-emerald-400 font-bold">POST /nodes/heartbeat</td>
                  <td className="p-2 border border-border/40 font-mono">&#123; node_id, status &#125;</td>
                  <td className="p-2 border border-border/40 font-sans">ارسال ضربان قلب هر ۱۰ ثانیه جهت اعلام سلامت و تمدید لایسنس.</td>
                </tr>
                <tr>
                  <td className="p-2 border border-border/40 font-mono text-emerald-400 font-bold">POST /nodes/deregister</td>
                  <td className="p-2 border border-border/40 font-mono">&#123; node_id &#125;</td>
                  <td className="p-2 border border-border/40 font-sans">خروج منظم نود و پاکسازی آنی مسیرها از LiteLLM.</td>
                </tr>
                <tr>
                  <td className="p-2 border border-border/40 font-mono text-blue-400 font-bold">GET /nodes</td>
                  <td className="p-2 border border-border/40 font-mono">-</td>
                  <td className="p-2 border border-border/40 font-sans">لیست تمام نودهای فعال، مشخصات سخت‌افزاری و ثانیه‌های سپری‌شده از آخرین پینگ.</td>
                </tr>
                <tr>
                  <td className="p-2 border border-border/40 font-mono text-blue-400 font-bold">GET /models</td>
                  <td className="p-2 border border-border/40 font-mono">-</td>
                  <td className="p-2 border border-border/40 font-sans">استعلام مستقیم مدل‌های فعال و آماده پاسخ‌گویی از LiteLLM Proxy.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

/* ==============================================================================
   3. SEMANTIC DOCUMENTATION & TOPOLOGY
============================================================================== */
function SemanticDocs() {
  const semanticRouteRequestSample = `{
  "query": "یک کوئری SQL برای استخراج جمع فروش ماهانه به همراه شاخص رشد بنویس"
}`;

  const semanticRouteResponseSample = `{
  "query": "یک کوئری SQL برای استخراج جمع فروش ماهانه به همراه شاخص رشد بنویس",
  "route": "coding",
  "confidence": 0.985,
  "target_model": "coding-model",
  "needs_rag": false,
  "execution_time_ms": 3.8
}`;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-2">
          <Badge className="bg-brand-cyan/20 text-brand-cyan border-brand-cyan/30 text-[10.5px]">نسخه 2.0.0</Badge>
          <Badge variant="outline" className="border-border/40 text-[10.5px] font-mono">Sub-15ms Engine</Badge>
          <Badge variant="outline" className="border-purple-500/40 text-purple-400 text-[10.5px]">Hybrid RAG Engine</Badge>
        </div>
        <h1 className="text-xl sm:text-2xl font-black text-on-surface">مستندات مسیریاب معنایی و پایگاه دانش (Semantic Router & RAG)</h1>
        <p className="text-xs sm:text-sm text-on-surface-variant mt-1.5 leading-relaxed">
          تشخیص فوق‌سریع قصد کاربر (Intent Routing)، فیلتر کلیدواژه‌های فارسی و انگلیسی، کاوش خودکار پایگاه دانش (Dynamic RAG Probe) و هدایت هوشمند پرسش‌ها به مدل‌های تخصصی.
        </p>
      </div>

      {/* Concept & Motivation */}
      <Card className="bg-surface-raised border-border/40">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-bold text-on-surface flex items-center gap-2">
            <Zap className="size-4 text-brand-cyan" />
            ۱. مفهوم و چرایی مسیریاب معنایی (What is Semantic Router?)
          </CardTitle>
        </CardHeader>
        <CardContent className="text-xs text-on-surface-variant space-y-3 leading-relaxed">
          <p>
            در سامانه‌های چندمدلی، ارسال همه پرسش‌ها به یک مدل سنگین باعث هدررفت هزینه، افزایش زمان پاسخ‌دهی و کاهش دقت می‌شود. مسیریاب معنایی (<code className="font-mono text-brand-cyan text-[11.5px]">Semantic Router</code>) در کسری از میلی‌ثانیه مشخص می‌کند که کاربر چه درخواستی دارد:
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-on-surface pt-1">
            <div className="p-3 bg-surface-container/40 rounded-xl border border-border/30 space-y-1">
              <div className="font-bold text-amber-400 flex items-center gap-1.5 text-[11.5px]">
                <FileText className="size-3.5" />
                مسیر پایگاه دانش (RAG)
              </div>
              <p className="text-[11px] text-on-surface-variant leading-normal">
                پرسش‌های نیازمند آیین‌نامه‌ها، قراردادها، اسناد سازمانی بارگذاری‌شده و جزوات تخصصی.
              </p>
            </div>
            <div className="p-3 bg-surface-container/40 rounded-xl border border-border/30 space-y-1">
              <div className="font-bold text-brand-cyan flex items-center gap-1.5 text-[11.5px]">
                <Code2 className="size-3.5" />
                مسیر کدنویسی (Coding)
              </div>
              <p className="text-[11px] text-on-surface-variant leading-normal">
                پیاده‌سازی الگوریتم‌ها، اشکال‌زدایی کد، پرسش‌های مربوط به فریم‌ورک‌ها و بهینه‌سازی توابع.
              </p>
            </div>
            <div className="p-3 bg-surface-container/40 rounded-xl border border-border/30 space-y-1">
              <div className="font-bold text-purple-400 flex items-center gap-1.5 text-[11.5px]">
                <Workflow className="size-3.5" />
                مسیر استدلال منطقی (Reasoning)
              </div>
              <p className="text-[11px] text-on-surface-variant leading-normal">
                مسائل ریاضی، تحلیل شواهد منطقی، اثبات‌های مرحله‌به‌مرحله و پازل‌های فکری.
              </p>
            </div>
            <div className="p-3 bg-surface-container/40 rounded-xl border border-border/30 space-y-1">
              <div className="font-bold text-emerald-400 flex items-center gap-1.5 text-[11.5px]">
                <BookOpen className="size-3.5" />
                مسیر عمومی (General)
              </div>
              <p className="text-[11px] text-on-surface-variant leading-normal">
                احوالپرسی، بازنویسی متون، ترجمه زبان‌ها و گفتگوهای عادی بدون نیاز به ابزار یا مستندات.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Semantic Architecture & Multi-Tier Engine */}
      <Card className="bg-surface-raised border-border/40">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-bold text-on-surface flex items-center gap-2">
            <Network className="size-4 text-brand-cyan" />
            ۲. معماری موتور طبقه‌بندی ترکیبی (Hybrid Classification Engine)
          </CardTitle>
        </CardHeader>
        <CardContent className="text-xs text-on-surface-variant space-y-4 leading-relaxed">
          <p>
            موتور طبقه‌بندی داخلی گیت‌وی (<code className="font-mono text-brand-cyan">app.router.engine.SemanticRouterEngine</code>) از ساختار ۳ لایه اولویت‌دار استفاده می‌کند:
          </p>

          <div className="space-y-3 pt-1">
            <div className="p-3.5 bg-surface-container/40 rounded-xl border border-brand-cyan/30 space-y-1.5">
              <div className="font-bold text-brand-cyan flex items-center gap-2 text-[12px]">
                <Badge className="bg-brand-cyan/20 text-brand-cyan border-brand-cyan/30 text-[10px]">لایه اول</Badge>
                <span>اولویت قطعی کلید فرانت‌اند (RAG Toggle Override)</span>
              </div>
              <p className="text-[11px] text-on-surface-variant">
                اگر کاربر دکمه پایگاه دانش را در فرانت‌اند فعال کرده باشد (<code className="font-mono text-brand-cyan">use_rag=True</code>)، بدون معطلی مسیر به عنوان <code className="font-mono text-amber-400">rag</code> با ضریب اطمینان ۱.۰ انتخاب می‌شود. اگر کاربر دکمه را خاموش کرده باشد (<code className="font-mono text-brand-cyan">use_rag=False</code>)، جستجوی اسناد مسدود شده و پیام به مسیر عمومی یا کدنویسی هدایت می‌شود.
              </p>
            </div>

            <div className="p-3.5 bg-surface-container/40 rounded-xl border border-emerald-500/30 space-y-1.5">
              <div className="font-bold text-emerald-400 flex items-center gap-2 text-[12px]">
                <Badge className="bg-emerald-500/20 text-emerald-400 border-emerald-500/30 text-[10px]">لایه دوم</Badge>
                <span>تطابق کلمات کلیدی و عبارات با نرمال‌ساز فارسی (Persian Keyword Normalizer)</span>
              </div>
              <p className="text-[11px] text-on-surface-variant">
                حذف نیم‌فاصله‌ها، یکسان‌سازی حروف «ی» و «ک» عربی و فارسی، و وزن‌دهی ۳ برابری به عبارات چندکلمه‌ای (نظیر «کد پایتون»، «کوئری دیتابیس»، «اثبات ریاضی») جهت پاسخ‌دهی زیر ۱ میلی‌ثانیه.
              </p>
            </div>

            <div className="p-3.5 bg-surface-container/40 rounded-xl border border-purple-500/30 space-y-1.5">
              <div className="font-bold text-purple-400 flex items-center gap-2 text-[12px]">
                <Badge className="bg-purple-500/20 text-purple-400 border-purple-500/30 text-[10px]">لایه سوم</Badge>
                <span>امبدینگ برداری چندزبانه (Sentence-Transformers MiniLM)</span>
              </div>
              <p className="text-[11px] text-on-surface-variant">
                تحلیل برداری جملات پیچیده و چندزبانه با مدل سبک <code className="font-mono text-brand-cyan">paraphrase-multilingual-MiniLM-L12-v2</code> و مقایسه شباهت کسینوسی با الگوهای مرجع در کمتر از ۱۰ میلی‌ثانیه.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Standalone Semantic Service APIs with CodeBlock */}
      <Card className="bg-surface-raised border-border/40">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-bold text-on-surface flex items-center gap-2">
            <Terminal className="size-4 text-brand-cyan" />
            ۳. وب‌سرویس مستقیم مسیریاب معنایی (Semantic Router Endpoints)
          </CardTitle>
        </CardHeader>
        <CardContent className="text-xs text-on-surface-variant space-y-4 leading-relaxed">
          <p>
            میکروسرویس سمنتیک متد ارزیابی مسیر را بدون درگیر کردن مدل‌های سنگین ارائه می‌دهد:
          </p>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Badge className="bg-emerald-500/20 text-emerald-400 border-emerald-500/30 font-mono font-bold">POST</Badge>
                <code className="font-mono font-bold text-on-surface text-[12px]">/route</code>
              </div>
              <Badge variant="outline" className="text-[10px] font-mono border-border/40">Fast Routing</Badge>
            </div>

            <CodeSnippet
              title="نمونه ورودی ارزیابی مسیر (Query Request)"
              language="json"
              badge="Request"
              badgeColor="cyan"
              code={semanticRouteRequestSample}
            />

            <CodeSnippet
              title="نمونه خروجی طبقه‌بندی (Classification Response)"
              language="json"
              badge="Response 200 OK"
              badgeColor="emerald"
              code={semanticRouteResponseSample}
            />
          </div>
        </CardContent>
      </Card>

      {/* Modern Visual Tripartite Topology (Replaced ASCII Art Box Diagram) */}
      <Card className="bg-surface-raised border-brand-cyan/40 shadow-lg">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-bold text-brand-cyan flex items-center gap-2">
            <Waypoints className="size-4 text-brand-cyan" />
            ۴. توپولوژی و معماری تعامل سه‌گانه (Gateway + Registry + Semantic Topology)
          </CardTitle>
        </CardHeader>
        <CardContent className="text-xs text-on-surface-variant space-y-6 leading-relaxed">
          <p>
            این سه بخش در یک معماری ماژولار و مستقل (Decoupled Microservices) بدون وابستگی چرخه‌ای با هم تعامل دارند:
          </p>

          {/* Visual Interactive Tripartite Architecture Diagram */}
          <div className="p-5 bg-surface-container-lowest/80 rounded-2xl border border-border/50 space-y-6">
            {/* Top Level: Central AI Gateway */}
            <div className="p-4 rounded-xl bg-surface-raised border-2 border-brand-cyan/40 shadow-sm relative space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 rounded-lg bg-brand-cyan/15 text-brand-cyan">
                    <Server className="size-4" />
                  </div>
                  <div>
                    <div className="text-xs font-bold text-on-surface">Central AI Gateway</div>
                    <div className="text-[10px] text-on-surface-variant">FastAPI ASGI Core / نقطه ورود متمرکز</div>
                  </div>
                </div>
                <Badge className="bg-brand-cyan/20 text-brand-cyan border-brand-cyan/40 text-[10px]">Master Orchestrator</Badge>
              </div>
              <p className="text-[11px] text-on-surface-variant leading-normal">
                احراز هویت نشست‌ها (JWT/Session)، اعتبارسنجی ۳ سطحی سهمیه توکن، ذخیره پیام‌ها در دیتابیس و مدیریت استریم بلادرنگ پاسخ‌ها (SSE).
              </p>
            </div>

            {/* Middle Level Connectors: Two Main Wings */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 relative">
              {/* Left Wing: Semantic Router Engine */}
              <div className="p-4 rounded-xl bg-surface-container/50 border border-purple-500/30 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="p-1.5 rounded-lg bg-purple-500/15 text-purple-400">
                      <Zap className="size-4" />
                    </div>
                    <div>
                      <div className="text-xs font-bold text-on-surface">Semantic Router Engine</div>
                      <div className="text-[10px] text-on-surface-variant">موتور تشخیص قصد و کاوش پایگاه دانش</div>
                    </div>
                  </div>
                  <Badge variant="outline" className="text-[10px] font-mono border-purple-500/40 text-purple-400">Sub-15ms</Badge>
                </div>
                <p className="text-[11px] text-on-surface-variant leading-normal">
                  تحلیل قصد کاربر، نرمال‌سازی عبارات فارسی، کاوش خودکار شباهت برداری و هدایت پرسش به مدل مناسب.
                </p>
                <div className="pt-2 border-t border-border/20 flex items-center justify-between text-[10px] text-purple-400 font-mono">
                  <span>ارتباط با Weaviate DB</span>
                  <ArrowDown className="size-3.5 animate-bounce" />
                </div>
              </div>

              {/* Right Wing: GPU Node Registry */}
              <div className="p-4 rounded-xl bg-surface-container/50 border border-emerald-500/30 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="p-1.5 rounded-lg bg-emerald-500/15 text-emerald-400">
                      <Cpu className="size-4" />
                    </div>
                    <div>
                      <div className="text-xs font-bold text-on-surface">GPU Node Registry</div>
                      <div className="text-[10px] text-on-surface-variant">ارکستراتور نودها و پایش ضربان قلب</div>
                    </div>
                  </div>
                  <Badge variant="outline" className="text-[10px] font-mono border-emerald-500/40 text-emerald-400">Auto Discovery</Badge>
                </div>
                <p className="text-[11px] text-on-surface-variant leading-normal">
                  کشف مشخصات کارت‌های گرافیک ورکرها، مدیریت پینگ ۱۰ ثانیه‌ای و تزریق/حذف آنی مدل‌ها در LiteLLM.
                </p>
                <div className="pt-2 border-t border-border/20 flex items-center justify-between text-[10px] text-emerald-400 font-mono">
                  <span>همگام‌سازی با LiteLLM Proxy</span>
                  <ArrowDown className="size-3.5 animate-bounce" />
                </div>
              </div>
            </div>

            {/* Bottom Level: Data & Inference Backends */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Bottom Left: Weaviate Vector DB */}
              <div className="p-3.5 rounded-xl bg-surface-raised border border-border/40 space-y-1.5">
                <div className="flex items-center gap-2 text-amber-400 font-bold text-xs">
                  <Database className="size-3.5" />
                  <span>Weaviate Vector DB</span>
                </div>
                <p className="text-[10.5px] text-on-surface-variant leading-normal">
                  ذخیره‌سازی و جستجوی برداری متون با تفکیک شارد سازمان و تیم و بازیابی اسناد با شباهت بالای ۰.۴۰.
                </p>
              </div>

              {/* Bottom Right: LiteLLM Proxy */}
              <div className="p-3.5 rounded-xl bg-surface-raised border border-border/40 space-y-1.5">
                <div className="flex items-center gap-2 text-brand-cyan font-bold text-xs">
                  <Workflow className="size-3.5" />
                  <span>LiteLLM Inference Proxy</span>
                </div>
                <p className="text-[10.5px] text-on-surface-variant leading-normal">
                  پروکسی یکپارچه استنتاج مدل‌ها، بالانس بار و استریم مستقیم توکن‌ها با تفکیک تگ تفکر.
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
