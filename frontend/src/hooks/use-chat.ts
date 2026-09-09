"use client";

import * as React from "react";
import { toast } from "sonner";
import { apiFetch, appPath } from "@/lib/api";
import { safeRandomUUID } from "@/lib/utils";
import type {
  Conversation,
  ConversationDetail,
  Message,
  Citation,
  Workflow,
  Language,
  StreamEvent,
  ProgressStage,
  FileAttachment,
  ToolCall,
} from "@/lib/types";

function localizeErrorMessage(raw: unknown, fallback: string, lang: Language): string {
  if (typeof raw === "string" && raw.trim()) {
    const lower = raw.toLowerCase();
    if (lang === "fa") {
      if (
        lower.includes("failed to fetch") ||
        lower.includes("networkerror") ||
        lower.includes("network request failed") ||
        lower.includes("load failed") ||
        lower.includes("connection refused")
      ) {
        return "خطا در برقراری ارتباط با سرور. لطفاً اتصال اینترنت خود را بررسی کنید.";
      }
      if (lower.includes("too many requests") || lower.includes("rate limit")) {
        return "تعداد درخواست‌های ارسالی بیش از حد مجاز است. لطفاً کمی بعد تلاش کنید.";
      }
    }
    return raw;
  }
  if (raw instanceof Error && raw.message) {
    return localizeErrorMessage(raw.message, fallback, lang);
  }
  return fallback;
}

async function readErrorMessage(response: Response, fallback: string, lang: Language = "fa"): Promise<string> {
  const payload: unknown = await response.json().catch(() => null);

  if (payload && typeof payload === "object") {
    const data = payload as { detail?: unknown; title?: unknown };
    if (typeof data.detail === "string" && data.detail.trim()) return localizeErrorMessage(data.detail, fallback, lang);
    if (typeof data.title === "string" && data.title.trim()) return localizeErrorMessage(data.title, fallback, lang);
  }

  return fallback;
}

export function useChat(initialLanguage: Language = "fa") {
  const [language, setLanguage] = React.useState<Language>(initialLanguage);
  const [conversations, setConversations] = React.useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = React.useState<string | null>(null);
  const [activeConversation, setActiveConversation] = React.useState<ConversationDetail | null>(null);

  const [isStreaming, setIsStreaming] = React.useState(false);
  const [streamingText, setStreamingText] = React.useState("");
  const [streamingThinkingText, setStreamingThinkingText] = React.useState("");
  const [streamingStage, setStreamingStage] = React.useState<ProgressStage | undefined>(undefined);
  const [streamingLabel, setStreamingLabel] = React.useState<string | undefined>(undefined);
  const [streamingTools, setStreamingTools] = React.useState<ToolCall[]>([]);
  const [activeWorkflow, setActiveWorkflow] = React.useState<Workflow | null>(null);
  const [activeRequestId, setActiveRequestId] = React.useState<string | null>(null);
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null);
  const [limitReached, setLimitReached] = React.useState(false);
  const [isCreatingConversation, setIsCreatingConversation] = React.useState(false);
  const [pendingEditMessageId, setPendingEditMessageId] = React.useState<string | null>(null);

  const abortControllerRef = React.useRef<AbortController | null>(null);
  const createConversationRef = React.useRef<Promise<Conversation | null> | null>(null);
  const streamingTextRef = React.useRef("");

  // Load conversations on mount
  const loadConversations = React.useCallback(async () => {
    try {
      const res = await apiFetch("conversations");
      if (res.ok) {
        const raw = await res.json();
        const data: Conversation[] = Array.isArray(raw)
          ? raw
          : Array.isArray(raw?.conversations)
          ? raw.conversations
          : [];
        setConversations(data);
        if (data.length >= 20) {
          setLimitReached(true);
        } else {
          setLimitReached(false);
        }
      }
    } catch {
      // Offline / initial state
      setConversations([]);
    }
  }, []);

  React.useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  // Select conversation by ID
  const selectConversation = React.useCallback(
    async (id: string) => {
      try {
        const res = await apiFetch(`conversations/${id}`);
        if (res.ok) {
          const detail: ConversationDetail = await res.json();
          setActiveConversationId(detail.id);
          setActiveConversation(detail);
          setActiveWorkflow(detail.workflow || null);
          setLanguage(detail.language || "fa");
        }
      } catch (err) {
        console.error("Error loading conversation:", err);
      }
    },
    []
  );

  // Reset to a new chat state (without duplicate empty creations)
  const startNewChat = React.useCallback(() => {
    if (!activeConversationId && !activeConversation) return;
    if (activeConversation && activeConversation.messages.length === 0) {
      setActiveConversationId(null);
      setActiveConversation(null);
      setActiveWorkflow(null);
      setErrorMessage(null);
      return;
    }
    setActiveConversationId(null);
    setActiveConversation(null);
    setActiveWorkflow(null);
    setErrorMessage(null);
  }, [activeConversationId, activeConversation]);

  // Create a new conversation
  const createConversation = React.useCallback((): Promise<Conversation | null> => {
    // Reuse the pending request when clicks arrive before navigation finishes.
    if (createConversationRef.current) return createConversationRef.current;

    setIsCreatingConversation(true);

    const request = (async (): Promise<Conversation | null> => {
      try {
        const res = await apiFetch("conversations", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ language }),
        });

        if (res.status === 409) {
          const message =
            language === "fa"
              ? "سقف ۲۰ گفتگوی فعال تکمیل شده است. لطفاً ابتدا یکی از گفتگوهای قبلی را حذف کنید."
              : "Limit of 20 active conversations reached. Please delete an older conversation first.";
          setLimitReached(true);
          setErrorMessage(message);
          toast.error(message);
          return null;
        }

        if (!res.ok) {
          const fallback = language === "fa" ? "ساخت گفتگوی جدید انجام نشد." : "Could not create a conversation.";
          throw new Error(await readErrorMessage(res, fallback));
        }

        const newConv: Conversation = await res.json();
        setConversations((prev) => [newConv, ...prev]);
        setActiveConversationId(newConv.id);
        setActiveConversation({
          ...newConv,
          messages: [],
          context: [],
          workflow: null,
        });
        setActiveWorkflow(null);
        return newConv;
      } catch (err) {
        const message =
          err instanceof Error && err.message
            ? err.message
            : language === "fa"
              ? "ساخت گفتگوی جدید انجام نشد."
              : "Could not create a conversation.";
        setErrorMessage(message);
        toast.error(message);
        console.error("Error creating conversation:", err);
        return null;
      }
    })();

    createConversationRef.current = request;
    void request.finally(() => {
      if (createConversationRef.current === request) {
        createConversationRef.current = null;
        setIsCreatingConversation(false);
      }
    });

    return request;
  }, [language]);

  // Rename a conversation
  const renameConversation = React.useCallback(
    async (id: string, newTitle: string) => {
      try {
        const res = await apiFetch(`conversations/${id}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title: newTitle }),
        });

        if (res.ok) {
          const updated: Conversation = await res.json();
          setConversations((prev) =>
            prev.map((c) => (c.id === id ? { ...c, title: updated.title, titleSource: "user" } : c))
          );
          if (activeConversationId === id) {
            setActiveConversation((prev) => (prev ? { ...prev, title: updated.title } : null));
          }
          toast.success(language === "fa" ? "عنوان تغییر کرد" : "Title updated");
        }
      } catch (err) {
        console.error("Error renaming conversation:", err);
      }
    },
    [activeConversationId, language]
  );

  // Delete a conversation
  const deleteConversation = React.useCallback(
    async (id: string) => {
      try {
        const res = await apiFetch(`conversations/${id}`, {
          method: "DELETE",
        });

        if (res.ok || res.status === 204) {
          setConversations((prev) => {
            const next = prev.filter((c) => c.id !== id);
            if (next.length < 20) setLimitReached(false);
            return next;
          });

          if (activeConversationId === id) {
            setActiveConversationId(null);
            setActiveConversation(null);
            setActiveWorkflow(null);
          }
          toast.success(language === "fa" ? "گفتگو حذف شد" : "Conversation deleted");
        }
      } catch (err) {
        console.error("Error deleting conversation:", err);
      }
    },
    [activeConversationId, language]
  );

  const uploadPdf = React.useCallback(
    async (file: File): Promise<FileAttachment | null> => {
      let targetConversationId = activeConversationId;
      if (!targetConversationId) {
        const newConversation = await createConversation();
        if (!newConversation) return null;
        targetConversationId = newConversation.id;
      }

      const formData = new FormData();
      formData.append("file", file, file.name);
      formData.append("conversation_id", targetConversationId);

      try {
        const response = await apiFetch("uploads/pdf", {
          method: "POST",
          body: formData,
        });
        if (!response.ok) {
          const data = await response.json().catch(() => null);
          throw new Error(data?.detail || "PDF upload failed");
        }
        const data: {
          id: string;
          name: string;
          size: number;
          contentType: "application/pdf";
          pageCount?: number;
        } = await response.json();
        return data;
      } catch (error) {
        toast.error(
          language === "fa"
            ? "بارگذاری PDF انجام نشد. لطفاً فایل متنی و کوچک‌تری انتخاب کنید."
            : "PDF upload failed. Try a smaller text-based file."
        );
        console.error("PDF upload error:", error);
        return null;
      }
    },
    [activeConversationId, createConversation, language]
  );

  const branchConversation = React.useCallback(
    async (messageId: string, mode: "branch" | "edit" = "branch"):
      Promise<ConversationDetail | null> => {
      if (!activeConversationId) return null;

      try {
        const response = await apiFetch(`conversations/${activeConversationId}/branch`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ sourceMessageId: messageId, mode }),
        });
        if (!response.ok) throw new Error(`Branch failed: ${response.status}`);

        const detail: ConversationDetail = await response.json();
        setConversations((prev) => [detail, ...prev.filter((conversation) => conversation.id !== detail.id)]);
        setActiveConversationId(detail.id);
        setActiveConversation(detail);
        setActiveWorkflow(detail.workflow || null);
        setLanguage(detail.language);
        toast.success(
          mode === "edit"
            ? language === "fa"
              ? "ویرایش در همین گفتگو آماده شد"
              : "Edit prepared in this conversation"
            : language === "fa"
              ? "شاخه گفتگو ساخته شد"
              : "Conversation branch created"
        );
        return detail;
      } catch (error) {
        toast.error(
          language === "fa" ? "ساخت شاخه گفتگو انجام نشد." : "Could not create a conversation branch."
        );
        console.error("Branch conversation error:", error);
        return null;
      }
    },
    [activeConversationId, language]
  );

  const editConversation = React.useCallback(
    async (messageId: string, syncActive = true): Promise<ConversationDetail | null> => {
      if (!activeConversationId) return null;

      try {
        const response = await apiFetch(`conversations/${activeConversationId}/edit`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ sourceMessageId: messageId }),
        });
        if (!response.ok) {
          throw new Error(await readErrorMessage(response, `Edit failed: ${response.status}`));
        }

        const detail: ConversationDetail = await response.json();
        setConversations((prev) =>
          prev.map((conversation) =>
            conversation.id === detail.id ? { ...conversation, ...detail } : conversation
          )
        );
        if (syncActive) {
          setActiveConversationId(detail.id);
          setActiveConversation(detail);
          setActiveWorkflow(detail.workflow || null);
          setLanguage(detail.language);
        }
        return detail;
      } catch (error) {
        const message =
          error instanceof Error && error.message
            ? error.message
            : language === "fa"
              ? "ویرایش پیام انجام نشد."
              : "Could not edit the message.";
        toast.error(message);
        console.error("Edit conversation error:", error);
        return null;
      }
    },
    [activeConversationId, language]
  );

  const createShareLink = React.useCallback(
    async (conversationId: string | null = activeConversationId): Promise<string | null> => {
      if (!conversationId) return null;

      try {
        const response = await apiFetch(`conversations/${conversationId}/share`, { method: "POST" });
        if (!response.ok) throw new Error(`Share failed: ${response.status}`);
        const data: { token: string } = await response.json();
        return `${window.location.origin}${appPath(`/share/${data.token}`)}`;
      } catch (error) {
        toast.error(language === "fa" ? "ساخت پیوند اشتراک انجام نشد." : "Could not create a share link.");
        console.error("Share link error:", error);
        return null;
      }
    },
    [activeConversationId, language]
  );

  const [useRag, setUseRag] = React.useState<boolean>(true);

  // Send message and handle SSE stream
  const sendMessage = React.useCallback(
    async (
      messageText: string,
      attachments: FileAttachment[] = [],
      seededConversation?: ConversationDetail,
      explicitUseRag?: boolean,
      replyTo?: { id: string; content: string } | null
    ) => {
      let targetConvId = seededConversation?.id ?? activeConversationId;
      const effectiveUseRag = explicitUseRag !== undefined ? explicitUseRag : useRag;

      const requestLanguage = seededConversation?.language ?? language;
      const replySnippet = replyTo?.content ? (replyTo.content.slice(0, 100) + (replyTo.content.length > 100 ? "..." : "")) : undefined;
      const userMsg: Message = {
        id: safeRandomUUID(),
        role: "user",
        content: messageText,
        direction: requestLanguage === "fa" ? "rtl" : "ltr",
        status: "complete",
        attachments,
        replyToId: replyTo?.id,
        replyToSnippet: replySnippet,
        createdAt: new Date().toISOString(),
      };

      if (!targetConvId) {
        const pendingId = `pending-${userMsg.id}`;
        setActiveConversation({
          id: pendingId,
          title: messageText.slice(0, 30),
          titleSource: "placeholder",
          language: requestLanguage,
          status: "active",
          createdAt: userMsg.createdAt,
          updatedAt: userMsg.createdAt,
          expiresAt: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
          messages: [userMsg],
          context: [],
          workflow: null,
        });
      }

      if (!targetConvId) {
        const newConversation = await createConversation();
        if (!newConversation) return;
        targetConvId = newConversation.id;
      }

      if (seededConversation) {
        setActiveConversationId(seededConversation.id);
        setActiveConversation(seededConversation);
        setActiveWorkflow(seededConversation.workflow || null);
      }

      const workflowId = seededConversation?.workflow?.id ?? activeWorkflow?.id;

      setActiveConversation((prev) => {
        const baseConversation = seededConversation ?? prev;
        if (!baseConversation) {
          return {
            id: targetConvId!,
            title: messageText.slice(0, 30),
            titleSource: "placeholder",
            language: requestLanguage,
            status: "active",
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
            expiresAt: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
            messages: [userMsg],
            context: [],
            workflow: null,
          };
        }
        return {
          ...baseConversation,
          messages: baseConversation.messages.some((item) => item.id === userMsg.id)
            ? baseConversation.messages
            : [...baseConversation.messages, userMsg],
        };
      });

      setIsStreaming(true);
      setStreamingText("");
      streamingTextRef.current = "";
      setStreamingThinkingText("");
      setStreamingStage(effectiveUseRag ? "searching" : "reasoning");
      setStreamingLabel(
        requestLanguage === "fa"
          ? effectiveUseRag
            ? "جستجو در پایگاه دانش سازمانی…"
            : "پردازش و تدوین پاسخ هوش مصنوعی…"
          : effectiveUseRag
            ? "Searching knowledge base…"
            : "Processing AI response…"
      );
      setErrorMessage(null);

      const controller = new AbortController();
      abortControllerRef.current = controller;
      const idempotencyKey = safeRandomUUID();
      const connectionError =
        requestLanguage === "fa"
          ? "ارتباط با سرویس هوشمند سازمانی برقرار نشد. لطفاً مجدداً تلاش کنید."
          : "Could not connect to Sovereign AI Assistant. Please try again.";
      let hasTerminalEvent = false;

      try {
        const res = await apiFetch("chat", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Idempotency-Key": idempotencyKey,
          },
          body: JSON.stringify({
            conversationId: targetConvId,
            message: messageText,
            language: requestLanguage,
            workflowId,
            fileIds: attachments.map((attachment) => attachment.id),
            useRag: effectiveUseRag,
            replyToMessageId: replyTo?.id,
            replyToSnippet: replySnippet,
          }),
          signal: controller.signal,
        });

        if (res.status === 429) {
          throw new Error(
            requestLanguage === "fa"
              ? "تعداد درخواست‌ها زیاد است. لطفاً کمی بعد دوباره تلاش کنید."
              : "Too many requests. Please try again shortly."
          );
        }

        if (!res.ok) {
          throw new Error(await readErrorMessage(res, connectionError));
        }

        if (!res.body) {
          throw new Error(connectionError);
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed || !trimmed.startsWith("data:")) continue;

            const jsonStr = trimmed.replace(/^data:\s*/, "");
            if (jsonStr === "[DONE]") continue;

            try {
              const event: StreamEvent = JSON.parse(jsonStr);

              if (event.type === "progress") {
                setActiveRequestId(event.requestId);
                setStreamingStage(event.stage);
                setStreamingLabel(event.label);
              } else if (event.type === "delta") {
                setActiveRequestId(event.requestId);
                streamingTextRef.current += event.text;
                setStreamingText(streamingTextRef.current);
              } else if (event.type === "thinking") {
                setActiveRequestId(event.requestId);
                setStreamingThinkingText((prev) => prev + event.text);
              } else if (event.type === "tool") {
                setActiveRequestId(event.requestId);
                setStreamingTools((prev) => {
                  const next = prev.filter(
                    (tool) => !(tool.requestId === event.requestId && tool.name === event.name)
                  );
                  return [...next, event];
                });
              } else if (event.type === "complete") {
                hasTerminalEvent = true;
                setActiveRequestId(null);
                setStreamingLabel(undefined);
                setStreamingStage(undefined);
                if (event.workflow) {
                  setActiveWorkflow(event.workflow);
                }

                setActiveConversation((prev) => {
                  if (!prev) return null;
                  const updatedUserMsgId = event.userMessageId;
                  const messages = updatedUserMsgId
                    ? prev.messages.map((message) =>
                        message.id === userMsg.id
                          ? { ...message, id: updatedUserMsgId }
                          : message
                      )
                    : prev.messages;
                  return {
                    ...prev,
                    messages: [...messages, event.message],
                    workflow: event.workflow || prev.workflow,
                  };
                });

                // Refresh conversation list to get low-cost generated title
                loadConversations();
              } else if (event.type === "error") {
                hasTerminalEvent = true;
                const message = localizeErrorMessage(event.message, event.message, requestLanguage);
                setErrorMessage(message);
                toast.error(message);
              }
            } catch {
              // Parse error on incomplete chunk
            }
          }
        }

        if (!hasTerminalEvent && !controller.signal.aborted) {
          throw new Error(connectionError);
        }
      } catch (err) {
        if (controller.signal.aborted) {
          // Interrupted by user
            const interruptedMsg: Message = {
            id: safeRandomUUID(),
            role: "assistant",
            content: streamingTextRef.current || (requestLanguage === "fa" ? "پاسخ متوقف شد." : "Generation stopped."),
            direction: requestLanguage === "fa" ? "rtl" : "ltr",
            status: "interrupted",
            createdAt: new Date().toISOString(),
          };
          setActiveConversation((prev) => {
            if (!prev) return null;
            return {
              ...prev,
              messages: [...prev.messages, interruptedMsg],
            };
          });
        } else {
          const message = err instanceof Error && err.message ? err.message : connectionError;
          setErrorMessage(message);
          toast.error(message);
        }
      } finally {
        setIsStreaming(false);
        setStreamingText("");
        setStreamingThinkingText("");
        setStreamingLabel(undefined);
        setStreamingStage(undefined);
        setStreamingTools([]);
        streamingTextRef.current = "";
        abortControllerRef.current = null;
      }
    },
    [activeConversationId, activeWorkflow?.id, createConversation, language, loadConversations]
  );

  const editMessage = React.useCallback(
    async (message: Message, content: string) => {
      const conversationId = activeConversationId;
      const previousConversation = activeConversation;
      if (!conversationId || !previousConversation) return;

      const sourceIndex = previousConversation.messages.findIndex((item) => item.id === message.id);
      if (sourceIndex < 0) return;

      const pendingMessage: Message = {
        ...message,
        content,
        status: "pending",
        citations: [],
      };

      setPendingEditMessageId(message.id);
      setErrorMessage(null);
      setActiveConversation((prev) => {
        if (!prev || prev.id !== conversationId) return prev;
        const currentIndex = prev.messages.findIndex((item) => item.id === message.id);
        if (currentIndex < 0) return prev;

        return {
          ...prev,
          messages: [...prev.messages.slice(0, currentIndex), pendingMessage],
          updatedAt: new Date().toISOString(),
        };
      });

      try {
        const edited = await editConversation(message.id, false);
        if (!edited) {
          setActiveConversation((prev) =>
            prev?.id === conversationId ? previousConversation : prev
          );
          return;
        }

        setPendingEditMessageId(null);
        toast.success(language === "fa" ? "پیام در همین گفتگو ویرایش شد" : "Message edited in this conversation");
        await sendMessage(content, message.attachments || [], edited);
      } finally {
        setPendingEditMessageId(null);
      }
    },
    [activeConversation, activeConversationId, editConversation, language, sendMessage]
  );

  // Cancel active stream
  const cancelStreaming = React.useCallback(async () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    if (activeRequestId) {
      try {
        await apiFetch(`chat/${activeRequestId}/cancel`, { method: "POST" });
      } catch {
        // Ignore cancel fetch error
      }
    }
  }, [activeRequestId]);

  // Retry last message
  const retryLastMessage = React.useCallback(() => {
    if (!activeConversation || activeConversation.messages.length === 0) return;
    const lastUserMsg = [...activeConversation.messages].reverse().find((m) => m.role === "user");
    if (lastUserMsg) {
      sendMessage(lastUserMsg.content, lastUserMsg.attachments || []);
    }
  }, [activeConversation, sendMessage]);

  // Collect all citations across current conversation (fixed: no deduplication by single URL, tagged by messageId)
  const allCitations = React.useMemo(() => {
    if (!activeConversation) return [];
    const citations: Citation[] = [];
    const seen = new Set<string>();

    for (let i = 0; i < activeConversation.messages.length; i++) {
      const msg = activeConversation.messages[i];
      const prevUserMsg = i > 0 && activeConversation.messages[i - 1].role === "user"
        ? activeConversation.messages[i - 1]
        : null;
      const promptSnippet = prevUserMsg
        ? (prevUserMsg.content.slice(0, 35) + (prevUserMsg.content.length > 35 ? "..." : ""))
        : undefined;

      if (msg.citations && Array.isArray(msg.citations)) {
        for (const cit of msg.citations) {
          const key = `${msg.id}-${cit.title || ""}-${cit.section || ""}-${(cit.snippet || "").slice(0, 50)}`;
          if (!seen.has(key)) {
            seen.add(key);
            citations.push({
              ...cit,
              messageId: msg.id,
              promptSnippet: cit.promptSnippet || promptSnippet,
            });
          }
        }
      }
    }
    return citations;
  }, [activeConversation]);

  const addVoiceMessages = React.useCallback(
    (userMessage: Message, assistantMessage: Message, conversationId: string) => {
      setActiveConversationId(conversationId);
      setActiveConversation((prev) => {
        if (!prev) {
          return {
            id: conversationId,
            title: userMessage.content.slice(0, 30),
            titleSource: "placeholder",
            language,
            status: "active",
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
            expiresAt: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
            messages: [userMessage, assistantMessage],
            context: [],
            workflow: null,
          };
        }
        return {
          ...prev,
          messages: [...prev.messages, userMessage, assistantMessage],
        };
      });
      loadConversations();
    },
    [language, loadConversations]
  );

  return {
    language,
    setLanguage,
    conversations,
    activeConversationId,
    activeConversation,
    activeWorkflow,
    allCitations,
    isStreaming,
    streamingText,
    streamingThinkingText,
    streamingStage,
    streamingLabel,
    streamingTools,
    errorMessage,
    limitReached,
    isCreatingConversation,
    pendingEditMessageId,
    loadConversations,
    selectConversation,
    startNewChat,
    createConversation,
    renameConversation,
    deleteConversation,
    sendMessage,
    uploadPdf,
    branchConversation,
    editConversation,
    editMessage,
    createShareLink,
    cancelStreaming,
    retryLastMessage,
    addVoiceMessages,
    useRag,
    setUseRag,
  };
}
