"use client";

import * as React from "react";
import { Check, Mic, Volume2, VolumeX } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { ttsPreviewApi } from "@/api/index";
import type { Language } from "@/lib/types";

interface VoiceTabProps {
  language: Language;
}

const VOICE_PERSONAS = [
  { id: "Aoede", name: "Aoede (آئوده)", desc: "صدای رسمی، شفاف و رسا جهت گزارش‌ها و تحلیل‌های مدیریتی", tone: "Formal & Crisp" },
  { id: "Charon", name: "Charon (خارون)", desc: "صدای بم، جدی و فنی مناسب دیباگ و تحلیل‌های تخصصی مهندسی", tone: "Deep & Technical" },
  { id: "Fenrir", name: "Fenrir (فنریر)", desc: "صدای پرانرژی و متمرکز جهت جلسات طوفان فکری و کدنویسی", tone: "Dynamic & Fast" },
  { id: "Kore", name: "Kore (کوره)", desc: "صدای گرم، ملایم و تعاملی جهت راهنمایی سازمانی و پاسخ‌های عمومی", tone: "Warm & Friendly" },
  { id: "Puck", name: "Puck (پوک)", desc: "صدای پویا، ریتمیک و انعطاف‌پذیر با پردازش سریع کلمات", tone: "Natural & Agile" },
];

export function VoiceTab({ language }: VoiceTabProps) {
  const isFa = language === "fa";
  const [selectedVoice, setSelectedVoice] = React.useState("Aoede");
  const [playingVoice, setPlayingVoice] = React.useState<string | null>(null);
  const audioPreviewRef = React.useRef<HTMLAudioElement | null>(null);

  React.useEffect(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("sovereign_voice_persona");
      if (saved) setSelectedVoice(saved);
    }
  }, []);

  const handleVoiceSelect = (voiceId: string) => {
    setSelectedVoice(voiceId);
    if (typeof window !== "undefined") {
      localStorage.setItem("sovereign_voice_persona", voiceId);
      window.dispatchEvent(new CustomEvent("sovereign_voice_change", { detail: voiceId }));
    }
    toast.success(isFa ? `گوینده هوش مصنوعی به «${voiceId}» تغییر یافت.` : `AI voice persona updated to ${voiceId}.`);
  };

  const playVoicePreview = async (e: React.MouseEvent, voiceId: string) => {
    e.stopPropagation();
    if (audioPreviewRef.current) {
      audioPreviewRef.current.pause();
      audioPreviewRef.current = null;
    }
    if (playingVoice === voiceId) {
      setPlayingVoice(null);
      return;
    }

    setPlayingVoice(voiceId);
    try {
      const sampleText = isFa
        ? `سلام، من گوینده ${voiceId} در دستیار هوشمند سازمانی هستم.`
        : `Hello, I am the ${voiceId} voice assistant for Sovereign AI.`;

      const blob = await ttsPreviewApi(sampleText, voiceId);
      const audioUrl = URL.createObjectURL(blob);
      const audio = new Audio(audioUrl);
      audioPreviewRef.current = audio;
      audio.onended = () => setPlayingVoice(null);
      audio.onerror = () => setPlayingVoice(null);
      await audio.play();
    } catch {
      setPlayingVoice(null);
      toast.error(isFa ? "خطا در پخش نمونه صدا. سرویس موقتاً در دسترس نیست." : "Voice preview unavailable.");
    }
  };

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-xs font-bold text-on-surface flex items-center gap-2">
          <Mic className="size-4 text-brand-cyan" />
          {isFa ? "گوینده صوتی و موتور TTS" : "Voice Persona & TTS Engine"}
        </h3>
        <p className="text-[11px] text-on-surface-variant mt-0.5">
          {isFa
            ? "انتخاب صدای پاسخ‌دهی دستیار در تعامل صوتی بلادرنگ (Voice Streaming)"
            : "Choose the synthesized voice persona for real-time speech interaction."}
        </p>
      </div>

      <div className="space-y-2.5">
        {VOICE_PERSONAS.map((voice) => {
          const isSelected = selectedVoice === voice.id;
          const isPlaying = playingVoice === voice.id;
          return (
            <div
              key={voice.id}
              onClick={() => handleVoiceSelect(voice.id)}
              className={`flex items-center justify-between p-3 rounded-2xl border transition-all cursor-pointer ${
                isSelected
                  ? "bg-brand-cyan/15 border-brand-cyan/40 text-on-surface shadow-sm"
                  : "bg-surface-container/30 border-border/30 text-on-surface-variant hover:border-border/60 hover:text-on-surface"
              }`}
            >
              <div className="space-y-0.5">
                <div className="text-xs font-bold text-on-surface flex items-center gap-2">
                  <span>{voice.name}</span>
                  <span className="text-[10px] text-on-surface-variant font-mono font-normal">({voice.tone})</span>
                </div>
                <div className="text-[10.5px] text-on-surface-variant leading-relaxed">{voice.desc}</div>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  onClick={(e) => playVoicePreview(e, voice.id)}
                  className={`size-8 rounded-xl border-border/40 ${isPlaying ? "text-brand-cyan border-brand-cyan/40 bg-brand-cyan/10" : ""}`}
                  title={isPlaying ? "توقف پخش" : "پخش نمونه صدا"}
                >
                  {isPlaying ? <VolumeX className="size-4 animate-pulse" /> : <Volume2 className="size-4" />}
                </Button>
                {isSelected && <Check className="size-4 text-brand-cyan" />}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
