/**
 * Voice & TTS API Client
 */

import { apiFetch } from "@/api/client";

export async function ttsPreviewApi(text: string, voiceId: string): Promise<Blob> {
  const res = await apiFetch("voice/tts", {
    method: "POST",
    body: JSON.stringify({ text, voice: voiceId }),
  });
  if (!res.ok) {
    throw new Error(`TTS request failed with status ${res.status}`);
  }
  return res.blob();
}
