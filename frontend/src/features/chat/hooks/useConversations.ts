"use client";

import * as React from "react";
import { toast } from "sonner";
import {
  createConversationApi,
  deleteConversationApi,
  fetchConversationDetailApi,
  fetchConversationsApi,
  shareConversationApi,
  updateConversationApi,
} from "@/api/index";
import type { Conversation, ConversationDetail, Language } from "@/lib/types";

export function useConversations(language: Language) {
  const [conversations, setConversations] = React.useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = React.useState<string | null>(null);
  const [activeConversation, setActiveConversation] = React.useState<ConversationDetail | null>(null);
  const [limitReached, setLimitReached] = React.useState(false);
  const [isCreatingConversation, setIsCreatingConversation] = React.useState(false);
  const createConversationRef = React.useRef<Promise<Conversation | null> | null>(null);

  const loadConversations = React.useCallback(async () => {
    try {
      const data = await fetchConversationsApi();
      const list = Array.isArray(data)
        ? data
        : Array.isArray(data?.conversations)
        ? data.conversations
        : [];
      setConversations(list);
      setLimitReached(list.length >= 20);
    } catch {
      setConversations([]);
    }
  }, []);

  React.useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  const selectConversation = React.useCallback(async (id: string) => {
    try {
      const detail = await fetchConversationDetailApi(id);
      setActiveConversationId(detail.id);
      setActiveConversation(detail);
      return detail;
    } catch (err) {
      console.error("Error loading conversation:", err);
      return null;
    }
  }, []);

  const createConversation = React.useCallback(async (): Promise<Conversation | null> => {
    if (createConversationRef.current) return createConversationRef.current;
    setIsCreatingConversation(true);

    const request = (async () => {
      try {
        const newConv = await createConversationApi({ language });
        setConversations((prev) => [newConv, ...prev]);
        setActiveConversationId(newConv.id);
        setActiveConversation({
          ...newConv,
          messages: [],
          context: [],
          workflow: null,
        });
        return newConv;
      } catch (err) {
        toast.error(language === "fa" ? "ساخت گفتگوی جدید انجام نشد." : "Could not create conversation.");
        return null;
      }
    })();

    createConversationRef.current = request;
    try {
      return await request;
    } finally {
      createConversationRef.current = null;
      setIsCreatingConversation(false);
    }
  }, [language]);

  const renameConversation = React.useCallback(
    async (id: string, title: string) => {
      try {
        const updated = await updateConversationApi(id, { title });
        setConversations((prev) =>
          prev.map((c) => (c.id === id ? { ...c, title: updated.title, titleSource: "user" } : c))
        );
        if (activeConversationId === id) {
          setActiveConversation((prev) => (prev ? { ...prev, title: updated.title } : null));
        }
        toast.success(language === "fa" ? "عنوان تغییر کرد" : "Title updated");
      } catch (err) {
        console.error("Error renaming conversation:", err);
      }
    },
    [activeConversationId, language]
  );

  const deleteConversation = React.useCallback(
    async (id: string) => {
      try {
        await deleteConversationApi(id);
        setConversations((prev) => {
          const next = prev.filter((c) => c.id !== id);
          if (next.length < 20) setLimitReached(false);
          return next;
        });
        if (activeConversationId === id) {
          setActiveConversationId(null);
          setActiveConversation(null);
        }
        toast.success(language === "fa" ? "گفتگو حذف شد" : "Conversation deleted");
      } catch (err) {
        toast.error(language === "fa" ? "حذف گفتگو با خطا مواجه شد." : "Could not delete conversation.");
      }
    },
    [activeConversationId, language]
  );

  const createShareLink = React.useCallback(
    async (id: string): Promise<string | null> => {
      try {
        const res = await shareConversationApi(id);
        if (res.token) {
          return `${window.location.origin}/share/${res.token}`;
        }
        return null;
      } catch {
        toast.error(language === "fa" ? "ساخت لینک اشتراک‌گذاری انجام نشد." : "Failed to create share link.");
        return null;
      }
    },
    [language]
  );

  return {
    conversations,
    setConversations,
    activeConversationId,
    setActiveConversationId,
    activeConversation,
    setActiveConversation,
    limitReached,
    isCreatingConversation,
    loadConversations,
    selectConversation,
    createConversation,
    renameConversation,
    deleteConversation,
    createShareLink,
  };
}
