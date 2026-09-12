"use client";

import * as React from "react";
import Image from "next/image";
import Link from "next/link";
import {
  Plus,
  BookOpen,
  Settings,
  Gauge,
  Globe,
  Menu,
  Share2,
  MoreVertical,
  Edit2,
  Trash2,
  Check,
  X,
  GitBranch,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { appPath } from "@/lib/api";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { BrandLogoFull, BrandLogoIcon } from "@/components/ui/brand-logo";
import { useTranslation } from "@/lib/locale";
import type { Conversation, Language } from "@/lib/types";

export interface ChatRailProps extends React.ComponentProps<"nav"> {
  conversations: Conversation[];
  activeConversationId?: string;
  onSelectConversation: (id: string) => void;
  onNewChat: () => void;
  onShareConversation: (id: string) => void;
  onRenameConversation: (id: string, newTitle: string) => void;
  onDeleteConversation: (id: string) => void;
  onOpenAccount: () => void;
  onToggleLanguage?: () => void;
  language?: Language;
  isSharing?: boolean;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
}

export function ChatRail({
  conversations,
  activeConversationId,
  onSelectConversation,
  onNewChat,
  onShareConversation,
  onRenameConversation,
  onDeleteConversation,
  onOpenAccount,
  onToggleLanguage,
  language = "fa",
  isSharing = false,
  collapsed = false,
  onToggleCollapse,
  className,
  ...props
}: ChatRailProps) {
  const t = useTranslation(language);
  const [editingId, setEditingId] = React.useState<string | null>(null);
  const [editTitle, setEditTitle] = React.useState("");

  const startRename = (conv: Conversation) => {
    setEditingId(conv.id);
    setEditTitle(conv.title);
  };

  const saveRename = (id: string) => {
    const trimmed = editTitle.trim();
    if (trimmed) {
      onRenameConversation(id, trimmed);
    }
    setEditingId(null);
  };

  // Group conversations by recency (Today, Yesterday, Previous 7 Days, Older)
  const grouped = React.useMemo(() => {
    const now = new Date();
    const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
    const yesterdayStart = todayStart - 24 * 60 * 60 * 1000;
    const sevenDaysAgo = todayStart - 7 * 24 * 60 * 60 * 1000;

    const groups: { [key: string]: Conversation[] } = {
      today: [],
      yesterday: [],
      previous7Days: [],
      older: [],
    };

    const safeConversations = Array.isArray(conversations) ? conversations : [];
    for (const conv of safeConversations.slice(0, 20)) {
      const convTime = new Date(conv.updatedAt || conv.createdAt).getTime();
      if (convTime >= todayStart) {
        groups.today.push(conv);
      } else if (convTime >= yesterdayStart) {
        groups.yesterday.push(conv);
      } else if (convTime >= sevenDaysAgo) {
        groups.previous7Days.push(conv);
      } else {
        groups.older.push(conv);
      }
    }

    return groups;
  }, [conversations]);

  return (
    <nav
      data-testid="chat-rail"
      data-slot="chat-rail"
      id="sidebar"
      className={cn(
        "bg-surface-container/30 backdrop-blur-md flex flex-col h-[calc(100vh-1.5rem)] shrink-0 shadow-lg shadow-black/30 rounded-3xl m-3 relative transition-[width,padding,margin] duration-300 ease-[cubic-bezier(0.4,0,0.2,1)] border border-border/20 select-none overflow-hidden",
        collapsed ? "w-16" : "w-72",
        className
      )}
      {...props}
    >
      {/* Background Gradient Overlay */}
      <div className="absolute inset-0 bg-gradient-to-b from-white/5 to-transparent pointer-events-none rounded-3xl" />

      {/* Top Header & Identity with Hamburger Toggle */}
      <div
        className={cn(
          "flex relative z-10 transition-all duration-300 ease-[cubic-bezier(0.4,0,0.2,1)]",
          collapsed
            ? "flex-col items-center gap-2.5 pt-4 pb-2 px-0"
            : "h-16 px-4 items-center justify-between"
        )}
      >
        {collapsed ? (
          <>
            {/* Little Brand Logo Icon at the very top */}
            <div
              className="size-9 rounded-xl flex items-center justify-center bg-surface/50 border border-border/30 shadow-sm shrink-0 transition-transform duration-200 hover:scale-105"
              title={t.appName}
            >
              <BrandLogoIcon className="size-6" />
            </div>

            {/* Hamburger Toggle */}
            {onToggleCollapse && (
              <button
                type="button"
                data-testid="sidebar-toggle-btn"
                id="toggleSidebarBtn"
                onClick={onToggleCollapse}
                className="text-on-surface-variant hover:text-on-surface hover:bg-surface-raised/70 size-9 rounded-xl transition-all duration-200 ease-out shadow-sm cursor-pointer flex items-center justify-center shrink-0 active:scale-95"
                aria-label="Expand sidebar"
                title={language === "fa" ? "باز کردن منو" : "Open sidebar"}
              >
                <Menu className="size-5" />
              </button>
            )}
          </>
        ) : (
          <>
            <div className="w-24 h-auto flex items-center sidebar-label-fade">
              <BrandLogoFull className="w-24 h-auto" />
            </div>

            {onToggleCollapse && (
              <button
                type="button"
                data-testid="sidebar-toggle-btn"
                id="toggleSidebarBtn"
                onClick={onToggleCollapse}
                className="text-on-surface-variant hover:text-on-surface hover:bg-surface-raised/70 size-9 rounded-xl transition-all duration-200 ease-out shadow-sm cursor-pointer flex items-center justify-center shrink-0 active:scale-95"
                aria-label="Collapse sidebar"
                title={language === "fa" ? "بستن منو" : "Close sidebar"}
              >
                <Menu className="size-5 text-on-surface-variant hover:text-on-surface transition-colors" />
              </button>
            )}
          </>
        )}
      </div>

      {/* New Chat Button */}
      <div className={cn("px-4 mb-2 relative z-10 transition-all duration-300", collapsed && "px-2")}>
        <button
          type="button"
          onClick={onNewChat}
          className={cn(
            "group w-full bg-surface-active/60 backdrop-blur-sm rounded-2xl text-on-surface font-medium text-[13px] hover:bg-surface-raised transition-all duration-300 ease-out flex items-center justify-center gap-2 shadow-lg shadow-black/10 border border-transparent hover:border-[#6EF0C2]/40 hover:shadow-[#6EF0C2]/15 cursor-pointer hover:scale-[1.02] active:scale-[0.95]",
            collapsed ? "size-11 mx-auto p-0" : "py-3 px-4"
          )}
          title={t.newChat}
          aria-label={t.newChat}
        >
          <Plus className="size-4.5 text-[#6EF0C2] shrink-0 transition-transform duration-300 ease-[cubic-bezier(0.34,1.56,0.64,1)] group-hover:rotate-90 group-hover:scale-125 group-active:scale-90" />
          {!collapsed && <span className="sidebar-label-fade font-semibold">{t.newChat}</span>}
        </button>
      </div>

      {/* Conversations List Grouped by Recency (Shown when expanded) */}
      <div className={cn("flex-1 overflow-y-auto pt-2 relative z-10", collapsed && "hidden")}>
        <div className="flex flex-col gap-5 px-4 pb-4">
          {Object.entries(grouped).map(([groupKey, items]) => {
            if (items.length === 0) return null;
            const groupTitle =
              groupKey === "today"
                ? t.recency.today
                : groupKey === "yesterday"
                ? (language === "fa" ? "دیروز" : "Yesterday")
                : groupKey === "previous7Days"
                ? t.recency.previous7Days
                : t.recency.older;

            return (
              <div key={groupKey} className="flex flex-col gap-2">
                <h4 className="flex items-center gap-2 px-2 text-[10px] font-extrabold uppercase tracking-[0.18em] text-brand-cyan/90 decorative-font">
                  <span
                    aria-hidden="true"
                    className="size-1.5 shrink-0 rounded-full bg-brand-cyan/80"
                  />
                  <span className="shrink-0">{groupTitle}</span>
                  <span aria-hidden="true" className="h-px flex-1 bg-brand-cyan/20" />
                </h4>
                <ul className="flex flex-col gap-1">
                  {items.map((conv) => {
                    const isActive = conv.id === activeConversationId;
                    const isEditing = conv.id === editingId;

                    if (isEditing) {
                      return (
                        <li key={conv.id}>
                          <div className="flex items-center gap-1.5 rounded-2xl border border-brand-cyan/40 bg-surface-raised p-1.5 text-xs">
                            <Input
                              value={editTitle}
                              onChange={(e) => setEditTitle(e.target.value)}
                              onKeyDown={(e) => {
                                if (e.key === "Enter") saveRename(conv.id);
                                if (e.key === "Escape") setEditingId(null);
                              }}
                              autoFocus
                              maxLength={80}
                              className="h-7 text-xs border-0 bg-transparent focus-visible:ring-0 px-2 text-foreground"
                            />
                            <button
                              type="button"
                              onClick={() => saveRename(conv.id)}
                              className="p-1 text-brand-mint hover:bg-surface-active rounded"
                            >
                              <Check className="size-3.5" />
                            </button>
                            <button
                              type="button"
                              onClick={() => setEditingId(null)}
                              className="p-1 text-muted-foreground hover:bg-surface-active rounded"
                            >
                              <X className="size-3.5" />
                            </button>
                          </div>
                        </li>
                      );
                    }

                    const isBranch = conv.title?.includes("(شاخه)") || conv.title?.includes("(Branch)");
                    return (
                      <li key={conv.id}>
                        <div
                          onClick={() => onSelectConversation(conv.id)}
                          className={cn(
                            "group flex items-center justify-between px-3.5 py-2.5 rounded-2xl font-body-ui text-[14px] transition-all cursor-pointer shadow-sm relative",
                            isActive
                              ? "bg-surface-active/50 backdrop-blur-sm border-r-2 border-r-[#6EF0C2] text-on-surface shadow-md shadow-black/10"
                              : "text-on-surface-variant hover:bg-surface-raised/40 hover:text-on-surface"
                          )}
                        >
                          <span
                            className={cn(
                              "truncate decorative-font flex-1 min-w-0 flex items-center gap-1.5",
                              isActive && "bg-clip-text text-transparent bg-gradient-to-r from-[#6EF0C2] to-[#31C8ED] font-bold"
                            )}
                          >
                            {isBranch && (
                              <GitBranch className="size-3.5 text-brand-mint shrink-0" />
                            )}
                            <span className="truncate">{conv.title || "گفتگوی جدید"}</span>
                          </span>

                          <div className="flex shrink-0 items-center gap-0.5 opacity-0 transition-opacity group-hover:opacity-100 group-focus-within:opacity-100 focus-within:opacity-100">
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                onShareConversation(conv.id);
                              }}
                              disabled={isSharing}
                              className="group/share flex size-6 items-center justify-center rounded-md text-on-surface-variant hover:bg-surface-raised hover:text-on-surface transition-all duration-200 active:scale-90 disabled:cursor-wait disabled:opacity-50"
                              aria-label={t.actions.share}
                              title={t.actions.share}
                            >
                              <Share2 className="size-3.5 transition-transform duration-300 ease-[cubic-bezier(0.34,1.56,0.64,1)] group-hover/share:scale-125 group-hover/share:text-brand-cyan group-active/share:scale-90" />
                            </button>

                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <button
                                  type="button"
                                  onClick={(e) => e.stopPropagation()}
                                  className="flex size-6 items-center justify-center rounded-md text-on-surface-variant hover:bg-surface-raised hover:text-on-surface transition-colors"
                                  aria-label="Options"
                                >
                                  <MoreVertical className="size-3.5" />
                                </button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent
                                align="end"
                                className="w-36 border-border bg-surface-raised text-foreground"
                              >
                                <DropdownMenuItem
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    startRename(conv);
                                  }}
                                  className="gap-2 text-xs cursor-pointer hover:bg-surface-active"
                                >
                                  <Edit2 className="size-3.5" />
                                  <span>{t.actions.rename}</span>
                                </DropdownMenuItem>
                                <DropdownMenuItem
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    onDeleteConversation(conv.id);
                                  }}
                                  className="gap-2 text-xs text-destructive focus:bg-destructive/15 focus:text-destructive cursor-pointer"
                                >
                                  <Trash2 className="size-3.5" />
                                  <span>{t.actions.delete}</span>
                                </DropdownMenuItem>
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </div>
                        </div>
                      </li>
                    );
                  })}
                </ul>
              </div>
            );
          })}
        </div>
      </div>

      {/* Bottom Compact Nav */}
      <div
        className={cn(
          "p-4 bg-surface-container-low/20 backdrop-blur-md rounded-b-3xl relative z-10 mt-auto border-t border-border/30 transition-all duration-300",
          collapsed ? "px-2 py-3 space-y-2 flex flex-col items-center" : "space-y-3"
        )}
      >
        {!collapsed && (
          <ul className="space-y-1 mb-2">
            <li>
              <Link
                href={appPath("admin")}
                className="flex items-center gap-3 px-3 py-2 text-on-surface-variant hover:text-on-surface text-[13px] hover:bg-surface-raised/40 rounded-2xl transition-colors decorative-font"
              >
                <Gauge className="size-4 text-brand-cyan" />
                <span>Admin panel</span>
              </Link>
            </li>
            <li>
              <button
                type="button"
                onClick={onOpenAccount}
                className="w-full flex items-center gap-3 px-3 py-2 text-on-surface-variant hover:text-on-surface text-[13px] hover:bg-surface-raised/40 rounded-2xl transition-colors decorative-font text-start cursor-pointer"
              >
                <Settings className="size-4 text-brand-cyan" />
                <span>{t.account.settings}</span>
              </button>
            </li>
          </ul>
        )}

        <div
          className={cn(
            "flex items-center transition-all",
            collapsed ? "flex-col gap-2 justify-center" : "justify-between px-1"
          )}
        >
          {/* Direct Language Toggle */}
          <button
            type="button"
            onClick={onToggleLanguage}
            className={cn(
              "group text-on-surface-variant hover:text-on-surface hover:bg-surface-raised rounded-xl transition-all duration-300 ease-out shadow-sm cursor-pointer flex items-center justify-center gap-1.5 active:scale-90 border border-transparent hover:border-brand-cyan/30 hover:shadow-sm hover:shadow-brand-cyan/10",
              collapsed ? "size-10 p-0" : "px-3 py-1.5"
            )}
            title={language === "fa" ? "تغییر زبان به English" : "Switch to Persian"}
            aria-label="Toggle language"
          >
            <Globe className="size-4 text-brand-cyan shrink-0 transition-transform duration-500 ease-[cubic-bezier(0.34,1.56,0.64,1)] group-hover:rotate-180 group-active:rotate-[360deg]" />
            <span key={language} className="text-[11px] font-extrabold uppercase text-brand-cyan tracking-wider lang-fade-slide inline-block">
              {language === "fa" ? "FA" : "EN"}
            </span>
          </button>

          <button
            type="button"
            data-testid="account-menu-button"
            onClick={onOpenAccount}
            className="cursor-pointer hover:opacity-80 transition-all duration-200 active:scale-95 rounded-full"
            title="Local Profile"
            aria-label="Local Profile"
          >
            <Image
              src="/profile.png"
              alt="User profile"
              width={32}
              height={32}
              className="w-8 h-8 rounded-full shadow-md object-cover"
            />
          </button>
        </div>
      </div>
    </nav>
  );
}
