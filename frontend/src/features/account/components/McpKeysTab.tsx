"use client";

import * as React from "react";
import { McpKeysSection } from "@/components/account/mcp-keys-section";
import type { Language, UsageLimits } from "@/lib/types";

interface McpKeysTabProps {
  language: Language;
  isOpen?: boolean;
  limits?: UsageLimits | null;
}

export function McpKeysTab({ language, isOpen = true, limits = null }: McpKeysTabProps) {
  return <McpKeysSection isOpen={isOpen} language={language} limits={limits} />;
}
