import type { Citation } from "./types";

export const VOICE_STREAM_CONTENT_TYPE = "application/x-sovereign-voice-stream";
export const LEGACY_VOICE_STREAM_CONTENT_TYPE = "application/x-sovereign-voice-stream";

const AUDIO_FRAME = 1;
const METADATA_FRAME = 2;
const ERROR_FRAME = 3;
const MAX_FRAME_SIZE = 64 * 1024 * 1024;

export interface VoiceStreamMetadata {
  phase: "started" | "complete";
  transcription?: string;
  response_text?: string;
  citations?: Citation[];
  conversation_id?: string;
  user_message_id?: string;
  message_id?: string;
  audio_mime_type?: string;
}

export interface VoiceStreamCallbacks {
  onAudioChunk?: (chunk: Uint8Array) => void | Promise<void>;
  onMetadata?: (metadata: VoiceStreamMetadata) => void | Promise<void>;
}

function appendBytes(
  left: Uint8Array<ArrayBuffer>,
  right: Uint8Array<ArrayBufferLike>,
): Uint8Array<ArrayBuffer> {
  const combined = new Uint8Array(left.byteLength + right.byteLength);
  combined.set(left);
  combined.set(right, left.byteLength);
  return combined;
}

function parseMetadata(payload: Uint8Array): VoiceStreamMetadata {
  const value: unknown = JSON.parse(new TextDecoder().decode(payload));
  if (!value || typeof value !== "object" || !("phase" in value)) {
    throw new Error("Invalid voice stream metadata");
  }
  return value as VoiceStreamMetadata;
}

async function handleFrame(
  frameType: number,
  payload: Uint8Array,
  callbacks: VoiceStreamCallbacks,
): Promise<VoiceStreamMetadata | null> {
  if (frameType === AUDIO_FRAME) {
    await callbacks.onAudioChunk?.(payload);
    return null;
  }

  if (frameType === METADATA_FRAME) {
    const metadata = parseMetadata(payload);
    await callbacks.onMetadata?.(metadata);
    return metadata.phase === "complete" ? metadata : null;
  }

  if (frameType === ERROR_FRAME) {
    const value: unknown = JSON.parse(new TextDecoder().decode(payload));
    const message =
      value && typeof value === "object" && "message" in value && typeof value.message === "string"
        ? value.message
        : "Voice stream failed";
    throw new Error(message);
  }

  throw new Error("Unknown voice stream frame");
}

export async function consumeVoiceStream(
  response: Response,
  callbacks: VoiceStreamCallbacks = {},
): Promise<VoiceStreamMetadata> {
  if (!response.body) throw new Error("Voice stream body is unavailable");

  const reader = response.body.getReader();
  let buffer = new Uint8Array();
  let completeMetadata: VoiceStreamMetadata | null = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    if (!value?.byteLength) continue;
    buffer = appendBytes(buffer, value);

    while (buffer.byteLength >= 5) {
      const frameType = buffer[0];
      const frameLength = new DataView(buffer.buffer, buffer.byteOffset, buffer.byteLength).getUint32(1);
      if (frameLength > MAX_FRAME_SIZE) throw new Error("Voice stream frame is too large");
      if (buffer.byteLength < 5 + frameLength) break;

      const payload = buffer.slice(5, 5 + frameLength);
      buffer = buffer.slice(5 + frameLength);
      const metadata = await handleFrame(frameType, payload, callbacks);
      if (metadata) completeMetadata = metadata;
    }
  }

  if (buffer.byteLength) throw new Error("Voice stream ended mid-frame");
  if (!completeMetadata) throw new Error("Voice stream did not complete");
  return completeMetadata;
}

export class StreamingAudioPlayer {
  private readonly audio = new Audio();
  private readonly mimeType: string;
  private readonly onEnded: () => void;
  private readonly chunks: ArrayBuffer[] = [];
  private readonly pendingChunks: ArrayBuffer[] = [];
  private mediaSource: MediaSource | null = null;
  private sourceBuffer: SourceBuffer | null = null;
  private objectUrl: string | null = null;
  private finished = false;
  private started = false;
  private stopped = false;
  private useMediaSource = false;

  constructor(mimeType: string, onEnded: () => void) {
    this.mimeType = mimeType || "audio/mpeg";
    this.onEnded = onEnded;
    this.audio.preload = "auto";
    this.audio.onended = onEnded;
    this.audio.onerror = onEnded;

    if (
      typeof window !== "undefined" &&
      typeof MediaSource !== "undefined" &&
      MediaSource.isTypeSupported(this.mimeType)
    ) {
      this.useMediaSource = true;
      this.mediaSource = new MediaSource();
      this.objectUrl = URL.createObjectURL(this.mediaSource);
      this.audio.src = this.objectUrl;
      this.mediaSource.addEventListener("sourceopen", this.handleSourceOpen, { once: true });
    }
  }

  append(chunk: Uint8Array): void {
    if (this.stopped || !chunk.byteLength) return;

    const copy = new Uint8Array(chunk.byteLength);
    copy.set(chunk);
    const buffer = copy.buffer;
    this.chunks.push(buffer);

    if (!this.useMediaSource) return;
    this.pendingChunks.push(buffer);
    this.flushSourceBuffer();
  }

  finish(): void {
    if (this.stopped || this.finished) return;
    this.finished = true;

    if (!this.useMediaSource) {
      this.playBufferedAudio();
      return;
    }

    this.flushSourceBuffer();
    this.endMediaSourceWhenReady();
  }

  stop(): void {
    if (this.stopped) return;
    this.stopped = true;
    this.audio.onended = null;
    this.audio.onerror = null;
    this.audio.pause();
    this.audio.removeAttribute("src");
    this.audio.load();

    if (this.objectUrl) URL.revokeObjectURL(this.objectUrl);
    this.objectUrl = null;
    this.mediaSource = null;
    this.sourceBuffer = null;
    this.pendingChunks.length = 0;
  }

  private readonly handleSourceOpen = (): void => {
    if (!this.mediaSource || this.stopped) return;

    try {
      this.sourceBuffer = this.mediaSource.addSourceBuffer(this.mimeType);
      this.sourceBuffer.addEventListener("updateend", this.handleSourceUpdate);
      this.sourceBuffer.addEventListener("error", this.handleSourceError, { once: true });
      this.flushSourceBuffer();
      this.startPlayback();
    } catch {
      this.useBufferedFallback();
    }
  };

  private readonly handleSourceUpdate = (): void => {
    this.flushSourceBuffer();
    this.endMediaSourceWhenReady();
  };

  private readonly handleSourceError = (): void => {
    this.useBufferedFallback();
  };

  private flushSourceBuffer(): void {
    if (!this.sourceBuffer || this.sourceBuffer.updating || !this.pendingChunks.length) return;

    const next = this.pendingChunks.shift();
    if (!next) return;

    try {
      this.sourceBuffer.appendBuffer(next);
    } catch {
      this.useBufferedFallback();
    }
  }

  private endMediaSourceWhenReady(): void {
    if (
      !this.finished ||
      !this.mediaSource ||
      !this.sourceBuffer ||
      this.pendingChunks.length ||
      this.sourceBuffer.updating ||
      this.mediaSource.readyState !== "open"
    ) {
      return;
    }

    try {
      this.mediaSource.endOfStream();
    } catch {
      this.useBufferedFallback();
    }
  }

  private startPlayback(): void {
    if (this.started || this.stopped) return;
    this.started = true;
    void this.audio.play().catch(() => {
      this.started = false;
    });
  }

  private playBufferedAudio(): void {
    if (!this.chunks.length || this.stopped) {
      this.onEnded();
      return;
    }

    this.releaseObjectUrl();
    this.objectUrl = URL.createObjectURL(new Blob(this.chunks, { type: this.mimeType }));
    this.audio.src = this.objectUrl;
    this.startPlayback();
  }

  private useBufferedFallback(): void {
    if (this.stopped) return;
    this.useMediaSource = false;
    this.pendingChunks.length = 0;
    this.sourceBuffer = null;
    this.mediaSource = null;
    this.started = false;
    this.releaseObjectUrl();

    if (this.finished) this.playBufferedAudio();
  }

  private releaseObjectUrl(): void {
    if (!this.objectUrl) return;
    URL.revokeObjectURL(this.objectUrl);
    this.objectUrl = null;
    this.audio.removeAttribute("src");
    this.audio.load();
  }
}
