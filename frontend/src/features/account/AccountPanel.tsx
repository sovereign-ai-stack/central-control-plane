"use client";

import * as React from "react";
import {
  BookOpen,
  Gauge,
  Globe,
  KeyRound,
  Mic,
  Settings as SettingsIcon,
  User,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { BrandLogoIcon } from "@/components/ui/brand-logo";
import { useTranslation } from "@/lib/locale";
import type { AuthUser, Language } from "@/lib/types";

import { AccountTab } from "./components/AccountTab";
import { DocsTab } from "./components/DocsTab";
import { GeneralTab } from "./components/GeneralTab";
import { McpKeysTab } from "./components/McpKeysTab";
import { UsageTab } from "./components/UsageTab";
import { VoiceTab } from "./components/VoiceTab";

export interface AccountPanelProps {
  isOpen: boolean;
  onClose: () => void;
  language: Language;
  onLanguageChange: (lang: Language) => void;
  user?: AuthUser;
  onLogout?: () => void;
}

type SettingsTab = "general" | "voice" | "usage" | "mcp" | "account" | "docs";

export function AccountPanel({
  isOpen,
  onClose,
  language,
  onLanguageChange,
  user,
  onLogout,
}: AccountPanelProps) {
  const t = useTranslation(language);
  const isFa = language === "fa";
  const [activeTab, setActiveTab] = React.useState<SettingsTab>("general");

  const tabs: { id: SettingsTab; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
    { id: "general", label: isFa ? "تنظیمات عمومی" : "General", icon: Globe },
    // { id: "voice", label: isFa ? "گوینده صوتی" : "Voice Persona", icon: Mic },
    { id: "usage", label: isFa ? "سهمیه و مصرف" : "Usage & Quotas", icon: Gauge },
    // { id: "mcp", label: isFa ? "کلیدهای MCP" : "MCP API Keys", icon: KeyRound },
    { id: "account", label: isFa ? "حساب کاربری" : "Account", icon: User },
    { id: "docs", label: isFa ? "مستندات API" : "Docs", icon: BookOpen },
  ];

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent
        className="max-w-2xl bg-surface-raised border-border/40 p-0 overflow-hidden text-on-surface select-none"
        dir={isFa ? "rtl" : "ltr"}
      >
        <DialogTitle className="sr-only">
          {isFa ? "تنظیمات سامانه و حساب کاربری" : "System Settings & Account"}
        </DialogTitle>

        <div className="flex flex-col h-[560px] max-h-[85vh]">
          {/* MODAL HEADER */}
          <div className="flex items-center justify-between px-5 py-4 border-b border-border/30 bg-surface-container/20 shrink-0">
            <div className="flex items-center gap-2.5">
              <BrandLogoIcon className="size-6" />
              <div className="text-sm font-bold text-on-surface">
                {isFa ? "تنظیمات سامانه و حساب کاربری" : "System Settings & Account"}
              </div>
            </div>
          </div>

          {/* TAB BAR & CONTENT */}
          <div className="flex flex-col sm:flex-row flex-1 overflow-hidden">
            {/* TABS SIDEBAR (horizontal scroll on mobile, vertical list on sm+) */}
            <div className="w-full sm:w-48 shrink-0 bg-surface-container/20 border-b sm:border-b-0 sm:border-e border-border/30 p-2 sm:p-2.5 flex sm:flex-col gap-1 overflow-x-auto sm:overflow-x-visible">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                const isActive = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`shrink-0 sm:w-full flex items-center gap-2 sm:gap-2.5 px-3 py-2 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
                      isActive
                        ? "bg-brand-cyan/15 text-brand-cyan border border-brand-cyan/30 shadow-sm"
                        : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container/40 border border-transparent"
                    }`}
                  >
                    <Icon className={`size-4 ${isActive ? "text-brand-cyan" : "text-on-surface-variant"}`} />
                    <span className="whitespace-nowrap">{tab.label}</span>
                  </button>
                );
              })}
            </div>

            {/* TAB CONTENT AREA */}
            <div className="flex-1 overflow-y-auto p-4 sm:p-5">
              {activeTab === "general" && (
                <GeneralTab language={language} onLanguageChange={onLanguageChange} />
              )}
              {/* {activeTab === "voice" && <VoiceTab language={language} />} */}
              {activeTab === "usage" && <UsageTab language={language} user={user} />}
              {/* {activeTab === "mcp" && <McpKeysTab language={language} />} */}
              {activeTab === "account" && (
                <AccountTab user={user} language={language} onLogout={onLogout} />
              )}
              {activeTab === "docs" && <DocsTab language={language} />}
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
