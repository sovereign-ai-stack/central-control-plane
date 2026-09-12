"use client";

import * as React from "react";
import Image from "next/image";
import { ArrowUpRight, BookOpen, GitBranch, Layers, Menu, Plus, Reply, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { Drawer, DrawerContent, DrawerTitle } from "@/components/ui/drawer";
import { BrandLogoIcon } from "@/components/ui/brand-logo";
import { ChatRail } from "./chat-rail";
import { SourceList } from "../sources/source-list";
import { Thread } from "../chat/thread";
import { Composer } from "../chat/composer";
// import { FloatingVoiceWidget } from "../chat/floating-voice-widget";
import { EmptyChat } from "../chat/empty-chat";
import { ShareDialog } from "../chat/share-dialog";
import { AccountPanel } from "../account/account-panel";
import { DeleteChatDialog } from "../chat/delete-chat";
import { CitationDialog } from "../chat/citation-dialog";
import { useChat } from "@/hooks/use-chat";
import { useTranslation } from "@/lib/locale";
import type { AuthUser, Citation, Language, Message } from "@/lib/types";

export interface WorkspaceProps {
  initialLanguage?: Language;
  user: AuthUser;
  onLogout: () => void;
}

export function Workspace({ initialLanguage = "fa", user, onLogout }: WorkspaceProps) {
  const {
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
    isCreatingConversation,
    pendingEditMessageId,
    selectConversation,
    startNewChat,
    renameConversation,
    deleteConversation,
    sendMessage,
    uploadPdf,
    branchConversation,
    editMessage,
    createShareLink,
    cancelStreaming,
    retryLastMessage,
    addVoiceMessages,
    useRag,
    setUseRag,
  } = useChat(initialLanguage);

  const t = useTranslation(language);

  const [leftSidebarOpen, setLeftSidebarOpen] = React.useState(false);
  const [rightSidebarCollapsed, setRightSidebarCollapsed] = React.useState(false);
  const [mobileHistoryOpen, setMobileHistoryOpen] = React.useState(false);
  const [mobileSourcesOpen, setMobileSourcesOpen] = React.useState(false);
  const [accountOpen, setAccountOpen] = React.useState(false);
  const [deleteTargetId, setDeleteTargetId] = React.useState<string | null>(null);
  const [voiceWidgetOpen, setVoiceWidgetOpen] = React.useState(false);
  const [shareDialogOpen, setShareDialogOpen] = React.useState(false);
  const [shareUrl, setShareUrl] = React.useState<string | null>(null);
  const [shareLoading, setShareLoading] = React.useState(false);
  const [selectedCitation, setSelectedCitation] = React.useState<Citation | null>(null);
  const [hoveredMessageId, setHoveredMessageId] = React.useState<string | null>(null);
  const [selectedMessageId, setSelectedMessageId] = React.useState<string | null>(null);
  const [replyingBranchMessage, setReplyingBranchMessage] = React.useState<Message | null>(null);
  const [dismissedBranchConvId, setDismissedBranchConvId] = React.useState<string | null>(null);

  const parentConv = React.useMemo(() => {
    if (!activeConversation) return null;
    if (activeConversation.parentConversationId) {
      return conversations.find((c) => c.id === activeConversation.parentConversationId) || null;
    }
    if (activeConversation.title?.includes("(شاخه)") || activeConversation.title?.includes("(Branch)")) {
      const base = activeConversation.title.replace(" (شاخه)", "").replace(" (Branch)", "").trim();
      return conversations.find((c) => c.id !== activeConversation.id && c.title.trim().startsWith(base)) || null;
    }
    return null;
  }, [activeConversation, conversations]);

  const isBranchConversation = Boolean(
    activeConversation &&
    (activeConversation.parentConversationId ||
      activeConversation.title?.includes("(شاخه)") ||
      activeConversation.title?.includes("(Branch)"))
  );

  const activeHighlightedMessageId = hoveredMessageId || selectedMessageId;

  const prevSourcesCountRef = React.useRef(0);
  const starterRequestRef = React.useRef(false);
  React.useEffect(() => {
    const totalSources = allCitations.length + (activeConversation?.context?.length || 0);
    if (useRag && totalSources > 0 && prevSourcesCountRef.current === 0) {
      setLeftSidebarOpen(true);
    } else if (!useRag || (totalSources === 0 && !activeConversationId)) {
      setLeftSidebarOpen(false);
    }
    prevSourcesCountRef.current = totalSources;
  }, [allCitations.length, activeConversation?.context, activeConversationId, useRag]);

  const handleCitationClick = (citation?: Citation) => {
    if (citation) {
      setSelectedCitation(citation);
    }
    setLeftSidebarOpen(true);
    setMobileSourcesOpen(true);
  };

  const handleSelectMessage = (messageId: string) => {
    const targetMsg = (activeConversation?.messages || []).find((m) => m.id === messageId);
    if (targetMsg?.citations && targetMsg.citations.length > 0) {
      setSelectedMessageId(messageId);
      setLeftSidebarOpen(true);
    }
  };

  const handleToggleLanguage = () => {
    setLanguage(language === "fa" ? "en" : "fa");
  };

  const handleDeleteConfirm = () => {
    if (deleteTargetId) {
      deleteConversation(deleteTargetId);
      setDeleteTargetId(null);
    }
  };

  const handleSelectStarter = (prompt: string) => {
    if (starterRequestRef.current || isCreatingConversation || isStreaming) return;

    starterRequestRef.current = true;
    void sendMessage(prompt).finally(() => {
      starterRequestRef.current = false;
    });
  };

  const handleNewChat = () => {
    setReplyingBranchMessage(null);
    startNewChat();
  };

  const handleShare = async (conversationId: string) => {
    setShareLoading(true);
    const url = await createShareLink(conversationId);
    setShareLoading(false);
    if (url) {
      setShareUrl(url);
      setShareDialogOpen(true);
    }
  };

  const messages = activeConversation?.messages || [];
  const hasMessages = messages.length > 0;

  return (
    <div
      dir={language === "fa" ? "rtl" : "ltr"}
      className="bg-canvas text-on-surface flex flex-col h-[100dvh] w-full overflow-hidden font-sans select-none"
    >
      <div className="flex flex-1 h-full overflow-hidden">
        {/* 1. CHAT HISTORY RAIL (Physical Right in RTL, Physical Left in LTR) */}
        <ChatRail
          conversations={conversations}
          activeConversationId={activeConversationId || undefined}
          onSelectConversation={(id) => {
            setReplyingBranchMessage(null);
            selectConversation(id);
          }}
          onNewChat={handleNewChat}
          onShareConversation={handleShare}
          onRenameConversation={renameConversation}
          onDeleteConversation={(id) => setDeleteTargetId(id)}
          onOpenAccount={() => setAccountOpen(true)}
          onToggleLanguage={handleToggleLanguage}
          user={user}
          language={language}
          isSharing={shareLoading}
          collapsed={rightSidebarCollapsed}
          onToggleCollapse={() => setRightSidebarCollapsed(!rightSidebarCollapsed)}
          className="hidden md:flex"
        />

        {/* 2. MAIN CONTENT AREA (flex-row-reverse docks Sources on Left in RTL, and Right in LTR) */}
        <main className="flex-1 flex overflow-hidden bg-canvas relative flex-row-reverse transition-all duration-500 ease-[cubic-bezier(0.4,0,0.2,1)]">
          {/* Official Sources & Context Sidebar (Docks Right in EN, Left in FA) */}
          <aside
            id="leftSidebar"
            className={cn(
              "bg-surface-container/30 backdrop-blur-md hidden md:flex flex-col h-[calc(100vh-1.5rem)] shrink-0 shadow-lg shadow-black/30 rounded-3xl m-3 relative transition-[width,padding,margin,opacity] duration-500 ease-[cubic-bezier(0.4,0,0.2,1)] border border-border/20 overflow-hidden",
              leftSidebarOpen ? "w-80" : "w-0 p-0 m-0 border-none opacity-0 pointer-events-none"
            )}
          >
            {leftSidebarOpen && (
              <SourceList
                citations={allCitations}
                contextFacts={activeConversation?.context || []}
                language={language}
                highlightedMessageId={activeHighlightedMessageId}
                onClose={() => setLeftSidebarOpen(false)}
                onSelectCitation={(citation) => setSelectedCitation(citation)}
              />
            )}
          </aside>

          {/* Top Desktop Toolbar Toggle Button (only when RAG is enabled and sidebar is closed) */}
          {useRag && (
            <header className="absolute top-4 end-4 z-20 hidden md:flex items-center pointer-events-none animate-in fade-in zoom-in-95 duration-300">
              <div className="pointer-events-auto flex items-center gap-2">
                {!leftSidebarOpen && (
                  <button
                    type="button"
                    id="toggleLeftSidebarBtn"
                    onClick={() => setLeftSidebarOpen(true)}
                    className="pointer-events-auto text-on-surface-variant hover:text-on-surface bg-surface-container/40 backdrop-blur-md p-2.5 rounded-xl transition-all duration-300 shadow-sm border border-border/30 hover:bg-surface-raised cursor-pointer flex items-center gap-2 text-xs font-semibold hover:border-brand-cyan/40 hover:shadow-brand-cyan/10 active:scale-95"
                    title={t.sources.title}
                    aria-label="Open sources sidebar"
                  >
                    <Layers className="size-4 text-brand-cyan shrink-0 transition-transform duration-300 ease-[cubic-bezier(0.34,1.56,0.64,1)] group-hover:scale-110" />
                    <span>{t.sources.title}</span>
                  </button>
                )}
              </div>
            </header>
          )}

          {/* Mobile & Tablet Header Bar */}
          <header className="absolute top-0 inset-x-0 h-14 flex items-center justify-between border-b border-border/80 bg-surface/90 px-3 sm:px-4 md:hidden backdrop-blur-md z-20">
            <button
              type="button"
              data-testid="mobile-history-toggle"
              onClick={() => setMobileHistoryOpen(true)}
              className="p-2 text-on-surface-variant hover:text-on-surface rounded-xl hover:bg-surface-raised transition-colors cursor-pointer"
              aria-label="Toggle history"
            >
              <Menu className="size-5 text-brand-cyan" />
            </button>

            <div className="flex items-center gap-2">
              <BrandLogoIcon className="size-5" />
              <span className="text-xs font-bold text-foreground">{t.appName}</span>
            </div>

            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={handleNewChat}
                className="p-2 text-on-surface-variant hover:text-on-surface rounded-xl hover:bg-surface-raised transition-colors cursor-pointer"
                aria-label={t.newChat}
                title={t.newChat}
              >
                <Plus className="size-5 text-brand-cyan" />
              </button>

              {useRag && (
                <button
                  type="button"
                  data-testid="mobile-sources-toggle"
                  onClick={() => setMobileSourcesOpen(true)}
                  className="p-2 text-on-surface-variant hover:text-on-surface rounded-xl hover:bg-surface-raised transition-colors cursor-pointer"
                  aria-label="Toggle sources"
                >
                  <BookOpen className="size-5 text-brand-cyan" />
                </button>
              )}
            </div>
          </header>

          {/* 3. CENTER CONVERSATION PANE */}
          <div className="flex-1 flex flex-col h-full relative w-full pt-14 md:pt-2 overflow-hidden">
            {/* Branch Header Navigation Bar when active conversation is a branch */}
            {isBranchConversation && dismissedBranchConvId !== activeConversation?.id && (
              <div className="mx-auto my-1.5 flex items-center gap-2 sm:gap-2.5 rounded-full border border-brand-mint/30 bg-surface-container-high/90 px-3.5 py-1 text-xs shadow-md backdrop-blur-md animate-in fade-in slide-in-from-top-2 duration-200 shrink-0 z-10">
                <div className="flex items-center gap-1.5 text-brand-mint font-medium">
                  <GitBranch className="size-3.5 shrink-0" />
                  <span>{language === "fa" ? "منشعب از گفتگوی پیشین" : "Branched from previous chat"}</span>
                </div>

                {parentConv && (
                  <>
                    <span className="text-border/60">|</span>
                    <button
                      type="button"
                      onClick={() => selectConversation(parentConv.id)}
                      className="inline-flex items-center gap-1 text-[11.5px] font-semibold text-brand-mint hover:text-white bg-brand-mint/15 hover:bg-brand-mint/30 px-2.5 py-0.5 rounded-full transition-all cursor-pointer hover:scale-105 active:scale-95"
                      title={language === "fa" ? `بازگشت به: ${parentConv.title}` : `Return to: ${parentConv.title}`}
                    >
                      <span>{language === "fa" ? "بازگشت به گفتگوی اصلی" : "Back to parent chat"}</span>
                      <ArrowUpRight className="size-3 shrink-0" />
                    </button>
                  </>
                )}

                <button
                  type="button"
                  onClick={() => activeConversation && setDismissedBranchConvId(activeConversation.id)}
                  className="text-on-surface-variant hover:text-on-surface p-0.5 rounded-full hover:bg-surface-raised transition-colors cursor-pointer"
                  title={language === "fa" ? "بستن این پیام" : "Dismiss"}
                  aria-label="Dismiss branch banner"
                >
                  <X className="size-3" />
                </button>
              </div>
            )}

            {/* Conversation Thread or Welcome Empty State */}
            <div key={language} className="flex-1 overflow-hidden flex flex-col relative lang-view-transition">
              {hasMessages ? (
                <Thread
                  messages={messages}
                  isStreaming={isStreaming}
                  streamingText={streamingText}
                  streamingThinkingText={streamingThinkingText}
                  streamingStage={streamingStage}
                  streamingLabel={streamingLabel}
                  toolCalls={streamingTools}
                  activeWorkflow={activeWorkflow}
                  language={language}
                  onCitationClick={handleCitationClick}
                  onHoverMessage={setHoveredMessageId}
                  onSelectMessage={handleSelectMessage}
                  onRetry={retryLastMessage}
                  onEditMessage={editMessage}
                  pendingEditMessageId={pendingEditMessageId}
                  onBranchMessage={(message) => {
                    setReplyingBranchMessage(message);
                    setTimeout(() => {
                      const textarea = document.querySelector('textarea');
                      if (textarea) {
                        textarea.focus();
                        textarea.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                      }
                    }, 100);
                  }}
                  className="flex-1"
                />
              ) : (
                <EmptyChat
                  onSelectStarter={handleSelectStarter}
                  language={language}
                  disabled={isCreatingConversation || isStreaming}
                  className="flex-1"
                />
              )}
            </div>

            {/* Floating Bottom Composer */}
            <div className="absolute bottom-0 w-full bg-gradient-to-t from-canvas via-canvas/95 to-transparent pt-6 sm:pt-12 pb-2 sm:pb-4 px-2 sm:px-4 flex justify-center z-10 pointer-events-none">
              <div className="w-full max-w-3xl pointer-events-auto">
                {replyingBranchMessage && (
                  <div className="mb-2 flex items-center justify-between rounded-2xl border border-brand-cyan/30 bg-surface-container-high/90 backdrop-blur-md px-3.5 py-2 text-xs shadow-lg animate-in fade-in slide-in-from-bottom-2 duration-200">
                    <div className="flex items-center gap-2 overflow-hidden">
                      <div className="flex size-5 items-center justify-center rounded-lg bg-brand-cyan/15 text-brand-cyan shrink-0">
                        <Reply className="size-3.5" />
                      </div>
                      <span className="font-bold text-brand-cyan shrink-0 decorative-font">
                        {language === "fa" ? "در پاسخ به:" : "In reply to:"}
                      </span>
                      <span className="truncate text-on-surface-variant text-[11.5px] max-w-sm">
                        {replyingBranchMessage.content.slice(0, 80)}...
                      </span>
                    </div>
                    <button
                      type="button"
                      onClick={() => setReplyingBranchMessage(null)}
                      className="text-on-surface-variant/70 hover:text-on-surface p-1 rounded-md hover:bg-surface-active transition-colors shrink-0 ms-2 cursor-pointer"
                      title={language === "fa" ? "انصراف از پاسخ" : "Cancel reply"}
                    >
                      <X className="size-3.5" />
                    </button>
                  </div>
                )}
                {errorMessage && (
                  <div
                    role="alert"
                    aria-live="assertive"
                    className="mb-2 rounded-xl border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive shadow-lg"
                  >
                    {errorMessage}
                  </div>
                )}
                <Composer
                  onSubmit={(message, attachments = [], explicitUseRag) => {
                    const replyTarget = replyingBranchMessage;
                    setReplyingBranchMessage(null);
                    sendMessage(message, attachments, undefined, explicitUseRag, replyTarget);
                  }}
                  onUploadPdf={uploadPdf}
                  onCancel={cancelStreaming}
                  onOpenVoiceMode={() => setVoiceWidgetOpen(true)}
                  isStreaming={isStreaming}
                  language={language}
                  useRag={useRag}
                  onToggleRag={setUseRag}
                />
              </div>
            </div>
          </div>
        </main>
      </div>

      {/* <FloatingVoiceWidget
        isOpen={voiceWidgetOpen}
        onClose={() => setVoiceWidgetOpen(false)}
        language={language}
        conversationId={activeConversationId}
        onMessageAdded={addVoiceMessages}
      /> */}

      <ShareDialog
        open={shareDialogOpen}
        onOpenChange={setShareDialogOpen}
        url={shareUrl}
        language={language}
      />

      {/* Mobile History Drawer / Sheet */}
      <Sheet open={mobileHistoryOpen} onOpenChange={setMobileHistoryOpen}>
        <SheetContent
          side={language === "fa" ? "right" : "left"}
          className="p-0 border-border bg-surface text-foreground w-[85vw] max-w-xs"
        >
          <SheetTitle className="sr-only">Conversation History</SheetTitle>
          <ChatRail
            conversations={conversations}
            activeConversationId={activeConversationId || undefined}
            onSelectConversation={(id) => {
              selectConversation(id);
              setMobileHistoryOpen(false);
            }}
            onNewChat={() => {
              handleNewChat();
              setMobileHistoryOpen(false);
            }}
            onShareConversation={handleShare}
            onRenameConversation={renameConversation}
            onDeleteConversation={(id) => setDeleteTargetId(id)}
            onOpenAccount={() => {
              setMobileHistoryOpen(false);
              setAccountOpen(true);
            }}
            onToggleLanguage={handleToggleLanguage}
            user={user}
            language={language}
            isSharing={shareLoading}
            className="flex w-full h-full m-0 rounded-none border-0"
          />
        </SheetContent>
      </Sheet>

      {/* Mobile Sources Drawer */}
      <Drawer open={mobileSourcesOpen} onOpenChange={setMobileSourcesOpen}>
        <DrawerContent className="border-border bg-surface-raised max-h-[85dvh]">
          <DrawerTitle className="sr-only">Official Sources</DrawerTitle>
          <div className="p-3 sm:p-4 overflow-y-auto max-h-[75dvh]">
            <SourceList
              citations={allCitations}
              contextFacts={activeConversation?.context || []}
              language={language}
              highlightedMessageId={activeHighlightedMessageId}
              onClose={() => setMobileSourcesOpen(false)}
              onSelectCitation={(citation) => setSelectedCitation(citation)}
            />
          </div>
        </DrawerContent>
      </Drawer>

      {/* Authenticated Account Panel */}
      <AccountPanel
        isOpen={accountOpen}
        onClose={() => setAccountOpen(false)}
        language={language}
        onLanguageChange={setLanguage}
        user={user}
        onLogout={onLogout}
      />

      {/* Delete Confirmation Dialog */}
      <DeleteChatDialog
        open={!!deleteTargetId}
        onOpenChange={(open) => !open && setDeleteTargetId(null)}
        onConfirm={handleDeleteConfirm}
        language={language}
      />

      {/* RAG Citation Inspector Modal */}
      <CitationDialog
        citation={selectedCitation}
        open={!!selectedCitation}
        onOpenChange={(open) => !open && setSelectedCitation(null)}
        language={language}
      />
    </div>
  );
}
