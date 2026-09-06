import { describe, expect, it } from "vitest";
import { consumeVoiceStream } from "./voice-stream";

function encodeFrame(type: number, payload: Uint8Array): Uint8Array {
  const frame = new Uint8Array(5 + payload.byteLength);
  frame[0] = type;
  new DataView(frame.buffer).setUint32(1, payload.byteLength);
  frame.set(payload, 5);
  return frame;
}

function joinBytes(...chunks: Uint8Array[]): Uint8Array {
  const result = new Uint8Array(chunks.reduce((total, chunk) => total + chunk.byteLength, 0));
  let offset = 0;
  for (const chunk of chunks) {
    result.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return result;
}

describe("voice stream protocol", () => {
  it("parses frames split across network reads without base64 audio", async () => {
    const encoder = new TextEncoder();
    const started = encoder.encode(
      JSON.stringify({ phase: "started", transcription: "سلام", audio_mime_type: "audio/mpeg" }),
    );
    const complete = encoder.encode(
      JSON.stringify({
        phase: "complete",
        transcription: "سلام",
        response_text: "پاسخ صوتی",
        conversation_id: "conversation-1",
        user_message_id: "user-1",
        message_id: "assistant-1",
      }),
    );
    const audio = encoder.encode("raw-mp3-bytes");
    const body = joinBytes(
      encodeFrame(2, started),
      encodeFrame(1, audio.slice(0, 4)),
      encodeFrame(1, audio.slice(4)),
      encodeFrame(2, complete),
    );

    const response = new Response(
      new ReadableStream({
        start(controller) {
          controller.enqueue(body.slice(0, 7));
          controller.enqueue(body.slice(7, 19));
          controller.enqueue(body.slice(19));
          controller.close();
        },
      }),
      { headers: { "Content-Type": "application/x-sovereign-voice-stream" } },
    );
    const receivedAudio: Uint8Array[] = [];

    const metadata = await consumeVoiceStream(response, {
      onAudioChunk: (chunk) => {
        receivedAudio.push(chunk);
      },
    });

    expect(new TextDecoder().decode(joinBytes(...receivedAudio))).toBe("raw-mp3-bytes");
    expect(metadata.response_text).toBe("پاسخ صوتی");
    expect(metadata.message_id).toBe("assistant-1");
  });
});
