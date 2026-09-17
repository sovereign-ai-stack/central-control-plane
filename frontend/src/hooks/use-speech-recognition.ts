"use client";

import * as React from "react";
import { toast } from "sonner";
import { Language } from "@/lib/types";

export interface UseSpeechRecognitionProps {
  language: Language;
  onResult: (text: string) => void;
  onEnd: () => void;
}

export function useSpeechRecognition({ language, onResult, onEnd }: UseSpeechRecognitionProps) {
  const [isRecording, setIsRecording] = React.useState(false);
  const recognitionRef = React.useRef<any>(null);
  const isSupported = typeof window !== "undefined" && ("SpeechRecognition" in window || "webkitSpeechRecognition" in window);

  React.useEffect(() => {
    if (!isSupported) return;
    
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = language === "fa" ? "fa-IR" : "en-US";

    recognition.onresult = (event: any) => {
      let currentText = "";
      for (let i = 0; i < event.results.length; ++i) {
        currentText += event.results[i][0].transcript;
      }
      onResult(currentText);
    };

    recognition.onerror = (event: any) => {
      console.error("Speech recognition error:", event.error);
      if (event.error === "not-allowed" || event.error === "audio-capture") {
        toast.error(language === "fa" ? "دسترسی به میکروفون مسدود است." : "Microphone access denied.");
      }
      setIsRecording(false);
      onEnd();
    };

    recognition.onend = () => {
      setIsRecording(false);
      onEnd();
    };

    recognitionRef.current = recognition;
  }, [language, onResult, onEnd, isSupported]);

  const start = React.useCallback(() => {
    if (!isSupported) {
      toast.error(language === "fa" ? "مرورگر شما از تایپ صوتی پشتیبانی نمی‌کند." : "Browser does not support Speech Recognition.");
      return;
    }
    try {
      recognitionRef.current?.start();
      setIsRecording(true);
    } catch (e) {
      console.error("Speech API start error:", e);
    }
  }, [isSupported, language]);

  const stop = React.useCallback(() => {
    if (isRecording) {
      recognitionRef.current?.stop();
      setIsRecording(false);
    }
  }, [isRecording]);

  return { isRecording, isSupported, start, stop };
}
