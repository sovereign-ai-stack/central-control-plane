"use client";

import * as React from "react";
import { Mic, MicOff, X } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { apiFetch } from "@/lib/api";
import type { Citation, Language, Message } from "@/lib/types";
import {
  consumeVoiceStream,
  StreamingAudioPlayer,
  VOICE_STREAM_CONTENT_TYPE,
} from "@/lib/voice-stream";
import type { VoiceStreamMetadata } from "@/lib/voice-stream";

export interface FloatingVoiceWidgetProps {
  isOpen: boolean;
  onClose: () => void;
  language?: Language;
  conversationId?: string | null;
  onMessageAdded?: (userMessage: Message, assistantMessage: Message, conversationId: string) => void;
}

export type VoiceState = "listening" | "connecting" | "thinking" | "speaking" | "muted";
type HoldSource = "pointer" | "keyboard";

export function FloatingVoiceWidget({
  isOpen,
  onClose,
  language = "fa",
  conversationId,
  onMessageAdded,
}: FloatingVoiceWidgetProps) {
  const [voiceState, setVoiceState] = React.useState<VoiceState>("listening");
  const [isMuted, setIsMuted] = React.useState(false);
  const [transcript, setTranscript] = React.useState("");
  const [assistantText, setAssistantText] = React.useState("");
  const [isRecording, setIsRecording] = React.useState(false);
  const [voicePersona, setVoicePersona] = React.useState<string>("Aoede");

  const mediaRecorderRef = React.useRef<MediaRecorder | null>(null);
  const audioChunksRef = React.useRef<Blob[]>([]);
  const streamRef = React.useRef<MediaStream | null>(null);
  const audioPlayerRef = React.useRef<StreamingAudioPlayer | HTMLAudioElement | null>(null);
  const discardRecordingRef = React.useRef(false);
  const holdSourceRef = React.useRef<HoldSource | null>(null);
  const recordingRequestRef = React.useRef(0);

  React.useEffect(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("sovereign_voice_persona") || localStorage.getItem("sovereign_voice_persona") || "Aoede";
      setVoicePersona(saved);

      const handleVoiceChange = (e: CustomEvent<string>) => {
        if (e.detail) setVoicePersona(e.detail);
      };
      window.addEventListener("sovereign_voice_change", handleVoiceChange as EventListener);
      return () => {
        window.removeEventListener("sovereign_voice_change", handleVoiceChange as EventListener);
      };
    }
  }, [isOpen]);

  const stopAllAudio = React.useCallback(() => {
    if (audioPlayerRef.current instanceof StreamingAudioPlayer) {
      audioPlayerRef.current.stop();
    } else {
      audioPlayerRef.current?.pause();
    }
    audioPlayerRef.current = null;

    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      try {
        mediaRecorderRef.current.stop();
      } catch {
        // The recorder may already be stopping.
      }
    }
    mediaRecorderRef.current = null;

    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    setIsRecording(false);
  }, []);

  const handleClose = React.useCallback(() => {
    holdSourceRef.current = null;
    recordingRequestRef.current += 1;
    discardRecordingRef.current = true;
    stopAllAudio();
    onClose();
  }, [onClose, stopAllAudio]);

  const submitVoiceQuery = React.useCallback(
    async (audioBlob?: Blob, textMessage?: string) => {
      setVoiceState("connecting");
      setTranscript(textMessage || (language === "fa" ? "در حال پردازش گفتار…" : "Processing voice…"));

      try {
        const currentVoice = typeof window !== "undefined"
          ? localStorage.getItem("sovereign_voice_persona") || localStorage.getItem("sovereign_voice_persona") || voicePersona || "Aoede"
          : voicePersona || "Aoede";
        const formData = new FormData();
        if (audioBlob) formData.append("file", audioBlob, "voice_recording.webm");
        if (textMessage) formData.append("message", textMessage);
        if (conversationId) formData.append("conversation_id", conversationId);
        formData.append("language", language);
        formData.append("voice", currentVoice);
        formData.append("voice_mode", "true");

        const response = await apiFetch("voice/chat", { method: "POST", body: formData });
        if (!response.ok) throw new Error(`Server returned ${response.status}`);

        const contentType = response.headers.get("content-type")?.toLowerCase() || "";
        if (contentType.includes(VOICE_STREAM_CONTENT_TYPE)) {
          let audioMimeType = "audio/mpeg";
          let player: StreamingAudioPlayer | null = null;
          let completeMetadata: VoiceStreamMetadata | null = null;

          await consumeVoiceStream(response, {
            onMetadata: (metadata) => {
              if (metadata.audio_mime_type) audioMimeType = metadata.audio_mime_type;

              if (metadata.phase === "started") {
                setTranscript(metadata.transcription || "");
                setVoiceState("thinking");
              } else {
                completeMetadata = metadata;
                setTranscript(metadata.transcription || "");
                setAssistantText(metadata.response_text || "");
              }
            },
            onAudioChunk: (chunk) => {
              const nextPlayer =
                player ||
                new StreamingAudioPlayer(audioMimeType, () => {
                  setVoiceState(isMuted ? "muted" : "listening");
                  if (audioPlayerRef.current === player) audioPlayerRef.current = null;
                });
              player = nextPlayer;
              audioPlayerRef.current = nextPlayer;
              setVoiceState("speaking");
              nextPlayer.append(chunk);
            },
          });

          if (!completeMetadata) throw new Error("Voice stream did not return final metadata");
          const data = completeMetadata as VoiceStreamMetadata;
          setTranscript(data.transcription || "");
          setAssistantText(data.response_text || "");

          if (data.conversation_id && data.user_message_id && data.message_id) {
            onMessageAdded?.(
              {
                id: data.user_message_id,
                role: "user",
                content: data.transcription || "",
                direction: language === "fa" ? "rtl" : "ltr",
                status: "complete",
                createdAt: new Date().toISOString(),
              },
              {
                id: data.message_id,
                role: "assistant",
                content: data.response_text || "",
                direction: language === "fa" ? "rtl" : "ltr",
                status: "complete",
                citations: data.citations || [],
                createdAt: new Date().toISOString(),
              },
              data.conversation_id,
            );
          }

          const activePlayer = player as StreamingAudioPlayer | null;
          if (activePlayer) {
            activePlayer.finish();
          } else {
            setVoiceState(isMuted ? "muted" : "listening");
          }
          return;
        }

        // Keep compatibility with older deployments while they roll out the binary stream.
        const data: {
          transcription: string;
          response_text: string;
          citations: Citation[];
          audio_base64: string;
          conversation_id: string;
          user_message_id: string;
          message_id: string;
        } = await response.json();

        setTranscript(data.transcription);
        setAssistantText(data.response_text);

        onMessageAdded?.(
          {
            id: data.user_message_id,
            role: "user",
            content: data.transcription,
            direction: language === "fa" ? "rtl" : "ltr",
            status: "complete",
            createdAt: new Date().toISOString(),
          },
          {
            id: data.message_id,
            role: "assistant",
            content: data.response_text,
            direction: language === "fa" ? "rtl" : "ltr",
            status: "complete",
            citations: data.citations,
            createdAt: new Date().toISOString(),
          },
          data.conversation_id,
        );

        if (data.audio_base64) {
          setVoiceState("speaking");
          const mime = data.audio_base64.startsWith("UklGR") ? "audio/wav" : "audio/mpeg";
          const audio = new Audio(`data:${mime};base64,${data.audio_base64}`);
          audioPlayerRef.current = audio;
          audio.onended = () => {
            setVoiceState(isMuted ? "muted" : "listening");
            if (audioPlayerRef.current === audio) audioPlayerRef.current = null;
          };
          audio.onerror = () => {
            setVoiceState(isMuted ? "muted" : "listening");
            if (audioPlayerRef.current === audio) audioPlayerRef.current = null;
          };
          await audio.play();
        } else {
          setVoiceState(isMuted ? "muted" : "listening");
        }
      } catch (error) {
        stopAllAudio();
        console.error("Voice chat error:", error);
        toast.error(
          language === "fa"
            ? "خطا در پردازش صوت. لطفاً مجدداً تلاش کنید."
            : "Voice processing failed. Please try again."
        );
        setVoiceState(isMuted ? "muted" : "listening");
      }
    },
    [conversationId, isMuted, language, onMessageAdded, stopAllAudio, voicePersona]
  );

  const startRecording = React.useCallback(async () => {
    if (isRecording || isMuted || voiceState === "connecting" || voiceState === "speaking") return;

    const requestId = recordingRequestRef.current + 1;
    recordingRequestRef.current = requestId;
    setVoiceState("connecting");
    setTranscript("");
    setAssistantText("");

    try {
      discardRecordingRef.current = false;
      stopAllAudio();

      if (!window.isSecureContext) {
        throw new Error("MIC_REQUIRES_SECURE_CONTEXT");
      }

      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error("MEDIA_UNSUPPORTED");
      }

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      if (requestId !== recordingRequestRef.current || holdSourceRef.current === null) {
        stream.getTracks().forEach((track) => track.stop());
        return;
      }

      streamRef.current = stream;

      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/webm";
      const recorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = recorder;
      audioChunksRef.current = [];

      recorder.ondataavailable = (event) => {
        if (event.data?.size) audioChunksRef.current.push(event.data);
      };
      recorder.onstop = () => {
        const blob = new Blob(audioChunksRef.current, { type: mimeType });
        if (!discardRecordingRef.current && blob.size > 1000) {
          void submitVoiceQuery(blob);
        } else if (!discardRecordingRef.current) {
          setVoiceState(isMuted ? "muted" : "listening");
        }
        discardRecordingRef.current = false;
      };

      recorder.start(250);
      setIsRecording(true);
      setVoiceState("listening");
    } catch (error: unknown) {
      if (requestId !== recordingRequestRef.current || holdSourceRef.current === null) return;

      console.error("Microphone access error:", error);
      const errName = error && typeof error === "object" && "name" in error ? String(error.name) : "";
      const errMessage = error instanceof Error ? error.message : "";
      if (errMessage === "MIC_REQUIRES_SECURE_CONTEXT") {
        toast.error(
          language === "fa"
            ? "برای دسترسی به میکروفون، برنامه را با HTTPS باز کنید."
            : "Microphone access requires a secure HTTPS connection."
        );
      } else if (errName === "NotAllowedError" || errName === "PermissionDeniedError") {
        toast.error(
          language === "fa"
            ? "دسترسی به میکروفون مسدود است. لطفاً در تنظیمات مرورگر مجوز میکروفون را فعال کنید."
            : "Microphone permission denied. Please allow microphone access in your browser settings."
        );
      } else if (errName === "NotFoundError" || errName === "DevicesNotFoundError") {
        toast.error(
          language === "fa"
            ? "هیچ دستگاه میکروفونی یافت نشد."
            : "No microphone device found on your system."
        );
      } else {
        toast.error(
          language === "fa" ? "دسترسی به میکروفون داده نشد." : "Microphone access denied."
        );
      }
      holdSourceRef.current = null;
      setVoiceState("muted");
      setIsMuted(true);
    }
  }, [isMuted, isRecording, language, stopAllAudio, submitVoiceQuery, voiceState]);

  const stopAndSubmitRecording = React.useCallback(() => {
    recordingRequestRef.current += 1;

    if (mediaRecorderRef.current?.state !== "recording") {
      discardRecordingRef.current = true;
      stopAllAudio();
      setVoiceState(isMuted ? "muted" : "listening");
      return;
    }

    discardRecordingRef.current = false;
    mediaRecorderRef.current.stop();
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    setIsRecording(false);
    setVoiceState("connecting");
  }, [isMuted, stopAllAudio]);

  const beginHold = React.useCallback(
    (source: HoldSource) => {
      if (
        holdSourceRef.current ||
        isMuted ||
        isRecording ||
        voiceState === "connecting" ||
        voiceState === "speaking"
      ) {
        return false;
      }

      holdSourceRef.current = source;
      void startRecording();
      return true;
    },
    [isMuted, isRecording, startRecording, voiceState]
  );

  const endHold = React.useCallback(
    (source: HoldSource) => {
      if (holdSourceRef.current !== source) return;
      holdSourceRef.current = null;
      stopAndSubmitRecording();
    },
    [stopAndSubmitRecording]
  );

  const handleToggleMute = () => {
    if (!isMuted) {
      setIsMuted(true);
      setVoiceState("muted");
      holdSourceRef.current = null;
      recordingRequestRef.current += 1;
      discardRecordingRef.current = true;
      stopAllAudio();
    } else {
      setIsMuted(false);
      setVoiceState("listening");
    }
  };

  const handleOrbPointerDown = (event: React.PointerEvent<HTMLButtonElement>) => {
    if (event.button !== 0 || !beginHold("pointer")) return;
    event.preventDefault();
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const handleOrbPointerUp = (event: React.PointerEvent<HTMLButtonElement>) => {
    if (holdSourceRef.current !== "pointer") return;
    event.preventDefault();
    endHold("pointer");
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  };

  React.useEffect(() => {
    if (!isOpen) return;

    const isTextEntry = (target: EventTarget | null) => {
      if (!(target instanceof HTMLElement)) return false;
      return (
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        target instanceof HTMLSelectElement ||
        target.isContentEditable
      );
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.code !== "Space" || event.repeat || isTextEntry(event.target)) return;
      if (!beginHold("keyboard")) return;
      event.preventDefault();
    };

    const handleKeyUp = (event: KeyboardEvent) => {
      if (event.code !== "Space" || holdSourceRef.current !== "keyboard") return;
      event.preventDefault();
      endHold("keyboard");
    };

    const handleWindowBlur = () => {
      if (holdSourceRef.current === "keyboard") endHold("keyboard");
      if (holdSourceRef.current === "pointer") endHold("pointer");
    };

    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("keyup", handleKeyUp);
    window.addEventListener("blur", handleWindowBlur);

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("keyup", handleKeyUp);
      window.removeEventListener("blur", handleWindowBlur);
    };
  }, [beginHold, endHold, isOpen]);

  React.useEffect(() => {
    if (!isOpen) {
      holdSourceRef.current = null;
      recordingRequestRef.current += 1;
      discardRecordingRef.current = true;
      stopAllAudio();
      return;
    }

    setVoiceState(isMuted ? "muted" : "listening");
  }, [isMuted, isOpen, stopAllAudio]);

  React.useEffect(() => {
    return () => {
      holdSourceRef.current = null;
      recordingRequestRef.current += 1;
      discardRecordingRef.current = true;
      stopAllAudio();
    };
  }, [stopAllAudio]);

  if (!isOpen) return null;

  const orbLabel =
    language === "fa"
      ? isRecording
        ? "برای ارسال صدا رها کنید"
        : "برای صحبت دایره یا کلید فاصله را نگه دارید"
      : isRecording
        ? "Release to send voice"
        : "Hold the orb or Space to talk";

  return (
    <div data-slot="floating-voice-widget" className="fixed inset-0 z-50 flex flex-col items-center justify-end pb-8 sm:pb-12 pointer-events-none">
      {/* Subtle backdrop overlay - click to dismiss */}
      <div onClick={handleClose} className="pointer-events-auto absolute inset-0 bg-black/35 backdrop-blur-xs transition-opacity" />

      {/* Floating Interactive Voice Container */}
      <div className="pointer-events-none relative z-10 flex w-full max-w-xl flex-col items-center gap-4 px-4">
        {/* Floating Voice Orb */}
        <div className="flex flex-col items-center gap-3">
          <button
            type="button"
            onPointerDown={handleOrbPointerDown}
            onPointerUp={handleOrbPointerUp}
            onPointerCancel={() => endHold("pointer")}
            onLostPointerCapture={() => endHold("pointer")}
            aria-keyshortcuts="Space"
            className={cn(
              "pointer-events-auto relative flex size-28 sm:size-32 touch-none select-none items-center justify-center overflow-hidden rounded-full bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 transition-all duration-500 cursor-pointer shadow-2xl border border-white/20",
              voiceState === "listening" && "animate-pulse-glow scale-105 shadow-[0_0_50px_16px_rgba(168,85,247,0.45)]",
              voiceState === "connecting" && "scale-105 shadow-[0_0_50px_16px_rgba(49,200,237,0.5)]",
              voiceState === "speaking" && "animate-voice-wave scale-110 shadow-[0_0_70px_25px_rgba(217,70,239,0.6)]",
              voiceState === "muted" && "scale-95 opacity-50 grayscale-[50%]"
            )}
            aria-label={orbLabel}
            title={orbLabel}
          >
            <div className="pointer-events-none absolute inset-0 rounded-full bg-white/15 blur-md" />
            <div className={cn("pointer-events-none absolute inset-0 rounded-full bg-gradient-to-tr from-purple-200/40 via-purple-400/20 to-transparent mix-blend-overlay", voiceState !== "muted" && "animate-orb-spin")} />
            
            {/* Center Animation State */}
            <div className="relative z-10 text-white drop-shadow-md flex items-center justify-center pointer-events-none">
              {voiceState === "connecting" && (
                <div className="flex items-center gap-1.5">
                  <span className="size-2.5 rounded-full bg-white animate-pulse" />
                  <span className="size-3 rounded-full bg-white animate-pulse [animation-delay:150ms]" />
                  <span className="size-2.5 rounded-full bg-white animate-pulse [animation-delay:300ms]" />
                </div>
              )}
              {voiceState === "thinking" && (
                <div className="flex items-center gap-1">
                  <span className="w-1.5 h-4 bg-white/90 rounded-full animate-pulse" />
                  <span className="w-1.5 h-7 bg-white rounded-full animate-pulse [animation-delay:150ms]" />
                  <span className="w-1.5 h-10 bg-white rounded-full animate-pulse [animation-delay:300ms]" />
                  <span className="w-1.5 h-7 bg-white rounded-full animate-pulse [animation-delay:150ms]" />
                  <span className="w-1.5 h-4 bg-white/90 rounded-full animate-pulse" />
                </div>
              )}
              {voiceState === "speaking" && (
                <div className="flex items-center gap-1">
                  <span className="w-1.5 h-4 bg-white rounded-full animate-bounce [animation-delay:-0.2s]" />
                  <span className="w-1.5 h-8 bg-white rounded-full animate-bounce [animation-delay:-0.4s]" />
                  <span className="w-1.5 h-12 bg-white rounded-full animate-bounce" />
                  <span className="w-1.5 h-8 bg-white rounded-full animate-bounce [animation-delay:-0.4s]" />
                  <span className="w-1.5 h-4 bg-white rounded-full animate-bounce [animation-delay:-0.2s]" />
                </div>
              )}
              {voiceState === "listening" && isRecording && (
                <div className="relative flex items-center justify-center">
                  <span className="absolute size-10 rounded-full bg-white/30 animate-ping" />
                  <span className="size-4 rounded-full bg-white shadow-lg" />
                </div>
              )}
              {voiceState === "listening" && !isRecording && (
                <Mic className="size-9 text-white drop-shadow-md" />
              )}
              {voiceState === "muted" && (
                <MicOff className="size-9 text-white/70 drop-shadow-md" />
              )}
            </div>
          </button>

          {/* Status Badge */}
          <div className="min-h-7 px-3.5 py-1.5 rounded-full bg-surface-container/85 border border-white/15 backdrop-blur-md shadow-sm text-center">
            <div className="text-xs font-medium text-foreground">
              {voiceState === "connecting" && (
                <span className="flex items-center justify-center gap-2 text-brand-cyan">
                  <span className="relative flex size-2 shrink-0">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-cyan opacity-75"></span>
                    <span className="relative inline-flex rounded-full size-2 bg-brand-cyan"></span>
                  </span>
                  <span>{language === "fa" ? "در حال اتصال به دستیار صوتی…" : "Connecting to voice assistant…"}</span>
                </span>
              )}
              {voiceState === "thinking" && (
                <span className="flex items-center justify-center gap-2 text-brand-mint">
                  <span className="relative flex size-2 shrink-0">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-mint opacity-75"></span>
                    <span className="relative inline-flex rounded-full size-2 bg-brand-mint"></span>
                  </span>
                  <span>{language === "fa" ? "در حال پردازش و استخراج پاسخ…" : "Processing response…"}</span>
                </span>
              )}
              {voiceState === "speaking" && (
                <span className="flex items-center justify-center gap-2 text-foreground">
                  <span className="line-clamp-1 max-w-xs">{assistantText || transcript}</span>
                  <span className="text-[10px] text-purple-300 bg-purple-500/20 px-2 py-0.5 rounded-full font-mono shrink-0">
                    {voicePersona}
                  </span>
                </span>
              )}
              {voiceState === "listening" && (
                <span className="text-muted-foreground">
                  {isRecording
                    ? language === "fa"
                      ? "برای ارسال رها کنید"
                      : "Release to send"
                    : language === "fa"
                      ? "دایره یا کلید فاصله را برای صحبت نگه دارید"
                      : "Hold the orb or Space to talk"}
                </span>
              )}
              {voiceState === "muted" && (
                <span className="text-muted-foreground/60">{language === "fa" ? "میکروفون غیرفعال است" : "Microphone muted"}</span>
              )}
            </div>
          </div>
        </div>

        <div className="pointer-events-auto flex items-center gap-2 rounded-full border border-white/15 bg-surface-container-highest/80 p-1.5 shadow-xl shadow-black/20 backdrop-blur-2xl">
          <button
            type="button"
            onClick={handleToggleMute}
            className={cn(
              "group relative flex size-11 items-center justify-center rounded-full border transition-all duration-200 hover:-translate-y-0.5 active:translate-y-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-cyan/80 cursor-pointer",
              isMuted
                ? "border-destructive/40 bg-destructive/15 text-destructive shadow-[0_0_20px_rgba(242,116,122,0.18)] hover:bg-destructive/25"
                : "border-white/10 bg-white/5 text-muted-foreground hover:border-white/25 hover:bg-white/10 hover:text-foreground"
            )}
            aria-pressed={isMuted}
            aria-label={isMuted ? "Unmute mic" : "Mute mic"}
            title={isMuted ? "Unmute microphone" : "Mute microphone"}
          >
            {isMuted ? <MicOff className="size-5" /> : <Mic className="size-5" />}
            <span
              className={cn(
                "absolute bottom-1.5 end-1.5 size-1.5 rounded-full ring-2 ring-surface-container-highest",
                isMuted ? "bg-destructive" : "bg-brand-mint"
              )}
            />
          </button>
          <button
            type="button"
            onClick={handleClose}
            className="flex size-11 shrink-0 items-center justify-center rounded-full bg-white text-black shadow-md transition-transform hover:scale-105 active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white cursor-pointer"
            aria-label={language === "fa" ? "بستن حالت صوتی" : "Close voice mode"}
          >
            <X className="size-5 stroke-[2.5]" />
          </button>
        </div>
      </div>
    </div>
  );
}
