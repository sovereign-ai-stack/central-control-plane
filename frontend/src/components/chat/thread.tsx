"use client";

import * as React from "react";
import Image from "next/image";
import {
  BookOpen,
  Check,
  ChevronDown,
  Copy,
  FileText,
  GitBranch,
  Loader2,
  Pencil,
  Sparkles,
  Volume2,
  VolumeX,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import {
  MessageScrollerProvider,
  MessageScroller,
  MessageScrollerViewport,
  MessageScrollerContent,
  MessageScrollerItem,
  MessageScrollerButton,
  useMessageScroller,
} from "@/components/ui/message-scroller";
import { BrandLogoIcon } from "@/components/ui/brand-logo";
import { MarkdownContent } from "./content";
import { CitationDialog } from "./citation-dialog";
import { WorkflowProgress } from "../workflow/progress";
import { MessageSkeleton, ErrorAlert } from "./status";
import { DirectionBoundary } from "./direction";
import { useTranslation } from "@/lib/locale";
import type {
  Citation,
  FileAttachment,
  Language,
  Message as MessageType,
  ProgressStage,
  ToolCall,
  Workflow,
} from "@/lib/types";
import { Attachment, AttachmentContent, AttachmentDescription, AttachmentGroup, AttachmentMedia, AttachmentTitle } from "@/components/ui/attachment";
import { Marker, MarkerContent, MarkerIcon } from "@/components/ui/marker";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

export interface ThreadProps extends React.ComponentProps<"div"> {
  messages: MessageType[];
  isStreaming?: boolean;
  streamingText?: string;
  streamingThinkingText?: string;
  streamingStage?: ProgressStage;
  streamingLabel?: string;
  activeWorkflow?: Workflow | null;
  language?: Language;
  onCitationClick?: (citation: Citation) => void;
  onHoverMessage?: (messageId: string | null) => void;
  onSelectMessage?: (messageId: string) => void;
  onRetry?: () => void;
  onEditMessage?: (message: MessageType, content: string) => void | Promise<void>;
  pendingEditMessageId?: string | null;
  onBranchMessage?: (message: MessageType) => void | Promise<void>;
  toolCalls?: ToolCall[];
}

function ThreadScrollSync({ messagesCount, isStreaming }: { messagesCount: number; isStreaming?: boolean }) {
  const { scrollToBottom } = useMessageScroller();
  React.useEffect(() => {
    scrollToBottom(true);
  }, [messagesCount, isStreaming, scrollToBottom]);
  return null;
}

export function Thread({
  messages,
  isStreaming = false,
  streamingText = "",
  streamingThinkingText = "",
  streamingStage,
  streamingLabel,
  activeWorkflow,
  language = "fa",
  onCitationClick,
  onHoverMessage,
  onSelectMessage,
  onRetry,
  onEditMessage,
  pendingEditMessageId,
  onBranchMessage,
  toolCalls = [],
  className,
  ...props
}: ThreadProps) {
  const t = useTranslation(language);
  const [playingMessageId, setPlayingMessageId] = React.useState<string | null>(null);
  const [ttsLoadingId, setTtsLoadingId] = React.useState<string | null>(null);
  const [copiedMessageId, setCopiedMessageId] = React.useState<string | null>(null);
  const [thinkingOpen, setThinkingOpen] = React.useState(true);
  const [editingMessageId, setEditingMessageId] = React.useState<string | null>(null);
  const [editingValue, setEditingValue] = React.useState("");
  const [branchingMessageId, setBranchingMessageId] = React.useState<string | null>(null);
  const [selectedCitation, setSelectedCitation] = React.useState<Citation | null>(null);
  const audioPlayerRef = React.useRef<HTMLAudioElement | null>(null);

  React.useEffect(() => {
    if (isStreaming) {
      if (streamingText && streamingText.length > 0) {
        setThinkingOpen(false);
      } else {
        setThinkingOpen(true);
      }
    }
  }, [isStreaming, streamingText]);

  React.useEffect(() => {
    return () => {
      audioPlayerRef.current?.pause();
      audioPlayerRef.current = null;
    };
  }, []);

  const toggleSpeakMessage = async (messageId: string, text: string) => {
    if (playingMessageId === messageId) {
      audioPlayerRef.current?.pause();
      audioPlayerRef.current = null;
      setPlayingMessageId(null);
      return;
    }

    audioPlayerRef.current?.pause();
    audioPlayerRef.current = null;
    setTtsLoadingId(messageId);

    try {
      const currentVoice = typeof window !== "undefined"
        ? localStorage.getItem("sovereign_voice_persona") || localStorage.getItem("sovereign_voice_persona") || "Aoede"
        : "Aoede";
      const response = await apiFetch("voice/tts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, voice: currentVoice }),
      });
      if (!response.ok) throw new Error("TTS request failed");

      const audioUrl = URL.createObjectURL(await response.blob());
      const audio = new Audio(audioUrl);
      audioPlayerRef.current = audio;
      audio.onended = () => {
        URL.revokeObjectURL(audioUrl);
        setPlayingMessageId(null);
        audioPlayerRef.current = null;
      };
      audio.onerror = () => {
        URL.revokeObjectURL(audioUrl);
        setPlayingMessageId(null);
        audioPlayerRef.current = null;
      };

      await audio.play();
      setPlayingMessageId(messageId);
    } catch (error) {
      console.error("TTS playback error:", error);
      toast.error(language === "fa" ? "خطا در پخش صوتی پاسخ." : "Failed to play voice audio.");
      setPlayingMessageId(null);
    } finally {
      setTtsLoadingId(null);
    }
  };

  const copyMessage = async (messageId: string, text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedMessageId(messageId);
      toast.success(language === "fa" ? "پاسخ در کلیپ‌بورد کپی شد." : "Answer copied to clipboard.");
      window.setTimeout(() => setCopiedMessageId(null), 2000);
    } catch {
      toast.error(language === "fa" ? "کپی کردن پاسخ ناموفق بود." : "Could not copy the answer.");
    }
  };

  const startEditing = (message: MessageType) => {
    setEditingMessageId(message.id);
    setEditingValue(message.content);
  };

  const cancelEditing = () => {
    setEditingMessageId(null);
    setEditingValue("");
  };

  const saveEditing = async (message: MessageType) => {
    const content = editingValue.trim();
    if (!content || !onEditMessage) return;
    cancelEditing();
    await onEditMessage(message, content);
  };

  const renderAttachments = (attachments?: FileAttachment[]) => {
    if (!attachments?.length) return null;
    return (
      <AttachmentGroup className="mb-3">
        {attachments.map((attachment) => (
          <Attachment key={attachment.id} size="sm" state="done" className="max-w-full">
            <AttachmentMedia variant="icon">
              <span className="text-[10px] font-bold">PDF</span>
            </AttachmentMedia>
            <AttachmentContent>
              <AttachmentTitle>{attachment.name}</AttachmentTitle>
              <AttachmentDescription>
                {((attachment.size || 0) / 1_000_000).toFixed(1)} MB
              </AttachmentDescription>
            </AttachmentContent>
          </Attachment>
        ))}
      </AttachmentGroup>
    );
  };

  return (
    <div
      data-slot="chat-thread"
      className={cn("relative flex h-full w-full flex-col overflow-hidden", className)}
      {...props}
    >
      <MessageScrollerProvider autoScroll isStreaming={isStreaming}>
        <ThreadScrollSync messagesCount={messages.length} isStreaming={isStreaming} />
        <MessageScroller className="h-full">
          <MessageScrollerViewport className="p-2.5 sm:p-4 md:p-6">
            <MessageScrollerContent className="mx-auto max-w-4xl w-full gap-5 sm:gap-8 pt-2 pb-44 sm:pb-52 md:pb-60">
              {messages.map((message) => {
                const isUser = message.role === "user";

                if (isUser) {
                  return (
                    <MessageScrollerItem
                      key={message.id}
                      messageId={message.id}
                      scrollAnchor={true}
                    >
                      <div
                        onClick={() => {
                          const msgIdx = messages.findIndex((m) => m.id === message.id);
                          const nextAssistant = messages.slice(msgIdx + 1).find((m) => m.role === "assistant");
                          onSelectMessage?.(nextAssistant ? nextAssistant.id : message.id);
                        }}
                        onMouseEnter={() => {
                          const msgIdx = messages.findIndex((m) => m.id === message.id);
                          const nextAssistant = messages.slice(msgIdx + 1).find((m) => m.role === "assistant");
                          onHoverMessage?.(nextAssistant ? nextAssistant.id : message.id);
                        }}
                        onMouseLeave={() => onHoverMessage?.(null)}
                        className={cn(
                          "flex flex-col gap-1.5 sm:gap-2 max-w-[92%] sm:max-w-[85%] cursor-pointer",
                          language === "en" ? "items-end ms-auto" : "items-start"
                        )}
                      >
                        <div className="flex items-center gap-2 sm:gap-3 mb-0.5 px-2">
                          <Image
                            src="/profile.png"
                            alt="User"
                            width={28}
                            height={28}
                            className="w-6 h-6 sm:w-8 sm:h-8 rounded-full object-cover shadow-sm"
                          />
                          <span className="text-[13px] sm:text-[14px] text-on-surface-variant/80 decorative-font font-medium">
                            {language === "fa" ? "شما" : "You"}
                          </span>
                        </div>
                        {editingMessageId === message.id ? (
                          <div className="w-full rounded-2xl sm:rounded-3xl border border-brand-cyan/30 bg-surface-raised/80 p-3.5 sm:p-5 shadow-sm">
                            {renderAttachments(message.attachments)}
                            <textarea
                              value={editingValue}
                              onChange={(event) => setEditingValue(event.target.value)}
                              dir={editingValue.trim() ? "auto" : language === "fa" ? "rtl" : "ltr"}
                              className="min-h-24 w-full resize-y rounded-xl border border-border/60 bg-surface-container-low/60 p-3 text-sm text-foreground text-start outline-none focus-visible:ring-2 focus-visible:ring-brand-cyan/40"
                              aria-label={t.actions.edit}
                            />
                            <div className="mt-3 flex items-center justify-end gap-2">
                              <button
                                type="button"
                                onClick={cancelEditing}
                                className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs text-muted-foreground transition-all duration-200 hover:bg-surface-active hover:text-foreground active:scale-95 cursor-pointer"
                              >
                                <X className="size-3.5" />
                                {t.actions.cancelEdit}
                              </button>
                              <button
                                type="button"
                                onClick={() => saveEditing(message)}
                                disabled={!editingValue.trim()}
                                className="inline-flex items-center gap-1.5 rounded-lg bg-brand-cyan px-2.5 py-1.5 text-xs font-semibold text-canvas transition-all duration-200 hover:opacity-90 active:scale-95 disabled:cursor-not-allowed disabled:opacity-50 cursor-pointer"
                              >
                                <Check className="size-3.5" />
                                {t.actions.saveEdit}
                              </button>
                            </div>
                          </div>
                        ) : (
                          <>
                            <div className="bg-surface-raised/80 backdrop-blur-sm rounded-2xl sm:rounded-3xl p-3.5 sm:p-5 shadow-sm border border-border/30 w-full text-start">
                              {renderAttachments(message.attachments)}
                              <DirectionBoundary language={language} content={message.content}>
                                <MarkdownContent
                                  content={message.content}
                                  citations={message.citations}
                                  onCitationClick={onCitationClick}
                                />
                              </DirectionBoundary>
                            </div>
                            {onEditMessage && (
                              <div className="flex items-center gap-1 ps-2">
                                <TooltipProvider delayDuration={150}>
                                  <Tooltip>
                                    <TooltipTrigger asChild>
                                      <button
                                        type="button"
                                        onClick={() => startEditing(message)}
                                        disabled={pendingEditMessageId !== null && pendingEditMessageId !== undefined}
                                        className="inline-flex size-6 sm:size-7 items-center justify-center rounded-lg text-muted-foreground transition-all duration-200 hover:bg-surface-active hover:text-foreground active:scale-95 cursor-pointer disabled:cursor-not-allowed disabled:opacity-40"
                                        aria-label={t.actions.edit}
                                      >
                                        <Pencil className="size-3.5" />
                                      </button>
                                    </TooltipTrigger>
                                    <TooltipContent side="top" sideOffset={4} className="text-xs">
                                      {t.actions.edit}
                                    </TooltipContent>
                                  </Tooltip>
                                </TooltipProvider>
                              </div>
                            )}
                          </>
                        )}
                        {pendingEditMessageId === message.id && (
                          <div
                            className="flex items-center gap-1.5 px-2 text-[11px] text-on-surface-variant"
                            role="status"
                            aria-live="polite"
                          >
                            <Loader2 className="size-3 animate-spin text-brand-cyan" />
                            <span>{language === "fa" ? "در حال آماده‌سازی ویرایش…" : "Applying edit…"}</span>
                          </div>
                        )}
                      </div>
                    </MessageScrollerItem>
                  );
                }

                return (
                  <MessageScrollerItem
                    key={message.id}
                    messageId={message.id}
                  >
                    <div className="flex flex-col items-start gap-1.5 sm:gap-2 w-full">
                      {/* Assistant Header (Left-aligned) */}
                      <div className="w-full flex justify-start me-auto mb-0.5" dir="ltr">
                        <div className="flex flex-row items-center gap-2">
                          <div className="size-6 sm:size-7 flex items-center justify-center shrink-0">
                            <BrandLogoIcon className="size-5 sm:size-6" />
                          </div>
                          <span className="text-[14px] sm:text-[15px] font-bold bg-clip-text text-transparent bg-gradient-to-r from-[#6EF0C2] to-[#31C8ED]">
                            Sovereign AI
                          </span>
                        </div>
                      </div>

                      {/* Assistant Bubble */}
                      <div
                        onClick={() => onSelectMessage?.(message.id)}
                        onMouseEnter={() => onHoverMessage?.(message.id)}
                        onMouseLeave={() => onHoverMessage?.(null)}
                        className="bg-surface-container-lowest/30 backdrop-blur-md rounded-2xl sm:rounded-3xl rounded-tl-md p-4 sm:p-6 md:p-8 w-full shadow-xl shadow-black/10 text-start relative border border-border/30 transition-all hover:border-[#31C8ED]/30 cursor-pointer"
                      >
                        {/* Completed Model Thinking Accordion */}
                        {message.reasoningContent && (
                          <details
                            className="w-full mb-3.5 overflow-hidden rounded-2xl border border-brand-cyan/25 bg-brand-cyan/5 text-start group/think"
                          >
                            <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-2.5 text-xs font-semibold text-brand-cyan marker:hidden [&::-webkit-details-marker]:hidden hover:bg-brand-cyan/10 transition-colors">
                              <span className="decorative-font flex items-center gap-1.5">
                                <Sparkles className="size-3.5" />
                                {language === "fa" ? "روند تفکر و استدلال مدل (Chain of Thought)" : "Model reasoning process"}
                              </span>
                              <ChevronDown className="size-3.5 shrink-0 transition-transform group-open/think:rotate-180" />
                            </summary>
                            <div className="max-h-72 overflow-y-auto overscroll-contain border-t border-brand-cyan/15 px-4 py-3 text-xs text-on-surface-variant/90 leading-relaxed font-sans">
                              <DirectionBoundary language={language} content={message.reasoningContent}>
                                <MarkdownContent content={message.reasoningContent} />
                              </DirectionBoundary>
                            </div>
                          </details>
                        )}

                        <DirectionBoundary language={language} content={message.content}>
                          <MarkdownContent
                            content={message.content}
                            citations={message.citations}
                            onCitationClick={(citation) => {
                              onCitationClick?.(citation);
                              setSelectedCitation(citation);
                            }}
                          />
                        </DirectionBoundary>

                        {message.content && message.status === "complete" && (
                          <div className="flex items-center justify-start gap-1 sm:gap-1.5 mt-3 sm:mt-4 pt-2 sm:pt-3 border-t border-border/20">
                            <TooltipProvider delayDuration={150}>
                              {onBranchMessage && (
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <button
                                      type="button"
                                      onClick={async () => {
                                        setBranchingMessageId(message.id);
                                        try {
                                          await onBranchMessage(message);
                                        } finally {
                                          setBranchingMessageId(null);
                                        }
                                      }}
                                      disabled={branchingMessageId === message.id}
                                      className="group/branch size-7 sm:size-8 rounded-lg flex items-center justify-center text-on-surface-variant/70 hover:text-brand-mint hover:bg-brand-mint/10 border border-transparent hover:border-brand-mint/30 active:scale-90 transition-all duration-300 cursor-pointer disabled:opacity-50"
                                      aria-label={t.actions.branch}
                                    >
                                      {branchingMessageId === message.id ? (
                                        <Loader2 className="size-3.5 sm:size-4 animate-spin text-brand-mint" />
                                      ) : (
                                        <GitBranch className="size-3.5 sm:size-4 transition-transform duration-300 ease-[cubic-bezier(0.34,1.56,0.64,1)] group-hover/branch:scale-125 group-hover/branch:rotate-12 group-active/branch:rotate-45" />
                                      )}
                                    </button>
                                  </TooltipTrigger>
                                  <TooltipContent side="top" sideOffset={6} className="text-xs">
                                    {t.actions.branch}
                                  </TooltipContent>
                                </Tooltip>
                              )}

                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <button
                                    type="button"
                                    onClick={() => copyMessage(message.id, message.content)}
                                    className="size-7 sm:size-8 rounded-lg flex items-center justify-center text-on-surface-variant/70 hover:text-on-surface hover:bg-surface-raised/70 active:scale-95 transition-all cursor-pointer"
                                    aria-label={
                                      copiedMessageId === message.id
                                        ? language === "fa"
                                          ? "کپی شد"
                                          : "Answer copied"
                                        : language === "fa"
                                          ? "کپی پاسخ"
                                          : "Copy answer"
                                    }
                                  >
                                    {copiedMessageId === message.id ? (
                                      <Check className="size-3.5 sm:size-4 text-brand-mint" />
                                    ) : (
                                      <Copy className="size-3.5 sm:size-4" />
                                    )}
                                  </button>
                                </TooltipTrigger>
                                <TooltipContent side="top" sideOffset={6} className="text-xs">
                                  {copiedMessageId === message.id
                                    ? language === "fa"
                                      ? "کپی شد"
                                      : "Copied"
                                    : language === "fa"
                                      ? "کپی پاسخ"
                                      : "Copy answer"}
                                </TooltipContent>
                              </Tooltip>
                            </TooltipProvider>
                          </div>
                        )}

                        {message.status === "failed" && (
                          <ErrorAlert
                            description={t.errors.upstreamUnavailable}
                            retryable={true}
                            onRetry={onRetry}
                            language={language}
                          />
                        )}

                        {message.status === "interrupted" && (
                          <div className="text-[11px] text-muted-foreground italic mt-3 pt-2 border-t border-border/20">
                            {t.errors.interrupted}
                          </div>
                        )}
                      </div>
                    </div>
                  </MessageScrollerItem>
                );
              })}

              {/* Streaming state */}
              {isStreaming && (
                <MessageScrollerItem messageId="streaming-item">
                  <div className="flex flex-col items-start gap-1.5 sm:gap-2 w-full">
                    {/* Assistant Header (Left-aligned) */}
                    <div className="w-full flex justify-start me-auto mb-0.5" dir="ltr">
                      <div className="flex flex-row items-center gap-2">
                        <div className="size-6 sm:size-7 flex items-center justify-center shrink-0">
                          <BrandLogoIcon className="size-5 sm:size-6 animate-pulse" />
                        </div>
                        <span className="text-[14px] sm:text-[15px] font-bold bg-clip-text text-transparent bg-gradient-to-r from-[#6EF0C2] to-[#31C8ED]">
                          Sovereign AI
                        </span>
                      </div>
                    </div>

                    {/* Thinking State Card */}
                    <WorkflowProgress
                      workflow={activeWorkflow}
                      stage={streamingStage}
                      label={streamingLabel}
                      language={language}
                    />

                    {toolCalls.map((toolCall) => (
                      <Marker key={`${toolCall.requestId}-${toolCall.name}`} variant="border" className="rounded-xl border border-brand-cyan/20 bg-brand-cyan/5 px-3 text-start">
                        <MarkerIcon className="text-brand-cyan">
                          {toolCall.status === "started" ? (
                            <Loader2 className="animate-spin" />
                          ) : toolCall.status === "completed" ? (
                            <Check />
                          ) : (
                            <X />
                          )}
                        </MarkerIcon>
                        <MarkerContent className="flex-1 justify-between gap-3">
                          <span className="decorative-font">{toolCall.label}</span>
                          {toolCall.summary && <span className="text-[11px] text-muted-foreground">{toolCall.summary}</span>}
                        </MarkerContent>
                      </Marker>
                    ))}

                    {streamingThinkingText ? (
                      <details
                        open={thinkingOpen}
                        onToggle={(event) => setThinkingOpen(event.currentTarget.open)}
                        className="w-full overflow-hidden rounded-2xl border border-brand-cyan/20 bg-brand-cyan/5 text-start"
                      >
                        <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 text-sm text-brand-cyan marker:hidden [&::-webkit-details-marker]:hidden">
                          <span className="decorative-font">
                            {language === "fa" ? "روند تفکر مدل" : "Model thinking"}
                          </span>
                          <ChevronDown className="size-4 shrink-0" />
                        </summary>
                        <div className="max-h-72 overflow-y-auto overscroll-contain border-t border-brand-cyan/15 px-4 py-3 sm:max-h-96">
                          <DirectionBoundary language={language} content={streamingThinkingText}>
                            <MarkdownContent content={streamingThinkingText} />
                          </DirectionBoundary>
                        </div>
                      </details>
                    ) : null}

                    {/* Streaming Text Bubble */}
                    {streamingText ? (
                      <div className="bg-surface-container-lowest/30 backdrop-blur-md rounded-2xl sm:rounded-3xl rounded-tl-md p-4 sm:p-6 md:p-8 w-full shadow-xl shadow-black/10 text-start relative border border-border/30">
                        <DirectionBoundary language={language} content={streamingText}>
                          <MarkdownContent content={streamingText} />
                        </DirectionBoundary>
                      </div>
                    ) : (
                      !streamingLabel && <MessageSkeleton />
                    )}
                  </div>
                </MessageScrollerItem>
              )}

              {/* Bottom Breathing Space Buffer */}
              <div className="h-12 sm:h-20 w-full shrink-0 pointer-events-none" aria-hidden="true" />
            </MessageScrollerContent>
          </MessageScrollerViewport>
          <MessageScrollerButton label={t.actions.jumpToBottom} />
        </MessageScroller>
      </MessageScrollerProvider>

      {/* Citation Inspector Modal */}
      <CitationDialog
        citation={selectedCitation}
        open={!!selectedCitation}
        onOpenChange={(open) => !open && setSelectedCitation(null)}
        language={language}
      />
    </div>
  );
}
