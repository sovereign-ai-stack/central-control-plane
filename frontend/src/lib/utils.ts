import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function safeRandomUUID(): string {
  if (typeof window !== "undefined" && window.crypto && typeof window.crypto.randomUUID === "function") {
    try {
      return window.crypto.randomUUID();
    } catch {
      // Fallback if invocation fails
    }
  }
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    try {
      return crypto.randomUUID();
    } catch {
      // Fallback if invocation fails
    }
  }
  if (typeof crypto !== "undefined" && typeof crypto.getRandomValues === "function") {
    return ("" + 1e7 + -1e3 + -4e3 + -8e3 + -1e11).replace(/[018]/g, (c) =>
      (
        Number(c) ^
        (crypto.getRandomValues(new Uint8Array(1))[0] & (15 >> (Number(c) / 4)))
      ).toString(16)
    );
  }
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

export async function copyToClipboard(text: string): Promise<boolean> {
  if (!text) return false;
  // 1. Try standard navigator.clipboard API
  if (typeof navigator !== "undefined" && navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      // If permission denied or restricted context, fall through to textarea fallback
    }
  }

  // 2. Fallback using document.execCommand('copy') for HTTP / restricted environments
  if (typeof document !== "undefined") {
    try {
      const textArea = document.createElement("textarea");
      textArea.value = text;
      textArea.style.position = "fixed";
      textArea.style.left = "-9999px";
      textArea.style.top = "-9999px";
      textArea.style.opacity = "0";
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();
      const successful = document.execCommand("copy");
      document.body.removeChild(textArea);
      if (successful) return true;
    } catch {
      // Both approaches failed
    }
  }

  return false;
}
