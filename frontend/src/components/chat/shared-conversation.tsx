"use client";

import * as React from "react";
import Link from "next/link";
import Image from "next/image";
import { ArrowLeft, Loader2 } from "lucide-react";
import { Thread } from "./thread";
import { BrandLogoIcon } from "@/components/ui/brand-logo";
import { useTranslation } from "@/lib/locale";
import { apiFetch, appPath } from "@/lib/api";
import type { Language, Message } from "@/lib/types";

interface SharedConversationData {
  id: string;
  title: string;
  language: Language;
  messages: Message[];
}

export function SharedConversation({ token }: { token: string }) {
  const [data, setData] = React.useState<SharedConversationData | null>(null);
  const [error, setError] = React.useState(false);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    let cancelled = false;
    apiFetch(`shares/${encodeURIComponent(token)}`)
      .then(async (response) => {
        if (!response.ok) throw new Error("Share unavailable");
        return (await response.json()) as SharedConversationData;
      })
      .then((value) => {
        if (!cancelled) setData(value);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  const language = data?.language || "fa";
  const t = useTranslation(language);

  return (
    <main dir={language === "fa" ? "rtl" : "ltr"} className="flex h-[100dvh] flex-col overflow-hidden bg-canvas text-foreground">
      <header className="flex items-center justify-between border-b border-border/60 bg-surface-container/40 px-4 py-3 backdrop-blur-md sm:px-6">
        <div className="flex items-center gap-2">
          <BrandLogoIcon className="size-6" />
          <div className="flex flex-col">
            <span className="text-sm font-bold">{t.appName}</span>
            {data && <span className="max-w-[55vw] truncate text-xs text-muted-foreground">{data.title}</span>}
          </div>
        </div>
        <Link href={appPath()} className="inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-xs text-muted-foreground transition-colors hover:bg-surface-active hover:text-foreground">
          <ArrowLeft className="size-3.5 rtl:rotate-180" />
          {language === "fa" ? "گفتگوی جدید" : "Start a new chat"}
        </Link>
      </header>

      {loading && (
        <div className="flex flex-1 items-center justify-center gap-2 text-sm text-muted-foreground" role="status" aria-live="polite">
          <Loader2 className="size-4 animate-spin" />
          {language === "fa" ? "در حال بارگذاری گفتگو…" : "Loading conversation…"}
        </div>
      )}
      {!loading && error && (
        <div className="flex flex-1 items-center justify-center px-6 text-center text-sm text-muted-foreground">
          {language === "fa" ? "این پیوند اشتراک نامعتبر یا منقضی شده است." : "This share link is invalid or expired."}
        </div>
      )}
      {!loading && data && <Thread messages={data.messages} language={data.language} className="min-h-0 flex-1" />}
    </main>
  );
}
