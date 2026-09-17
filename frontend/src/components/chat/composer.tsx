"use client";

import * as React from "react";
import {
  ArrowUp,
  FileText,
  Loader2,
  Mic,
  MicOff,
  Paperclip,
  Square,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { apiFetch } from "@/lib/api";
import { useTranslation } from "@/lib/locale";
import type { FileAttachment, Language } from "@/lib/types";
import { toast } from "sonner";
import {
  Attachment,
  AttachmentAction,
  AttachmentContent,
  AttachmentDescription,
  AttachmentGroup,
  AttachmentMedia,
  AttachmentTitle,
} from "@/components/ui/attachment";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

export function WaveformVoiceIcon({ className = "size-4" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="currentColor"
      className={className}
      xmlns="http://www.w3.org/2000/svg"
    >
      <rect x="3.5" y="8" width="2.5" height="8" rx="1.25" />
      <rect x="8.5" y="4" width="2.5" height="16" rx="1.25" />
      <rect x="13.5" y="6.5" width="2.5" height="11" rx="1.25" />
      <rect x="18.5" y="9" width="2.5" height="6" rx="1.25" />
    </svg>
  );
}

import { RagToggle } from "./rag-toggle";
import { useSpeechRecognition } from "@/hooks/use-speech-recognition";

export interface ComposerProps extends Omit<React.ComponentProps<"div">, "onSubmit"> {
  onSubmit: (message: string, attachments?: FileAttachment[], useRag?: boolean) => void;
  onUploadPdf?: (file: File) => Promise<FileAttachment | null>;
  onCancel?: () => void;
  onOpenVoiceMode?: () => void;
  isStreaming?: boolean;
  disabled?: boolean;
  language?: Language;
  initialValue?: string;
  useRag?: boolean;
  onToggleRag?: (enabled: boolean) => void;
}

export function Composer({
  onSubmit,
  onUploadPdf,
  onCancel,
  onOpenVoiceMode,
  isStreaming = false,
  disabled = false,
  language = "fa",
  initialValue = "",
  useRag,
  onToggleRag,
  className,
  ...props
}: ComposerProps) {
  const t = useTranslation(language);
  const [value, setValue] = React.useState(initialValue);
  const [internalUseRag, setInternalUseRag] = React.useState(true);
  const activeUseRag = useRag !== undefined ? useRag : internalUseRag;
  const handleToggleRag = onToggleRag || setInternalUseRag;
  const [isTranscribing, setIsTranscribing] = React.useState(false);
  const [isUploadingPdf, setIsUploadingPdf] = React.useState(false);
  const [isDragging, setIsDragging] = React.useState(false);
  const [attachments, setAttachments] = React.useState<FileAttachment[]>([]);
  const textareaRef = React.useRef<HTMLTextAreaElement | null>(null);
  const fileInputRef = React.useRef<HTMLInputElement | null>(null);
  const dragCounterRef = React.useRef(0);
  const baseTextRef = React.useRef("");
  
  const { isRecording: isRecordingDictation, start: startSpeech, stop: stopSpeech } = useSpeechRecognition({
    language,
    onResult: (transcript) => {
      setValue(baseTextRef.current + (baseTextRef.current ? " " : "") + transcript);
      textareaRef.current?.focus();
    },
    onEnd: () => {
      setIsTranscribing(false);
    }
  });

  React.useEffect(() => {
    if (initialValue) {
      setValue(initialValue);
      if (textareaRef.current) {
        textareaRef.current.focus();
      }
    }
  }, [initialValue]);

  React.useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    const nextHeight = Math.min(Math.max(el.scrollHeight, 28), 200);
    el.style.height = `${nextHeight}px`;
  }, [value]);

  const startDictation = () => {
    if (isStreaming || disabled || isTranscribing) return;
    baseTextRef.current = value;
    startSpeech();
  };

  const stopDictation = () => {
    stopSpeech();
  };

  const removeAttachment = (id: string) => {
    setAttachments((prev) => prev.filter((item) => item.id !== id));
  };

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (isRecordingDictation) {
      stopDictation();
      return;
    }
    const trimmed = value.trim();
    if ((!trimmed && attachments.length === 0) || isStreaming || disabled || isUploadingPdf) return;
    if (attachments.length > 0) {
      onSubmit(trimmed || t.composer.defaultAttachmentPrompt, attachments, activeUseRag);
    } else {
      onSubmit(trimmed, undefined, activeUseRag);
    }
    setValue("");
    setAttachments([]);
  };

  const processPdfFile = async (file: File) => {
    if (!onUploadPdf) return;

    if (attachments.length >= 3) {
      toast.error(language === "fa" ? "حداکثر ۳ فایل PDF مجاز است." : "You can attach up to 3 PDFs.");
      return;
    }

    if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
      toast.error(language === "fa" ? "فقط فایل PDF پشتیبانی می‌شود." : "Only PDF files are supported.");
      return;
    }
    if (file.size > 10_000_000) {
      toast.error(language === "fa" ? "حجم PDF باید کمتر از ۱۰ مگابایت باشد." : "PDFs must be smaller than 10 MB.");
      return;
    }

    setIsUploadingPdf(true);
    try {
      const attachment = await onUploadPdf(file);
      if (attachment) {
        setAttachments((prev) => [...prev, attachment].slice(0, 3));
      }
    } finally {
      setIsUploadingPdf(false);
    }
  };

  const handlePdfChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
    event.target.value = "";
    if (!files.length) return;
    await processPdfFile(files[0]);
  };

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounterRef.current += 1;
    if (e.dataTransfer?.items && e.dataTransfer.items.length > 0) {
      setIsDragging(true);
    }
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounterRef.current -= 1;
    if (dragCounterRef.current <= 0) {
      setIsDragging(false);
      dragCounterRef.current = 0;
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer) {
      e.dataTransfer.dropEffect = "copy";
    }
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    dragCounterRef.current = 0;

    if (disabled || isStreaming || isUploadingPdf) return;

    const droppedFiles = Array.from(e.dataTransfer.files || []);
    if (droppedFiles.length > 0) {
      await processPdfFile(droppedFiles[0]);
    }
  };

  const handlePaste = async (e: React.ClipboardEvent<HTMLTextAreaElement>) => {
    const items = Array.from(e.clipboardData?.items || []);
    const fileItems = items.filter((item) => item.kind === "file");
    if (fileItems.length > 0) {
      const files = fileItems
        .map((item) => item.getAsFile())
        .filter((file): file is File => file !== null);
      if (files.length > 0 && (files[0].type === "application/pdf" || files[0].name.toLowerCase().endsWith(".pdf"))) {
        e.preventDefault();
        await processPdfFile(files[0]);
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div
      data-slot="composer-container"
      className={cn("w-full max-w-3xl mx-auto px-2 sm:px-4 pb-4 sm:pb-6 pt-1 flex flex-col items-center", className)}
      onDragEnter={handleDragEnter}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      {...props}
    >
      {attachments.length > 0 && (
        <AttachmentGroup className="mb-2 w-full max-w-full px-1">
          {attachments.map((attachment) => (
            <Attachment key={attachment.id} size="sm" state="done" className="max-w-full">
              <AttachmentMedia variant="icon">
                <FileText />
              </AttachmentMedia>
              <AttachmentContent>
                <AttachmentTitle>{attachment.name}</AttachmentTitle>
                <AttachmentDescription>
                  PDF · {((attachment.size || 0) / 1_000_000).toFixed(1)} MB
                </AttachmentDescription>
              </AttachmentContent>
              <AttachmentAction
                onClick={() => setAttachments((prev) => prev.filter((item) => item.id !== attachment.id))}
                aria-label={language === "fa" ? `حذف ${attachment.name}` : `Remove ${attachment.name}`}
              >
                <X />
              </AttachmentAction>
            </Attachment>
          ))}
        </AttachmentGroup>
      )}

      <form onSubmit={handleSubmit} className="w-full">
        <input
          ref={fileInputRef}
          type="file"
          accept="application/pdf,.pdf"
          onChange={handlePdfChange}
          className="sr-only"
          tabIndex={-1}
        />
        <div
          dir="ltr"
          className={cn(
            "w-full bg-surface-container-highest/70 backdrop-blur-xl rounded-[26px] sm:rounded-[28px] px-3.5 sm:px-5 py-2 sm:py-2.5 transition-all shadow-xl shadow-black/30 flex items-end gap-2 sm:gap-3 relative border border-border/30",
            isDragging && "border-brand-cyan ring-2 ring-brand-cyan/40 bg-surface-container-highest/90",
            disabled && "opacity-60 cursor-not-allowed"
          )}
        >
          {/* Drag & Drop Visual Overlay */}
          {isDragging && (
            <div className="absolute inset-0 z-30 flex items-center justify-center rounded-[26px] sm:rounded-[28px] bg-surface-container-highest/95 backdrop-blur-md border-2 border-dashed border-brand-cyan pointer-events-none transition-all">
              <div className="flex items-center gap-2 text-brand-cyan font-medium text-xs sm:text-sm">
                <Paperclip className="size-4 animate-bounce" />
                <span>
                  {language === "fa"
                    ? "فایل PDF را برای پیوست اینجا رها کنید"
                    : "Drop PDF here to attach"}
                </span>
              </div>
            </div>
          )}

          {/* Left Action Group: RAG Knowledge Base Toggle */}
          <div className="flex items-center gap-1.5 shrink-0 pb-0.5 relative z-10">
            <RagToggle
              enabled={activeUseRag}
              onToggle={handleToggleRag}
              disabled={disabled || isStreaming}
              language={language}
            />
          </div>

          {/* Center: Textarea */}
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            onPaste={handlePaste}
            placeholder={
              isRecordingDictation
                ? language === "fa"
                  ? "در حال ضبط صدا… (صحبت کنید)"
                  : "Recording speech… (speak now)"
                : isTranscribing
                  ? language === "fa"
                    ? "در حال تبدیل گفتار به متن…"
                    : "Transcribing speech…"
                  : t.composer.placeholder
            }
            disabled={disabled || isTranscribing}
            maxLength={12000}
            rows={1}
            dir={value.trim() ? "auto" : language === "fa" ? "rtl" : "ltr"}
            className="flex-1 bg-transparent border-0 outline-none shadow-none focus:outline-none focus:ring-0 focus:border-0 focus-visible:ring-0 focus-visible:outline-none text-on-surface text-start text-[14px] sm:text-[15px] p-0 placeholder:text-on-surface-variant/50 decorative-font relative z-10 resize-none max-h-48 min-h-[28px] my-auto leading-relaxed overflow-y-auto no-scrollbar"
          />

          {/* Right Action Group: Send / Stop Action */}
          <div className="flex items-center gap-1.5 sm:gap-2 shrink-0 pb-0.5 relative z-10">
            <TooltipProvider delayDuration={150}>
              {isStreaming ? (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button
                      type="button"
                      onClick={onCancel}
                      className="size-8 sm:size-9 rounded-full text-canvas bg-destructive hover:opacity-90 transition-opacity shrink-0 flex items-center justify-center cursor-pointer shadow-md outline-none focus:outline-none"
                      aria-label={t.composer.cancel}
                    >
                      <Square className="size-3.5 fill-current" />
                    </button>
                  </TooltipTrigger>
                  <TooltipContent side="top" sideOffset={6} className="text-xs">
                    {t.composer.cancel}
                  </TooltipContent>
                </Tooltip>
              ) : isRecordingDictation || (!value.trim() && attachments.length === 0) ? (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button
                      type="button"
                      onClick={isRecordingDictation ? stopDictation : startDictation}
                      disabled={disabled || isTranscribing}
                      className={cn(
                        "size-8 sm:size-9 rounded-full shrink-0 flex items-center justify-center transition-all cursor-pointer outline-none focus:outline-none",
                        isRecordingDictation
                          ? "bg-red-500/10 text-red-500 hover:bg-red-500/20"
                          : "text-on-surface-variant hover:bg-surface-raised/80 hover:text-on-surface",
                        (disabled || isTranscribing) && "opacity-50 cursor-not-allowed"
                      )}
                      aria-label={isRecordingDictation ? "Stop recording" : "Start recording"}
                    >
                      {isRecordingDictation ? <MicOff className="size-4.5" /> : <Mic className="size-4.5" />}
                    </button>
                  </TooltipTrigger>
                  <TooltipContent side="top" sideOffset={6} className="text-xs">
                    {isRecordingDictation 
                      ? (language === "fa" ? "توقف ضبط" : "Stop recording") 
                      : (language === "fa" ? "تبدیل صدا به متن" : "Speech to text")}
                  </TooltipContent>
                </Tooltip>
              ) : (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button
                      type="submit"
                      disabled={disabled}
                      className={cn(
                        "size-8 sm:size-9 rounded-full shrink-0 flex items-center justify-center transition-all cursor-pointer shadow-md outline-none focus:outline-none",
                        !disabled
                          ? "text-[#121319] bg-brand-gradient hover:opacity-90 active:scale-95 shadow-sm shadow-[#6EF0C2]/20"
                          : "bg-surface-raised/80 text-on-surface-variant/40 cursor-not-allowed opacity-50"
                      )}
                      aria-label={t.composer.send}
                    >
                      {disabled ? (
                        <Loader2 className="size-4 animate-spin" />
                      ) : (
                        <ArrowUp className="size-4 sm:size-4.5 stroke-[2.5]" />
                      )}
                    </button>
                  </TooltipTrigger>
                  <TooltipContent side="top" sideOffset={6} className="text-xs">
                    {t.composer.send}
                  </TooltipContent>
                </Tooltip>
              )}
            </TooltipProvider>
          </div>
        </div>
      </form>

      {/* Footer warning note */}
      <div className="text-center mt-2 sm:mt-3 px-2">
        <span className="text-[10px] sm:text-[11px] text-on-surface-variant/50 tracking-wide font-sans leading-tight">
          {language === "fa"
            ? "دستیار هوشمند سازمانی ممکن است خطا داشته باشد. اقدامات حساس را بررسی کنید."
            : "Sovereign AI can make mistakes. Verify critical actions."}
        </span>
      </div>
    </div>
  );
}
