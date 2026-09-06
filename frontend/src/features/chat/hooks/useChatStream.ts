"use client";

import * as React from "react";
import type {
  Citation,
  FileAttachment,
  Language,
  Message,
  ProgressStage,
  StreamEvent,
  ToolCall,
  Workflow,
} from "@/lib/types";

export interface StreamState {
  isStreaming: boolean;
  streamingText: string;
  streamingThinkingText: string;
  streamingStage: ProgressStage | undefined;
  streamingLabel: string | undefined;
  streamingTools: ToolCall[];
  activeWorkflow: Workflow | null;
  activeRequestId: string | null;
}

export function useChatStream() {
  const [isStreaming, setIsStreaming] = React.useState(false);
  const [streamingText, setStreamingText] = React.useState("");
  const [streamingThinkingText, setStreamingThinkingText] = React.useState("");
  const [streamingStage, setStreamingStage] = React.useState<ProgressStage | undefined>(undefined);
  const [streamingLabel, setStreamingLabel] = React.useState<string | undefined>(undefined);
  const [streamingTools, setStreamingTools] = React.useState<ToolCall[]>([]);
  const [activeWorkflow, setActiveWorkflow] = React.useState<Workflow | null>(null);
  const [activeRequestId, setActiveRequestId] = React.useState<string | null>(null);

  const resetStream = React.useCallback(() => {
    setIsStreaming(false);
    setStreamingText("");
    setStreamingThinkingText("");
    setStreamingStage(undefined);
    setStreamingLabel(undefined);
    setStreamingTools([]);
    setActiveRequestId(null);
  }, []);

  return {
    isStreaming,
    setIsStreaming,
    streamingText,
    setStreamingText,
    streamingThinkingText,
    setStreamingThinkingText,
    streamingStage,
    setStreamingStage,
    streamingLabel,
    setStreamingLabel,
    streamingTools,
    setStreamingTools,
    activeWorkflow,
    setActiveWorkflow,
    activeRequestId,
    setActiveRequestId,
    resetStream,
  };
}
